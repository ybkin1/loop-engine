#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hook_path.py — Path handling and validation utilities extracted from hook_common.py.

Functions for extracting target paths from hook input, normalizing paths,
checking protected paths, and path safety validation.
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Bash command sets (shared with _hook_bash.py) ────────────────────────

_WRITE_CMDS: set[str] = {
    "write", "edit", "create", "delete", "move", "rename", "copy",
    "bash", "shell", "run", "exec", "install", "uninstall",
    "git", "python", "python3", "pip", "npm", "yarn", "cargo",
}

_GIT_WRITE: set[str] = {
    "add", "commit", "push", "tag", "branch", "checkout", "merge", "rebase",
    "stash", "reset", "rm", "mv", "clean", "cherry-pick", "revert",
}

_GIT_RO: set[str] = {
    "status", "log", "diff", "show", "ls-files", "rev-parse", "config",
    "remote", "fetch", "describe", "blame",
}

_RO_CMDS: set[str] = {
    "ls", "dir", "cat", "type", "echo", "pwd", "cd", "head", "tail",
    "find", "grep", "wc", "sort", "uniq", "cut", "awk", "sed",
    "less", "more", "tree", "file", "stat", "which", "where", "whoami",
    "date", "env", "printenv", "df", "du", "free", "ps", "top",
    "python -c", "python3 -c", "node -e", "node -p",
}


def _extract_paths_from_bash_command(command: str) -> list[str]:
    """Extract file paths from a Bash/Win command string.

    Returns list of path-like substrings found in the command.
    Handles: absolute paths, relative paths with extensions,
    paths with --flag=value syntax, and quoted paths.
    """
    if not command or not isinstance(command, str):
        return []
    paths: list[str] = []
    # Match paths with extensions: *.py, *.md, *.yaml, *.json, *.toml, *.txt, *.cfg, *.ini, *.sh, *.bat, *.ps1, *.yml
    ext_pattern = re.compile(
        r'(?:^|\s|[=:;"\'\`])([^\s;`|&<>\"\'$(){}\[\]*?]+\.(?:py|md|ya?ml|json|toml|txt|cfg|ini|sh|bat|ps1|js|ts|css|html|xml|csv|env|lock|gitignore|dockerignore)(?:\s|$))',
        re.IGNORECASE,
    )
    for match in ext_pattern.finditer(command):
        p = match.group(1).strip().strip('"').strip("'")
        if p and len(p) > 2:
            paths.append(p)
    # Match paths starting with ./ or ../
    rel_pattern = re.compile(r'(?:^|\s)(\.{1,2}/[^\s;`|&<>]+)')
    for match in rel_pattern.finditer(command):
        paths.append(match.group(1))
    return paths


def extract_target_path(hook_input: dict) -> str | None:
    """Extract the target file path from a ZCode hook input dictionary.

    Handles Write (file_path), Edit (file_path), Bash (command analysis),
    and raw string input.
    """
    if not isinstance(hook_input, dict):
        return None
    # Direct file_path (Write, Edit tools)
    ti = hook_input.get("tool_input", {})
    if isinstance(ti, dict):
        fp = ti.get("file_path")
        if fp and isinstance(fp, str):
            return fp
    # Bash: analyze command for file paths
    command = ti.get("command", "") if isinstance(ti, dict) else ""
    if command and isinstance(command, str):
        paths = _extract_paths_from_bash_command(command)
        if paths:
            return paths[0]  # Primary target
    return None


def normalize_rel(root: Path, target) -> str | None:
    """Convert a target path to a relative POSIX path within root.

    Returns None if target is None or cannot be normalized relative to root.
    """
    if target is None:
        return None
    try:
        if os.path.isabs(target):
            p = Path(target).resolve()
        else:
            p = (root / target).resolve()
        rel = p.relative_to(root.resolve())
        return rel.as_posix()
    except (ValueError, OSError):
        return None


def matches_protected(rel_posix: str, protected_paths: list[str]) -> str | None:
    """Check if a relative POSIX path matches any protected path pattern.

    Returns the matching pattern or None.
    A protected path with trailing '/' matches as prefix (directory).
    """
    if not rel_posix or not protected_paths:
        return None
    for pattern in protected_paths:
        p = pattern.replace("\\", "/")
        if p.endswith("/"):
            if rel_posix == p[:-1] or rel_posix.startswith(p):
                return pattern
        elif rel_posix == p:
            return pattern
    return None


def is_path_safe(root: Path, target) -> bool:
    """Check whether a target path is safely within the project root.

    Returns True if the resolved path is inside project root, False otherwise.
    None targets are considered safe (no path to check).
    """
    if target is None:
        return True
    try:
        if os.path.isabs(target):
            resolved = Path(target).resolve()
        else:
            resolved = (root / target).resolve()
        root_resolved = root.resolve()
        # Check if resolved is under root
        try:
            resolved.relative_to(root_resolved)
            return True
        except ValueError:
            return False
    except (ValueError, OSError):
        return False
