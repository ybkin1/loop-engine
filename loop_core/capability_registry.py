"""
Capability Registry — explicit registration, sealed snapshots, fail-closed rehydration.

T-0087 U1: the StaffDeck CapabilityRegistry pattern (capabilities/registry.py,
benchmarked in T-0086 staffdeck-benchmark.md U1) applied to loop-engine's
governance assets (.ai/checkers/ and .ai/guards/). The registry answers a gap
guard_health.py cannot: a guard can be alive AND unregistered (omitted from the
governance surface), or registered but silently drifted from the implementation
that was originally bound.

Core mechanics (mirroring StaffDeck, in loop-engine style):
- Explicit registration: each checker/guard is bound once with an id, version,
  contract version, implementation path, description and health requirement.
- seal() freezes the registry: register() after seal raises (immutability).
- Deterministic snapshot: snapshot(requested) filters -> sorts -> serializes
  canonically -> sha256 snapshot_id, exposed as a read-only mapping.
- Fail-closed rehydration: rehydrate() raises instead of silently degrading when
  a payload's version/contract does not match the sealed registry.

The default registry (build_default_registry) is content-addressed: versions are
derived from each implementation file (a __version__ constant when present,
otherwise the sha256 prefix), so drift in the file is visible both as a hash
mismatch and as a version mismatch.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional

# ── Default registration manifest (T-0087 U1) ───────────────────────────────
# capability_id -> (provider_id, rel_path, contract_version, description,
#                   health_required). version/implementation_hash are derived
# from the file content at build time.
_DEFAULT_MANIFEST: dict[str, tuple[str, str, str, str, bool]] = {
    "compile_gate": (
        "checker",
        ".ai/checkers/compile_gate.py",
        "checker-result.schema.yaml@1",
        "编译门禁检查器 — 验证指定目录下所有 .py 文件是否可成功编译",
        True,
    ),
    "run_governance_checks": (
        "checker",
        ".ai/checkers/run_governance_checks.py",
        "checker-result.schema.yaml@1",
        "治理检查聚合器 — 对门禁注册表运行 validate_gate_register 并附加 checker_id",
        True,
    ),
    "validate_gate_register": (
        "checker",
        ".ai/checkers/validate_gate_register.py",
        "checker-result.schema.yaml@1",
        "门禁注册表校验器 — 校验 gates.yaml 结构、状态、审批证据与高风险管理",
        True,
    ),
    "policy_guard": (
        "guard",
        ".ai/guards/policy_guard.py",
        "guard-decision.schema.yaml@1",
        "策略守卫 — 依据 tool-entry-restrictions.yaml 对动作族/路径/门禁状态做出放行决策",
        True,
    ),
    "slo_gate_checker": (
        "checker",
        ".ai/checkers/slo_gate_checker.py",
        "checker-result.schema.yaml@1",
        "SLO 门禁检查器 — 依据 error budget 状态判定发布冻结（FREEZE 阻断 / CONSUMING 警告放行）",
        True,
    ),
    "second_failure_checker": (
        "checker",
        ".ai/checkers/second_failure_checker.py",
        "checker-result.schema.yaml@1",
        "Second-failure 门禁检查器 — 同类失败复发未解决（关联复盘无 open 行动项）时阻断（B2 §3.4）",
        True,
    ),
}

_HASH_PREFIX_LEN = 12  # version derived from content when no __version__ exists


def sha256_file(path: str | Path) -> str:
    """Full sha256 hexdigest of a file's bytes (empty string if unreadable)."""
    p = Path(path)
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def detect_version(path: str | Path, implementation_hash: str) -> str:
    """Read a version constant from the file header, else hash-prefix version.

    版本号从文件实际内容派生：若文件头声明 `__version__ = "x.y.z"` 则用之；
    否则用实现文件 sha256 的前缀作为版本（内容变 → 版本变，漂移可见）。
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError:
        text = ""
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if match:
        return match.group(1)
    return implementation_hash[:_HASH_PREFIX_LEN]


@dataclass(frozen=True)
class CapabilityBinding:
    """One registered checker/guard: identity + version + contract + health."""
    capability_id: str
    provider_id: str            # "checker" | "guard"
    implementation_path: str    # 相对项目根（正斜杠）或绝对路径
    version: str                # 版本号（文件头常量或内容哈希前缀）
    contract_version: str       # 契约版本（输出 schema 标识）
    description: str = ""
    health_required: bool = True
    # 实现文件 sha256 —— 漂移检测基准：注册后文件被改 → 哈希不一致 → DRIFT
    implementation_hash: str = ""

    def to_dict(self) -> dict[str, str]:
        """Plain dict for deterministic serialization (field order stable)."""
        return {
            "capability_id": self.capability_id,
            "provider_id": self.provider_id,
            "implementation_path": self.implementation_path,
            "version": self.version,
            "contract_version": self.contract_version,
            "description": self.description,
            "health_required": self.health_required,
            "implementation_hash": self.implementation_hash,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CapabilityBinding":
        return cls(
            capability_id=str(data["capability_id"]),
            provider_id=str(data.get("provider_id", "")),
            implementation_path=str(data.get("implementation_path", "")),
            version=str(data.get("version", "")),
            contract_version=str(data.get("contract_version", "")),
            description=str(data.get("description", "")),
            health_required=bool(data.get("health_required", True)),
            implementation_hash=str(data.get("implementation_hash", "")),
        )


@dataclass(frozen=True)
class CapabilitySnapshot:
    """Immutable, deterministically fingerprinted view of a registry.

    - entries: read-only mapping (MappingProxyType) capability_id -> binding
    - canonical_json: canonical serialization of the entries (no snapshot_id —
      the id is derived FROM this json, so including it would be circular)
    - snapshot_id: sha256 of canonical_json — same input, same id (AC-01)
    """
    entries: Mapping[str, CapabilityBinding]
    canonical_json: str
    snapshot_id: str

    @classmethod
    def from_bindings(cls, bindings: Iterable[CapabilityBinding]) -> "CapabilitySnapshot":
        ordered = sorted(bindings, key=lambda b: b.capability_id)
        canonical = json.dumps(
            [b.to_dict() for b in ordered],
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        )
        snapshot_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(
            entries=MappingProxyType({b.capability_id: b for b in ordered}),
            canonical_json=canonical,
            snapshot_id=snapshot_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Full payload form — round-trips through rehydrate()."""
        return {
            "snapshot_id": self.snapshot_id,
            "entries": [b.to_dict() for b in self.entries.values()],
        }


class CapabilityRegistry:
    """Explicit registration -> seal -> deterministic snapshot -> fail-closed rehydrate."""

    def __init__(self) -> None:
        self._bindings: dict[str, CapabilityBinding] = {}
        self._sealed = False

    # ── Registration lifecycle ──────────────────────────────────────────
    @property
    def sealed(self) -> bool:
        return self._sealed

    def register(self, binding: CapabilityBinding) -> None:
        """Register one binding. Raises after seal() (AC-01 immutability)."""
        if self._sealed:
            raise RuntimeError(
                f"registry is sealed: cannot register capability "
                f"'{binding.capability_id}' after seal"
            )
        if binding.capability_id in self._bindings:
            raise ValueError(
                f"capability already registered: {binding.capability_id}"
            )
        self._bindings[binding.capability_id] = binding

    def seal(self) -> None:
        """Freeze the registry — register() afterwards raises RuntimeError."""
        self._sealed = True

    # ── Query / snapshot ────────────────────────────────────────────────
    def require(self, capability_id: str) -> CapabilityBinding:
        """Return the binding or raise LookupError — missing is never silent."""
        try:
            return self._bindings[capability_id]
        except KeyError:
            raise LookupError(f"capability not registered: {capability_id}") from None

    def snapshot(self, requested: Optional[Iterable[str]] = None) -> CapabilitySnapshot:
        """Deterministic snapshot of (a subset of) the registry.

        requested=None -> all registered capabilities. Unknown requested ids
        raise LookupError (fail-closed: never silently drop a requested item).
        """
        if requested is None:
            ids = set(self._bindings)
        else:
            ids = set(requested)
            unknown = ids - set(self._bindings)
            if unknown:
                raise LookupError(
                    "requested capabilities not registered: "
                    + ", ".join(sorted(unknown))
                )
        return CapabilitySnapshot.from_bindings(
            b for b in self._bindings.values() if b.capability_id in ids
        )

    # ── Fail-closed rehydration (AC-03) ─────────────────────────────────
    def rehydrate(self, payload: dict[str, Any] | str) -> CapabilitySnapshot:
        """Rehydrate a persisted snapshot payload — mismatch raises, never degrades.

        Fail-closed rules:
        - payload snapshot_id present but != recomputed id  -> ValueError (tamper)
        - payload entry id unknown to the sealed registry    -> LookupError
        - payload version != registered version             -> ValueError
        - payload contract_version != registered contract   -> ValueError
        """
        data = json.loads(payload) if isinstance(payload, str) else payload
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(
                "snapshot payload is invalid: missing 'entries' list"
            )
        bindings = [CapabilityBinding.from_dict(e) for e in raw_entries]

        # 1. Recompute the canonical identity first — a tampered snapshot_id
        #    is rejected before any per-entry comparison.
        provisional = CapabilitySnapshot.from_bindings(bindings)
        claimed = data.get("snapshot_id")
        if claimed and claimed != provisional.snapshot_id:
            raise ValueError(
                f"snapshot_id mismatch (payload claims {claimed}, recomputed "
                f"{provisional.snapshot_id}) — payload tampered or corrupted"
            )

        # 2. Every entry must match the registry exactly — version or contract
        #    mismatch raises instead of silently downgrading the binding.
        for b in bindings:
            if b.capability_id not in self._bindings:
                raise LookupError(
                    f"rehydrate failed: capability not in registry: {b.capability_id}"
                )
            reg = self._bindings[b.capability_id]
            if reg.version != b.version:
                raise ValueError(
                    f"rehydrate failed: version mismatch for {b.capability_id}: "
                    f"registered={reg.version}, payload={b.version}"
                )
            if reg.contract_version != b.contract_version:
                raise ValueError(
                    f"rehydrate failed: contract mismatch for {b.capability_id}: "
                    f"registered={reg.contract_version}, payload={b.contract_version}"
                )
        return provisional


def build_default_registry(project_root: str | Path | None = None,
                           seal: bool = True) -> CapabilityRegistry:
    """Build the built-in registry for .ai/checkers/ and .ai/guards/.

    version/implementation_hash derive from each implementation file's actual
    content (detect_version: __version__ constant, else sha256 prefix), so the
    registry is content-addressed and drift is detectable (T-0087 U1).
    """
    root = Path(project_root) if project_root is not None else Path.cwd()
    registry = CapabilityRegistry()
    for capability_id, (provider_id, rel_path, contract_version,
                        description, health_required) in _DEFAULT_MANIFEST.items():
        impl = (root / rel_path) if not Path(rel_path).is_absolute() else Path(rel_path)
        impl_hash = sha256_file(impl)
        registry.register(CapabilityBinding(
            capability_id=capability_id,
            provider_id=provider_id,
            implementation_path=rel_path,
            version=detect_version(impl, impl_hash),
            contract_version=contract_version,
            description=description,
            health_required=health_required,
            implementation_hash=impl_hash,
        ))
    if seal:
        registry.seal()
    return registry


# ═══════════════════════════════════════════════════════════════════════════
# T-0109 F5: 工具层 capability 化 —— 36 工具分组元数据 + audience 分级
# ═══════════════════════════════════════════════════════════════════════════
# 每个 tools/*.py 模块（36 个）登记：域分组（domain）+ audience 分级 +
# 描述。元数据只读标注（不改变任何工具行为）；注册表完整性由
# tests/test_t0109_f5_tool_capability.py 断言（36 全覆盖 + 无多余）。

# Audience 分级（design-bh-integration.md F5）：
AUDIENCE_WORKFLOW = "workflow"      # 主会话日常工作流直接调用
AUDIENCE_ADVANCED = "advanced"      # 需要领域知识的高级用法
AUDIENCE_MAINTAINER = "maintainer"  # 治理维护/审计用途
AUDIENCES: tuple[str, ...] = (AUDIENCE_WORKFLOW, AUDIENCE_ADVANCED, AUDIENCE_MAINTAINER)

# 域分组（只读标注，供 dashboard/文档/调度消费）：
DOMAIN_GOVERNANCE = "governance"
DOMAIN_EVIDENCE = "evidence"
DOMAIN_QUALITY = "quality"
DOMAIN_SECURITY = "security"
DOMAIN_PLANNING = "planning"
DOMAIN_WORKFLOW = "workflow"
DOMAIN_CONTEXT = "context"
DOMAIN_EXECUTION = "execution"
DOMAIN_REVIEW = "review"
DOMAIN_METRICS = "metrics"
DOMAIN_DASHBOARD = "dashboard"
DOMAIN_DISPATCH = "dispatch"
DOMAIN_SETUP = "setup"
DOMAIN_RUNTIME = "runtime"


@dataclass(frozen=True)
class ToolCapability:
    """一个工具模块的 capability 元数据（T-0109 F5）。"""
    name: str                 # tools/<name>.py 模块名（不含 .py）
    domain: str               # 域分组（DOMAIN_*）
    audience: str             # workflow | advanced | maintainer
    description: str = ""


# name -> ToolCapability（36 个，与 tools/*.py 一一对应；新增工具必须登记，
# 否则注册表完整性测试失败 —— fail-closed，绝不让未登记工具静默存在）。
TOOL_CAPABILITY_MANIFEST: dict[str, ToolCapability] = {
    "loop_dashboard": ToolCapability("loop_dashboard", DOMAIN_DASHBOARD, AUDIENCE_WORKFLOW,
        "AutoPlan dashboard 快照 CLI（text/html/json）"),
    "loop_dispatch_role": ToolCapability("loop_dispatch_role", DOMAIN_DISPATCH, AUDIENCE_MAINTAINER,
        "主线程 role dispatch prepare/complete/verify/list CLI"),
    "loop_execute_phase": ToolCapability("loop_execute_phase", DOMAIN_EXECUTION, AUDIENCE_WORKFLOW,
        "执行完整 Loop 阶段 CLI"),
    "loop_guard_health": ToolCapability("loop_guard_health", DOMAIN_GOVERNANCE, AUDIENCE_MAINTAINER,
        "Guard Health 检测 CLI（T-0083 battery/report）"),
    "loop_metrics": ToolCapability("loop_metrics", DOMAIN_METRICS, AUDIENCE_ADVANCED,
        "Loop-DORA 指标报告 CLI（SLO/error-budget/DORA，含 F1 repair/loop 分离）"),
    "loop_onboard": ToolCapability("loop_onboard", DOMAIN_SETUP, AUDIENCE_MAINTAINER,
        "项目接入/升级/卸载（onboard/update/remove）"),
    "loop_self_audit": ToolCapability("loop_self_audit", DOMAIN_GOVERNANCE, AUDIENCE_MAINTAINER,
        "Loop 自审 CLI（validate/guard-health/compile/pytest/security/static）"),
    "loop_vertical_slice": ToolCapability("loop_vertical_slice", DOMAIN_QUALITY, AUDIENCE_ADVANCED,
        "S1→S6 垂直切片证据链校验 CLI"),
    "mcp_agent_runtime": ToolCapability("mcp_agent_runtime", DOMAIN_RUNTIME, AUDIENCE_ADVANCED,
        "MCP Agent Runtime（绕过 ZCode 子代理限制的批量调度）"),
    "server": ToolCapability("server", DOMAIN_RUNTIME, AUDIENCE_MAINTAINER,
        "MCP stdio 服务器注册表（tools/list + tools/call 分发）"),
    "tool_audit_log": ToolCapability("tool_audit_log", DOMAIN_GOVERNANCE, AUDIENCE_ADVANCED,
        "链式哈希审计日志追加/验证（loop_audit_log）"),
    "tool_certify_role": ToolCapability("tool_certify_role", DOMAIN_GOVERNANCE, AUDIENCE_ADVANCED,
        "角色能力认证挑战（loop_certify_role）"),
    "tool_constraint_check": ToolCapability("tool_constraint_check", DOMAIN_GOVERNANCE, AUDIENCE_WORKFLOW,
        "全部 8 项硬约束检查 C1-C8（loop_constraint_check）"),
    "tool_contract_validate": ToolCapability("tool_contract_validate", DOMAIN_QUALITY, AUDIENCE_ADVANCED,
        "接口契约 schema 验证（contract_validate，委托 module-architect 脚本）"),
    "tool_cost_tracker": ToolCapability("tool_cost_tracker", DOMAIN_METRICS, AUDIENCE_ADVANCED,
        "token 成本报告（cost_report，委托 scripts/cost_tracker.py）"),
    "tool_dashboard": ToolCapability("tool_dashboard", DOMAIN_DASHBOARD, AUDIENCE_WORKFLOW,
        "Dashboard MCP 处理器（status/task_graph/gates/guard_health/snapshot）"),
    "tool_dependency_analysis": ToolCapability("tool_dependency_analysis", DOMAIN_QUALITY, AUDIENCE_ADVANCED,
        "依赖图分析/循环依赖检测（dependency_analysis，委托 system-architect 脚本）"),
    "tool_eval": ToolCapability("tool_eval", DOMAIN_QUALITY, AUDIENCE_MAINTAINER,
        "Agent eval 套件运行器 CLI（guard sample set/自定义 cases）"),
    "tool_evidence_chain": ToolCapability("tool_evidence_chain", DOMAIN_EVIDENCE, AUDIENCE_WORKFLOW,
        "证据链验证/冻结（evidence_verify/evidence_freeze，T-0109 收敛至 loop_core）"),
    "tool_evidence_submit": ToolCapability("tool_evidence_submit", DOMAIN_EVIDENCE, AUDIENCE_WORKFLOW,
        "证据提交并绑定内容哈希（loop_evidence_submit）"),
    "tool_execute_phase": ToolCapability("tool_execute_phase", DOMAIN_EXECUTION, AUDIENCE_WORKFLOW,
        "执行完整 Loop 阶段（loop_execute_phase MCP）"),
    "tool_execution_log": ToolCapability("tool_execution_log", DOMAIN_EXECUTION, AUDIENCE_ADVANCED,
        "执行账本查询（loop_execution_log）"),
    "tool_governance_status": ToolCapability("tool_governance_status", DOMAIN_GOVERNANCE, AUDIENCE_WORKFLOW,
        "治理健康状态摘要（loop_governance_status）"),
    "tool_handoff": ToolCapability("tool_handoff", DOMAIN_WORKFLOW, AUDIENCE_WORKFLOW,
        "角色间交接记录（loop_handoff）"),
    "tool_inbox": ToolCapability("tool_inbox", DOMAIN_WORKFLOW, AUDIENCE_WORKFLOW,
        "需求/消息收件箱（loop_inbox submit/list）"),
    "tool_load_context": ToolCapability("tool_load_context", DOMAIN_CONTEXT, AUDIENCE_WORKFLOW,
        "渐进式角色上下文加载（loop_load_context）"),
    "tool_planner": ToolCapability("tool_planner", DOMAIN_PLANNING, AUDIENCE_WORKFLOW,
        "计划草案生成（loop_planner）"),
    "tool_quality_gates": ToolCapability("tool_quality_gates", DOMAIN_QUALITY, AUDIENCE_WORKFLOW,
        "质量门禁运行（quality_gates_run，委托 quality-engineer 脚本）"),
    "tool_registry_status": ToolCapability("tool_registry_status", DOMAIN_GOVERNANCE, AUDIENCE_MAINTAINER,
        "Capability Registry 状态 CLI（T-0087 snapshot/missing/drift）"),
    "tool_review_packet": ToolCapability("tool_review_packet", DOMAIN_REVIEW, AUDIENCE_WORKFLOW,
        "gate 审批/否决升级/变更请求包生成（loop_review_packet）"),
    "tool_route_intent": ToolCapability("tool_route_intent", DOMAIN_PLANNING, AUDIENCE_WORKFLOW,
        "意图分析/模式推荐（loop_route_intent）"),
    "tool_safe_bash": ToolCapability("tool_safe_bash", DOMAIN_EXECUTION, AUDIENCE_ADVANCED,
        "安全 Bash 执行（路径校验/只读分类，safe_bash MCP）"),
    "tool_security_scan": ToolCapability("tool_security_scan", DOMAIN_SECURITY, AUDIENCE_WORKFLOW,
        "安全扫描（security_scan_run，委托 security-engineer 脚本）"),
    "tool_state": ToolCapability("tool_state", DOMAIN_GOVERNANCE, AUDIENCE_WORKFLOW,
        "项目状态查询（loop_state）"),
    "tool_task_queue": ToolCapability("tool_task_queue", DOMAIN_PLANNING, AUDIENCE_WORKFLOW,
        "任务队列分析（loop_task_queue analysis/ready）"),
    "tool_veto_escalate": ToolCapability("tool_veto_escalate", DOMAIN_REVIEW, AUDIENCE_ADVANCED,
        "否决分析与升级级别（loop_veto_escalate）"),
}


def tool_capability(name: str) -> ToolCapability:
    """按模块名（含/不含 .py 均可）取 capability；未知 → LookupError
    （fail-closed：注册表外工具绝不静默存在）。"""
    key = name[:-3] if name.endswith(".py") else name
    try:
        return TOOL_CAPABILITY_MANIFEST[key]
    except KeyError:
        raise LookupError(f"tool not registered in capability manifest: {key}") from None


def tools_by_domain(domain: str) -> list[str]:
    """某域分组下的工具名（稳定排序）。"""
    return sorted(
        name for name, cap in TOOL_CAPABILITY_MANIFEST.items()
        if cap.domain == domain
    )


def tools_by_audience(audience: str) -> list[str]:
    """某 audience 分级下的工具名（稳定排序）。"""
    if audience not in AUDIENCES:
        raise ValueError(f"非法 audience: {audience!r}（允许 {AUDIENCES}）")
    return sorted(
        name for name, cap in TOOL_CAPABILITY_MANIFEST.items()
        if cap.audience == audience
    )


def all_tool_names() -> list[str]:
    """注册表全部工具模块名（稳定排序，供完整性测试对照）。"""
    return sorted(TOOL_CAPABILITY_MANIFEST)


def build_tool_registry(project_root: str | Path | None = None,
                        seal: bool = True) -> CapabilityRegistry:
    """构建 tools/ 工具层 capability 注册表（T-0109 F5）。

    每个工具模块绑定 content-addressed version/hash（文件被改 → 版本
    漂移可见），provider_id="tool"。36 工具全覆盖由完整性测试断言；
    server.py 的 TOOLS 注册表是 MCP 运行期注册，本注册表是治理期元数据。
    """
    root = Path(project_root) if project_root is not None else Path.cwd()
    registry = CapabilityRegistry()
    for name in all_tool_names():
        rel = f"tools/{name}.py"
        impl = root / rel
        impl_hash = sha256_file(impl)
        registry.register(CapabilityBinding(
            capability_id=name,
            provider_id="tool",
            implementation_path=rel,
            version=detect_version(impl, impl_hash),
            contract_version="tool-capability@1",
            description=tool_capability(name).description,
            health_required=False,  # 工具层为元数据标注，不参与 guard 健康判定
            implementation_hash=impl_hash,
        ))
    if seal:
        registry.seal()
    return registry
