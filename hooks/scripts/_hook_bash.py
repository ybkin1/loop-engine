"""
_hook_bash.py — Bash command tokenizer and write detection engine.

Extracted from hook_common.py to reduce module size (841→~700 lines).
Imported by hook_common.py; also usable standalone for new code.
"""
from __future__ import annotations
import re
import shlex
from typing import Any

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

# T-0082 Phase 4: interpreters/extractors/generators that can write files even
# without visible shell write operators (script execution, -e/-m, archive
# extraction, scaffolding, PowerShell cmdlets, Windows cmd built-ins).
# They are classified as write-capable (NOT readonly) unless a known-safe
# marker from _SAFE_MARKER_RE / _SAFE_HELP_WORD_RE is present.
# Note: deliberately NOT added to _WRITE_CMDS — that would make
# `python --version` look like a write command.
# T-0086-P1: extended with shell interpreters (sh/bash/dash/...) and
# php/ruby/perl — `sh script.sh`, `php -r '...'`, `ruby -e '...'` can all
# write arbitrary files, so they must be write-capable (fail-closed).
_SIDE_EFFECT_CAPABLE: tuple[str, ...] = (
    "sh", "bash", "dash", "ash", "zsh", "ksh", "csh", "tcsh", "fish",
    "php", "ruby", "perl",
    "python", "python3", "node", "npx", "7z", "xz", "gzip", "zstd",
    "rar", "powershell", "pwsh", "copy", "del", "move", "ren",
)

# Safe-invocation markers for interpreter commands.  Markers only exempt
# single-segment commands (no `;`/`|`/`&`/newline chains) — a "safe" snippet
# must not mask a second, arbitrary command (`python -c 'print' && sh -c ...`).
_SAFE_MARKER_RE = re.compile(r"(?:^|\s)(?:--version|-V|--help|-h)(?=\s|$)")
# `help` 作为独立词（`python --help` 形态），不匹配 `python help.py`（脚本名）。
_SAFE_HELP_WORD_RE = re.compile(r"(?:^|\s)help(?=\s|$)")
# python 专属的平凡 `-c "print"` 片段标记（仅 python 家族解释器适用）。
_PY_PRINT_MARKERS: tuple[str, ...] = ('-c "print', "-c 'print")

# Versioned interpreters (python2, python3.11, python.exe, ...) are
# side-effect capable too.
_PYTHON_RE = re.compile(r"python[23]?(?:\.\d+)?(?:\.exe)?")

# 命令前缀词（shell 内置/包装器）：实际执行的是其后的命令。
_SKIP_PREFIXES: frozenset[str] = frozenset({
    "sudo", "exec", "command", "nohup", "time", "nice", "env",
    "timeout", "watch",
})
# 前缀词后带取值选项（`sudo -u root bash`、`env -u NAME bash`、`nice -n 10 bash`）。
_SKIP_OPT_VALUE: frozenset[str] = frozenset({
    "-u", "-g", "-p", "-C", "-r", "-t", "-T", "-c", "-U", "-R", "-d", "-D",
    "-n",
})
# xargs 中带取值的选项（`xargs -n 1 cmd`、`xargs -I {} cmd`、`xargs -d '\n' cmd`）。
_XARGS_VALUE_OPTS: frozenset[str] = frozenset({
    "-a", "-d", "-E", "-I", "-i", "-L", "-n", "-P", "-s",
})

# ══════════════════════════════════════════════════════════════════════════
# Tokenizer
# ══════════════════════════════════════════════════════════════════════════

def _flush_cmd(buf: list[str], cmds: list[str], is_first: bool) -> bool:
    if not buf: return False
    word = ''.join(buf); buf.clear()
    if not word or not is_first: return False
    if '/' in word: word = word.rsplit('/', 1)[-1]
    if '=' in word and word.split('=', 1)[0].isidentifier(): return True
    if word in ('sudo', 'exec', 'command', 'nohup', 'time', 'nice', 'env'): return True
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
# Execution-form detection (T-0086-P1)
# ══════════════════════════════════════════════════════════════════════════

def _split_segments(command: str) -> list[str]:
    """按命令分隔符（; | & 与换行）切分命令段，引号感知。

    与 shell_tokenize 不同：保留段内全部内容（含参数），供
    first_command_word / _xargs_command 使用。
    """
    if not command or not isinstance(command, str):
        return []
    segs: list[str] = []
    buf: list[str] = []
    in_sq = in_dq = False
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif not in_sq and not in_dq and ch in ";|&\n":
            segs.append("".join(buf))
            buf = []
            if ch == "&" and i + 1 < n and command[i + 1] == "&":
                i += 1
            elif ch == "|" and i + 1 < n and command[i + 1] == "|":
                i += 1
            i += 1
            continue
        buf.append(ch)
        i += 1
    segs.append("".join(buf))
    return [s for s in segs if s.strip()]


def first_command_word(command: str) -> str:
    """返回首个命令段的可执行词（原始形态，含路径/前缀），取不到返回 ''。

    - 跳过 sudo/env/nice 等前缀词及其选项（`sudo -u root bash` → 'bash'）
    - `command -v NAME` 是查询形态 → 返回 ''（NAME 是参数，不是执行）
    - 与 shell_tokenize 不同：不做基名化，保留 `./x.sh`、`/abs/tool`
      的路径形态，用于识别直接脚本/二进制执行。
    """
    if not command or not isinstance(command, str):
        return ""
    seg = re.split(r"[;&|]", command, maxsplit=1)[0]
    words = re.findall(r'"([^"]*)"|\'([^\']*)\'|(\S+)', seg)
    opts = False
    last_skip = ""
    i = 0
    while i < len(words):
        w = (words[i][0] or words[i][1] or words[i][2]).strip()
        if not opts:
            if w in _SKIP_PREFIXES:
                opts = True
                last_skip = w
                i += 1
                continue
            return w
        # 前缀词之后：跳过选项及其取值
        if w == "--":
            i += 1
            continue
        if w.startswith("-") and w != "-":
            if last_skip == "command" and w in ("-v", "-V"):
                return ""  # `command -v NAME` 查询形态
            if w in _SKIP_OPT_VALUE and i + 1 < len(words):
                i += 2
            else:
                i += 1
            continue
        if last_skip == "timeout" and w.lstrip("-").isdigit():
            i += 1  # `timeout 5 cmd`
            continue
        return w
    return ""


def _xargs_command(seg: str) -> str:
    """xargs 段中实际被执行的命令：xargs 之后的首个非选项参数。

    例：`xargs -0 rm` → 'rm'；`find | xargs grep` → 'grep'；
    无命令（`xargs` 裸用，默认 /bin/echo）→ ''。
    """
    try:
        words = shlex.split(seg)
    except ValueError:
        words = seg.split()
    i = 0
    while i < len(words) and words[i] != "xargs":
        i += 1
    i += 1
    while i < len(words):
        w = words[i]
        if w == "--":
            i += 1
            continue
        if w.startswith("-") and w != "-":
            if w in _XARGS_VALUE_OPTS and i + 1 < len(words):
                i += 2
            else:
                i += 1
            continue
        return w
    return ""


def _has_safe_marker(cmd: str, allow_py_print: bool = False) -> bool:
    """命令是否含已知安全标记（版本/帮助类）。

    allow_py_print：仅 python 家族解释器允许 `-c "print"` 平凡片段标记。
    """
    if _SAFE_MARKER_RE.search(cmd) or _SAFE_HELP_WORD_RE.search(cmd):
        return True
    if allow_py_print and any(m in cmd for m in _PY_PRINT_MARKERS):
        return True
    return False


def is_execution_command(command: str) -> bool:
    """命令的首个可执行词是否为"执行形态"（T-0086-P1）。

    解释器（sh/bash/python/php/ruby/perl/node/...）或直接路径/脚本执行
    （./x.sh、/abs/tool、. x、source x）的副作用未知——脚本内部可写
    任意文件。调用方应 fail-closed 视为写能力。

    注意：与 is_readonly_command 的 safe-marker 豁免无关（例如
    `python --version` 是执行形态但 is_readonly_command 仍为 True）。
    """
    if not command or not isinstance(command, str):
        return False
    fw = first_command_word(command)
    if not fw:
        return False
    if fw in _SIDE_EFFECT_CAPABLE or bool(_PYTHON_RE.fullmatch(fw)):
        return True
    if "/" in fw or "\\" in fw or fw in (".", "source"):
        return True
    return False

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

    # T-0082 Phase 4: side-effect-capable commands (interpreters, extractors,
    # generators, PowerShell, cmd built-ins) are NOT readonly unless a known
    # safe marker is present (`--version`, `-V`, `help`, `--help`, `-h`,
    # or a python `-c "print"` snippet).  `python script.py`, `node -e ...`,
    # `7z x ...`, `npx create-app` can all write files — treat as writes.
    # T-0086-P1: extended to shell interpreters (sh/bash/dash/zsh/...) and
    # php/ruby/perl — `sh script.sh`, `php -r 'file_put_contents(...)'` etc.
    # are write-capable (fail-closed).  Safe markers only exempt single-segment
    # commands so `python -c 'print' && sh -c 'rm ...'` cannot slip through.
    tokens = shell_tokenize(cmd)
    if tokens:
        first = tokens[0]
        if first in _SIDE_EFFECT_CAPABLE or bool(_PYTHON_RE.fullmatch(first)):
            allow_py_print = bool(_PYTHON_RE.fullmatch(first))
            if len(_split_segments(cmd)) <= 1 and _has_safe_marker(
                    cmd, allow_py_print):
                return True  # known-safe invocation (e.g. `python --version`)
            return False

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

    # T-0086-P1: per-segment execution-form scan (fail-closed).  shell_tokenize
    # only emits segment-first words, so arguments like `which python` are not
    # affected; but `curl ... | bash`, `... | base64 -d | bash` and
    # `sudo -u root bash script.sh` are now correctly write-capable.
    for seg in _split_segments(cmd):
        fw = first_command_word(seg)
        if not fw:
            continue
        # 解释器执行形态 → 写能力（fail-closed）
        if fw in _SIDE_EFFECT_CAPABLE or bool(_PYTHON_RE.fullmatch(fw)):
            return False
        # 直接路径/脚本执行（./x.sh、/abs/tool、. x、source x）→ 写能力
        if "/" in fw or "\\" in fw or fw in (".", "source"):
            return False
        # xargs：实际执行的是紧随其后的首个非选项参数
        if fw == "xargs":
            xc = _xargs_command(seg)
            if xc and (xc in _SIDE_EFFECT_CAPABLE
                       or bool(_PYTHON_RE.fullmatch(xc))
                       or is_write_command(xc, seg)):
                return False
        if is_write_command(fw, cmd):
            return False

    # awk 可执行任意代码：system(...)、`print ... | "cmd"` 管道与
    # `"cmd" | getline` 均可写任意文件 → 判为写能力；纯 print 程序
    # （常见只读用法，含 `-F"|"` 分隔符）保持只读。
    if re.search(r"\bawk\b[^;|&]*\bsystem\s*\(", cmd, re.I):
        return False
    if re.search(r"\bawk\b[^;|&]*\bprint\w*\b[^;|&]*\|\s*\"", cmd):
        return False
    if re.search(r'\bawk\b[^;|&]*"[^"]*"\s*\|\s*getline\b', cmd):
        return False
    return True
