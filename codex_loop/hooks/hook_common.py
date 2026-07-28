"""
hook_common.py — loop-governance 三个 ZCode hook 脚本的共享工具。

只依赖标准库 + 可选的 PyYAML；PyYAML 缺失时退化为保守的行扫描（fail-closed）。
所有函数对异常宽容：hook 脚本自己决定失败策略（fail-open / fail-closed），
共享层只负责如实返回或抛出让调用方捕获。
"""

import json
import logging
import os
import re
import shlex
import sys
from pathlib import Path


# Ensure codex_loop is importable when run as subprocess
_hook_root = Path(__file__).resolve().parent.parent.parent  # loop-engine-lab/
if str(_hook_root) not in sys.path:
    sys.path.insert(0, str(_hook_root))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING, format='[%(name)s] %(levelname)s: %(message)s')

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - 取决于运行环境
    yaml = None

SKILL_REL_DIR = Path(".zcode") / "skills" / "loop-governance"
STATE_REL = Path(".ai") / "state.yaml"
GATES_REL = Path(".ai") / "gates.yaml"

DEFAULT_CONFIG = {
    "hooks": {
        # fail_closed_on_error: 异常时阻断（true, 默认）还是放行（false, 仅调试用）
        "fail_closed_on_error": True,
    },
    "gate_guard": {
        "enabled": True,
        # closed: 状态文件不可读时阻断写入；open: 放行并在 stderr 警告
        "fail_on_state_error": "closed",
        # gate 状态异常（missing/rejected/blocked）时仍允许写入的治理文件路径
        # 防止 fail-closed 死锁：无法写 gates.yaml/state.yaml 修复状态
        "decision_recording_exempt": [".ai/gates.yaml", ".ai/state.yaml", ".ai/task_graph.yaml", ".ai/project_continuity.yaml"],
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


def should_fail_closed(root: Path) -> bool:
    """判断 Hook 内部异常时是否应 fail-closed（阻断）还是 fail-open（放行）。

    读取 config.yaml 中的 hooks.fail_closed_on_error：
    - true（默认）→ 打印完整 traceback 并返回 True（调用方应 EXIT_BLOCK）
    - false（仅调试用）→ 记录 warning 并返回 False（调用方应 EXIT_PASS）

    此函数必须在 except 块内调用，以便 traceback.format_exc() 能捕获异常信息。
    """
    import traceback
    tb_str = traceback.format_exc()
    cfg = load_config(root)
    hooks_cfg = cfg.get("hooks", {})
    fail_closed = hooks_cfg.get("fail_closed_on_error", True)

    if fail_closed:
        sys.stderr.write(f"[hook fail-closed] Unexpected error:\n{tb_str}\n")
        logger.warning("Hook fail-closed: blocking due to unexpected error")
        return True
    else:
        logger.warning(
            "Hook fail-open (DEBUG ONLY): unexpected error, passing through\n%s",
            tb_str,
        )
        return False


def is_path_safe(root: Path, target) -> bool:
    """检查目标路径是否在项目根目录内。

    返回 False：路径明确在项目根目录外（ValueError from relative_to）
    返回 True：路径在项目根目录内，或无法确定（保守放行，由上层决定）

    与 normalize_rel 不同：此函数专门区分"路径在外"与"无法解析"两种场景。
    """
    try:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = root / target_path
        target_path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        # 路径在项目根目录外
        return False
    except Exception:
        # 无法确定 → 保守返回 True，由上层逻辑继续判断
        return True



# ── Bash analysis — imported from _hook_bash ──

def load_tasks_for_context(root: Path) -> list[dict]:
    """从 task_graph.yaml 加载任务列表，格式适配 HardConstraints。

    返回 list[dict]，每个 dict 至少包含 'id' 和 'status' 字段。
    文件不存在或解析失败返回空列表。
    """
    task_graph_path = root / ".ai" / "task_graph.yaml"
    if not task_graph_path.exists():
        return []

    text = task_graph_path.read_text(encoding="utf-8")
    data = None

    if yaml is not None:
        try:
            data = yaml.safe_load(text) or {}
        except Exception:
            data = {}
    else:
        # 退化解析
        try:
            import re as _re
            data = {}
            lines = text.splitlines()
            current_task = None
            tasks = []
            for line in lines:
                stripped = line.strip()
                m = _re.match(r"^-\s+id:\s*(\S+)\s*$", stripped)
                if m:
                    if current_task:
                        tasks.append(current_task)
                    current_task = {"id": m.group(1).strip('"').strip("'")}
                    continue
                if current_task is not None:
                    m2 = _re.match(r"^\s{2,}(\S+):\s*(.*)$", line)
                    if m2:
                        current_task[m2.group(1)] = m2.group(2).strip().strip('"').strip("'")
            if current_task:
                tasks.append(current_task)
            data["tasks"] = tasks
        except Exception:
            return []

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        return []
    return [t for t in tasks if isinstance(t, dict)]


def load_gates_for_context(root: Path) -> dict:
    """从 gates.yaml 加载 gate 状态，格式适配 HardConstraints。

    返回 dict[str, str]，key 为 gate id，value 为 gate status 字符串。
    文件不存在或解析失败返回空字典。
    """
    gates_path = root / GATES_REL
    if not gates_path.exists():
        return {}

    text = gates_path.read_text(encoding="utf-8")

    gates: dict[str, str] = {}

    if yaml is not None:
        try:
            data = yaml.safe_load(text) or {}
        except Exception:
            data = {}
        gate_list = data.get("gates", [])
        if isinstance(gate_list, list):
            for gate in gate_list:
                if isinstance(gate, dict):
                    gate_id = gate.get("id", "")
                    gate_status = gate.get("status", "")
                    if gate_id:
                        gates[str(gate_id)] = str(gate_status)
        return gates

    # 退化解析
    try:
        import re as _re
        current_id = None
        for line in text.splitlines():
            m_id = _re.match(r"^\s*-?\s*id:\s*(\S+)\s*$", line)
            if m_id:
                current_id = m_id.group(1).strip('"').strip("'")
            s = _re.match(r"^\s*status:\s*(\S+)\s*(#.*)?$", line)
            if s and current_id:
                gates[current_id] = s.group(1).strip('"').strip("'")
    except Exception:
        return {}

    return gates


def load_gates_full(root: Path) -> dict:
    """Load full gate data including execution_status (v3.5).

    Returns dict[str, dict] with keys: status, execution_status, task_id.
    Use this when you need to distinguish in_progress from completed gates.
    """
    gates_path = root / GATES_REL
    if not gates_path.exists():
        return {}

    gates: dict[str, dict] = {}

    if yaml is not None:
        try:
            data = yaml.safe_load(gates_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
        gate_list = data.get("gates", [])
        if isinstance(gate_list, list):
            for gate in gate_list:
                if isinstance(gate, dict) and gate.get("id"):
                    gates[str(gate["id"])] = {
                        "status": str(gate.get("status", "")),
                        "execution_status": str(gate.get("execution_status", "")),
                        "task_id": str(gate.get("task_id", "")),
                    }
    return gates


def load_phase_gates_for_context(root: Path) -> dict:
    """从 gates.yaml 构建 phase_gates 映射，用于 C1/C2 检查。

    根据 gate 的 gate_type 字段映射到对应的 Phase：
    - requirements -> S1-requirements
    - architecture -> S2-architecture
    - 等等

    返回 dict[str, str]，key 为 phase 名称，value 为 gate status 字符串。
    """
    gates_path = root / GATES_REL
    if not gates_path.exists():
        return {}

    text = gates_path.read_text(encoding="utf-8")
    phase_gates: dict[str, str] = {}

    # gate_type -> Phase value mapping
    _GATE_TYPE_TO_PHASE: dict[str, str] = {
        "requirements": "S1-requirements",
        "architecture": "S2-architecture",
        "interface": "S3-interface",
        "implementation": "S4-implementation",
        "quality": "S5-quality",
        "delivery": "S6-delivery",
        "integration": "S7-integration",
        "functional_test": "S8-functional-test",
        "fix_optimize": "S9-fix-optimize",
        "performance": "S10-performance",
        "maintenance": "S11-maintenance",
    }

    if yaml is not None:
        try:
            data = yaml.safe_load(text) or {}
        except Exception:
            data = {}
        gate_list = data.get("gates", [])
        if isinstance(gate_list, list):
            for gate in gate_list:
                if isinstance(gate, dict):
                    gate_type = str(gate.get("gate_type", "")).lower()
                    gate_status = str(gate.get("status", ""))
                    if gate_type in _GATE_TYPE_TO_PHASE and gate_status:
                        phase_key = _GATE_TYPE_TO_PHASE[gate_type]
                        # Use the most restrictive status if multiple gates for same phase
                        existing = phase_gates.get(phase_key)
                        if existing is None or gate_status == "blocked":
                            phase_gates[phase_key] = gate_status
        return phase_gates

    # 退化解析
    try:
        import re as _re
        current_gate: dict[str, str] = {}
        for line in text.splitlines():
            m_id = _re.match(r"^\s*-?\s*id:\s*(\S+)\s*$", line)
            if m_id:
                if current_gate:
                    gt = current_gate.get("gate_type", "").lower()
                    gs = current_gate.get("status", "")
                    if gt in _GATE_TYPE_TO_PHASE and gs:
                        phase_key = _GATE_TYPE_TO_PHASE[gt]
                        existing = phase_gates.get(phase_key)
                        if existing is None or gs == "blocked":
                            phase_gates[phase_key] = gs
                current_gate = {}
                continue
            if current_gate is not None:
                m_field = _re.match(r"^\s{2,}(\S+):\s*(.*)$", line)
                if m_field:
                    current_gate[m_field.group(1)] = m_field.group(2).strip().strip('"').strip("'")
        if current_gate:
            gt = current_gate.get("gate_type", "").lower()
            gs = current_gate.get("status", "")
            if gt in _GATE_TYPE_TO_PHASE and gs:
                phase_key = _GATE_TYPE_TO_PHASE[gt]
                existing = phase_gates.get(phase_key)
                if existing is None or gs == "blocked":
                    phase_gates[phase_key] = gs
    except Exception:
        return {}

    return phase_gates


def try_import_hard_constraints() -> tuple[type | None, type | None]:
    """尝试导入 HardConstraints 和 Severity。

    返回 (HardConstraints, Severity) 元组；导入失败则返回 (None, None)。
    """
    try:
        from codex_loop.core.hard_constraints import HardConstraints, Severity  # noqa: F811
        return HardConstraints, Severity
    except ImportError:
        return None, None


# ═══════════════════════════════════════════════════════════════════════
# 自愈同步：本地 hooks/scripts/*.py → 插件缓存
# ═══════════════════════════════════════════════════════════════════════


def auto_sync_to_plugin_cache(project_root_path: Path) -> bool:
    """将项目本地 hooks/scripts/ 下的 .py 文件同步到插件缓存。

    本地文件与缓存不一致时执行同步。同步后清除两个目录的 __pycache__。
    返回 True 表示执行了同步操作（需要外部重启 ZCode 生效）。

    设计原则：
    - 只从项目 → 缓存单向同步（项目是真相源）
    - Hash 相同时不触发（避免无意义的 __pycache__ 清理）
    - 异常时静默失败（不阻断 hook 主流程）
    """
    import hashlib
    import shutil

    # 当前脚本所在目录 = 插件缓存中的 hooks/scripts/
    current_dir = Path(__file__).resolve().parent

    # 项目本地 hooks/scripts/
    local_scripts = project_root_path / "hooks" / "scripts"
    # 项目本地 hooks/（含 hooks.json）
    local_hooks_dir = project_root_path / "hooks"
    # 插件缓存 hooks/（当前 scripts/ 的父目录）
    cache_hooks_dir = current_dir.parent

    if not local_scripts.is_dir():
        return False

    synced = False

    # ── 同步 hooks/scripts/*.py ──
    for py_file in sorted(local_scripts.glob("*.py")):
        cache_copy = current_dir / py_file.name
        if not cache_copy.exists():
            continue

        try:
            local_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
            cache_hash = hashlib.sha256(cache_copy.read_bytes()).hexdigest()
        except OSError:
            continue

        if local_hash != cache_hash:
            try:
                shutil.copy2(str(py_file), str(cache_copy))
                logger.warning(
                    "[auto-sync] %s → plugin cache (SHA256 changed)", py_file.name
                )
                synced = True
            except OSError as e:
                logger.warning("[auto-sync] FAILED to copy %s: %s", py_file.name, e)

    # ── 同步 hooks/*.json（如 hooks.json）──
    for json_file in sorted(local_hooks_dir.glob("*.json")):
        cache_copy = cache_hooks_dir / json_file.name
        if not cache_copy.exists():
            continue

        try:
            local_hash = hashlib.sha256(json_file.read_bytes()).hexdigest()
            cache_hash = hashlib.sha256(cache_copy.read_bytes()).hexdigest()
        except OSError:
            continue

        if local_hash != cache_hash:
            try:
                shutil.copy2(str(json_file), str(cache_copy))
                logger.warning(
                    "[auto-sync] %s → plugin cache (SHA256 changed)", json_file.name
                )
                synced = True
            except OSError as e:
                logger.warning("[auto-sync] FAILED to copy %s: %s", json_file.name, e)

    if synced:
        # 清除两个目录的 __pycache__
        for d in (current_dir, local_scripts):
            pycache = d / "__pycache__"
            if pycache.is_dir():
                try:
                    shutil.rmtree(str(pycache), ignore_errors=True)
                except OSError:
                    pass
        logger.warning(
            "[auto-sync] %d file(s) synced & __pycache__ cleared. "
            "Restart ZCode session for changes to take effect.",
            sum(1 for _ in local_scripts.glob("*.py")
                if (current_dir / _.name).exists()),
        )

    return synced


# ── v3.3 Module split: re-export from specialized modules ─────────────
# The functions above remain for backward compatibility. New code should
# import directly from the specialized modules:
#   _hook_bash.py  — Bash command tokenization and analysis
#   _hook_state.py — Governance state file reading
#   _hook_path.py  — Path extraction, normalization, validation
#   _hook_config.py — Configuration loading and fail-closed policy
#   _hook_sync.py  — Plugin cache synchronization

try:
    from _hook_state import (  # noqa: E402, F401
        load_state as _load_state_v2,
        pending_gates as _pending_gates_v2,
        load_tasks_for_context as _load_tasks_v2,
        load_gates_for_context as _load_gates_v2,
        load_phase_gates_for_context as _load_phase_gates_v2,
    )
    _SPLIT_STATE_AVAILABLE = True
except ImportError:
    _SPLIT_STATE_AVAILABLE = False

try:
    from _hook_path import (  # noqa: E402, F401
        extract_target_path as _extract_target_path_v2,
        normalize_rel as _normalize_rel_v2,
        matches_protected as _matches_protected_v2,
        is_path_safe as _is_path_safe_v2,
    )
    _SPLIT_PATH_AVAILABLE = True
except ImportError:
    _SPLIT_PATH_AVAILABLE = False

try:
    from _hook_config import (  # noqa: E402, F401
        DEFAULT_CONFIG as _DEFAULT_CONFIG_V2,
        load_config as _load_config_v2,
        should_fail_closed as _should_fail_closed_v2,
    )
    _SPLIT_CONFIG_AVAILABLE = True
except ImportError:
    _SPLIT_CONFIG_AVAILABLE = False

try:
    from _hook_sync import (  # noqa: E402, F401
        auto_sync_to_plugin_cache as _auto_sync_v2,
    )
    _SPLIT_SYNC_AVAILABLE = True
except ImportError:
    _SPLIT_SYNC_AVAILABLE = False
