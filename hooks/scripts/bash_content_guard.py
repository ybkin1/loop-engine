#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bash_content_guard.py — PreToolUse hook: intercept dangerous Bash file operations.

Detects patterns that bypass Write/Edit hooks:
- echo "content" > file  (including no-space variant echo>file)
- echo "content" >> file (append redirect)
- cat > file / cat << EOF > file (heredoc redirect)
- cp source dest / mv source dest
- rm file / touch file (create/delete bypass)
- dd of=file / curl -o file / wget -O file
- git checkout -- file (revert bypass)
- Python inline writes / PowerShell Out-File / Set-Content

T-0082: Enhanced to close echo>file, cat>, dd, touch, curl, git checkout bypasses.

Exit: 0 = allow, 2 = block
"""

import json, logging, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import is_governance_project, load_config, project_root, read_stdin_json

EXIT_PASS = 0
EXIT_BLOCK = 2

# Dangerous write patterns — grouped by severity
DANGEROUS_PATTERNS = [
    # === Redirect writes (echo/printf/cat with > or >>) ===
    # Matches: echo>file, echo > file, echo "x">file, echo "x" > file
    (re.compile(r'(?:echo|printf|cat)[^|&;]*?>>?s*S+'), "redirect write (echo/printf/cat >)"),
    # Heredoc redirect: cat << EOF > file
    (re.compile(r'<<s*w+.*>>?s*S+'), "heredoc redirect"),

    # === File copy/move/remove/create ===
    (re.compile(r'cps+(?:-[a-zA-Z]+s+)?S+s+S+'), "cp command (file copy bypass)"),
    (re.compile(r'mvs+(?:-[a-zA-Z]+s+)?S+s+S+'), "mv command (file move bypass)"),
    (re.compile(r'rms+(?:-[a-zA-Z]*[rRf][a-zA-Z]*s+)?S+'), "rm command (file delete bypass)"),
    (re.compile(r'touchs+S+'), "touch command (file create bypass)"),

    # === Download to file ===
    (re.compile(r'(?:curl|wget).*?(?:-o|-O|--output)s+S+'), "download to file (curl/wget bypass)"),

    # === dd ===
    (re.compile(r'dd.*?of=S+'), "dd command (direct write bypass)"),

    # === Git revert (can undo changes outside hook control) ===
    (re.compile(r'gits+checkouts+--s+S+'), "git checkout (file revert bypass)"),
    (re.compile(r'gits+resets+--hard'), "git reset --hard (destructive revert)"),

    # === Python/Node inline writes ===
    (re.compile(r'pythond*.*?(?:-cs+|-S*cS*).*?(?:open|write)s*(', re.IGNORECASE), "Python inline file write"),
    (re.compile(r'nodes+(?:-e|--eval).*?(?:writeFile|createWriteStream)', re.IGNORECASE), "Node inline file write"),

    # === PowerShell writes ===
    (re.compile(r'(?:Out-File|Set-Content|Add-Content)', re.IGNORECASE), "PowerShell file write"),

    # === tee (writes to file AND stdout) ===
    (re.compile(r'tees+(?:-[a-zA-Z]+s+)?S+'), "tee command (file write bypass)"),

    # === sed -i (in-place edit bypasses Write hook) ===
    (re.compile(r'seds+(?:-[a-zA-Z]*i[a-zA-Z]*)s+'), "sed -i (in-place edit bypass)"),
]

# Paths exempt from bash guard (governance-only writes)
EXEMPT_DIRS = ['.ai/', '.git/', '__pycache__/', '.zcode/', 'node_modules/']

# Commands that are safe even if they match patterns (read-only operations)
SAFE_COMMAND_PATTERNS = [
    re.compile(r'echo.*?|s*(?:grep|head|tail|wc|sort)'),  # echo piped to read-only
    re.compile(r'gits+(?:status|log|diff|show|branch)'),       # git read-only
    re.compile(r'rms+-[rRf]s+(?:__pycache__|.pytest_cache)'), # cleanup dirs OK
]


def _is_exempt(command: str) -> bool:
    """Check if command targets exempt directories."""
    for d in EXEMPT_DIRS:
        if d in command:
            return True
    return False


def _is_safe(command: str) -> bool:
    """Check if a matching command is actually safe (read-only pattern)."""
    for pattern in SAFE_COMMAND_PATTERNS:
        if pattern.search(command):
            return True
    return False


def _extract_target_path(command: str) -> str | None:
    """Extract the likely target file path from a dangerous command."""
    # Try to find path after redirect operator
    m = re.search(r'>>?s*(S+)', command)
    if m:
        return m.group(1)
    # Try cp/mv target (last arg)
    m = re.search(r'(?:cp|mv)s+(?:-[a-zA-Z]+s+)?S+s+(S+)', command)
    if m:
        return m.group(1)
    # Try touch/rm target
    m = re.search(r'(?:touch|rm)s+(?:-[a-zA-Z]+s+)?(S+)', command)
    if m:
        return m.group(1)
    # Try curl/wget -o target
    m = re.search(r'(?:-o|--output)s+(S+)', command)
    if m:
        return m.group(1)
    # Try dd of=target
    m = re.search(r'of=(S+)', command)
    if m:
        return m.group(1)
    return None


def _is_in_project(target_path: str, project_root: str) -> bool:
    """Check if target path is within the project root."""
    if not target_path or not project_root:
        return False
    try:
        # Resolve the target path relative to project root
        resolved = str(Path(target_path).resolve())
        proj = str(Path(project_root).resolve())
        return resolved.startswith(proj + os.sep) or resolved == proj
    except Exception:
        return False


def main():
    try:
        hook_input = read_stdin_json()
    except Exception as _e:
        logger.warning("bash_content_guard fatal: %s", _e)
        return EXIT_PASS

    root = project_root()
    if not root or not is_governance_project(root):
        return EXIT_PASS

    config = load_config(root)
    bc = config.get("bash_content_guard", {})
    if not bc.get("enabled", True):
        return EXIT_PASS

    tool_name = str(hook_input.get("tool_name", ""))
    if tool_name != "Bash":
        return EXIT_PASS

    command = str(hook_input.get("tool_input", {}).get("command", ""))
    if not command:
        return EXIT_PASS

    if _is_exempt(command):
        return EXIT_PASS

    violations = []
    for pattern, desc in DANGEROUS_PATTERNS:
        if pattern.search(command):
            # Check if this specific match is actually safe
            if _is_safe(command):
                continue
            # Extract target and check if in project
            target = _extract_target_path(command)
            if target and not _is_in_project(target, root):
                continue  # Writing outside project — not our concern
            violations.append(f"{desc}: {command[:150]}")

    if violations:
        msg = "=== bash_content_guard: DANGEROUS FILE OPERATION ===" + "\n" + "\n".join(violations)
        logger.warning(msg)
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": msg}}))
        return EXIT_BLOCK

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
