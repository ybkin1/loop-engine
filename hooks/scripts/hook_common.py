#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hook_common.py — loop-governance 三个 ZCode hook 脚本的共享工具。

只依赖标准库 + 可选的 PyYAML；PyYAML 缺失时退化为保守的行扫描（fail-closed）。
所有函数对异常宽容：hook 脚本自己决定失败策略（fail-open / fail-closed），
共享层只负责如实返回或抛出让调用方捕获。
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - 取决于运行环境
    yaml = None

SKILL_REL_DIR = Path(".zcode") / "skills" / "loop-governance"
STATE_REL = Path(".ai") / "state.yaml"
GATES_REL = Path(".ai") / "gates.yaml"

DEFAULT_CONFIG = {
    "gate_guard": {
        "enabled": True,
        # closed: 状态文件不可读时阻断写入；open: 放行并在 stderr 警告
        "fail_on_state_error": "closed",
        # pending gate 期间仍允许写入的路径（决策记录豁免，见 references/decision-rules.md）
        "decision_recording_exempt": [".ai/gates.yaml"],
    },
    "path_guard": {
        "enabled": True,
        # ask: 返回 permissionDecision=ask 由用户交互确认；deny: 直接 exit 2 阻断
        "decision": "ask",
        "protected_paths": [
            "AGENTS.md",
            "stable/",
            "registry/",
            ".zcode/config.json",
            ".zcode/tools/",
        ],
    },
    "session_brief": {
        "enabled": True,
        "max_pending_listed": 10,
    },
}


def read_stdin_json():
    """读取 hook 的标准输入 JSON；任何失败都返回空 dict。"""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def project_root(hook_input):
    """按 ZCODE_PROJECT_DIR → CLAUDE_PROJECT_DIR → 输入 cwd → 进程 cwd 解析项目根。"""
    for env_key in ("ZCODE_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(env_key)
        if value:
            return Path(value)
    cwd = hook_input.get("cwd")
    if cwd:
        return Path(cwd)
    return Path.cwd()


def is_governance_project(root):
    """只有存在 .ai/state.yaml 的目录才视为 Loop 治理项目，否则 hook 一律放行。"""
    return (root / STATE_REL).exists()


def _merge(defaults, override):
    """一层深合并：override 中缺失的键保留默认值。"""
    merged = {}
    for key, default_value in defaults.items():
        value = override.get(key) if isinstance(override, dict) else None
        if isinstance(default_value, dict) and isinstance(value, dict):
            merged[key] = _merge(default_value, value)
        elif value is None:
            merged[key] = default_value
        else:
            merged[key] = value
    return merged


def load_config(root):
    """读取技能目录下的 config.yaml，与 DEFAULT_CONFIG 合并。读取失败返回默认值。"""
    cfg_path = root / SKILL_REL_DIR / "config.yaml"
    if yaml is None or not cfg_path.exists():
        return DEFAULT_CONFIG
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return DEFAULT_CONFIG
    return _merge(DEFAULT_CONFIG, data)


def load_state(root):
    """解析 .ai/state.yaml；失败抛异常由调用方处理。"""
    state_path = root / STATE_REL
    with open(state_path, "r", encoding="utf-8") as f:
        text = f.read()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # 退化解析：只取顶层 scalar 键
    state = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            value = m.group(2).strip().strip('"').strip("'")
            state[m.group(1)] = None if value in ("null", "~", "") else value
    return state


def _naive_pending_scan(text):
    """无 PyYAML 时的保守扫描：gates 列表中 id 后紧跟 status: pending 即计入。"""
    pending = []
    current_id = None
    for line in text.splitlines():
        m = re.match(r"^\s*-?\s*id:\s*(\S+)\s*$", line)
        if m:
            current_id = m.group(1).strip('"').strip("'")
        s = re.match(r"^\s*status:\s*pending\s*(#.*)?$", line)
        if s and current_id:
            pending.append(current_id)
    return pending


def pending_gates(root):
    """返回 gates.yaml 中 status == "pending" 的 gate id 列表。文件不存在返回空列表。"""
    gates_path = root / GATES_REL
    if not gates_path.exists():
        return []
    with open(gates_path, "r", encoding="utf-8") as f:
        text = f.read()
    if yaml is None:
        return _naive_pending_scan(text)
    data = yaml.safe_load(text) or {}
    gates = data.get("gates") or []
    pending = []
    for gate in gates:
        if isinstance(gate, dict) and gate.get("status") == "pending":
            pending.append(str(gate.get("id", "<unknown>")))
    return pending


def _extract_paths_from_bash_command(command: str):
    """从 Bash 命令字符串中提取可能的目标文件路径列表。

    只识别高置信度的写入/修改目标模式：
    - 输出重定向: > file, >> file, 2> file, &> file
    - 创建/修改命令: touch file..., mkdir dir..., cp ... dst, mv ... dst
    - 追加写入: tee file, tee -a file, cat > file
    - 不能解析时返回空列表（不臆断）。
    """
    if not command or not isinstance(command, str):
        return []

    paths = []

    # 1. 重定向运算符：cmd > file, cmd >> file, cmd 2> file, cmd &> file
    # 匹配模式：(>>|>|2>|&>|1>) 后跟可选空格，再跟路径
    redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])(?:>>|[12]?>|&>)\s*([^\s;|&<]+)'
    )
    for m in redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    # 2. touch 命令: touch file1 file2 ...
    touch_pattern = re.compile(
        r'(?:^|\s|[;|&])touch\s+(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in touch_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            # 拆分参数，过滤掉选项（以 - 开头）
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            for tok in tokens:
                if not tok.startswith('-') and not tok.startswith('/dev/'):
                    paths.append(tok.strip('"\''))

    # 3. mkdir 命令: mkdir dir1 dir2 ...
    mkdir_pattern = re.compile(
        r'(?:^|\s|[;|&])mkdir\s+(?:-p\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in mkdir_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            for tok in tokens:
                if not tok.startswith('-') and not tok.startswith('/dev/'):
                    paths.append(tok.strip('"\''))

    # 4. cp 命令: cp src... dst (最后一个参数是目标)
    cp_pattern = re.compile(
        r'(?:^|\s|[;|&])cp\s+(?:-[a-zA-Z]+\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in cp_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            # 过滤选项，最后一个是目标
            args = [t for t in tokens if not t.startswith('-')]
            if len(args) >= 2:
                dst = args[-1].strip('"\'')
                if not dst.startswith('/dev/'):
                    paths.append(dst)

    # 5. mv 命令: mv src... dst (最后一个参数是目标)
    mv_pattern = re.compile(
        r'(?:^|\s|[;|&])mv\s+(?:-[a-zA-Z]+\s+)?(.*?)(?:$|[;|&]{2}|[;|&](?!>))'
    )
    for m in mv_pattern.finditer(command):
        rest = m.group(1).strip()
        if rest:
            try:
                tokens = shlex.split(rest)
            except ValueError:
                tokens = rest.split()
            args = [t for t in tokens if not t.startswith('-')]
            if len(args) >= 2:
                dst = args[-1].strip('"\'')
                if not dst.startswith('/dev/'):
                    paths.append(dst)

    # 6. tee 命令: tee file, tee -a file
    tee_pattern = re.compile(
        r'(?:^|\s|[;|&])tee\s+(?:-a\s+)?([^\s;|&<]+)'
    )
    for m in tee_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('-') and not p.startswith('/dev/'):
            paths.append(p)

    # 7. cat > file (重定向写入)
    cat_redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])cat\s+.*?>\s*([^\s;|&]+)'
    )
    for m in cat_redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    # 8. 写入类: echo "..." > file, printf "..." > file
    write_redirect_pattern = re.compile(
        r'(?:^|\s|[;|&])(?:echo|printf)\s+.*?>>?\s*([^\s;|&]+)'
    )
    for m in write_redirect_pattern.finditer(command):
        p = m.group(1).strip('"\'')
        if p and not p.startswith('/dev/'):
            paths.append(p)

    return paths


def extract_target_path(hook_input):
    """从 PreToolUse 输入中提取被写文件路径；取不到返回 None。

    支持的工具输入格式：
    - Write/Edit: tool_input.file_path, tool_input.path
    - Bash:      tool_input.command (从命令字符串中解析目标路径)
    - Notebook:  tool_input.notebook_path
    """
    tool_input = hook_input.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None

    # 标准文件操作工具
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if value:
            return value

    # Bash 命令：从 command 字段提取路径
    command = tool_input.get("command")
    if command:
        paths = _extract_paths_from_bash_command(command)
        if paths:
            # 返回第一个解析出的路径（保守：hook 可对多条路径分别触发）
            return paths[0]

    return None


def normalize_rel(root, target):
    """把目标路径规范化为相对项目根的 posix 风格路径；在根之外返回 None。"""
    try:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = root / target_path
        rel = target_path.resolve().relative_to(root.resolve())
        return rel.as_posix()
    except Exception:
        return None


def matches_protected(rel_posix, protected_paths):
    """rel_posix 是否命中保护清单（目录前缀或精确文件）。返回命中的规则或 None。"""
    if rel_posix is None:
        return None
    for rule in protected_paths:
        rule = str(rule).replace("\\", "/").lstrip("./")
        if rule.endswith("/"):
            if rel_posix.startswith(rule):
                return rule
        elif rel_posix == rule:
            return rule
    return None
