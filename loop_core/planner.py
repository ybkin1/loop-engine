"""
Planner — Automatic plan generation from requirements.

Takes an ACCEPTED requirement and decomposes it into a task graph draft.
The draft is READ-ONLY — it must be approved via a plan-approval Gate
before any tasks are registered in task_graph.yaml.

Design constraints:
- Does NOT write to task_graph.yaml directly (user gate required).
- Uses intent_router for requirement analysis.
- Uses role_orchestrator for phase-to-role mapping.
- Fail-closed: exceptions return BLOCKED.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class EdgeType(str, Enum):
    BLOCKS = "BLOCKS"
    INFORMS = "INFORMS"
    RELATED = "RELATED"


class Complexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class TaskDraft:
    """A single task in a plan draft (not yet registered)."""
    title: str
    description: str
    phase: str
    acceptance_criteria: list[str] = field(default_factory=list)
    suggested_roles: list[str] = field(default_factory=list)
    estimated_complexity: Complexity = Complexity.MEDIUM
    priority: str = "P2"
    depends_on_plan_index: list[int] = field(default_factory=list)


@dataclass
class PlanEdge:
    """A dependency edge between two tasks in a plan draft."""
    from_task_index: int
    to_task_index: int
    edge_type: EdgeType = EdgeType.BLOCKS


@dataclass
class PlanDraft:
    """A generated plan draft — NOT registered in task_graph.yaml."""
    plan_id: str
    requirement_id: str
    tasks: list[TaskDraft] = field(default_factory=list)
    edges: list[PlanEdge] = field(default_factory=list)
    estimated_phases: list[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    clarification_needed: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "requirement_id": self.requirement_id,
            "status": self.status.value,
            "tasks": [
                {
                    "title": t.title,
                    "description": t.description,
                    "phase": t.phase,
                    "acceptance_criteria": t.acceptance_criteria,
                    "suggested_roles": t.suggested_roles,
                    "estimated_complexity": t.estimated_complexity.value,
                    "priority": t.priority,
                    "depends_on_plan_index": t.depends_on_plan_index,
                }
                for t in self.tasks
            ],
            "edges": [
                {
                    "from_task_index": e.from_task_index,
                    "to_task_index": e.to_task_index,
                    "edge_type": e.edge_type.value,
                }
                for e in self.edges
            ],
            "estimated_phases": self.estimated_phases,
            "clarification_needed": self.clarification_needed,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


class PlannerError(Exception):
    """Base exception for Planner operations."""


class Planner:
    """Generates plan drafts from accepted requirements.

    The planner analyses a requirement description and decomposes it
    into a structured task graph with dependencies.  It does NOT
    register tasks — that requires user gate approval.
    """

    # Standard phases for common project types (legacy, keep for backward compat)
    DEFAULT_PHASES = [
        "S1-requirements", "S2-architecture", "S3-interface",
        "S4-implementation", "S5-quality", "S6-delivery",
    ]

    def __init__(self, project_root: str | Path) -> None:
        self._root = Path(project_root)
        self._plans_dir = self._root / ".ai" / "plans"
        self._plans_dir.mkdir(parents=True, exist_ok=True)
        self._last_analysis = None
        self._last_route = None

    def generate(self, title: str, description: str, requirement_id: str | None = None) -> PlanDraft:
        """Generate a plan draft from a requirement description.

        Returns a PlanDraft that is NOT registered — the user must
        approve it via a plan-approval Gate.
        """
        if not description.strip():
            raise PlannerError("Description must not be empty")

        plan_id = self._next_plan_id()
        phases = self._select_phases(description)
        tasks = self._decompose(title, description, phases)
        edges = self._derive_edges(tasks)

        draft = PlanDraft(
            plan_id=plan_id,
            requirement_id=requirement_id or "",
            tasks=tasks,
            edges=edges,
            estimated_phases=phases,
        )
        self._save(draft)
        return draft

    def get(self, plan_id: str) -> PlanDraft:
        """Retrieve a plan draft by ID."""
        path = self._plans_dir / f"{plan_id}.yaml"
        if not path.exists():
            raise PlannerError(f"Plan not found: {plan_id}")
        return self._load(path)

    def list_all(self, status: str | None = None) -> list[PlanDraft]:
        """List all plan drafts, optionally filtered by status."""
        results = []
        for entry in sorted(self._plans_dir.glob("PLAN-*.yaml")):
            try:
                draft = self._load(entry)
                if status is None or draft.status.value == status:
                    results.append(draft)
            except Exception:
                continue
        return results

    def approve(self, plan_id: str, gate_id: str) -> PlanDraft:
        """Mark a plan as approved (called after user gate approval)."""
        draft = self.get(plan_id)
        draft.status = PlanStatus.APPROVED
        draft.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(draft)
        return draft

    # -- Internal helpers ---------------------------------------------------

    # Phase sets for different Loop modes
    LIGHTWEIGHT_PHASES = ["S4-implementation", "S6-delivery"]
    STANDARD_PHASES = ["S1-requirements", "S2-architecture", "S4-implementation", "S5-quality", "S6-delivery"]
    FULL_PHASES = [
        "S1-requirements", "S2-architecture", "S3-interface",
        "S4-implementation", "S5-quality", "S6-delivery",
    ]

    # Role recommendations per phase
    PHASE_ROLES = {
        "S1-requirements": ["product-manager", "project-manager"],
        "S2-architecture": ["system-architect", "module-architect"],
        "S3-interface": ["module-architect", "developer"],
        "S4-implementation": ["developer"],
        "S5-quality": ["quality-engineer", "test-engineer", "security-engineer"],
        "S6-delivery": ["delivery-manager", "release-engineer"],
    }

    # Task templates per phase (more than one task for complex phases)
    PHASE_TASK_TEMPLATES = {
        "S1-requirements": [
            ("需求澄清与范围定义", "Clarify requirements and define scope boundaries."),
            ("验收标准制定", "Define acceptance criteria for each feature."),
        ],
        "S2-architecture": [
            ("系统架构设计", "Design system architecture and component topology."),
            ("数据模型设计", "Design data models and storage strategy."),
        ],
        "S3-interface": [
            ("接口契约定义", "Define API/interfaces contracts with schemas."),
        ],
        "S4-implementation": [
            ("核心逻辑实现", "Implement core business logic."),
            ("单元测试编写", "Write unit tests for all modules."),
        ],
        "S5-quality": [
            ("质量门禁检查", "Run quality gates: lint, typecheck, coverage, security scan."),
            ("集成测试验证", "Verify integration tests pass."),
        ],
        "S6-delivery": [
            ("部署准备", "Prepare deployment artifacts and documentation."),
            ("交付验收", "Run delivery gate checks and produce release decision."),
        ],
    }

    def _select_phases(self, description: str) -> list[str]:
        """Select applicable phases using intent_router analysis."""
        desc_lower = description.lower()

        # Primary: use intent_router for domain-aware analysis
        try:
            from loop_core.intent_router import IntentRouter
            router = IntentRouter()
            analysis = router.analyze(description)
            route_result = router.route(analysis)

            # Cache analysis for reuse in _decompose
            self._last_analysis = analysis
            self._last_route = route_result

            mode = str(route_result.mode) if route_result else 'STANDARD'
            if 'LIGHTWEIGHT' in mode:
                return self.LIGHTWEIGHT_PHASES
            elif 'FULL' in mode:
                return self.FULL_PHASES
            else:
                return self.STANDARD_PHASES
        except (ImportError, Exception):
            self._last_analysis = None
            self._last_route = None

        # Fallback: keyword heuristics
        high_risk_keywords = ["auth", "payment", "security", "production", "deploy", "database", "migration"]
        has_high_risk = any(kw in desc_lower for kw in high_risk_keywords)
        web_keywords = ["web", "frontend", "ui", "page", "browser", "responsive", "mobile"]
        is_web = any(kw in desc_lower for kw in web_keywords)

        if has_high_risk:
            return self.FULL_PHASES
        if is_web:
            return self.STANDARD_PHASES
        return self.STANDARD_PHASES

    def _decompose(self, title: str, description: str, phases: list[str]) -> list[TaskDraft]:
        """Decompose a requirement into task drafts using phase templates and analysis."""
        tasks = []
        prev_indices: dict[str, int] = {}
        analysis = getattr(self, '_last_analysis', None)
        route = getattr(self, '_last_route', None)

        # Derive overall priority from risk analysis
        if route and hasattr(route, 'risk_level'):
            risk_priority_map = {'CRITICAL': 'P0', 'HIGH': 'P1', 'MEDIUM': 'P2', 'LOW': 'P3'}
            base_priority = risk_priority_map.get(str(route.risk_level), 'P2')
        else:
            base_priority = 'P2'

        # Extract domains for acceptance criteria enrichment
        domains = []
        if analysis and hasattr(analysis, 'domains'):
            try:
                domains = list(analysis.domains) if analysis.domains else []
            except Exception:
                pass

        for phase_idx, phase in enumerate(phases):
            templates = self.PHASE_TASK_TEMPLATES.get(
                phase, [(phase.split('-', 1)[-1].capitalize() if '-' in phase else phase,
                         f"Phase {phase} work for: {description}")]
            )
            roles = self.PHASE_ROLES.get(phase, ["developer"])

            for tmpl_idx, (tmpl_title, tmpl_desc) in enumerate(templates):
                deps = []
                if phase_idx > 0:
                    prev_phase = phases[phase_idx - 1]
                    if prev_phase in prev_indices:
                        deps.append(prev_indices[prev_phase])
                elif tmpl_idx > 0:
                    deps.append(len(tasks) - 1)

                # Smart priority: quality/delivery phases get elevated priority
                if phase in ("S5-quality", "S6-delivery"):
                    priority = 'P1' if base_priority == 'P2' else base_priority
                else:
                    priority = base_priority

                # Smart complexity based on phase and analysis
                if phase in ("S2-architecture", "S4-implementation"):
                    complexity = Complexity.HIGH
                elif phase in ("S1-requirements", "S3-interface"):
                    complexity = Complexity.MEDIUM
                else:
                    complexity = Complexity.MEDIUM

                # Enriched acceptance criteria with domain context
                criteria = [
                    f"All {phase} deliverables for '{tmpl_title}' verified",
                    f"Evidence recorded in .ai/evidence/{{task_id}}/",
                ]
                if domains and phase == 'S5-quality':
                    criteria.append(f"Quality checks cover domains: {', '.join(domains[:3])}")
                if phase == 'S6-delivery':
                    criteria.append("Delivery gate: runtime quality + deployment checks pass")

                task = TaskDraft(
                    title=f"[{phase}] {tmpl_title}",
                    description=f"{tmpl_desc} (project: {title})",
                    phase=phase,
                    acceptance_criteria=criteria,
                    suggested_roles=roles,
                    estimated_complexity=complexity,
                    priority=priority,
                    depends_on_plan_index=deps,
                )
                prev_indices[phase] = len(tasks)
                tasks.append(task)

        return tasks

    def _derive_edges(self, tasks: list[TaskDraft]) -> list[PlanEdge]:
        """Derive dependency edges from task ordering."""
        edges = []
        for i in range(1, len(tasks)):
            edges.append(PlanEdge(from_task_index=i - 1, to_task_index=i, edge_type=EdgeType.BLOCKS))
        return edges

    # -- Persistence --------------------------------------------------------

    def _save(self, draft: PlanDraft) -> None:
        import yaml
        path = self._plans_dir / f"{draft.plan_id}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(draft.to_dict(), f, allow_unicode=True, sort_keys=False)

    def _load(self, path: Path) -> PlanDraft:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise PlannerError(f"Invalid plan file: {path}")

        tasks = [
            TaskDraft(
                title=t.get("title", ""),
                description=t.get("description", ""),
                phase=t.get("phase", ""),
                acceptance_criteria=t.get("acceptance_criteria", []),
                suggested_roles=t.get("suggested_roles", []),
                estimated_complexity=Complexity(t.get("estimated_complexity", "MEDIUM")),
                priority=t.get("priority", "P2"),
                depends_on_plan_index=t.get("depends_on_plan_index", []),
            )
            for t in data.get("tasks", [])
        ]
        edges = [
            PlanEdge(
                from_task_index=e.get("from_task_index", 0),
                to_task_index=e.get("to_task_index", 0),
                edge_type=EdgeType(e.get("edge_type", "BLOCKS")),
            )
            for e in data.get("edges", [])
        ]

        return PlanDraft(
            plan_id=data.get("plan_id", path.stem),
            requirement_id=data.get("requirement_id", ""),
            tasks=tasks,
            edges=edges,
            estimated_phases=data.get("estimated_phases", []),
            status=PlanStatus(data.get("status", "DRAFT")),
            clarification_needed=data.get("clarification_needed", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=data.get("version", 1),
        )

    def _next_plan_id(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        existing = sorted(self._plans_dir.glob(f"PLAN-{today}-*.yaml"))
        if existing:
            nums = [int(p.stem.split("-")[-1]) for p in existing if p.stem.split("-")[-1].isdigit()]
            next_num = max(nums) + 1 if nums else 1
        else:
            next_num = 1
        return f"PLAN-{today}-{next_num:03d}"
