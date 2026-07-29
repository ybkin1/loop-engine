"""
Task Queue — DAG-based dependency resolution and scheduling.

Analyses task_graph.yaml to provide topological ordering, ready-task
identification, blocking analysis, and batch scheduling recommendations.

Design constraints:
- Pure computation — does NOT modify task_graph.yaml or any state file.
- Fail-closed: missing/invalid input returns empty safe defaults.
- All operations are read-only with respect to governance state.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class BlockedTask:
    """A task that cannot be executed due to blocking conditions."""
    task_id: str
    reason: str  # DEPENDENCY, GATE_PENDING, PHASE_BLOCKED, CYCLE_DETECTED
    blocked_by: list[str] = field(default_factory=list)
    detail: str = ""


class TaskQueueError(Exception):
    """Base exception for TaskQueue operations."""


class TaskQueue:
    """DAG-based task queue engine.

    Reads task_graph.yaml (tasks + edges) and gates.yaml to provide
    scheduling recommendations, dependency resolution, and blocking
    analysis.  Does NOT modify any governance files.
    """

    def __init__(self, project_root: str | Path) -> None:
        self._root = Path(project_root)

    # -- Public API ---------------------------------------------------------

    def topological_order(self) -> list[str]:
        """Return all task IDs in dependency-respecting order."""
        tasks, edges = self._load_graph()
        return self._kahn_sort(tasks, edges)

    def ready_tasks(self) -> list[str]:
        """Return tasks with all dependencies satisfied and gates approved."""
        tasks, edges = self._load_graph()
        order = self._kahn_sort(tasks, edges)
        ready = []
        for tid in order:
            task = tasks.get(tid, {})
            status = str(task.get("status", "")).lower()
            if status == "pending":
                if self._deps_satisfied(tid, edges, tasks):
                    if not self._gate_blocked(tid):
                        ready.append(tid)
        return ready

    def blocked_tasks(self) -> list[BlockedTask]:
        """Return all blocked tasks with reasons."""
        tasks, edges = self._load_graph()
        blocked = []
        for tid, task in tasks.items():
            status = str(task.get("status", "")).lower()
            if status == "completed":
                continue
            # Check dependency blocking
            deps = self._unsatisfied_deps(tid, edges, tasks)
            if deps:
                blocked.append(BlockedTask(
                    task_id=tid,
                    reason="DEPENDENCY",
                    blocked_by=deps,
                    detail=f"Waiting for: {', '.join(deps)}",
                ))
                continue
            # Check gate blocking
            if self._gate_blocked(tid):
                blocked.append(BlockedTask(
                    task_id=tid,
                    reason="GATE_PENDING",
                    blocked_by=[],
                    detail="Gate approval required",
                ))
                continue
        return blocked

    def detect_cycles(self) -> list[list[str]]:
        """Detect dependency cycles. Returns list of cycle paths."""
        tasks, edges = self._load_graph()
        return self._find_cycles(tasks, edges)

    def critical_path(self) -> list[str]:
        """Compute the longest dependency chain (critical path)."""
        tasks, edges = self._load_graph()
        return self._longest_path(tasks, edges)

    def next_recommended(self) -> Optional[str]:
        """Return the single highest-priority ready task."""
        ready = self.ready_tasks()
        if not ready:
            return None
        tasks, _ = self._load_graph()
        # Sort by priority (P0 > P1 > P2 > P3)
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        ready.sort(key=lambda tid: priority_order.get(
            str(tasks.get(tid, {}).get("priority", "P2")), 2
        ))
        return ready[0]

    def suggest_batch(self, max_parallel: int = 3) -> list[str]:
        """Return ready tasks that can execute in parallel."""
        ready = self.ready_tasks()
        tasks, edges = self._load_graph()
        # Filter to tasks with no mutual dependencies
        independent = []
        for tid in ready:
            deps = self._unsatisfied_deps(tid, edges, tasks)
            if not deps:
                independent.append(tid)
        return independent[:max_parallel]

    def task_stats(self) -> dict:
        """Return task count statistics."""
        tasks, _ = self._load_graph()
        stats = {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "blocked": 0}
        for task in tasks.values():
            stats["total"] += 1
            status = str(task.get("status", "")).lower()
            if status == "completed":
                stats["completed"] += 1
            elif status in ("active", "in_progress"):
                stats["in_progress"] += 1
            elif status == "pending":
                stats["pending"] += 1
        blocked_list = self.blocked_tasks()
        stats["blocked"] = len(blocked_list)
        return stats

    # -- Internal helpers ---------------------------------------------------

    def _load_graph(self) -> tuple[dict, dict]:
        """Load tasks and edges from task_graph.yaml."""
        ai_dir = self._root / ".ai"
        graph_path = ai_dir / "task_graph.yaml"
        if not graph_path.exists():
            return {}, {}

        import yaml
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return {}, {}

        tasks = {}
        for t in data.get("tasks", []):
            tid = t.get("id")
            if tid:
                tasks[tid] = t

        edges = defaultdict(list)
        for e in data.get("edges", []):
            src = e.get("from")
            dst = e.get("to")
            if src and dst:
                edges[src].append(dst)

        return tasks, edges

    def _load_gates(self) -> dict:
        """Load gate status from gates.yaml."""
        ai_dir = self._root / ".ai"
        gates_path = ai_dir / "gates.yaml"
        if not gates_path.exists():
            return {}

        import yaml
        try:
            with open(gates_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return {}

        gate_map = {}
        for g in data.get("gates", []):
            gid = g.get("id")
            tid = g.get("task_id")
            if gid and tid:
                gate_map[tid] = g
        return gate_map

    def _kahn_sort(self, tasks: dict, edges: dict) -> list[str]:
        """Topological sort using Kahn's algorithm."""
        in_degree = {tid: 0 for tid in tasks}
        adj = defaultdict(list)
        for src, dsts in edges.items():
            for dst in dsts:
                if src in in_degree and dst in in_degree:
                    adj[src].append(dst)
                    in_degree[dst] += 1

        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _deps_satisfied(self, tid: str, edges: dict, tasks: dict) -> bool:
        """Check if all predecessors of tid are completed."""
        predecessors = [src for src, dsts in edges.items() if tid in dsts]
        for pred in predecessors:
            pred_status = str(tasks.get(pred, {}).get("status", "")).lower()
            if pred_status != "completed":
                return False
        return True

    def _unsatisfied_deps(self, tid: str, edges: dict, tasks: dict) -> list[str]:
        """Return list of predecessor IDs that are not completed."""
        predecessors = [src for src, dsts in edges.items() if tid in dsts]
        return [
            pred for pred in predecessors
            if str(tasks.get(pred, {}).get("status", "")).lower() != "completed"
        ]

    def _gate_blocked(self, tid: str) -> bool:
        """Check if task has a pending/blocked gate."""
        gate_map = self._load_gates()
        gate = gate_map.get(tid)
        if not gate:
            return False
        status = str(gate.get("status", "")).lower()
        return status in ("pending", "blocked", "rejected")

    def _find_cycles(self, tasks: dict, edges: dict) -> list[list[str]]:
        """Find all cycles using DFS with coloring."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in tasks}
        cycles = []

        def _dfs(node: str, path: list[str]):
            color[node] = GRAY
            path.append(node)
            for neighbor in edges.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif color[neighbor] == WHITE:
                    _dfs(neighbor, path)
            path.pop()
            color[node] = BLACK

        for tid in tasks:
            if color[tid] == WHITE:
                _dfs(tid, [])
        return cycles

    def _longest_path(self, tasks: dict, edges: dict) -> list[str]:
        """Compute longest path in DAG using DP."""
        if not tasks:
            return []
        order = self._kahn_sort(tasks, edges)
        dist = {tid: 1 for tid in tasks}
        prev = {tid: None for tid in tasks}

        for u in order:
            for v in edges.get(u, []):
                if v in dist and dist[u] + 1 > dist[v]:
                    dist[v] = dist[u] + 1
                    prev[v] = u

        end = max(dist, key=dist.get) if dist else list(tasks.keys())[0]
        path = []
        while end:
            path.append(end)
            end = prev.get(end)
        path.reverse()
        return path

    def to_dict(self) -> dict:
        """Return a full analysis as a dictionary (for schema-compliant output)."""
        return {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "topological_order": self.topological_order(),
            "ready_tasks": self.ready_tasks(),
            "blocked_tasks": [
                {"task_id": b.task_id, "reason": b.reason, "blocked_by": b.blocked_by, "detail": b.detail}
                for b in self.blocked_tasks()
            ],
            "cycles": self.detect_cycles(),
            "critical_path": self.critical_path(),
            "next_recommended": self.next_recommended(),
            "suggested_batch": self.suggest_batch(),
            "task_stats": self.task_stats(),
        }
