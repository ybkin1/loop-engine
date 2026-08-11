#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""bash_content_guard.py — PreToolUse hook: intercept dangerous Bash file operations.

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
T-0082 Phase 4: repaired corrupted regex escapes (0x08 backspace bytes and
stripped backslashes from every \s/\S/\d) that made every pattern dead and
the module crash with re.error at import time. All patterns rewritten from
the intended 10-pattern list and re-verified with re.compile at import.
Also fixed the crash in main(): project_root() requires hook_input.

Exit: 0 = allow, 2 = block
"""

import json, logging, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import (
    EXIT_PASS, EXIT_BLOCK,
    is_governance_project, load_config, project_root, read_stdin_json,
)


# Dangerous write patterns — grouped by severity
# T-0082 Phase 4: rebuilt with correct escapes (previously every `\b` was a
# literal 0x08 backspace byte and every `\s`/`\S`/`\d` had lost its backslash,
# so no pattern could ever match and the module raised re.error on import).
DANGEROUS_PATTERNS = [
    # 1. Redirect writes (echo/printf/cat with > or >>)
    # Matches: echo>file, echo > file, echo "x">file, echo "x" > file,
    #          cat << EOF > file (heredoc redirects contain no |&; before the >)
    (re.compile(r'(?:echo|printf|cat)\s+[^|&;]*?>>?\s*\S+'), "redirect write (echo/printf/cat >)"),

    # 2. File copy/move/remove/create
    (re.compile(r'(?:^|\s|;|&)(?:cp|mv|rm|touch)\s+'), "cp/mv/rm/touch file op (copy/move/delete/create bypass)"),

    # 3. dd raw write
    (re.compile(r'(?:^|\s|;|&)dd\s+'), "dd command (direct write bypass)"),

    # 4. curl/wget -o download-write
    (re.compile(r'(?:curl|wget)\s+.*?-\s*[oO]\s*\S+'), "download to file (curl/wget bypass)"),

    # 5. Git destructive revert (can undo changes outside hook control)
    (re.compile(r'git\s+(?:checkout\s+--|reset\s+--hard|clean)'), "git checkout --/reset --hard/clean (destructive revert)"),

    # 6. tee write (writes to file AND stdout)
    (re.compile(r'(?:^|\s|;|&)tee\s+'), "tee command (file write bypass)"),

    # 7. sed -i in-place edit (bypasses Write hook)
    (re.compile(r'sed\s+-i'), "sed -i (in-place edit bypass)"),

    # 8. Python/Node inline writes (open(), writeFileSync, writeFile)
    (re.compile(r'(?:python|python3|node)\s+.*?(?:open\(|writeFileSync|writeFile)', re.IGNORECASE), "python/node inline file write"),

    # 9. PowerShell writes
    (re.compile(r'(?:Set-Content|Out-File|Add-Content)', re.IGNORECASE), "PowerShell file write"),

    # 10. Archive extraction (tar -x / unzip / 7z x)
    (re.compile(r'(?:tar\s+.*?-x|unzip|7z\s+x)'), "archive extraction (tar/unzip/7z)"),

    # 11. Generic heredoc redirect (e.g. python - <<EOF > file)
    (re.compile(r'<<\s*\w+.*>>?\s*\S+'), "heredoc redirect"),
]

# Paths exempt from bash guard (governance-only writes)
EXEMPT_DIRS = ['.ai/', '.git/', '__pycache__/', '.zcode/', 'node_modules/']

# Commands that are safe even if they match patterns (read-only operations)
SAFE_COMMAND_PATTERNS = [
    re.compile(r'\becho\b.*?\|\s*(?:grep|head|tail|wc|sort)\b'),  # echo piped to read-only
    re.compile(r'\bgit\s+(?:status|log|diff|show|branch)\b'),       # git read-only
    re.compile(r'\brm\s+-[rRf]\s+(?:__pycache__|\.pytest_cache)\b'), # cleanup dirs OK
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
    m = re.search(r'>>?\s*(\S+)', command)
    if m:
        return m.group(1)
    # Try cp/mv target (last arg)
    m = re.search(r'\b(?:cp|mv)\s+(?:-[a-zA-Z]+\s+)?\S+\s+(\S+)', command)
    if m:
        return m.group(1)
    # Try touch/rm target
    m = re.search(r'\b(?:touch|rm)\s+(?:-[a-zA-Z]+\s+)?(\S+)', command)
    if m:
        return m.group(1)
    # Try curl/wget -o/-O target
    m = re.search(r'(?:-\s*[oO]|--output)\s*(\S+)', command)
    if m:
        return m.group(1)
    # Try dd of=target
    m = re.search(r'\bof=(\S+)', command)
    if m:
        return m.group(1)
    return None


def _is_in_project(target_path: str, project_root: str) -> bool:
    """Check if target path is within the project root."""
    if not target_path or not project_root:
        return False
    try:
        # Resolve the target path relative to the project root (not the hook's
        # process CWD — the hook may run from anywhere).
        target = Path(target_path)
        if not target.is_absolute():
            target = Path(project_root) / target
        resolved = str(target.resolve())
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

    root = project_root(hook_input)
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
