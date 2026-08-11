"""
quota_decision.py — T-0156 配额决策路由（loopx P0-2 采纳）。

在 cost_tracker 之上提供「该不该跑」的机器决策：输入成本账本 + gate
状态 + 悬空轮次，输出 5 态决策（deliver/ask/wait/repair/quiet）+ reason。

原则：
- **只建议不执行**：放行必须用户 gate（与升级协议一致）。
- **fail-safe**：默认 quiet/wait；输入异常降级 wait。
- hooks/ 零改动；cost_tracker/rounds_heartbeat 只读调用。

用法（经 cli_entries main_quota）：
    loop-quota <root>     # 打印决策 + reason + factors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# 预算阈值：成本占比超过即 quiet（暂停）
BUDGET_RATIO_QUIET = 0.8
# 返工率阈值：超过即 wait（需用户介入方向）
REWORK_RATIO_WAIT = 0.3

DECISIONS = ("deliver", "ask", "wait", "repair", "quiet")


@dataclass
class QuotaContext:
    """决策输入（可由 CLI 组装，也便于测试注入）。"""
    cost_tokens: int = 0
    budget_tokens: int = 0
    rework_ratio: float = 0.0
    pending_gates: list[str] = field(default_factory=list)
    stale_rounds: int = 0
    extra: dict = field(default_factory=dict)


def decide_quota(ctx: QuotaContext) -> dict:
    """5 态决策。fail-safe 优先级：ask > repair > quiet > wait > deliver。"""
    factors = {
        "cost_tokens": ctx.cost_tokens,
        "budget_tokens": ctx.budget_tokens,
        "budget_ratio": round(ctx.cost_tokens / ctx.budget_tokens, 3) if ctx.budget_tokens else None,
        "rework_ratio": round(ctx.rework_ratio, 3),
        "pending_gates": ctx.pending_gates,
        "stale_rounds": ctx.stale_rounds,
    }
    # 1. pending gate → ask（用户裁决，规则层）
    if ctx.pending_gates:
        return {"decision": "ask", "reason": f"pending gate(s): {', '.join(ctx.pending_gates[:3])}", "factors": factors}
    # 2. 悬空轮次 → repair（心跳 fail-stop）
    if ctx.stale_rounds > 0:
        return {"decision": "repair", "reason": f"{ctx.stale_rounds} stale round(s) — fix before continuing", "factors": factors}
    # 3. 超预算 → quiet（暂停节省）
    if ctx.budget_tokens and ctx.cost_tokens / ctx.budget_tokens >= BUDGET_RATIO_QUIET:
        return {"decision": "quiet", "reason": f"budget ratio {factors['budget_ratio']} >= {BUDGET_RATIO_QUIET}", "factors": factors}
    # 4. 返工率高 → wait（需用户方向）
    if ctx.rework_ratio >= REWORK_RATIO_WAIT:
        return {"decision": "wait", "reason": f"rework ratio {ctx.rework_ratio:.2f} >= {REWORK_RATIO_WAIT}", "factors": factors}
    # 5. 正常 → deliver
    return {"decision": "deliver", "reason": "no blockers, within budget", "factors": factors}


def decide_quota_safe(root: Path) -> dict:
    """从项目读取真实输入组装决策；任何异常降级 wait（fail-safe）。"""
    try:
        # cost_tracker 只读（兼容顶层命名空间包与 src 布局两种位置）。
        # T-0156 审查 P2 修复：cost 数据不可得 → 视为"不确定" → wait
        # （fail-safe 默认保守，不得 deliver）。
        cost_available = False
        budget_available = False
        cost_tokens = 0
        budget_tokens = 0
        rework_ratio = 0.0
        try:
            # T-0177 H4: 去除 sys.path.insert(root) 污染（目标项目根的模块
            # 可能覆盖 loop_engine 自身）。cost_tracker 与 quota_decision 同包，
            # 相对导入不依赖 sys.path，src 布局与顶层命名空间包均兼容。
            from .cost_tracker import CostTracker  # noqa: PLC0415 — 延迟导入保持 fail-safe 语义
            summary = CostTracker(root).summary()
            cost_tokens = int(summary.get("total_tokens") or summary.get("tokens") or 0)
            # T-0156 审查 P2-1 方案 A：summary 无独立 budget_tokens 键时
            # budget 维度视为"不确定"（不退化回退为 total —— 那会使
            # ratio 恒 1.0 失去阈值语义），由调用方降级 wait。
            if summary.get("budget_tokens") is not None:
                budget_tokens = int(summary["budget_tokens"])
                budget_available = True
            rework_ratio = float(summary.get("rework_ratio") or 0.0)
            cost_available = True
        except Exception:  # noqa: BLE001 — cost 不可得 → 不确定
            cost_available = False
        # pending gates
        import yaml
        doc = yaml.safe_load((root / ".ai" / "gates.yaml").read_text(encoding="utf-8")) or {}
        pending = [str(g.get("id")) for g in doc.get("gates", [])
                   if isinstance(g, dict) and g.get("status") == "pending"]
        # 悬空轮次（rounds_heartbeat 只读）—— 工具在 loop 安装仓库
        # （.zcode/tools），root 是目标项目；先找工具再对 root 检测。
        stale = 0
        try:
            import subprocess, sys as _sys2
            module_dir = Path(__file__).resolve().parent
            repo_root = module_dir.parent.parent if module_dir.name == "loop_engine" else module_dir.parent
            hb = repo_root / ".zcode" / "tools" / "rounds_heartbeat.py"
            if hb.is_file():
                r = subprocess.run([_sys2.executable, str(hb), str(root)],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 2:
                    stale = 1
        except Exception:  # noqa: BLE001 — 心跳读取失败不算悬空
            stale = 0
        if not cost_available:
            return {"decision": "wait",
                    "reason": "cost data unavailable — uncertain, default wait (fail-safe)",
                    "factors": {"cost_available": False}}
        if not budget_available:
            return {"decision": "wait",
                    "reason": "budget data unavailable — uncertain, default wait (fail-safe)",
                    "factors": {"cost_available": True, "budget_available": False}}
        return decide_quota(QuotaContext(
            cost_tokens=cost_tokens, budget_tokens=budget_tokens,
            rework_ratio=rework_ratio, pending_gates=pending, stale_rounds=stale,
        ))
    except Exception as exc:  # noqa: BLE001 — fail-safe 降级 wait
        return {"decision": "wait", "reason": f"quota input unavailable: {exc}", "factors": {}}
