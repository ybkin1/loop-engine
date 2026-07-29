#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bash_content_guard.py — PreToolUse hook: intercept dangerous Bash file operations.

Detects patterns that bypass Write/Edit hooks:
- echo "content" > file
- cp source dest
- mv source dest  
- rm file
- PowerShell Out-File / Set-Content

Exit: 0 = allow, 2 = block
"""

import json, logging, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from hook_common import is_governance_project, load_config, project_root, read_stdin_json

EXIT_PASS = 0
EXIT_BLOCK = 2

# Dangerous write patterns in Bash commands
DANGEROUS_PATTERNS = [
    # echo/printf redirects
    (re.compile(r'\becho\b.*>\s*\S+'), "echo redirect (potential file write bypass)"),
    (re.compile(r'\bprintf\b.*>\s*\S+'), "printf redirect"),
    # cp/mv/rm
    (re.compile(r'\bcp\s+'), "cp command"),
    (re.compile(r'\bmv\s+'), "mv command"),
    (re.compile(r'\brm\s+-[rRf]'), "rm -rf command"),
    # Python inline writes
    (re.compile(r'python.*-c.*open\('), "Python inline file write"),
    # PowerShell writes
    (re.compile(r'Out-File|Set-Content'), "PowerShell file write"),
    # tee
    (re.compile(r'\btee\b'), "tee command (potential write bypass)"),
]

# Paths exempt from bash guard
EXEMPT_DIRS = ['.ai/', '.git/', '__pycache__/', '.zcode/', 'node_modules/']


def _is_exempt(command):
    for d in EXEMPT_DIRS:
        if d in command:
            return True
    return False


def main():
    try:
        hook_input = read_stdin_json()
    except Exception as _e:
        import logging; logging.getLogger("content_guard").warning("%s fatal: %s", "bash_content_guard", _e)
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
            violations.append(f"{desc}: {command[:120]}")

    if violations:
        msg = "=== bash_content_guard: 危险文件操作 ===\n" + "\n".join(violations)
        logger.warning(msg)
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": msg}}))
        return EXIT_BLOCK

    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
