"""
risk_grading.py — T-0157 风险驱动执行分级（loopx P0-3 采纳）。

按任务描述/标志自动判定执行等级（LIGHT/STANDARD/FULL）：
- critical_triggers 任一命中 → FULL（不可降级，fail-closed 底线）
- score_rules 打分按阈值分级
- ACCEPTED_RISK：降级需用户确认 + 理由（记录事件，不自动改 gate）
- SKIPPED 白名单：仅审核/审计类门可跳过（开发/验证/健康门保留）

原则：
- **advisory-only**：分级仅建议/呈现，现有 gate 批准语义零变更。
- hooks/ 零改动；内核零触碰。

用法（经 cli_entries main_risk）：
    loop-risk <task_desc>   # 输出分级建议
"""

from __future__ import annotations

from pathlib import Path

# ── 常量 ─────────────────────────────────────────────────────────────
CRITICAL_TRIGGERS = (
    "auth", "permission", "db_schema", "external_side_effect",
    "core_state_transition", "secret", "payment", "production_data",
)

SCORE_RULES = {
    "api_contract": 3,
    "sql": 3,
    "mq": 3,
    "ambiguous_requirement": 2,
    "multi_module": 1,
    "test_only": -1,
    "docs_only": -1,
}

SCORE_FULL = 4
SCORE_STANDARD = 2

# SKIPPED 白名单：LIGHT 下仅审核/审计类门可建议跳过（单一事实源）
MODE_SKIPPABLE_STAGES = {"design_review", "audit_review"}

LEVELS = ("LIGHT", "STANDARD", "FULL")


def grade_risk(task_desc: str, flags: dict | None = None) -> dict:
    """三态分级。flags: {trigger: bool, score_signal: bool, ...}。"""
    flags = flags or {}
    triggers_hit = [t for t in CRITICAL_TRIGGERS
                    if flags.get(t) or _trigger_in_desc(task_desc, t)]
    if triggers_hit:
        return {
            "level": "FULL",
            "triggers_hit": triggers_hit,
            "score": None,
            "reason": f"critical trigger(s): {', '.join(triggers_hit)} — cannot downgrade",
        }
    score = 0
    signals = []
    for signal, pts in SCORE_RULES.items():
        if flags.get(signal) or _signal_in_desc(task_desc, signal):
            score += pts
            signals.append(signal)
    if score >= SCORE_FULL:
        level = "FULL"
    elif score >= SCORE_STANDARD:
        level = "STANDARD"
    else:
        level = "LIGHT"
    return {
        "level": level,
        "triggers_hit": [],
        "score": score,
        "reason": f"score {score} ({', '.join(signals) or 'no signals'}) → {level}",
    }


def _trigger_in_desc(desc: str, trigger: str) -> bool:
    """从任务描述推断 critical trigger（保守关键字，防漏判）。"""
    desc_l = (desc or "").lower()
    keywords = {
        "auth": ("登录", "认证", "auth", "login"),
        "permission": ("权限", "permission", "rbac"),
        "db_schema": ("数据库表", "建表", "改表", "schema", "ddl", "迁移表"),
        "external_side_effect": ("外部系统", "第三方", "webhook", "external"),
        "core_state_transition": ("状态机", "状态流转", "phase", "gate 语义"),
        "secret": ("密钥", "token", "密码", "secret", "api key"),
        "payment": ("支付", "扣款", "账单", "payment", "billing"),
        "production_data": ("生产数据", "线上数据", "production data"),
    }
    return any(k in desc_l for k in keywords.get(trigger, ()))


def _signal_in_desc(desc: str, signal: str) -> bool:
    """从任务描述文本推断信号（关键字匹配，保守）。"""
    desc_l = (desc or "").lower()
    keywords = {
        "api_contract": ("api", "interface", "contract", "契约", "接口"),
        "sql": ("sql", "query", "数据库查询", "数据访问"),
        "mq": ("queue", "mq", "消息队列", "kafka", "rabbitmq"),
        "ambiguous_requirement": ("模糊", "不确定", "待确认", "tbd", "maybe"),
        "multi_module": ("跨模块", "多个模块", "multi-module"),
        "test_only": ("test only", "仅测试", "只加测试"),
        "docs_only": ("docs only", "仅文档", "文档修改", "注释"),
    }
    return any(k in desc_l for k in keywords.get(signal, ()))


def accepted_risk(root: Path, task_id: str, level: str, reason: str) -> bool:
    """记录 ACCEPTED_RISK（降级确认 + 理由，事件日志 user actor）。

    不自动改变 gate 流程（advisory-only）；仅留审计痕迹。
    """
    try:
        import sys as _sys
        # 向上查找仓库根（兼容 src 布局：模块在 <root>/src/loop_engine/ 下）
        module_dir = Path(__file__).resolve().parent
        repo_root = module_dir.parent.parent if module_dir.name == "loop_engine" else module_dir.parent
        _sys.path.insert(0, str(repo_root / ".zcode" / "tools"))
        from event_log import append
        # T-0158: 独立 risk_accepted 事件类型（审计语义纯净，不复用 gate_approved）
        return append(root, "risk_accepted",
                      task_id=task_id, actor="user",
                      detail={"accepted_risk": True, "level": level, "reason": reason})
    except Exception:  # noqa: BLE001 — 记录失败不阻断
        return False


def is_skippable(stage: str, level: str) -> bool:
    """SKIPPED 白名单校验：仅 LIGHT 可建议跳过审核/审计门（T-0158 收紧）。

    STANDARD/FULL 一律不可跳过（任务描述"LIGHT 仅允许跳过审核/审计门"）。
    """
    if level != "LIGHT":
        return False
    return stage in MODE_SKIPPABLE_STAGES
