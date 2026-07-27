from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class GraphError(ValueError):
    """Raised when a task graph is incomplete or cyclic."""


@dataclass(frozen=True)
class TaskNode:
    task_id: str
    title: str
    phase_id: str
    owner_role: str
    depends_on: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    internal_checks: tuple[str, ...] = ()
    user_gate: bool = False
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskGraph:
    nodes: dict[str, TaskNode] = field(default_factory=dict)

    def add(self, node: TaskNode) -> None:
        if node.task_id in self.nodes:
            raise GraphError(f"duplicate task: {node.task_id}")
        self.nodes[node.task_id] = node

    def validate(self) -> None:
        for node in self.nodes.values():
            missing = sorted(set(node.depends_on) - self.nodes.keys())
            if missing:
                raise GraphError(f"{node.task_id} missing dependencies: {', '.join(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise GraphError(f"cycle detected at {task_id}")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in self.nodes[task_id].depends_on:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in self.nodes:
            visit(task_id)

    def ready(self, completed: set[str]) -> tuple[TaskNode, ...]:
        self.validate()
        return tuple(
            node
            for node in self.nodes.values()
            if node.task_id not in completed and set(node.depends_on) <= completed
        )

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [node.to_dict() for node in self.nodes.values()]}


def default_task_graph() -> TaskGraph:
    """Create a conservative role-per-phase skeleton for initial routing."""
    from codex_loop.planning.phases import default_phases

    graph = TaskGraph()
    previous: tuple[str, ...] = ()
    for phase in default_phases():
        phase_nodes: list[str] = []
        for index, role_id in enumerate(phase.required_roles):
            task_id = f"{phase.phase_id}-{role_id}"
            dependencies = previous if index == 0 else (phase_nodes[-1],)
            graph.add(TaskNode(
                task_id, f"{phase.name}: {role_id}", phase.phase_id, role_id,
                dependencies, expected_outputs=(), internal_checks=phase.internal_checks,
                user_gate=bool(phase.user_decision) and index == len(phase.required_roles) - 1,
            ))
            phase_nodes.append(task_id)
        previous = tuple(phase_nodes)
    graph.validate()
    return graph
