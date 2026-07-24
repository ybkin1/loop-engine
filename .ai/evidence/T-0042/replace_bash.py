"""Clean replacement: Bash section → tokenizer-based implementation."""
path = r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts\hook_common.py'
lines = open(path, encoding='utf-8').readlines()

# Find start (line 394, 0-indexed 393) and end (line 707, 0-indexed 706)
# Replace lines 393-706 (0-indexed) with new code
bash_start = 393  # '# ── Bash 只读命令判断 ──'
bash_end = 706    # just before '# ── HardConstraints Integration Helpers ──'

new_code = r'''
# ── Shell Tokenizer ────────────────────────────────────────────────────
# v3.1: Replaces blind regex matching with proper quote/escape-aware
# command extraction. Eliminates false positives like \binstall\b
# matching URL paths and echo arguments.


def shell_tokenize(command: str) -> list[str]:
    """Extract actual command words from a shell command string.

    Handles quotes, escapes, command separators, sudo prefixes,
    variable assignments, and path prefixes.
    """
    if not command or not isinstance(command, str):
        return []
    commands: list[str] = []
    i, n = 0, len(command)
    current_word: list[str] = []
    in_sq, in_dq = False, False
    is_first = True
    while i < n:
        ch = command[i]
        if ch == "'" and not in_dq:
            in_sq = not in_sq; i += 1; continue
        if ch == '"' and not in_sq:
            in_dq = not in_dq; i += 1; continue
        if in_sq or in_dq:
            i += 1; continue
        if ch == '\\' and i + 1 < n:
            i += 2; continue
        if ch in (';', '|', '&'):
            _flush_cmd(current_word, commands, is_first)
            current_word = []; is_first = True
            if ch == '&' and i + 1 < n and command[i + 1] == '&': i += 1
            if ch == '|' and i + 1 < n and command[i + 1] == '|': i += 1
            i += 1; continue
        if ch in (' ', '\t', '\n'):
            if current_word and is_first:
                _flush_cmd(current_word, commands, is_first); is_first = False
            elif current_word: current_word = []
            i += 1; continue
        current_word.append(ch); i += 1
    _flush_cmd(current_word, commands, is_first)
    return commands


def _flush_cmd(buf: list[str], cmds: list[str], is_first: bool) -> None:
    if not buf: return
    word = ''.join(buf); buf.clear()
    if not word or not is_first: return
    if '/' in word: word = word.rsplit('/', 1)[-1]
    if '=' in word and word.split('=', 1)[0].isidentifier(): return
    if word in ('sudo', 'exec', 'command', 'nohup', 'time', 'nice', 'env'): return
    cmds.append(word)


# ── Write Command Detection ────────────────────────────────────────────

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
    "fetch", "pull", "clone", "branch", "tag", "stash", "clean", "gc",
    "filter-branch", "am", "apply", "bisect", "config", "submodule",
    "notes", "worktree",
})

_RO_CMDS: frozenset[str] = frozenset({
    "ls", "cat", "head", "tail", "less", "more", "file",
    "find", "grep", "egrep", "fgrep", "rg", "ag", "ack",
    "echo", "printf", "pwd", "whoami", "id", "hostname",
    "uname", "date", "env", "printenv", "which", "where",
    "type", "command", "stat", "du", "df", "wc", "sort",
    "uniq", "diff", "cmp", "cut", "tr", "od", "xxd", "strings",
    "readelf", "objdump", "git",
})


def is_write_command(word: str, full_cmd: str = "") -> bool:
    if not word or word in _RO_CMDS: return False
    if word not in _WRITE_CMDS: return False
    if word in ('curl', 'wget'):
        return bool(full_cmd and re.search(r'(?:^|\s)-[^-]*[oO]', full_cmd))
    if word == 'git' and full_cmd:
        m = re.search(r'\bgit\s+([a-z][a-z-]*)', full_cmd)
        return m.group(1) in _GIT_WRITE if m else False
    if word in ('sed', 'perl', 'awk'):
        return bool(full_cmd and re.search(r'(?:^|\s)-i\b', full_cmd))
    if word == 'tar':
        return bool(full_cmd and re.search(r'(?:^|\s)-x\b', full_cmd))
    if word == 'openssl':
        return bool(full_cmd and 'enc' in full_cmd)
    if word in ('pip', 'pip3', 'npm', 'yarn', 'pnpm', 'apt-get', 'apt', 'yum', 'dnf', 'brew', 'choco', 'cargo', 'go'):
        return bool(full_cmd and re.search(r'\b(install|add|remove|uninstall|update|upgrade|build|publish)\b', full_cmd)) if full_cmd else True
    return True


def has_write_operations(command: str) -> bool:
    """Check if command contains file write operations (v3.1 tokenizer-based)."""
    if not command or not isinstance(command, str): return True
    if re.search(r'(?:^|\s|[;|&])(?:>>|[12]?>|&>)\s*[^\s;|&<]', command): return True
    if re.search(r'<<\s*\w+', command): return True
    if re.search(r'\bfind\b', command) and '-delete' in command: return True
    for w in shell_tokenize(command):
        if is_write_command(w, command): return True
    return False


def is_readonly_command(command: str) -> bool:
    """Check if Bash command is read-only (v3.1 tokenizer-based)."""
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
    for w in shell_tokenize(cmd):
        if is_write_command(w, cmd): return False
    return True

'''

# Do the replacement
new_lines = lines[:bash_start] + [new_code] + lines[bash_end + 1:]
open(path, 'w', encoding='utf-8').write(''.join(new_lines))

# Verify
content = open(path, encoding='utf-8').read()
for func in ['shell_tokenize', 'is_write_command', 'has_write_operations', 'is_readonly_command']:
    count = content.count(f'def {func}')
    print(f'{func}: {count}')
print(f'Total lines: {len(content.splitlines())}')
