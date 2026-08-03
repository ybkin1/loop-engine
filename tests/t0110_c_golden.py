"""T-0110 批 C golden 语料捕获助手（hooks/scripts/loop_enforcement.py 拆分等价）。

本模块不被 pytest 直接收集（无 test_ 前缀），由两类消费者使用：
1. ``.ai/evidence/T-0110/golden/generate_golden_c.py`` —— 拆分前/后各跑一次，
   产出 golden-c-before.json / golden-c-after.json（逐字节 diff 证据）；
2. ``tests/test_t0110_batch_c.py`` —— 运行时重放语料，与 golden-c-before.json
   逐字节断言（sha256 对比）。

捕获范围（design-common-weakness.md §1.1 + 任务卡批 C 硬门槛 1）：
- hook 入口判定矩阵（子进程实跑 hook 脚本，stdin JSON + ZCODE_PROJECT_DIR）：
  PASS 放行（治理写入/任务范围内/编排/git 提交/只读治理引用/治理工具调用/
  白名单豁免/legacy fixture）、外部路径 BLOCK、任务范围外写入 BLOCK、
  loop 模式开关各态、MCP 白名单（拒绝/放行）、多门禁证据检查
  （S4 无门禁 / S5 / S6 / S7 / S8 回归 / S11）、自审阻断（B6）、
  runtime projection 各态（SETUP_INCOMPLETE / IDENTITY_REQUIRED /
  GOVERNANCE_CONTROLLER_ONLY）、EXTERNAL_READ 只读豁免、C11 max_files 计数；
- 关键函数直接调用：路径/命令判定辅助（_is_python_interpreter/_msys_to_windows/
  _split_command_segments/_is_governance_tool_segment/_is_safe_cd_segment/
  _is_safe_display_segment/_script_in_governance_dirs/_command_references_outside/
  is_governance_tool_command/is_in_task_scope/check_diff_scope（patch subprocess））、
  契约解析（load_task_contract/_task_mcp_allowed_tools/_parse_task_front_matter_legacy/
  _read_task_max_files）、gate 证据检查（check_quality_gate_evidence/
  check_delivery_gate_evidence/check_runtime_quality_gate/check_security_gate_evidence/
  check_slo_gate_evidence/check_second_failure_gate_evidence/
  check_phase_gate_enforcement/_check_phase_evidence_file/trace_review_evidence_isolation/
  _self_review_block_enabled/build_hard_constraints_context + C11 计数）、
  常量值 + dir() 全量快照（re-export 完整性基线）。

确定性保证：
- 全部输入为固定字面量/固定 fixture 文件；子进程环境显式弹出
  PYTEST_CURRENT_TEST（模拟真实主会话，is_legacy_synthetic_hook_fixture 不受
  捕获进程影响）；
- hook 输入一律使用真实临时路径；输出归一化：所有 fixture 根路径（正/反斜杠
  两种形态）→ ``<ROOT>``、ISO 时间戳（mtime 派生 created_at）→ ``<TS>``、
  反斜杠 → 正斜杠；stdout/stderr 按 (rc, stdout, stderr) 原样记录；
- 依赖磁盘文件哈希的输出（_snapshot_hook_file_shas 等）不捕获（拆分前后
  文件内容必然不同，属预期差异，由 AC-03 自愈实测单独验证行为）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "hooks" / "scripts"
PYTHON = sys.executable

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "hooks" / "scripts"))

import loop_enforcement as LE  # noqa: E402, N812
from t0110_b1_golden import (  # noqa: E402
    dump_json,  # noqa: F401 — re-export 供 generate_golden_c.py 使用
    module_dir_snapshot,
    to_jsonable,
    try_exc,
)

# ══════════════════════════════════════════════════════════════════════
# 归一化
# ══════════════════════════════════════════════════════════════════════

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?")

# hook 自家 logger 名（脚本态 __main__ / 模块态 loop_enforcement 及其拆分模块）
# 拆分后随函数迁移而变化的仅 logger 名前缀（logging.getLogger(__name__) 派生），
# 消息文本不变 → 归一化为统一标记 [HOOK_LOGGER]；loop_core.* 等外部 logger
# 名保持原样（拆分前后不变，继续参与逐字节断言）。
_HOOK_LOGGER_RE = re.compile(
    r"\[(?:__main__|loop_enforcement|loop_contract_parser|loop_command_utils"
    r"|gate_evidence_checks|loop_enforcement_constants)\] ")

_ALL_ROOTS: list[Path] = []


def _norm_text(text: str, root: Path) -> str:
    """stderr/stdout 归一化：root 路径（含 root.parent 形态）→ <ROOT>，
    时间戳 → <TS>、hook 自家 logger 前缀 → [HOOK_LOGGER]、\\ → /。"""
    out = text
    out = out.replace(str(root), "<ROOT>")
    out = out.replace(root.as_posix(), "<ROOT>")
    out = out.replace(str(root.parent), "<ROOT>")
    out = out.replace(root.parent.as_posix(), "<ROOT>")
    out = _TS_RE.sub("<TS>", out)
    out = _HOOK_LOGGER_RE.sub("[HOOK_LOGGER] ", out)
    out = out.replace("\\", "/")
    return out


def _to_jsonable_c(value: Any) -> Any:
    """扩展 to_jsonable：EvidenceEnvelope（硬约束 C8 信封，非 dataclass）
    按字段转 dict（phase 枚举取 .value）；module → __name__；
    其余走 t0110_b1_golden.to_jsonable。"""
    if isinstance(value, types.ModuleType):  # 模块对象（如 _import_loop_core_gate 返回值）
        return value.__name__
    if type(value).__name__ == "EvidenceEnvelope" and hasattr(value, "evidence_id"):
        return {
            "evidence_id": value.evidence_id,
            "content_hash": value.content_hash,
            "created_at": value.created_at,
            "expires_at": value.expires_at,
            "phase": value.phase.value if value.phase is not None else None,
        }
    if isinstance(value, (dict, list, tuple)):
        if isinstance(value, dict):
            return {str(k): _to_jsonable_c(v) for k, v in value.items()}
        return [_to_jsonable_c(v) for v in value]
    return to_jsonable(value)


def _norm_payload(value: Any) -> Any:
    """深度归一化：EvidenceEnvelope → dict、root 路径 → <ROOT>、
    时间戳 → <TS>、\\ → /。"""

    def _walk(v: Any) -> Any:
        v = _to_jsonable_c(v)
        if isinstance(v, str):
            for root in sorted(_ALL_ROOTS, key=lambda p: len(str(p)), reverse=True):
                v = v.replace(str(root), "<ROOT>")
                v = v.replace(root.as_posix(), "<ROOT>")
            v = _TS_RE.sub("<TS>", v)
            v = v.replace("\\", "/")
            return v
        if isinstance(v, dict):
            return {k: _walk(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_walk(x) for x in v]
        return v

    return _walk(value)


# ══════════════════════════════════════════════════════════════════════
# fixture 构建（与 tests/test_enforcement.py 同源，保证语料口径一致）
# ══════════════════════════════════════════════════════════════════════

GOVERNANCE_CONFIG_YAML = """\
# loop-governance behavior config (synthetic test fixture)
version: 1
gate_guard:
  enabled: true
  fail_on_state_error: closed
path_guard:
  enabled: true
  decision: ask
  protected_paths:
    - AGENTS.md
    - stable/
    - registry/
    - .zcode/config.json
    - .zcode/tools/
session_brief:
  enabled: true
  max_pending_listed: 10
"""

CONFIG_SELF_REVIEW_OPT_OUT = GOVERNANCE_CONFIG_YAML + """\
enforcement:
  self_review_block: false
"""

CONFIG_SLO_DISABLED = GOVERNANCE_CONFIG_YAML + """\
slo_gate:
  enabled: false
"""

STATE_FULL = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

STATE_FULL_NO_TASK = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
"""

STATE_STANDARD = """\
schema_version: 1
project_name: test-standard
current_phase: S4-implementation
loop_mode: STANDARD
current_task_id: T-0001
"""

STATE_LIGHTWEIGHT = """\
schema_version: 1
project_name: test-light
current_phase: S4-implementation
loop_mode: LIGHTWEIGHT
"""


def _state(phase: str, task: str | None = "T-0001") -> str:
    lines = [
        "schema_version: 1",
        "project_name: test-phase",
        f"current_phase: {phase}",
        "loop_mode: FULL",
    ]
    if task:
        lines.append(f"current_task_id: {task}")
    return "\n".join(lines) + "\n"


TASK_IN_SCOPE = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""

TASK_MCP_ALLOW = """\
# Task T-0001: MCP allowlist
allowed_paths:
- src/
mcp_allowed_tools: [mcp__node_repl__js, mcp__foo__bar]
"""

TASK_MCP_TABLE = """\
# Task T-0001: MCP table form
allowed_paths:
- src/

| mcp_allowed_tools | mcp__node_repl__js |
"""

TASK_MAX_FILES_1 = """\
# Task T-0001: max_files=1
allowed_paths:
- src/
max_files: 1
"""

GATES_APPROVED = """\
schema_version: 1
gates:
- id: G-T-0001-REQUIREMENTS
  task_id: T-0001
  gate_type: requirements
  status: approved
- id: G-T-0001-ARCHITECTURE
  task_id: T-0001
  gate_type: architecture
  status: approved
"""

REVIEW_EVIDENCE = """\
{
  "task_id": "T-0001",
  "role": "independent-reviewer",
  "verdict": "PASS",
  "findings": [],
  "reviewer_session_id": "session-reviewer-001",
  "developer_session_id": "session-developer-001"
}
"""

SELF_REVIEW_EVIDENCE = """\
{
  "task_id": "T-0001",
  "role": "independent-reviewer",
  "verdict": "PASS",
  "findings": ["reviewed"],
  "reviewer_session_id": "session-dev-same-001",
  "developer_session_id": "session-dev-same-001"
}
"""

QUALITY_REPORT_PASS = """\
{
  "schema": "quality_report/v1",
  "role": "quality-engineer",
  "overall": "PASS",
  "checks": []
}
"""

SECURITY_AUDIT_PASS = """\
{
  "evidence_id": "EVID-security-audit-test",
  "type": "security_scan",
  "verdict": "PASS",
  "bindings": {"task_id": "T-0001", "phase": "S5-quality", "gate": "G-TEST"}
}
"""

RUNTIME_REPORT_PASS = """\
{"overall": "PASS", "blocked_by": [], "diagnoses": []}
"""

RELEASE_DECISION_GO = """\
{"decision": "GO", "version": "v3.12.99"}
"""

INTEGRATION_REPORT_PASS = """\
{"schema": "integration_report/v1", "overall": "PASS"}
"""

REGRESSION_BASELINE = """\
{"schema": "regression_baseline/v1", "has_regressions": false, "checks": []}
"""


def make_project(root: Path, spec: dict) -> Path:
    """按 spec 构建受治理 fixture 项目。spec 键：
    state / task / gates / review_evidence / self_review_evidence /
    quality_report / security_audit / runtime_report / release_decision /
    integration_report / regression_baseline / config_variant /
    runtime_state / no_qg_config / extra（dict[relpath, content]）。
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    if not spec.get("no_qg_config"):
        qg = root / ".zcode" / "skills" / "loop-governance"
        qg.mkdir(parents=True, exist_ok=True)
        variant = spec.get("config_variant", "default")
        if variant == "self_review_opt_out":
            (qg / "config.yaml").write_text(CONFIG_SELF_REVIEW_OPT_OUT, encoding="utf-8")
        elif variant == "slo_disabled":
            (qg / "config.yaml").write_text(CONFIG_SLO_DISABLED, encoding="utf-8")
        else:
            (qg / "config.yaml").write_text(GOVERNANCE_CONFIG_YAML, encoding="utf-8")

    if spec.get("state"):
        (ai / "state.yaml").write_text(spec["state"], encoding="utf-8")
    if spec.get("task"):
        tasks = ai / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        (tasks / "T-0001.md").write_text(spec["task"], encoding="utf-8")
    if spec.get("gates"):
        (ai / "gates.yaml").write_text(spec["gates"], encoding="utf-8")
    if spec.get("review_evidence") or spec.get("self_review_evidence"):
        ev = ai / "evidence" / "T-0001"
        ev.mkdir(parents=True, exist_ok=True)
        content = spec.get("review_evidence") or spec.get("self_review_evidence")
        (ev / "review-evidence.json").write_text(content, encoding="utf-8")
    for key, rel in (
        ("quality_report", ".ai/evidence/quality/quality_report.json"),
        ("security_audit", ".ai/evidence/security/security_audit.json"),
        ("runtime_report", ".ai/evidence/quality/runtime_quality_report.json"),
        ("release_decision", ".ai/evidence/release/v3.12.99/release_decision.json"),
        ("integration_report", ".ai/evidence/T-0001/integration-report.json"),
        ("regression_baseline", ".ai/evidence/regression/baseline.json"),
    ):
        if spec.get(key):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(spec[key], encoding="utf-8")
    if spec.get("runtime_state") is not None:
        rt = root / ".ai" / "runtime"
        rt.mkdir(parents=True, exist_ok=True)
        (rt / "runtime-state.json").write_text(
            spec["runtime_state"], encoding="utf-8")
    for rel, content in (spec.get("extra") or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def _proj(tmp: Path, spec: dict) -> Path:
    root = make_project(Path(tempfile.mkdtemp(dir=str(tmp))), spec)
    _ALL_ROOTS.append(root)
    return root


def _write_input(file_path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


def _bash_input(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _read_input(file_path: str) -> dict:
    return {"tool_name": "Read", "tool_input": {"file_path": file_path}}


def _mcp_input(tool: str) -> dict:
    return {"tool_name": tool, "tool_input": {}}


def _run_hook(root: Path, hook_input: dict, env_extra: dict | None = None,
              pop_pytest: bool = True) -> dict:
    """子进程实跑 hook 脚本（同 ZCode 调用形态：进程 + stdin JSON + 环境变量）。"""
    env = dict(os.environ)
    if pop_pytest:
        env.pop("PYTEST_CURRENT_TEST", None)
    env["ZCODE_PROJECT_DIR"] = str(root)
    if env_extra:
        env.update(env_extra)
    payload = json.dumps(hook_input or {})
    r = subprocess.run(
        [PYTHON, str(SCRIPTS / "loop_enforcement.py")],
        input=payload, capture_output=True, text=True, env=env, timeout=60,
    )
    return {
        "rc": r.returncode,
        "stdout": _norm_text(r.stdout, root),
        "stderr": _norm_text(r.stderr, root),
    }


# ══════════════════════════════════════════════════════════════════════
# hook 入口判定矩阵（子进程实跑）
# ══════════════════════════════════════════════════════════════════════

def capture_hook_entry_matrix(tmp: Path) -> dict:
    """捕获 hook 入口判定矩阵（拆分前后逐字段一致）。

    每个场景：spec（fixture 构建参数）+ hook_input_builder（root → 输入 dict）。
    hook 输入一律用真实路径；输出在 _run_hook 内按该 root 归一化。
    """
    cases: dict[str, dict] = {}

    def add(name: str, spec: dict,
            input_builder: Callable[[Path], dict],
            env_extra: dict | None = None):
        root = _proj(tmp, spec)
        cases[name] = _run_hook(root, input_builder(root), env_extra=env_extra)

    # ── 非治理项目 / loop 模式开关 ──
    add("non_governance_project_write", {"state": None},
        lambda root: _write_input(str(root / "any.py")))
    add("lightweight_write_anywhere", {"state": STATE_LIGHTWEIGHT},
        lambda root: _write_input(str(root / "arbitrary" / "file.txt")))
    add("standard_no_task_blocks",
        {"state": STATE_STANDARD.replace("current_task_id: T-0001\n", "")},
        lambda root: _write_input(str(root / "src" / "main.py")))
    add("full_no_task_blocks_business_write", {"state": STATE_FULL_NO_TASK},
        lambda root: _write_input(str(root / "src" / "main.py")))

    # ── 治理文件豁免 ──
    for label, rel in (
        ("state_yaml", ".ai/state.yaml"),
        ("gates_yaml", ".ai/gates.yaml"),
        ("task_graph", ".ai/task_graph.yaml"),
        ("handoff", ".ai/HANDOFF.md"),
        ("evidence", ".ai/evidence/test.json"),
    ):
        add(f"governance_{label}_exempt", {"state": STATE_FULL_NO_TASK},
            lambda root, rel=rel: _write_input(str(root / rel)))

    # ── 任务范围 / 门禁（S4 基线：gates approved + independent review）──
    # 注：与测试套件同构，以下场景显式携带 legacy synthetic fixture 标记
    # （PYTEST_CURRENT_TEST=tests/test_enforcement.py::*）——真实测试进程在
    # pytest 下运行即继承该标记，hook 经"task scope only"路径给出判定；
    # 无标记的真实主会话形态（SETUP_INCOMPLETE 拦截）由
    # runtime_projection_missing_setup_incomplete 场景单独覆盖。
    legacy_env = {"PYTEST_CURRENT_TEST": "tests/test_enforcement.py::x"}
    gov_spec = {
        "state": STATE_FULL, "task": TASK_IN_SCOPE,
        "gates": GATES_APPROVED, "review_evidence": REVIEW_EVIDENCE,
    }
    add("full_task_in_scope_write_passes", gov_spec,
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("full_task_out_of_scope_write_blocks", gov_spec,
        lambda root: _write_input(str(root / "docs" / "readme.md")),
        env_extra=legacy_env)
    add("s4_no_baselines_blocks_c1c2c6",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s4_baselines_without_review_blocks_c6",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)

    # ── 外部路径（fail-closed）──
    add("write_outside_project_root_blocks", gov_spec,
        lambda root: _write_input(str(root.parent / "outside.txt")))

    # ── 只读豁免（EXTERNAL_READ）／只读治理引用 ──
    add("read_only_external_read_passes", gov_spec,
        lambda root: _read_input(str(root.parent / "plugin-cache" / "doc.md")))
    add("read_no_task_governance_metadata_passes", {"state": STATE_FULL_NO_TASK},
        lambda root: _read_input(str(root / ".ai" / "state.yaml")))
    add("read_no_task_business_file_blocks", {"state": STATE_FULL_NO_TASK},
        lambda root: _read_input(str(root / "src" / "main.py")))
    add("readonly_bash_no_task_gov_ref_passes", {"state": STATE_FULL_NO_TASK},
        lambda root: _bash_input("grep -r loop_mode .ai/state.yaml"))
    add("readonly_bash_no_task_exploration_blocks", {"state": STATE_FULL_NO_TASK},
        lambda root: _bash_input("grep -r TODO src/"))

    # ── 编排 / git 豁免 ──
    add("orchestration_agent_no_target_passes", {"state": STATE_FULL_NO_TASK},
        lambda root: {"tool_name": "Agent", "tool_input": {}})
    add("git_commit_exempt_with_task", gov_spec,
        lambda root: _bash_input("git add .ai/state.yaml && git commit -m 'wip'"))
    add("git_local_op_with_task_passes", gov_spec,
        lambda root: _bash_input("git status"))

    # ── MCP 白名单 ──
    add("mcp_no_task_blocks_dispatch_required", {"state": STATE_FULL_NO_TASK},
        lambda root: _mcp_input("mcp__node_repl__js"))
    add("mcp_not_in_allowlist_blocks",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE},
        lambda root: _mcp_input("mcp__node_repl__js"))
    add("mcp_in_allowlist_with_identity",
        {"state": STATE_FULL, "task": TASK_MCP_ALLOW, "runtime_state": "{}"},
        lambda root: {"tool_name": "mcp__node_repl__js",
                      "tool_input": {"actor_id": "actor-1", "caller_class": "main"}})

    # ── 治理工具调用（T-0086-P2/P3）──
    add("governance_tool_validate_state_passes", gov_spec,
        lambda root: _bash_input("python .zcode/tools/validate_state.py ."))
    add("governance_tool_compound_main_session_passes", gov_spec,
        lambda root: _bash_input(
            f"cd {root.as_posix()} && python .zcode/tools/validate_state.py . 2>&1 | tail -5"))
    add("governance_tool_compound_with_write_segment_blocks", gov_spec,
        lambda root: _bash_input("python .zcode/tools/validate_state.py . && rm -rf /tmp/x"))
    add("governance_tool_python_c_snippet_blocks", gov_spec,
        lambda root: _bash_input('python -c "print(1)"'))
    add("governance_tool_outside_target_blocks", gov_spec,
        lambda root: _bash_input("python .zcode/tools/validate_state.py > C:/Windows/Temp/evil.txt"))

    # ── 自审阻断（B6）──
    add("self_review_evidence_blocks",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED,
         "self_review_evidence": SELF_REVIEW_EVIDENCE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("self_review_opt_out_trace_only",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED,
         "self_review_evidence": SELF_REVIEW_EVIDENCE,
         "config_variant": "self_review_opt_out"},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)

    # ── 多门禁证据检查（S5/S7/S8/S11）──
    add("s5_quality_no_security_blocks",
        {"state": _state("S5-quality"), "task": TASK_IN_SCOPE,
         "quality_report": QUALITY_REPORT_PASS},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s5_quality_with_security_passes",
        {"state": _state("S5-quality"), "task": TASK_IN_SCOPE,
         "quality_report": QUALITY_REPORT_PASS,
         "security_audit": SECURITY_AUDIT_PASS},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s5_security_verdict_blocked_blocks",
        {"state": _state("S5-quality"), "task": TASK_IN_SCOPE,
         "quality_report": QUALITY_REPORT_PASS,
         "security_audit": SECURITY_AUDIT_PASS.replace('"PASS"', '"BLOCKED"')},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s7_no_evidence_blocks",
        {"state": _state("S7-integration"), "task": TASK_IN_SCOPE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s7_with_integration_report_passes",
        {"state": _state("S7-integration"), "task": TASK_IN_SCOPE,
         "integration_report": INTEGRATION_REPORT_PASS},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s8_regression_baseline_no_regression_passes",
        {"state": _state("S8-functional-test"), "task": TASK_IN_SCOPE,
         "regression_baseline": REGRESSION_BASELINE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s11_no_evidence_blocks",
        {"state": _state("S11-maintenance"), "task": TASK_IN_SCOPE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)

    # ── S6-delivery（SLO 数据不足 fail-closed / SLO 关闭放行）──
    s6_full = {
        "state": _state("S6-delivery"), "task": TASK_IN_SCOPE,
        "quality_report": QUALITY_REPORT_PASS,
        "security_audit": SECURITY_AUDIT_PASS,
        "runtime_report": RUNTIME_REPORT_PASS,
        "release_decision": RELEASE_DECISION_GO,
    }
    add("s6_slo_sources_missing_blocks", s6_full,
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)
    add("s6_slo_disabled_passes",
        {**s6_full, "config_variant": "slo_disabled"},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)

    # ── runtime projection 各态 ──
    add("runtime_projection_missing_setup_incomplete",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED,
         "review_evidence": REVIEW_EVIDENCE},
        lambda root: _write_input(str(root / "src" / "main.py")))
    add("runtime_projection_valid_identity_missing_blocks",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED,
         "review_evidence": REVIEW_EVIDENCE, "runtime_state": "{}"},
        lambda root: _write_input(str(root / "src" / "main.py")))
    add("runtime_projection_governance_write_controller_only_blocks",
        {"state": STATE_FULL_NO_TASK, "runtime_state": "{}"},
        lambda root: _write_input(str(root / ".ai" / "state.yaml")))
    add("runtime_projection_governance_recovery_controller_passes",
        {"state": STATE_FULL_NO_TASK, "runtime_state": "{}"},
        lambda root: {"tool_name": "Write", "tool_input": {
            "file_path": str(root / ".ai" / "state.yaml"),
            "recovery_mode": "GOVERNANCE_RECOVERY",
            "caller_class": "controller"}})

    # ── legacy synthetic fixture（PYTEST_CURRENT_TEST 标记）──
    add("legacy_synthetic_fixture_uses_task_scope",
        {"state": STATE_FULL, "task": TASK_IN_SCOPE, "gates": GATES_APPROVED,
         "review_evidence": REVIEW_EVIDENCE},
        lambda root: _write_input(str(root / "src" / "main.py")),
        env_extra=legacy_env)

    # ── C11 max_files 计数（同一 fixture 连续两次写入）──
    root = _proj(tmp, {"state": STATE_FULL, "task": TASK_MAX_FILES_1,
                       "gates": GATES_APPROVED, "review_evidence": REVIEW_EVIDENCE})
    cases["c11_first_write_passes"] = _run_hook(
        root, _write_input(str(root / "src" / "main.py")), env_extra=legacy_env)
    cases["c11_second_write_blocks_limit"] = _run_hook(
        root, _write_input(str(root / "src" / "main.py")), env_extra=legacy_env)

    return cases


# ══════════════════════════════════════════════════════════════════════
# 关键函数直接调用
# ══════════════════════════════════════════════════════════════════════

def capture_direct_calls(tmp: Path) -> dict:
    """捕获关键函数直接调用结果（try_exc 包裹，异常路径归一化）。"""
    out: dict[str, Any] = {}

    # ── 常量值 ──
    out["constants"] = {
        "EXIT_PASS": LE.EXIT_PASS,
        "EXIT_BLOCK": LE.EXIT_BLOCK,
        "_REEXEC_MAX": LE._REEXEC_MAX,
        "_REEXEC_PAYLOAD_ENV": LE._REEXEC_PAYLOAD_ENV,
        "_REEXEC_COUNT_ENV": LE._REEXEC_COUNT_ENV,
        "GOVERNANCE_EXEMPT": LE.GOVERNANCE_EXEMPT,
        "MINIMAL_METADATA_READ": LE.MINIMAL_METADATA_READ,
        "MAIN_THREAD_ALLOWED": LE.MAIN_THREAD_ALLOWED,
        "GOVERNANCE_TOOL_DIRS": list(LE.GOVERNANCE_TOOL_DIRS),
        "_AUTO_SYNC_AVAILABLE": LE._AUTO_SYNC_AVAILABLE,
        "_HARD_CONSTRAINTS_AVAILABLE": LE._HARD_CONSTRAINTS_AVAILABLE,
    }

    # ── 模式判定 ──
    for label, spec in (
        ("full", {"state": STATE_FULL}),
        ("standard", {"state": STATE_STANDARD}),
        ("lightweight", {"state": STATE_LIGHTWEIGHT}),
        ("unset", {"state": STATE_FULL.replace("loop_mode: FULL\n", "")}),
    ):
        root = _proj(tmp, spec)
        out[f"is_loop_mode_enforced_{label}"] = try_exc(LE.is_loop_mode_enforced, root)
    corrupt = _proj(tmp, {"state": None})
    (corrupt / ".ai" / "state.yaml").write_bytes(b"\x00\x01\x02not-yaml")
    out["is_loop_mode_enforced_corrupt_state_fail_closed"] = try_exc(
        LE.is_loop_mode_enforced, corrupt)

    old = os.environ.get("PYTEST_CURRENT_TEST")
    os.environ.pop("PYTEST_CURRENT_TEST", None)
    try:
        out["is_legacy_synthetic_hook_fixture_unset"] = try_exc(
            LE.is_legacy_synthetic_hook_fixture)
    finally:
        if old is None:
            os.environ.pop("PYTEST_CURRENT_TEST", None)
        else:
            os.environ["PYTEST_CURRENT_TEST"] = old
    os.environ["PYTEST_CURRENT_TEST"] = "tests/test_enforcement.py::x"
    try:
        out["is_legacy_synthetic_hook_fixture_marker"] = try_exc(
            LE.is_legacy_synthetic_hook_fixture)
    finally:
        if old is None:
            os.environ.pop("PYTEST_CURRENT_TEST", None)
        else:
            os.environ["PYTEST_CURRENT_TEST"] = old

    # ── 路径判定 ──
    for label, rel in (
        ("state_yaml", ".ai/state.yaml"),
        ("gates_yaml", ".ai/gates.yaml"),
        ("evidence_sub", ".ai/evidence/T-1/x.json"),
        ("tasks_sub", ".ai/tasks/T-1.md"),
        ("handoff", ".ai/HANDOFF.md"),
        ("business", "src/main.py"),
        ("zcode_config", ".zcode/config.json"),
        ("project_continuity", ".ai/project_continuity.yaml"),
        ("none", None),
    ):
        out[f"is_governance_write_{label}"] = try_exc(LE.is_governance_write, rel)
    for label, rel in (
        ("state_yaml", ".ai/state.yaml"),
        ("evidence_dir", ".ai/evidence/"),
        ("evidence_sub", ".ai/evidence/T-1/x.json"),
        ("tasks_dir", ".ai/tasks/"),
        ("agents_md", "AGENTS.md"),
        ("loop_core", "loop_core/"),
        ("business", "src/main.py"),
        ("business_sub", "docs/readme.md"),
    ):
        out[f"is_minimal_metadata_read_{label}"] = try_exc(LE.is_minimal_metadata_read, rel)
    contract = {"allowed_paths": ["src/", "./tests/", ".zcode/tools/"]}
    for label, rel in (
        ("src_exact", "src/main.py"),
        ("tests_dot_slash", "tests/x.py"),
        ("zcode_tools_dot", ".zcode/tools/t.py"),
        ("docs_out", "docs/a.md"),
        ("none", None),
    ):
        out[f"is_in_task_scope_{label}"] = try_exc(LE.is_in_task_scope, rel, contract)
    out["is_in_task_scope_no_contract"] = try_exc(LE.is_in_task_scope, "src/a.py", None)
    out["is_in_task_scope_empty_allowed"] = try_exc(
        LE.is_in_task_scope, "src/a.py", {"allowed_paths": []})

    # ── 契约解析 ──
    root_mcp = _proj(tmp, {"state": STATE_FULL, "task": TASK_MCP_ALLOW})
    root_table = _proj(tmp, {"state": STATE_FULL, "task": TASK_MCP_TABLE})
    root_plain = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE})
    root_empty = _proj(tmp, {"state": STATE_FULL})
    out["load_task_contract_inline"] = try_exc(LE.load_task_contract, root_mcp, "T-0001")
    out["load_task_contract_table"] = try_exc(LE.load_task_contract, root_table, "T-0001")
    out["load_task_contract_plain"] = try_exc(LE.load_task_contract, root_plain, "T-0001")
    out["load_task_contract_missing_file"] = try_exc(LE.load_task_contract, root_empty, "T-0001")
    out["task_mcp_allowed_tools_inline"] = try_exc(LE._task_mcp_allowed_tools, root_mcp, "T-0001")
    out["task_mcp_allowed_tools_table"] = try_exc(LE._task_mcp_allowed_tools, root_table, "T-0001")
    out["task_mcp_allowed_tools_none"] = try_exc(LE._task_mcp_allowed_tools, root_plain, "T-0001")
    out["task_mcp_allowed_tools_missing_file"] = try_exc(
        LE._task_mcp_allowed_tools, root_empty, "T-0001")
    for label, text in (
        ("inline", "mcp_allowed_tools: [mcp__a, mcp__b]\n"),
        ("list", "mcp_allowed_tools:\n- mcp__a\n- mcp__b\n"),
        ("table", "| mcp_allowed_tools | mcp__a |\n"),
        ("allowed_actions", "allowed_actions:\n- src/\n"),
    ):
        out[f"legacy_parse_{label}"] = try_exc(LE._parse_task_front_matter_legacy, text)
    out["front_matter_parser_available"] = try_exc(
        lambda: LE._front_matter_parser() is not None)
    out["front_matter_parser_parse_sample"] = try_exc(
        lambda: LE._front_matter_parser()(
            "allowed_paths:\n- src/\nmcp_allowed_tools: [mcp__a]\n"))

    # ── max_files / C11 计数 ──
    root_mf = _proj(tmp, {"state": STATE_FULL, "task": TASK_MAX_FILES_1})
    root_mf_bad = _proj(tmp, {"state": STATE_FULL, "task": TASK_MAX_FILES_1.replace(
        "max_files: 1", "max_files: abc")})
    root_mf_zero = _proj(tmp, {"state": STATE_FULL, "task": TASK_MAX_FILES_1.replace(
        "max_files: 1", "max_files: 0")})
    out["read_task_max_files_present"] = try_exc(LE._read_task_max_files, root_mf, "T-0001")
    out["read_task_max_files_malformed"] = try_exc(LE._read_task_max_files, root_mf_bad, "T-0001")
    out["read_task_max_files_zero"] = try_exc(LE._read_task_max_files, root_mf_zero, "T-0001")
    out["read_task_max_files_absent"] = try_exc(LE._read_task_max_files, root_plain, "T-0001")
    out["file_write_count_missing_is_zero"] = try_exc(LE._read_file_write_count, root_mf, "T-0001")
    counter_root = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE})
    out["file_write_count_path"] = try_exc(
        lambda: str(LE._get_file_write_count_file(counter_root, "T-0001")))
    out["increment_file_write_count_first"] = try_exc(
        LE._increment_file_write_count, counter_root, "T-0001", "src/main.py")
    out["increment_file_write_count_second"] = try_exc(
        LE._increment_file_write_count, counter_root, "T-0001", "src/other.py")
    out["file_write_count_after_increments"] = try_exc(
        LE._read_file_write_count, counter_root, "T-0001")

    # ── 命令/路径辅助（纯函数）──
    for label, cmd in (
        ("simple", "python .zcode/tools/validate_state.py ."),
        ("quoted", 'python ".zcode/tools/validate_state.py" .'),
        ("chain_semicolon", "cd /x; git status"),
        ("chain_and", "a && b"),
        ("chain_or", "a || b"),
        ("newline", "a\nb"),
        ("empty", ""),
        ("none", None),
        ("quotes_inner_semicolon", 'echo "a;b"'),
        ("single_quotes", "echo 'x | y'"),
    ):
        out[f"split_command_segments_{label}"] = try_exc(LE._split_command_segments, cmd)
    for label, path in (
        ("msys", "/c/Users/Administrator/x"),
        ("drive", "C:/Users/x"),
        ("plain", "relative/path"),
        ("root_slash", "/x"),
    ):
        out[f"msys_to_windows_{label}"] = try_exc(LE._msys_to_windows, path)
    for label, token in (
        ("python", "python"),
        ("python312", "python312"),
        ("python3_11", "python3.11"),
        ("exe", "python.exe"),
        ("win_path", "C:/Python312/python.exe"),
        ("py", "py"),
        ("bash", "bash"),
        ("node", "node"),
    ):
        out[f"is_python_interpreter_{label}"] = try_exc(LE._is_python_interpreter, token)

    root_cmd = _proj(tmp, {"state": STATE_FULL})
    for label, script in (
        ("zcode_tools", ".zcode/tools/validate_state.py"),
        ("dot_slash", "./.zcode/tools/x.py"),
        ("ai_checkers", ".ai/checkers/compile_gate.py"),
        ("scripts_dir", "scripts/foo.py"),
        ("hooks_dir", "hooks/scripts/loop_enforcement.py"),
        ("outside", "/tmp/evil.py"),
        ("not_py", ".zcode/tools/foo.sh"),
        ("dash_option", "-m"),
        ("empty", ""),
        ("plain_name", "validate_state.py"),
    ):
        out[f"script_in_governance_dirs_{label}"] = try_exc(
            LE._script_in_governance_dirs, script, root_cmd)
    out["script_in_governance_dirs_abs_without_root"] = try_exc(
        LE._script_in_governance_dirs, "/tmp/evil.py", None)

    for label, seg in (
        ("cd_root", "cd .zcode/tools"),
        ("cd_msys", "cd /c/Users/Administrator/x"),
        ("cd_tilde", "cd ~"),
        ("cd_dash", "cd -"),
        ("cd_outside", "cd .."),
        ("pushd_root", "pushd .ai"),
        ("not_cd", "python x.py"),
        ("cd_no_target", "cd"),
    ):
        out[f"is_safe_cd_segment_{label}"] = try_exc(
            LE._is_safe_cd_segment, seg, root_cmd)
    out["is_safe_cd_segment_no_root"] = try_exc(LE._is_safe_cd_segment, "cd .ai", None)
    for label, seg in (
        ("tail", "tail -5"),
        ("head", "head -10"),
        ("grep", "grep -i error"),
        ("echo", "echo done"),
        ("cat", "cat x"),
        ("python_display", "python -m pytest tests/ -q"),
        ("rm", "rm -rf /tmp/x"),
        ("empty", ""),
    ):
        out[f"is_safe_display_segment_{label}"] = try_exc(LE._is_safe_display_segment, seg)

    # ── is_governance_tool_command 判定矩阵 ──
    gov_cmds = [
        ("exempt_python_zcode_tools", "python .zcode/tools/validate_state.py ."),
        ("exempt_python_repair", "python .zcode/tools/repair_continuity.py ."),
        ("exempt_python_close_session", "python .zcode/tools/close_session.py . --note done"),
        ("exempt_python_ai_checkers", "python .ai/checkers/compile_gate.py ."),
        ("exempt_python_ai_guards", "python .ai/guards/policy_guard.py check"),
        ("exempt_python_scripts", "python scripts/runtime_delivery_gate.py ."),
        ("exempt_python_hooks", "python hooks/scripts/loop_enforcement.py"),
        ("exempt_python_tools", "python tools/tool_state.py status"),
        ("exempt_py3", "py -3 .zcode/tools/validate_state.py ."),
        ("exempt_python311", "python3.11 .zcode/tools/validate_state.py ."),
        ("exempt_quoted_script", 'python ".zcode/tools/validate_state.py" .'),
        ("exempt_direct_exec", ".zcode/tools/validate_state.py ."),
        ("exempt_direct_dot", "./.zcode/tools/close_session.py ."),
        ("not_python_c", 'python -c "print(1)"'),
        ("not_python_m", "python -m pytest tests/"),
        ("not_arbitrary_script", "python src/main.py"),
        ("not_bash_interp", "bash .zcode/tools/foo.sh"),
        ("not_sh_interp", "sh .zcode/tools/foo.sh"),
        ("not_php", "php .ai/checkers/x.php"),
        ("not_compound_rm", "python .zcode/tools/validate_state.py . && rm -rf /tmp/x"),
        ("not_compound_redirect", "python .zcode/tools/validate_state.py > /tmp/out.txt"),
        ("not_cd_inside_tools", "cd .zcode/tools && python validate_state.py ."),
        ("not_python_version_only", "python --version"),
        ("not_none", None),
        ("not_empty", ""),
        ("not_dash_script", "python - .zcode/tools/x.py"),
    ]
    for label, cmd in gov_cmds:
        out[f"is_governance_tool_command_{label}"] = try_exc(
            LE.is_governance_tool_command, cmd, root_cmd)

    # 绝对脚本路径（root 内 / root 外）+ cd 复合形态
    abs_inside = (root_cmd / ".zcode" / "tools" / "validate_state.py").as_posix()
    out["is_governance_tool_command_abs_inside_root"] = try_exc(
        LE.is_governance_tool_command, f"python {abs_inside} .", root_cmd)
    out["is_governance_tool_command_abs_outside_root"] = try_exc(
        LE.is_governance_tool_command, "python /tmp/evil.py", root_cmd)
    out["is_governance_tool_command_cd_msys_compound"] = try_exc(
        LE.is_governance_tool_command,
        "cd /c/Users/Administrator/ZCodeProject/loop-engine "
        "&& python .zcode/tools/validate_state.py .", root_cmd)
    out["is_governance_tool_command_cd_outside_root"] = try_exc(
        LE.is_governance_tool_command,
        "cd /c/Windows && python .zcode/tools/validate_state.py .", root_cmd)
    out["is_governance_tool_command_no_root_cd"] = try_exc(
        LE.is_governance_tool_command,
        "cd /c/Users/Administrator/ZCodeProject/loop-engine "
        "&& python .zcode/tools/validate_state.py .")
    out["is_governance_tool_command_pytest_display"] = try_exc(
        LE.is_governance_tool_command, "cd . && python -m pytest tests/ -q", root_cmd)

    # ── _command_references_outside ──
    for label, cmd in (
        ("outside_abs", "cat /c/Users/Administrator/other/x.md"),
        ("outside_rel", "cat ../../x.md"),
        ("inside", "cat .ai/state.yaml"),
        ("no_path", "echo hi"),
        ("flags_only", "grep -i error"),
        ("none", None),
    ):
        out[f"command_references_outside_{label}"] = try_exc(
            LE._command_references_outside, root_cmd, cmd)

    # ── check_diff_scope（patch subprocess.run 确定性捕获）──
    real_run = subprocess.run

    def _fake_run(rc: int, stdout: str, stderr: str = ""):
        def _fake(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], rc, stdout, stderr)
        return _fake

    def _raise(exc_cls):
        def _fake(*args, **kwargs):
            raise exc_cls(args[0] if args else ["git"])
        return _fake

    root_git = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE})
    (root_git / ".git").mkdir()
    try:
        subprocess.run = _fake_run(0, "src/main.py\n")
        out["check_diff_scope_out_of_scope_files_blocks"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
        subprocess.run = _fake_run(0, "")
        out["check_diff_scope_no_changes_passes"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
        subprocess.run = _fake_run(1, "", "fatal: not a git repo")
        out["check_diff_scope_git_failure_not_verified"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
        subprocess.run = _raise(FileNotFoundError)
        out["check_diff_scope_git_missing_not_verified"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
        subprocess.run = _raise(subprocess.TimeoutExpired)
        out["check_diff_scope_git_timeout_not_verified"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
        subprocess.run = _fake_run(0, ".ai/state.yaml\n.zcode/config.json\n")
        out["check_diff_scope_governance_only_passes"] = try_exc(
            LE.check_diff_scope, root_git, ["src/", "tests/"])
    finally:
        subprocess.run = real_run
    out["check_diff_scope_no_allowed_paths_skips"] = try_exc(
        LE.check_diff_scope, root_git, [])
    out["check_diff_scope_non_git_skips"] = try_exc(
        LE.check_diff_scope, _proj(tmp, {"state": STATE_FULL}), ["src/"])

    # ── gate 证据检查 ──
    q_pass = _proj(tmp, {"state": STATE_FULL, "quality_report": QUALITY_REPORT_PASS})
    out["check_quality_gate_evidence_pass"] = try_exc(LE.check_quality_gate_evidence, q_pass)
    out["check_quality_gate_evidence_missing"] = try_exc(
        LE.check_quality_gate_evidence, _proj(tmp, {"state": STATE_FULL}))
    q_bad = _proj(tmp, {"state": STATE_FULL, "quality_report": "{broken json"})
    out["check_quality_gate_evidence_unparsable"] = try_exc(
        LE.check_quality_gate_evidence, q_bad)
    q_empty = _proj(tmp, {"state": STATE_FULL, "quality_report": '{"overall": ""}'})
    out["check_quality_gate_evidence_empty_overall"] = try_exc(
        LE.check_quality_gate_evidence, q_empty)
    q_fabricated = _proj(tmp, {"state": STATE_FULL, "quality_report": (
        '{"overall": "PASS", "checks": [{"name": "lint", "status": "PASS", '
        '"execution_evidence": {"exit_code": 127, "command": "lint"}}]}')})
    out["check_quality_gate_evidence_fabricated"] = try_exc(
        LE.check_quality_gate_evidence, q_fabricated)

    d_go = _proj(tmp, {"state": STATE_FULL, "release_decision": '{"decision": "GO"}'})
    out["check_delivery_gate_evidence_go"] = try_exc(LE.check_delivery_gate_evidence, d_go)
    d_cg = _proj(tmp, {"state": STATE_FULL, "release_decision": (
        '{"decision": "CONDITIONAL_GO", "owners": ["a"], "deadline": "2026-08-10"}')})
    out["check_delivery_gate_evidence_conditional_go_full"] = try_exc(
        LE.check_delivery_gate_evidence, d_cg)
    d_cg_missing = _proj(tmp, {"state": STATE_FULL, "release_decision": (
        '{"decision": "CONDITIONAL_GO"}')})
    out["check_delivery_gate_evidence_conditional_go_incomplete"] = try_exc(
        LE.check_delivery_gate_evidence, d_cg_missing)
    d_nogo = _proj(tmp, {"state": STATE_FULL, "release_decision": '{"decision": "NOGO"}'})
    out["check_delivery_gate_evidence_nogo"] = try_exc(
        LE.check_delivery_gate_evidence, d_nogo)
    d_invalid = _proj(tmp, {"state": STATE_FULL, "release_decision": '{"decision": "MAYBE"}'})
    out["check_delivery_gate_evidence_invalid"] = try_exc(
        LE.check_delivery_gate_evidence, d_invalid)
    out["check_delivery_gate_evidence_missing"] = try_exc(
        LE.check_delivery_gate_evidence, _proj(tmp, {"state": STATE_FULL}))
    d_cert = _proj(tmp, {"state": STATE_FULL, "extra": {
        ".ai/certifications/state.yaml": (
            "roles:\n  delivery-manager:\n    state: CERTIFIED\n"
            "    last_challenge: '2026-08-01'\n")}})
    out["check_delivery_gate_evidence_certified"] = try_exc(
        LE.check_delivery_gate_evidence, d_cert)

    r_pass = _proj(tmp, {"state": STATE_FULL, "runtime_report": RUNTIME_REPORT_PASS})
    out["check_runtime_quality_gate_pass"] = try_exc(LE.check_runtime_quality_gate, r_pass)
    r_fail = _proj(tmp, {"state": STATE_FULL, "runtime_report": (
        '{"overall": "FAIL", "blocked_by": ["b1"], "diagnoses": '
        '[{"diagnosis_id": "D1", "root_causes": ["cause-1"]}]}')})
    out["check_runtime_quality_gate_fail"] = try_exc(LE.check_runtime_quality_gate, r_fail)
    out["check_runtime_quality_gate_missing"] = try_exc(
        LE.check_runtime_quality_gate, _proj(tmp, {"state": STATE_FULL}))

    s_pass = _proj(tmp, {"state": STATE_FULL, "security_audit": SECURITY_AUDIT_PASS})
    out["check_security_gate_evidence_pass"] = try_exc(LE.check_security_gate_evidence, s_pass)
    s_blocked = _proj(tmp, {"state": STATE_FULL, "security_audit": (
        SECURITY_AUDIT_PASS.replace('"PASS"', '"BLOCKED"'))})
    out["check_security_gate_evidence_blocked"] = try_exc(
        LE.check_security_gate_evidence, s_blocked)
    out["check_security_gate_evidence_missing"] = try_exc(
        LE.check_security_gate_evidence, _proj(tmp, {"state": STATE_FULL}))
    s_md = _proj(tmp, {"state": STATE_FULL, "extra": {
        ".ai/evidence/T-0001/phase-3/security-engineer-report.md":
        "# Security report\nno issues found\n"}})
    out["check_security_gate_evidence_md_fallback"] = try_exc(
        LE.check_security_gate_evidence, s_md)
    s_md_blocked = _proj(tmp, {"state": STATE_FULL, "extra": {
        ".ai/evidence/T-0001/phase-3/security-engineer-report.md":
        "# Security report\nBLOCKED: critical\n"}})
    out["check_security_gate_evidence_md_blocked"] = try_exc(
        LE.check_security_gate_evidence, s_md_blocked)

    # ── phase gate enforcement ──
    out["phase_gate_s4_config_missing"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S4-implementation"), "no_qg_config": True}),
        "S4-implementation")
    out["phase_gate_s5_no_evidence"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S5-quality")}), "S5-quality")
    out["phase_gate_s5_full_evidence"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S5-quality"), "quality_report": QUALITY_REPORT_PASS,
                    "security_audit": SECURITY_AUDIT_PASS}), "S5-quality")
    out["phase_gate_s6_slo_disabled"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S6-delivery"), "quality_report": QUALITY_REPORT_PASS,
                    "security_audit": SECURITY_AUDIT_PASS,
                    "runtime_report": RUNTIME_REPORT_PASS,
                    "release_decision": RELEASE_DECISION_GO,
                    "config_variant": "slo_disabled"}), "S6-delivery")
    out["phase_gate_s6_slo_missing_sources"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S6-delivery"), "quality_report": QUALITY_REPORT_PASS,
                    "security_audit": SECURITY_AUDIT_PASS,
                    "runtime_report": RUNTIME_REPORT_PASS,
                    "release_decision": RELEASE_DECISION_GO}), "S6-delivery")
    out["phase_gate_s7_missing"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S7-integration")}), "S7-integration")
    out["phase_gate_s7_present"] = try_exc(
        LE.check_phase_gate_enforcement,
        _proj(tmp, {"state": _state("S7-integration"),
                    "integration_report": INTEGRATION_REPORT_PASS}),
        "S7-integration")
    out["phase_gate_unknown_phase"] = try_exc(
        LE.check_phase_gate_enforcement, _proj(tmp, {"state": _state("S0-init")}),
        "S0-init")
    out["phase_gate_empty_phase"] = try_exc(
        LE.check_phase_gate_enforcement, _proj(tmp, {"state": _state("S0-init")}), "")

    # _check_phase_evidence_file
    out["phase_evidence_file_missing"] = try_exc(
        LE._check_phase_evidence_file, _proj(tmp, {"state": _state("S7-integration")}),
        "S7-integration", [".ai/evidence/T-0001/integration-report.json"])
    out["phase_evidence_file_pass"] = try_exc(
        LE._check_phase_evidence_file,
        _proj(tmp, {"state": _state("S7-integration"),
                    "integration_report": INTEGRATION_REPORT_PASS}),
        "S7-integration", [".ai/evidence/T-0001/integration-report.json"])
    out["phase_evidence_file_fail_status"] = try_exc(
        LE._check_phase_evidence_file,
        _proj(tmp, {"state": _state("S7-integration"),
                    "integration_report": '{"overall": "FAIL"}'}),
        "S7-integration", [".ai/evidence/T-0001/integration-report.json"])
    out["phase_evidence_file_verdict_fallback"] = try_exc(
        LE._check_phase_evidence_file,
        _proj(tmp, {"state": _state("S7-integration"),
                    "integration_report": '{"verdict": "PASS"}'}),
        "S7-integration", [".ai/evidence/T-0001/integration-report.json"])
    out["phase_evidence_file_no_regression"] = try_exc(
        LE._check_phase_evidence_file,
        _proj(tmp, {"state": _state("S8-functional-test"),
                    "regression_baseline": REGRESSION_BASELINE}),
        "S8-functional-test", [".ai/evidence/regression/baseline.json"])
    # 占位符无任务跳过
    out["phase_evidence_file_no_task_id"] = try_exc(
        LE._check_phase_evidence_file,
        _proj(tmp, {"state": STATE_FULL_NO_TASK}),
        "S7-integration", [".ai/evidence/{task_id}/integration-report.json"])

    # ── B6 自审 / context builders ──
    out["self_review_block_enabled_default"] = try_exc(
        LE._self_review_block_enabled, _proj(tmp, {"state": STATE_FULL}))
    out["self_review_block_opt_out"] = try_exc(
        LE._self_review_block_enabled,
        _proj(tmp, {"state": STATE_FULL, "config_variant": "self_review_opt_out"}))
    out["self_review_block_standard_mode"] = try_exc(
        LE._self_review_block_enabled, _proj(tmp, {"state": STATE_STANDARD}))

    root_rev = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE,
                           "review_evidence": REVIEW_EVIDENCE})
    out["trace_review_evidence_isolation_distinct"] = try_exc(
        LE.trace_review_evidence_isolation, root_rev, "T-0001")
    root_self = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE,
                            "self_review_evidence": SELF_REVIEW_EVIDENCE})
    out["trace_review_evidence_isolation_self_review_blocks"] = try_exc(
        LE.trace_review_evidence_isolation, root_self, "T-0001")
    root_opt = _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE,
                           "self_review_evidence": SELF_REVIEW_EVIDENCE,
                           "config_variant": "self_review_opt_out"})
    out["trace_review_evidence_isolation_opt_out_trace"] = try_exc(
        LE.trace_review_evidence_isolation, root_opt, "T-0001")
    out["trace_review_evidence_isolation_no_task"] = try_exc(
        LE.trace_review_evidence_isolation, root_rev, None)
    out["trace_review_evidence_isolation_no_dir"] = try_exc(
        LE.trace_review_evidence_isolation,
        _proj(tmp, {"state": STATE_FULL, "task": TASK_IN_SCOPE}), "T-0002")

    ctx_root = _proj(tmp, {"state": STATE_FULL, "task": TASK_MCP_ALLOW,
                           "gates": GATES_APPROVED, "review_evidence": REVIEW_EVIDENCE})
    out["load_quality_results_for_context"] = try_exc(
        LE._load_quality_results_for_context,
        _proj(tmp, {"state": STATE_FULL, "quality_report": QUALITY_REPORT_PASS}))
    out["load_review_status_for_context_found"] = try_exc(
        LE._load_review_status_for_context, root_rev, "T-0001")
    out["load_review_status_for_context_none"] = try_exc(
        LE._load_review_status_for_context, root_rev, None)
    out["load_evidence_envelopes_for_context"] = try_exc(
        LE._load_evidence_envelopes_for_context, root_rev, "T-0001")
    out["load_evidence_envelopes_for_context_empty"] = try_exc(
        LE._load_evidence_envelopes_for_context, root_rev, "T-999")
    state_ctx = {"loop_mode": "FULL", "current_phase": "S4-implementation"}
    out["build_hard_constraints_context"] = try_exc(
        LE.build_hard_constraints_context, ctx_root, state_ctx, "T-0001",
        "src/main.py", str(ctx_root / "src" / "main.py"),
        {"allowed_paths": ["src/"]}, [{"id": "T-0001", "status": "active"}])

    # ── SLO / second-failure 门禁直调 ──
    out["slo_gate_evidence_missing_sources"] = try_exc(
        LE.check_slo_gate_evidence, _proj(tmp, {"state": _state("S6-delivery")}))
    out["slo_gate_evidence_disabled"] = try_exc(
        LE.check_slo_gate_evidence,
        _proj(tmp, {"state": _state("S6-delivery"), "config_variant": "slo_disabled"}))
    out["second_failure_gate_evidence_default_disabled"] = try_exc(
        LE.check_second_failure_gate_evidence,
        _proj(tmp, {"state": _state("S6-delivery")}))

    # ── _import_loop_core_gate（子模块可解析）──
    out["import_loop_core_gate_slo_gate"] = try_exc(
        LE._import_loop_core_gate, _proj(tmp, {"state": STATE_FULL}), "slo_gate")

    return _norm_payload(out)


def capture_dir_snapshot() -> list[str]:
    """loop_enforcement 模块 dir() 全量快照（含私有名，re-export 完整性基线）。"""
    return module_dir_snapshot("loop_enforcement")


def capture_public_names() -> list[str]:
    """import * 公开面（非下划线名）。"""
    return sorted(n for n in dir(LE) if not n.startswith("_"))


def capture_all(tmp: Path) -> dict:
    """完整 golden 载荷。"""
    payload: dict = {}
    payload["hook_entry_matrix"] = capture_hook_entry_matrix(tmp)
    payload["direct_calls"] = capture_direct_calls(tmp)
    payload["dir_snapshot"] = capture_dir_snapshot()
    payload["public_names"] = capture_public_names()
    return payload
