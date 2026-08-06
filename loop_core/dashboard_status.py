"""dashboard_status.py — 项目状态仪表外部模块（T-0124 拆分）。

从 loop_core/dashboard_views.py 拆出：`ProjectStatus` / `Dashboard`（状态
生成/文本/HTML 呈现）。类方法自包含（yaml 直接加载，零壳引用），原样提取。
壳文件同名 re-export。行为逐字节等价。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

@dataclass
class ProjectStatus:
    """Complete project health snapshot."""
    generated_at: str = ""
    project_name: str = ""
    current_phase: str = ""
    loop_mode: str = ""
    current_task_id: Optional[str] = None
    current_gate_id: Optional[str] = None
    active_plan_id: Optional[str] = None
    task_stats: dict = field(default_factory=lambda: {
        "total": 0, "completed": 0, "in_progress": 0, "pending": 0, "blocked": 0,
    })
    ready_tasks: list[str] = field(default_factory=list)
    blocked_tasks: list[dict] = field(default_factory=list)
    next_recommended: Optional[str] = None
    pending_gates: list[dict] = field(default_factory=list)
    phase_progress: dict[str, float] = field(default_factory=dict)
    active_risks: list[str] = field(default_factory=list)
    next_action: str = ""
    inbox_count: int = 0
    health_indicator: str = "RED"


class Dashboard:
    """Generates project health snapshots from governance state."""

    def __init__(self, project_root: str | Path) -> None:
        self._root = Path(project_root)

    def generate(self) -> ProjectStatus:
        """Generate a complete project status snapshot."""
        status = ProjectStatus()
        status.generated_at = datetime.now(timezone.utc).isoformat()

        # Load state.yaml
        state = self._load_state()

        status.project_name = state.get("project_name", "unknown")
        status.current_phase = state.get("current_phase", "")
        status.loop_mode = state.get("loop_mode", "FULL")
        status.current_task_id = state.get("current_task_id")
        status.current_gate_id = state.get("current_gate_id")
        status.active_plan_id = state.get("active_plan_id")

        # Task statistics from queue engine
        try:
            from loop_core.task_queue import TaskQueue
            queue = TaskQueue(str(self._root))
            status.task_stats = queue.task_stats()
            status.ready_tasks = queue.ready_tasks()
            blocked = queue.blocked_tasks()
            status.blocked_tasks = [
                {"task_id": b.task_id, "reason": b.reason, "blocked_by": b.blocked_by}
                for b in blocked
            ]
            status.next_recommended = queue.next_recommended()
        except Exception:
            pass

        # Pending gates
        status.pending_gates = self._pending_gates()

        # Phase progress
        status.phase_progress = self._phase_progress()

        # Risks
        status.active_risks = self._load_risks()

        # Inbox count
        try:
            from loop_core.inbox import inbox_summary
            summary = inbox_summary(str(self._root))
            status.inbox_count = summary.get("total", 0)
        except Exception:
            pass

        # Health indicator
        status.health_indicator = self._compute_health(status)

        # Next action
        status.next_action = self._recommend_action(status)

        return status

    def to_dict(self, status: ProjectStatus | None = None) -> dict:
        """Convert ProjectStatus to a dictionary."""
        if status is None:
            status = self.generate()
        return {
            "generated_at": status.generated_at,
            "project_name": status.project_name,
            "current_phase": status.current_phase,
            "loop_mode": status.loop_mode,
            "current_task_id": status.current_task_id,
            "current_gate_id": status.current_gate_id,
            "active_plan_id": status.active_plan_id,
            "task_stats": status.task_stats,
            "ready_tasks": status.ready_tasks,
            "blocked_tasks": status.blocked_tasks,
            "next_recommended": status.next_recommended,
            "pending_gates": status.pending_gates,
            "phase_progress": status.phase_progress,
            "active_risks": status.active_risks,
            "next_action": status.next_action,
            "inbox_count": status.inbox_count,
            "health_indicator": status.health_indicator,
        }

    def to_markdown(self, status: ProjectStatus | None = None) -> str:
        """Render ProjectStatus as human-readable Markdown."""
        if status is None:
            status = self.generate()

        health_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
            status.health_indicator, "⚪"
        )

        lines = [
            f"# {health_emoji} {status.project_name} — {status.health_indicator}",
            "",
            f"**Phase**: {status.current_phase} | **Mode**: {status.loop_mode}",
            "",
            "## Task Progress",
            "",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| Total | {status.task_stats['total']} |",
            f"| ✅ Completed | {status.task_stats['completed']} |",
            f"| 🔄 In Progress | {status.task_stats['in_progress']} |",
            f"| 📋 Pending | {status.task_stats['pending']} |",
            f"| 🚫 Blocked | {status.task_stats['blocked']} |",
            "",
        ]

        if status.ready_tasks:
            lines.append("## Ready Tasks")
            lines.append("")
            for tid in status.ready_tasks[:5]:
                lines.append(f"- {tid}")
            lines.append("")

        if status.blocked_tasks:
            lines.append("## Blocked Tasks")
            lines.append("")
            for b in status.blocked_tasks[:5]:
                lines.append(f"- **{b['task_id']}**: {b['reason']} ({', '.join(b['blocked_by'])})")
            lines.append("")

        if status.pending_gates:
            lines.append("## Pending Gates")
            lines.append("")
            for g in status.pending_gates[:3]:
                lines.append(f"- {g.get('gate_id', '?')} ({g.get('status', '?')})")
            lines.append("")

        if status.active_risks:
            lines.append("## Active Risks")
            lines.append("")
            for r in status.active_risks[:5]:
                lines.append(f"- {r}")
            lines.append("")

        lines.append(f"## Next Action")
        lines.append("")
        lines.append(f"{status.next_action}")
        lines.append("")

        lines.append(f"*Generated: {status.generated_at}*")
        return "\n".join(lines)

    # -- Internal helpers ---------------------------------------------------

    def _load_state(self) -> dict:
        import yaml
        state_path = self._root / ".ai" / "state.yaml"
        if not state_path.exists():
            return {}
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _pending_gates(self) -> list[dict]:
        import yaml
        gates_path = self._root / ".ai" / "gates.yaml"
        if not gates_path.exists():
            return []
        try:
            with open(gates_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return []

        pending = []
        for g in data.get("gates", []):
            if str(g.get("status", "")).lower() == "pending":
                pending.append({
                    "gate_id": g.get("id", ""),
                    "task_id": g.get("task_id", ""),
                    "gate_type": g.get("gate_type", ""),
                    "status": g.get("status", ""),
                })
        return pending

    def _phase_progress(self) -> dict[str, float]:
        """Estimate phase completion based on task statuses."""
        import yaml
        graph_path = self._root / ".ai" / "task_graph.yaml"
        if not graph_path.exists():
            return {}
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return {}

        phase_tasks = {}
        for t in data.get("tasks", []):
            phase = t.get("phase", "unknown")
            if phase not in phase_tasks:
                phase_tasks[phase] = {"total": 0, "completed": 0}
            phase_tasks[phase]["total"] += 1
            if str(t.get("status", "")).lower() == "completed":
                phase_tasks[phase]["completed"] += 1

        return {
            phase: info["completed"] / info["total"] if info["total"] > 0 else 0
            for phase, info in phase_tasks.items()
        }

    def _load_risks(self) -> list[str]:
        """Extract active risks from KNOWN_ISSUES.md."""
        issues_path = self._root / ".ai" / "KNOWN_ISSUES.md"
        if not issues_path.exists():
            return []
        try:
            content = issues_path.read_text(encoding="utf-8")
            risks = []
            for line in content.split("\n"):
                if line.strip().startswith("- ") and "open" in line.lower():
                    risks.append(line.strip()[2:])
            return risks[:10]
        except Exception:
            return []

    def _compute_health(self, status: ProjectStatus) -> str:
        """Compute overall project health indicator."""
        if status.task_stats["blocked"] > 5:
            return "RED"
        if status.pending_gates:
            return "YELLOW"
        if status.task_stats["completed"] > 0 and status.task_stats["blocked"] == 0:
            return "GREEN"
        if status.task_stats["in_progress"] > 0:
            return "YELLOW"
        return "YELLOW"

    def _recommend_action(self, status: ProjectStatus) -> str:
        """Recommend next action for user or AI session."""
        if status.pending_gates:
            gate_ids = [g["gate_id"] for g in status.pending_gates[:3]]
            return f"Pending gates require user decision: {', '.join(gate_ids)}"
        if status.ready_tasks:
            return f"Ready to execute: {', '.join(status.ready_tasks[:3])}"
        if status.blocked_tasks:
            blocked_reasons = set(b["reason"] for b in status.blocked_tasks)
            return f"Tasks blocked: {', '.join(blocked_reasons)}. Review dependencies and gates."
        if not status.current_task_id:
            return "No active task. Submit a requirement or select a task to begin."
        return "Continue with current task execution."


def write_snapshot_files(
    root: str | Path,
    out_dir: str | Path | None = None,
    include_json: bool = False,
) -> dict[str, Path]:
    """Write the text + self-contained HTML snapshot (optionally JSON).

    Default output directory: ``<root>/.ai/evidence/observability/``.
    Returns the written file paths.  Data sources are never modified.
    """
    from loop_core.dashboard_views import (
        DashboardViews,
        SNAPSHOT_HTML_NAME,
        SNAPSHOT_JSON_NAME,
        SNAPSHOT_MD_NAME,
    )
    root_path = Path(root)
    target_dir = (
        Path(out_dir) if out_dir is not None
        else root_path / ".ai" / "evidence" / "observability"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    views = DashboardViews(root_path)
    snapshot = views.build_snapshot()
    written: dict[str, Path] = {}
    md_path = target_dir / SNAPSHOT_MD_NAME
    md_path.write_text(views.render_text(snapshot), encoding="utf-8")
    written["text"] = md_path
    html_path = target_dir / SNAPSHOT_HTML_NAME
    html_path.write_text(views.render_html(snapshot), encoding="utf-8")
    written["html"] = html_path
    if include_json:
        json_path = target_dir / SNAPSHOT_JSON_NAME
        json_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written["json"] = json_path
    return written


# ═══════════════════════════════════════════════════════════════════════════
# T-0109 F5: dashboard 四层合并 → 单一实现（本模块）
# ═══════════════════════════════════════════════════════════════════════════
# 原四处：loop_core/dashboard_views.py（DashboardViews，本模块主体）、
# loop_core/status_dashboard.py（Dashboard 健康快照）、tools/tool_dashboard.py
# （MCP 处理器壳）、tools/loop_dashboard.py（CLI 壳）。T-0109 将
# ProjectStatus/Dashboard 收敛至本模块（下方原样迁移），
# loop_core/status_dashboard.py 降级为兼容 re-export shim
# （hooks/scripts/session_brief.py 等既有 import 路径保持可用，
# 行为等价由 test_status_dashboard.py + 等价断言覆盖）。
# Dashboard 只读：不修改任何治理文件；fail-closed：缺数据 → 安全默认值。
# ── 以下为 status_dashboard.py 原实现（T-0109 迁移，逻辑零改动）──

from dataclasses import dataclass as _dataclass, field as _field
from datetime import datetime as _datetime, timezone as _timezone
from typing import Optional as _Optional


# T-0124 拆分：ProjectStatus/Dashboard 移入 dashboard_status 外部模块
#（同名 re-export，公开面保持——dir() 逐名一致）
from loop_core.dashboard_status import Dashboard, ProjectStatus  # noqa: F401 — re-export，公开面保持

