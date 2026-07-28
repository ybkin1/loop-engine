"""
_hook_bash.py — Bash command tokenizer and write detection engine.

Extracted from hook_common.py to reduce module size (841→~700 lines).
Imported by hook_common.py; also usable standalone for new code.
"""
from __future__ import annotations

import re

# ══════════════════════════════════════════════════════════════════════════
# Command sets
# ══════════════════════════════════════════════════════════════════════════

_WRITE_CMDS: frozenset[str] = frozenset({
    "tee", "cp", "mv", "mkdir", "touch", "rm", "chmod", "chown",
    "dd", "install", "ln", "patch", "rsync", "scp",
    "tar", "unzip", "gunzip", "bunzip2", "openssl",
    "pip", "pip3", "npm", "yarn", "pnpm", "apt-get", "apt", "yum", "dnf",
    "brew", "choco", "cargo", "go", "curl", "wget",
    "sed", "perl", "awk", "git",
})

_GIT_WRITE: frozenset[str] = frozenset({
    "add", "commit", "push", "merge", "rebase", "reset", "rm", "mv",
    "checkout", "switch", "restore", "revert", "cherry-pick",
    "fetch", "pull", "clone", "clean", "gc", "stash",
    "filter-branch", "am", "apply", "bisect", "config", "submodule",
    "notes", "worktree",
})

_GIT_RO: frozenset[str] = frozenset({
    "status", "log", "diff", "show", "blame", "grep",
    "ls-files", "ls-tree", "ls-remote", "rev-parse", "rev-list",
    "describe", "name-rev", "shortlog", "reflog", "help", "version",
    "whatchanged", "cherry", "archive", "cat-file", "check-ignore",
    "check-ref-format",
    # branch/tag: readonly when listed without destructive flags
    # Handled in is_write_command via context check
})

_RO_CMDS: frozenset[str] = frozenset({
    "ls", "cat", "head", "tail", "less", "more", "file",
    "find", "grep", "egrep", "fgrep", "rg", "ag", "ack",
    "echo", "printf", "pwd", "whoami", "id", "hostname",
    "uname", "date", "env", "printenv", "which", "where",
    "type", "command", "stat", "du", "df", "wc", "sort",
    "uniq", "diff", "cmp", "cut", "tr", "od", "xxd", "strings",
    "readelf", "objdump",
})

# ══════════════════════════════════════════════════════════════════════════
# Tokenizer
# ══════════════════════════════════════════════════════════════════════════

def _flush_cmd(buf: list[str], cmds: list[str], is_first: bool) -> bool:
    if not buf:
        return False
    word = ''.join(buf); buf.clear()
    if not word or not is_first:
        return False
    if '/' in word:
        word = word.rsplit('/', 1)[-1]
    if '=' in word and word.split('=', 1)[0].isidentifier():
        return True
    if word in ('sudo', 'exec', 'command', 'nohup', 'time', 'nice', 'env'):
        return True
    cmds.append(word)
    return False


def shell_tokenize(command: str) -> list[str]:
    if not command or not isinstance(command, str): return []
    commands: list[str] = []; i, n = 0, len(command)
    current_word: list[str] = []; in_sq, in_dq = False, False; is_first = True
    while i < n:
        ch = command[i]
        if ch == "'" and not in_dq: in_sq = not in_sq; i += 1; continue
        if ch == '"' and not in_sq: in_dq = not in_dq; i += 1; continue
        if in_sq or in_dq: i += 1; continue
        if ch == '\\' and i + 1 < n: i += 2; continue
        if ch in (';', '|', '&'):
            _flush_cmd(current_word, commands, is_first)
            current_word = []; is_first = True
            if ch == '&' and i + 1 < n and command[i + 1] == '&': i += 1
            if ch == '|' and i + 1 < n and command[i + 1] == '|': i += 1
            i += 1; continue
        if ch in (' ', '\t', '\n'):
            if current_word and is_first:
                skipped = _flush_cmd(current_word, commands, is_first)
                is_first = True if skipped else False
            elif current_word: current_word = []
            i += 1; continue
        current_word.append(ch); i += 1
    _flush_cmd(current_word, commands, is_first)
    return commands

# ══════════════════════════════════════════════════════════════════════════
# Write detection
# ══════════════════════════════════════════════════════════════════════════

def is_write_command(word: str, full_cmd: str = "") -> bool:
    if not word or word in _RO_CMDS: return False
    if word not in _WRITE_CMDS: return False
    if word in ('curl', 'wget'):
        return bool(full_cmd and re.search(r'(?:^|\s)-[^-]*[oO]', full_cmd))
    if word == 'git' and full_cmd:
        m = re.search(r'\bgit\s+([a-z][a-z-]*)', full_cmd)
        if m:
            sub = m.group(1)
            # Special cases checked BEFORE set lookups
            if sub == 'stash' and re.search(r'\bstash\s+(list|show)\b', full_cmd):
                return False  # stash list/show = readonly
            if sub in ('branch', 'tag') and not re.search(r'\s-[dD]\b', full_cmd):
                return False  # branch/tag listing = readonly
            # Set-based checks
            if sub in _GIT_WRITE: return True
            if sub in _GIT_RO: return False
            return True  # Unknown → conservative
    if word in ('sed', 'perl', 'awk'):
        return bool(full_cmd and re.search(r'(?:^|\s)-[^-]*i', full_cmd))
    if word == 'tar':
        return bool(full_cmd and re.search(r'(?:^|\s)-[^-]*x', full_cmd))
    if word == 'openssl':
        return bool(full_cmd and 'enc' in full_cmd)
    if word in ('pip', 'pip3', 'npm', 'yarn', 'pnpm', 'apt-get', 'apt', 'yum', 'dnf', 'brew', 'choco', 'cargo', 'go'):
        if full_cmd and '--dry-run' in full_cmd: return False
        return bool(full_cmd and re.search(r'\b(install|add|remove|uninstall|update|upgrade|build|publish)\b', full_cmd)) if full_cmd else True
    return True


def has_write_operations(command: str) -> bool:
    if not command or not isinstance(command, str): return True
    if re.search(r'(?:^|\s|[;|&])(?:>>|[12]?>|&>)\s*[^\s;|&<]', command): return True
    if re.search(r'<<\s*\w+', command): return True
    if re.search(r'\bfind\b', command) and '-delete' in command: return True
    for w in shell_tokenize(command):
        if is_write_command(w, command): return True
    return False


def is_readonly_command(command: str) -> bool:
    if not command or not isinstance(command, str): return False
    cmd = command.strip()
    if not cmd: return False
    if has_write_operations(cmd): return False
    if re.search(r'(?:^|[\s;|&])(?:python[23]?(?:\.\d+)?)\s+-c\b', cmd): return False
    m = re.search(r'(?:^|[\s;|&])(?:python[23]?(?:\.\d+)?)\s+-m\s+(\S+)', cmd)
    if m:
        mod = m.group(1).lower().rstrip(";")
        if any(kw in mod for kw in ("pip","install","uninstall","upload","deploy","compile","migrate","generate","init","create","update","setup","wheel","twine","publish","venv","virtualenv","ensurepip","easy_install")): return False
        if mod == "build" and "--check" not in cmd: return False
    if re.search(r'(?:^|[\s;|&])npm\s+.*--dry-run\b', cmd): return True
    if re.search(r'(?:^|[\s;|&])yarn\s+.*--dry-run\b', cmd): return True
    if re.search(r'(?:^|[\s;|&])(?:python[23]?(?:\.\d+)?\s+-m\s+)?build\s.*--check\b', cmd): return True
    if re.search(r'(?:^|[\s;|&])(?:python[23]?(?:\.\d+)?\s+(?:-m\s+)?)?pytest\b', cmd): return True
    for w in shell_tokenize(cmd):
        if is_write_command(w, cmd): return False
    return True
