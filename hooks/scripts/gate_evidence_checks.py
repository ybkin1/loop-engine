"""gate_evidence_checks.py — gate 证据检查（T-0110 批 C 从 loop_enforcement 外提）。

T-0110 批 C 外提的各类 gate 证据检查（design-common-weakness.md §1.1 行 4 +
任务卡批 C "gate 证据检查类（T-0056/T-0067 相关证据校验逻辑外提）"），
全部为纯函数，返回 ``(bool, str)``：

- ``check_quality_gate_evidence``：S5-quality 结构化质量证据 + 证据真实性校验
  （T-0078 P0）+ execution ledger 溯源 trace（T-0078 P1）
- ``check_delivery_gate_evidence``：S6-delivery GO/CONDITIONAL_GO/NOGO 判定
- ``check_runtime_quality_gate``：运行时质量门（overall == "PASS" 才放行）
- ``check_security_gate_evidence``：S5/S6 安全审计证据（JSON + markdown 兜底）
- ``check_slo_gate_evidence``：T-0093 SLO 门禁（error budget 耗尽冻结发布）
- ``check_second_failure_gate_evidence``：T-0097 second-failure 门禁
- ``_import_loop_core_gate``：插件缓存退化环境下的精确子模块解析（T-0097）
- ``check_phase_gate_enforcement``：按当前阶段组合上述门禁（S4+ 质量配置、
  S5/S6 链式检查、S7-S11 阶段证据、其余阶段放行）
- ``_PHASE_EVIDENCE_FILES`` / ``_check_phase_evidence_file``：S7-S11 证据表
- B6 自审证据隔离（T-0083 B6 + T-0067 verify_review_evidence 接线）：
  ``_self_review_block_enabled`` / ``trace_review_evidence_isolation``

全部代码逐字迁移自 loop_enforcement.py（行为等价拆分，fail-closed 语义
零变化）；依赖仅 hook_common（load_state/load_config）+ 可选的 loop_core
（slo_gate/second_failure/subagent_evidence_verifier/execution_ledger，
均 try/except 或调用方 fail-closed 处理）。本模块不依赖 loop_enforcement。
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
from pathlib import Path

from hook_common import (
    load_config,
    load_state,
)

logger = logging.getLogger(__name__)


def check_quality_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S5-quality phase has quality-engineer structured evidence.

    Returns (has_evidence, reason).
    Evidence: .ai/evidence/quality/quality_report.json with non-empty 'overall' field.
    """
    quality_json = root / ".ai" / "evidence" / "quality" / "quality_report.json"
    if not quality_json.exists():
        return False, (
            "缺少 quality-engineer 的结构化输出："
            f"{quality_json.relative_to(root)} 不存在。"
            "请运行 quality-engineer 质量门禁检查（run_quality_gates.py）"
            "并生成 quality_report.json。"
        )

    try:
        report = json.loads(quality_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return False, (
            f"quality_report.json 无法解析：{e}。"
            "请重新运行 quality-engineer 生成有效报告。"
        )

    overall = report.get("overall")
    # T-0078: 向后兼容 — 旧格式报告可能使用 'verdict' 字段
    if overall is None:
        overall = report.get("verdict")
    if overall is None or (isinstance(overall, str) and not overall.strip()):
        return False, (
            "quality_report.json 存在但 'overall' 字段为空。"
            "quality-engineer 报告不完整，请重新运行质量门禁。"
        )

    # T-0078 P0: 证据真实性校验 — 检查每个 check 是否真的执行过
    checks = report.get("checks", [])
    fabricated = []
    for c in checks:
        exec_ev = c.get("execution_evidence")
        if not exec_ev:
            # 旧格式报告 — 降级为警告但不阻断（向后兼容）
            continue
        claimed_status = c.get("status", "").upper()
        exit_code = exec_ev.get("exit_code")
        cmd = exec_ev.get("command", "unknown")
        if exit_code is not None:
            # exit_code=0 但 status=BLOCKED → 矛盾，可能是阈值阻断（正常）
            # exit_code≠0 但 status=PASS → 证据造假
            if exit_code != 0 and claimed_status == "PASS":
                fabricated.append(
                    f"{c.get('name', '?')}: command '{cmd}' exited {exit_code} but claimed PASS"
                )
            # lint 命令不可执行 (exit_code=-1/126/127) 但 status=PASS
            if exit_code in (-1, 126, 127) and claimed_status == "PASS":
                fabricated.append(
                    f"{c.get('name', '?')}: command '{cmd}' unavailable (exit {exit_code}) but claimed PASS"
                )
    if fabricated:
        return False, (
            "证据真实性校验失败 — 以下检查声称 PASS 但实际未成功执行："
            f"{'; '.join(fabricated[:5])}。"
            "请重新运行质量门禁并确保所有工具可用。"
        )

    # T-0078 P1: 证据溯源链交叉验证
    # 检查 evidence 是否在 execution ledger 中有对应记录
    try:
        from loop_core.execution_ledger import ExecutionLedger
        ledger = ExecutionLedger(root)
        evidence_events = ledger.find_evidence_events("quality-engineer")
        # 注意：当前只做日志记录（非阻断），完整实现需要将 quality report
        # 的 checks 与 ledger 中的 evidence_refs 逐一匹配
        import logging
        _logger = logging.getLogger(__name__)
        if not evidence_events:
            _logger.info("[EVIDENCE_TRACE] quality report 缺少 execution ledger 溯源记录")
    except Exception:
        pass  # 账本不可用时不阻断（向后兼容）

    return True, f"质量证据已通过（overall={overall}，证据真实性校验通过）"


# ── T-0082 Phase 3 → T-0083 (B6): subagent review-evidence isolation ──
# B6 change: self-review (reviewer_session_id == developer_session_id) now
# BLOCKS the write when enforcement.self_review_block is enabled (default)
# and loop_mode == FULL.  Projects can opt out via config.yaml
# (enforcement.self_review_block: false); STANDARD mode keeps the T-0082
# trace-only behavior.


def _self_review_block_enabled(root: Path) -> bool:
    """Config-gated self-review blocking (B6).

    Default: enabled in FULL mode.  Opt-out:
      .zcode/skills/loop-governance/config.yaml
        enforcement:
          self_review_block: false
    """
    try:
        state = load_state(root)
    except Exception:
        state = {}
    if str(state.get("loop_mode", "")).upper() != "FULL":
        return False
    cfg = load_config(root)
    enf = cfg.get("enforcement", {})
    if not isinstance(enf, dict):
        enf = {}
    return bool(enf.get("self_review_block", True))


def trace_review_evidence_isolation(root: Path, task_id: str | None) -> bool:
    """Scan review evidence for self-review; BLOCK when detected (B6).

    Scans .ai/evidence/<task_id>/ for review evidence JSONs carrying
    reviewer_session_id / developer_session_id fields.  When they are equal
    (self-review) AND blocking is enabled (config enforcement.
    self_review_block, default true) AND loop_mode == FULL → returns True
    and the caller must EXIT_BLOCK.

    When blocking is disabled or mode is not FULL, the scan degrades to the
    T-0082 trace behavior (warning log only, never blocks).  Additionally
    runs the subagent_evidence_verifier.verify_review_evidence trace
    (T-0067 logic) when importable (log-only).

    Returns True when the write must be blocked (SELF_REVIEW).
    """
    if not task_id:
        return False
    evidence_dir = root / ".ai" / "evidence" / task_id
    if not evidence_dir.is_dir():
        return False

    block_enabled = _self_review_block_enabled(root)

    verifier_available = False
    try:
        sys.path.insert(0, str(root))
        from loop_core.subagent_evidence_verifier import verify_review_evidence
        verifier_available = True
    except Exception:
        pass  # verifier unavailable → trace degrades to field comparison only

    for p in sorted(evidence_dir.rglob("*.json")):
        try:
            content = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(content, dict):
            continue
        reviewer = content.get("reviewer_session_id")
        developer = content.get("developer_session_id")
        if not reviewer:
            continue  # not a review-evidence file
        if reviewer == developer:
            logger.warning(
                "SELF_REVIEW_TRACE: %s: reviewer_session_id == developer_session_id (%s)",
                p.relative_to(root), reviewer,
            )
            if block_enabled:
                return True
            continue
        if verifier_available:
            try:
                result = verify_review_evidence(
                    str(p), main_session_id=developer or ""
                )
                if not result.get("valid"):
                    logger.warning(
                        "EVIDENCE_TRACE: %s: %s",
                        p.relative_to(root), result.get("reason", "invalid"),
                    )
            except Exception:
                pass  # trace only; never blocks

    return False


def check_delivery_gate_evidence(root: Path) -> tuple[bool, str]:
    """Check that S6-delivery phase has delivery-manager go_nogo decision.

    Returns (has_evidence, reason).
    Evidence priority:
    1. .ai/evidence/release/<version>/release_decision.json with 'decision' field
    2. .ai/certifications/state.yaml delivery-manager state=CERTIFIED
    """
    # 1. Check for release_decision.json
    release_dir = root / ".ai" / "evidence" / "release"
    if release_dir.is_dir():
        for version_dir in sorted(release_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                decision_file = version_dir / "release_decision.json"
                if decision_file.exists():
                    try:
                        decision = json.loads(decision_file.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        # 文件无法解析 → 不可信，继续检查更早版本
                        continue
                    # T-0083 (AC-06): 修复 NOGO-passes-as-GO bug（was: 任意
                    # truthy decision 都放行）。只有明确 GO / 带 owners+deadline
                    # 的 CONDITIONAL_GO 才通过；NOGO、非法或缺失决策一律阻断。
                    decision_str = str(decision.get("decision", "")).upper()
                    if decision_str == "GO":
                        return True, (
                            f"交付经理决策：GO（版本={version_dir.name}）"
                        )
                    if decision_str in ("CONDITIONAL_GO", "CONDITIONAL-GO"):
                        owners = decision.get("owners", [])
                        deadline = decision.get("deadline", "")
                        if owners and deadline:
                            return True, (
                                f"CONDITIONAL_GO: owners={owners} "
                                f"deadline={deadline}（版本={version_dir.name}）"
                            )
                        return False, (
                            "CONDITIONAL_GO 缺少 owners/deadline"
                            f"（版本={version_dir.name}）— 发布阻断"
                        )
                    if decision_str == "NOGO":
                        return False, (
                            "交付经理决策：NOGO"
                            f"（版本={version_dir.name}）— 发布阻断"
                        )
                    return False, (
                        f"决策值非法或缺失: {decision.get('decision')!r}"
                        f"（版本={version_dir.name}，须为 GO/CONDITIONAL_GO/NOGO）"
                        "— 发布阻断"
                    )

    # 2. Check certifications/state.yaml for delivery-manager
    cert_file = root / ".ai" / "certifications" / "state.yaml"
    if cert_file.exists():
        try:
            import yaml  # type: ignore
            with open(cert_file, encoding="utf-8") as f:
                cert_data = yaml.safe_load(f) or {}
        except Exception:
            cert_data = {}

        # Try PyYAML first
        if cert_data:
            roles = cert_data.get("roles", {})
            dm = roles.get("delivery-manager", {})
            # T-0083 (AC-06): 校验 delivery-manager 状态必须恰好为 CERTIFIED
            # （归一化大小写/空白后精确匹配），其余状态一律不算放行证据。
            if isinstance(dm, dict) and str(dm.get("state", "")).strip().upper() == "CERTIFIED":
                return True, (
                    "交付经理认证状态为 CERTIFIED（"
                    f"last_challenge={dm.get('last_challenge', 'N/A')}）"
                )
            return False, (
                "delivery-manager 尚未签署 GO/NOGO 决定。"
                "请运行 delivery-manager 完成发布决策检查并生成 release_decision.json。"
            )
        else:
            # Fallback: text scan
            try:
                text = cert_file.read_text(encoding="utf-8")
            except Exception:
                text = ""
            if "delivery-manager:" in text and "state: CERTIFIED" in text:
                return True, "交付经理认证状态为 CERTIFIED（文本检测）"

    return False, (
        "缺少 delivery-manager 的 GO/NOGO 决策证据。"
        "请运行 delivery-manager 完成发布决策检查："
        "生成 release_decision.json（decision=GO/NOGO）"
        "或确保 certifications/state.yaml 中 delivery-manager 已 CERTIFIED。"
    )


def check_runtime_quality_gate(root: Path) -> tuple[bool, str]:
    """Check that runtime quality gate has been executed and passed.

    Part of S6-delivery enforcement (T-0078 P0).
    Reads .ai/evidence/quality/runtime_quality_report.json.
    overall must be "PASS" — FAIL/BLOCKED/SKIPPED/NOT_RUN all fail-closed.
    """
    runtime_report = root / ".ai" / "evidence" / "quality" / "runtime_quality_report.json"
    if not runtime_report.exists():
        return False, (
            "缺少运行时质量门报告：runtime_quality_report.json 不存在。"
            "请运行 scripts/runtime_delivery_gate.py 生成运行时质量检查报告。"
        )

    try:
        data = json.loads(runtime_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, (
            f"runtime_quality_report.json 无法解析：{exc}。"
            "请重新运行 runtime_delivery_gate.py。"
        )

    overall = data.get("overall")
    if overall != "PASS":
        blocked = data.get("blocked_by", [])
        diagnoses = data.get("diagnoses", [])
        diag_summary = ", ".join(
            f"{d.get('diagnosis_id', '?')}: {d.get('root_causes', ['?'])[0][:60]}"
            for d in diagnoses[:3]
        ) if diagnoses else "no diagnoses"
        return False, (
            f"运行时质量门未通过：overall={overall}，"
            f"阻断项：{', '.join(blocked[:5])}。诊断：{diag_summary}。"
            "修复所有阻断项后重新运行 runtime_delivery_gate.py。"
        )

    return True, f"运行时质量门通过（overall={overall}）"


def _import_loop_core_gate(root: Path, submodule: str):
    """从项目根解析 loop_core 门禁子模块（slo_gate / second_failure）。

    hook 可能从插件缓存运行：Path(__file__) 指向缓存目录 → 显式把项目根
    插入 sys.path 后再 import（同 trace_review_evidence_isolation 的既有
    模式）。但仅插 sys.path 还不够：插件缓存是项目的完整副本（含陈旧的
    loop_core 包，早于门禁模块加入时的副本、没有对应子模块文件），hook
    模块加载期 try_import_hard_constraints() 已把缓存里的 loop_core 导入
    sys.modules —— 包缓存优先于路径查找，缓存包的 __path__ 里找不到目标
    子模块 → 直接 import 会 ModuleNotFoundError。

    精确修复（T-0097，替代"pop 整个 loop_core 再强制重解析"）：只有目标
    子模块确实缺失时才把它从项目根解析出来，且**从不替换已加载的
    loop_core 包对象**——只临时把现有包的 __path__ 前置项目根目录，import
    完成后立即恢复。这样：
    - 已加载的 loop_core 本身可用（如来自真实项目根）时零改动。同进程其他
      模块（如 pytest 测试套件）持有的包引用与子模块属性不受影响——旧实现
      pop 掉整个包后重解析得到的新包不再有任何子模块属性
      （loop_core/__init__.py 不 import 子模块），后续
      monkeypatch.setattr("loop_core.observability...") 等字符串解析会
      AttributeError，造成跨测试顺序依赖 flake。
    - 插件缓存陈旧副本场景（真实 hook 进程，每次调用是新进程）下，目标
      子模块从项目根加载并挂到现有包对象上；其余 loop_core.* 条目保持原样，
      fail-closed 语义不变。

    返回导入的子模块对象；导入失败（目标子模块在项目根也不存在、或
    loop_core 包整体不可用、或无关的缺失依赖如 yaml）时抛出原始异常，
    由调用方按 fail-closed 处理。
    """
    target = f"loop_core.{submodule}"
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module(target)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if not (missing == target or missing.startswith("loop_core.")):
            raise  # 无关的缺失依赖（如 yaml）— 不是缓存陈旧问题，直接失败
        # 已加载的 loop_core 无法提供目标子模块（典型：陈旧的插件缓存副本）。
        cached_pkg = sys.modules.get("loop_core")
        if cached_pkg is None:
            raise
        pkg_dirs = getattr(cached_pkg, "__path__", None)
        if not pkg_dirs:
            raise
        saved_path = list(pkg_dirs)
        root_core = str((root / "loop_core").resolve())
        try:
            # 临时把项目根前置到现有包的 __path__（finally 中恢复）；目标
            # 子模块从项目根解析并作为属性挂到现有包对象上，包本身不变。
            cached_pkg.__path__ = [root_core] + saved_path
            return importlib.import_module(target)
        finally:
            cached_pkg.__path__ = saved_path


def check_slo_gate_evidence(root: Path) -> tuple[bool, str]:
    """T-0093 (AC-02): SLO 门禁 — error budget 耗尽自动冻结发布。

    S6-delivery 分支新增检查（与 check_delivery_gate_evidence 同级，B2 §1.5
    ``slo_budget_available``）。本检查只会**新增**阻断条件，不会放松任何
    既有检查（T-0093 AC-06：约束只强化不弱化）。

    - budget HEALTHY/CONSUMING → 放行（CONSUMING 附警告信息）
    - budget FREEZE（耗尽）   → 阻断（ERROR_BUDGET_EXHAUSTED + 明细）
    - 数据不足/无法判定       → fail-closed 阻断（原因列出缺失源）
    - 有效豁免（未过期 + approver 非空）→ 放行（原因含豁免记录）
    - 开关禁用（config.yaml ``slo_gate.enabled: false`` 或环境变量
      LOOP_SLO_GATE_ENABLED=0/false）→ 放行（附说明，advisory 模式）

    门禁模块加载/执行异常 → fail-closed 阻断（T-0083 AC-06 姿态）。
    """
    try:
        # hook 可能从插件缓存运行：Path(__file__) 指向缓存目录 → 显式把
        # 项目根插入 sys.path 后再 import（同 trace_review_evidence_isolation
        # 的既有模式）。插件缓存可能是 T-0093 之前的完整副本，其 loop_core
        # 包（hook 模块加载期 try_import_hard_constraints() 已导入
        # sys.modules，包缓存优先于路径查找）没有 slo_gate.py →
        # ModuleNotFoundError。_import_loop_core_gate 只在该子模块确实缺失时
        # 才精确地从项目根解析（临时前置现有包的 __path__，完成后恢复），
        # 从不替换已加载的 loop_core 包对象——同进程其他模块（如测试套件）
        # 持有的包引用与子模块属性不受影响（旧实现 pop 整个包会破坏后续
        # monkeypatch.setattr("loop_core.observability...") 等解析）。
        module = _import_loop_core_gate(root, "slo_gate")
        check_slo_gate = module.check_slo_gate
    except Exception as exc:
        return False, (
            f"SLO 门禁模块加载失败（fail-closed）："
            f"{type(exc).__name__}: {exc}"
        )
    try:
        result = check_slo_gate(root)
    except Exception as exc:
        return False, (
            f"SLO 门禁执行异常（fail-closed）："
            f"{type(exc).__name__}: {exc}"
        )
    if result.decision == "PASS":
        return True, f"SLO 门禁通过：{result.reason}"
    return False, f"SLO 门禁阻断：{result.reason}"


def check_second_failure_gate_evidence(root: Path) -> tuple[bool, str]:
    """T-0097 (B2 §3.4): second-failure 门禁 — 同类失败复发未解决时阻断发布。

    S6-delivery 分支新增检查（与 check_slo_gate_evidence 同级，B2 §3.4
    ``action_item_closed`` 接线）。本检查只会**新增**阻断条件，不会放松任何
    既有检查（T-0093 AC-06 姿态延续）。

    - 开关未启用（config.yaml ``second_failure_gate.enabled`` 默认 false，
      或环境变量 LOOP_SECOND_FAILURE_GATE_ENABLED）→ 放行（advisory 模式，
      wave 1 opt-in）
    - 无 second-failure 记录            → 放行
    - 未解决复发（关联复盘无 open 行动项）→ 阻断（SECOND_FAILURE_UNRESOLVED
      + 明细）
    - 有 open 行动项 / 复盘闭环 / 已显式 resolved → 放行
    - 有效豁免（未过期 + approver 非空）→ 放行（原因含豁免记录）
    - 证据文件不可解析                 → fail-closed 阻断（列出文件）

    门禁模块加载/执行异常 → fail-closed 阻断（T-0083 AC-06 姿态）。
    """
    try:
        # hook 可能从插件缓存运行：显式把项目根插入 sys.path 后再 import
        # （同 check_slo_gate_evidence 的 _import_loop_core_gate 模式）——
        # 只在目标子模块确实缺失（陈旧缓存副本）时精确地从项目根解析，
        # 不替换已加载的 loop_core 包对象（不破坏同进程其他模块的引用）。
        module = _import_loop_core_gate(root, "second_failure")
        second_failure_block = module.second_failure_block
    except Exception as exc:
        return False, (
            f"Second-failure 门禁模块加载失败（fail-closed）："
            f"{type(exc).__name__}: {exc}"
        )
    try:
        result = second_failure_block(root)
    except Exception as exc:
        return False, (
            f"Second-failure 门禁执行异常（fail-closed）："
            f"{type(exc).__name__}: {exc}"
        )
    if result.decision == "PASS":
        return True, f"Second-failure 门禁通过：{result.reason}"
    return False, f"Second-failure 门禁阻断：{result.reason}"


# ── T-0082 Phase 5 GAP-2: S7-S11 阶段门禁证据 ───────────────────────────

# 每个阶段的可接受证据文件（相对项目根）。{task_id} 会被替换为
# state.current_task_id（无任务上下文时跳过含占位符的候选）。
_PHASE_EVIDENCE_FILES: dict[str, list[str]] = {
    "S7-integration": [
        ".ai/evidence/{task_id}/integration-report.json",
        ".ai/evidence/integration/integration_report.json",
    ],
    "S8-functional-test": [
        ".ai/evidence/{task_id}/functional-test-report.json",
        ".ai/evidence/{task_id}/regression-report.json",
    ],
    "S9-fix-optimize": [
        ".ai/evidence/{task_id}/fix-optimize-report.json",
    ],
    "S10-performance": [
        ".ai/evidence/{task_id}/performance-report.json",
    ],
    "S11-maintenance": [
        ".ai/evidence/{task_id}/maintenance-report.json",
    ],
}


def _check_phase_evidence_file(
    root: Path,
    phase: str,
    evidence_relpaths: list[str],
    accept_no_regression: bool = False,
) -> tuple[bool, str]:
    """检查给定阶段证据文件是否存在且解析为 JSON 且 overall == "PASS"。

    T-0082 Phase 5 GAP-2: S7-S11 阶段门禁的结构化证据检查。
    - "{task_id}" 占位符替换为 state.current_task_id（无任务时跳过该候选）。
    - overall 缺失时兼容旧格式 verdict 字段。
    - accept_no_regression=True 时接受 regression_runner 输出风格：
      has_regressions == false 或 verdict == PASS（无 overall 字段）。
    - T-0083 (AC-06)：任一候选通过即整体通过；但已存在候选的任何非 PASS
      判定（FAIL/BLOCKED/NOT_VERIFIED/NOT_RUN/SKIPPED 等）都记为该候选
      的失败（fail-closed，was 模糊的"需要 PASS"）；全部候选缺失/无效/非
      PASS → 阻断。

    Returns (ok, reason)。
    """
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception:
        task_id = None

    candidates: list[Path] = []
    for rel in evidence_relpaths:
        if "{task_id}" in rel:
            if not task_id:
                continue
            rel = rel.replace("{task_id}", str(task_id))
        candidates.append(root / rel)

    if not candidates:
        return False, (
            f"{phase} 阶段证据缺失：state 中没有 current_task_id，"
            "无法定位阶段报告。"
        )

    failures: list[str] = []
    for p in candidates:
        rel_p = p.relative_to(root)
        if not p.exists():
            failures.append(f"{rel_p} 不存在")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{rel_p} 无法解析: {exc}")
            continue
        overall = data.get("overall")
        if overall is None:
            overall = data.get("verdict")
        if overall == "PASS":
            return True, f"{phase} 阶段证据已通过（{rel_p} overall=PASS）"
        if accept_no_regression and (
            data.get("has_regressions") is False
            or str(data.get("verdict", "")).upper() == "PASS"
        ):
            return True, f"{phase} 阶段证据已通过（{rel_p} 无回归）"
        # T-0083 (AC-06): fail-closed — 任何非 PASS 判定
        # （FAIL/BLOCKED/NOT_VERIFIED/NOT_RUN/SKIPPED）都是 gate failure。
        failures.append(f"{rel_p} overall={overall} 非 PASS（fail-closed）")

    # 任一候选通过即整体通过；全部候选缺失/无效/非 PASS → 阻断
    return False, (
        f"{phase} 阶段证据不完整，以下文件均需存在且 overall=PASS："
        + "; ".join(f"{p.relative_to(root)}" for p in candidates)
        + "。详情：" + "; ".join(failures[:3])
    )


# ── T-0082 Phase 5 GAP-3: S5/S6 安全审计证据 ────────────────────────────


def check_security_gate_evidence(root: Path) -> tuple[bool, str]:
    """检查 S5-quality / S6-delivery 所需的安全审计证据。

    证据来源（任一通过即可）：
    1. .ai/evidence/security/security_audit.json — verdict != BLOCKED
    2. .ai/evidence/{task_id}/phase-3/security-engineer-report.md —
       存在且不含 BLOCKED 判定
    """
    sec_report = root / ".ai" / "evidence" / "security" / "security_audit.json"
    if sec_report.exists():
        try:
            sec_data = json.loads(sec_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, (
                f"安全审计证据无法解析（{sec_report.relative_to(root)}）: {exc}"
            )
        verdict = str(sec_data.get("verdict", "")).upper()
        if verdict == "BLOCKED":
            return False, "安全审计 verdict=BLOCKED：存在阻断级安全缺陷"
        if not verdict:
            return False, "安全审计证据缺少 verdict 字段"
        return True, f"安全审计证据已通过（verdict={verdict}）"

    # 兜底：安全工程师报告 markdown
    try:
        state = load_state(root)
        task_id = state.get("current_task_id")
    except Exception:
        task_id = None
    if task_id:
        md = root / ".ai" / "evidence" / task_id / "phase-3" / "security-engineer-report.md"
        if md.exists():
            try:
                text = md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                text = ""
            if "BLOCKED" in text.upper():
                return False, "安全工程师报告中包含 BLOCKED 判定"
            return True, "安全工程师报告存在且无 BLOCKED 判定"

    return False, (
        "S5/S6 需要安全审计证据：.ai/evidence/security/security_audit.json 不存在，"
        "且 .ai/evidence/{task_id}/phase-3/security-engineer-report.md 不存在。"
    )


def check_phase_gate_enforcement(root: Path, phase: str) -> tuple[bool, str]:
    """Check phase-specific gate evidence requirements.

    Returns (can_proceed, reason). can_proceed=False means writes should be
    restricted to governance files only.
    """
    phase = (phase or "").strip()

    # T-0078 P1: S4+ 阶段必须存在质量门禁配置
    if phase and phase.startswith(("S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11")):
        qg_config = root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
        if not qg_config.exists():
            return False, (
                "当前阶段需要质量门禁配置，但 .zcode/skills/loop-governance/config.yaml 不存在。"
                "请运行 /loop-onboard 初始化项目，或手动创建质量门禁配置。"
            )

    if phase == "S5-quality":
        q_ok, q_reason = check_quality_gate_evidence(root)
        if not q_ok:
            return q_ok, q_reason
        # T-0082 Phase 5 GAP-3: S5/S6 同时要求安全审计证据
        return check_security_gate_evidence(root)

    if phase == "S6-delivery":
        dm_ok, dm_reason = check_delivery_gate_evidence(root)
        if not dm_ok:
            return dm_ok, dm_reason
        rq_ok, rq_reason = check_runtime_quality_gate(root)
        if not rq_ok:
            return rq_ok, rq_reason
        # T-0082 Phase 5 GAP-3: S5/S6 同时要求安全审计证据
        sec_ok, sec_reason = check_security_gate_evidence(root)
        if not sec_ok:
            return sec_ok, sec_reason
        # T-0093 (AC-02): SLO 门禁 — error budget 耗尽自动冻结发布。
        # 新增约束（B2 §1.5 slo_budget_available 接线）；仅在既有三项
        # S6 检查之后追加，不改动它们各自的语义。开关/豁免/恢复语义见
        # check_slo_gate_evidence 与 loop_core/slo_gate.py。
        slo_ok, slo_reason = check_slo_gate_evidence(root)
        if not slo_ok:
            return slo_ok, slo_reason
        # T-0097 (B2 §3.4): second-failure 门禁 — 同类失败复发未解决阻断。
        # 默认关闭（wave 1 advisory / opt-in：启用只会新增阻断条件，既有
        # 检查零放松）。开关/豁免/闭环语义见 check_second_failure_gate_evidence
        # 与 loop_core/second_failure.py。
        sf_ok, sf_reason = check_second_failure_gate_evidence(root)
        if not sf_ok:
            return sf_ok, sf_reason
        return True, (
            "S6 delivery + runtime quality + security + SLO + second-failure "
            f"gates passed ({slo_reason}; {sf_reason})"
        )

    # T-0082 Phase 5 GAP-2: S7-S11 阶段门禁证据（overall=PASS 的结构化报告）
    if phase in _PHASE_EVIDENCE_FILES:
        ev_ok, ev_reason = _check_phase_evidence_file(root, phase, _PHASE_EVIDENCE_FILES[phase])
        if not ev_ok and phase == "S8-functional-test":
            # S8 兜底：regression_runner 输出（baseline.json，has_regressions=false）
            ev_ok, ev_reason = _check_phase_evidence_file(
                root, phase,
                [".ai/evidence/regression/baseline.json"],
                accept_no_regression=True,
            )
        return ev_ok, ev_reason

    # Other phases: no additional gate checks at this level
    return True, ""
