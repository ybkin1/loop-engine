"""
Projection Engine — Generate per-role views from PROJECT_MAP.

Each role's CONTRACT.yaml defines projection_rules that determine what
portions of the project map the role can see. The ProjectionEngine uses
ProjectMapQuery to extract these portions and produces a RoleProjection
that can be injected into the role's system prompt.

Principles:
  - Roles only see project information relevant to their domain.
  - Irrelevant information is never loaded (token savings).
  - Stale projections are automatically detected via hash comparison.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_core.project_map_schema import ProjectMapQuery


# ============================================================================
# RoleProjection
# ============================================================================


@dataclass
class RoleProjection:
    """Role-specific view of the project extracted from PROJECT_MAP.

    A projection is the subset of PROJECT_MAP that a specific role needs
    to see, plus quality checkpoints specific to that role.
    """

    role_id: str
    phase: str
    # Data extracted from PROJECT_MAP (only what the role needs to see)
    visible_sections: dict[str, Any]
    # Quality checkpoints for this role
    quality_checkpoints: list[str]
    # Sections explicitly excluded from the role's view
    excluded_sections: list[str]
    # When this projection was generated (ISO 8601 UTC)
    generated_at: str
    # SHA-256 of the source PROJECT_MAP content (for staleness detection)
    source_map_hash: str

    def to_prompt_context(self) -> str:
        """Convert the projection to text suitable for injecting into an agent's system prompt.

        The output is compact, well-structured, and token-efficient.
        """
        lines: list[str] = []

        # ── Header ───────────────────────────────────────────────────
        proj = self.visible_sections.get("project", {})
        proj_name = proj.get("name", "Unknown") if isinstance(proj, dict) else "Unknown"
        proj_type = proj.get("type", "unknown") if isinstance(proj, dict) else "unknown"
        proj_desc = proj.get("description", "") if isinstance(proj, dict) else ""

        phase_display = self.phase if self.phase else "unknown"

        lines.append(f"## 项目上下文（{self.role_id} 视角）")
        lines.append("")
        if proj_desc:
            lines.append(f"**项目**：{proj_name} | **类型**：{proj_type} | **描述**：{proj_desc} | **阶段**：{phase_display}")
        else:
            lines.append(f"**项目**：{proj_name} | **类型**：{proj_type} | **阶段**：{phase_display}")
        lines.append("")

        # ── Quality Checkpoints ──────────────────────────────────────
        if self.quality_checkpoints:
            lines.append("### 质量检查点")
            for i, cp in enumerate(self.quality_checkpoints, 1):
                lines.append(f"{i}. {cp}")
            lines.append("")

        # ── Visible Sections ─────────────────────────────────────────
        section_keys = [k for k in self.visible_sections if k != "project"]
        for key in section_keys:
            value = self.visible_sections[key]
            formatted = self._format_section(key, value)
            if formatted:
                lines.append(formatted)
                lines.append("")

        return "\n".join(lines).strip()

    def _format_section(self, key: str, value: Any) -> str:
        """Format a single visible section into human-readable text."""
        lines: list[str] = []
        title = _section_title(key)

        if isinstance(value, list):
            lines.append(f"### {title}（共 {len(value)} 个）")
            for item in value:
                if isinstance(item, dict):
                    summary = _item_summary(item)
                    lines.append(f"- {summary}")
                elif isinstance(item, str):
                    lines.append(f"- {item}")
                else:
                    lines.append(f"- {item}")
        elif isinstance(value, dict):
            lines.append(f"### {title}")
            for k, v in value.items():
                if isinstance(v, (str, int, float, bool)):
                    lines.append(f"- **{k}**: {v}")
                elif isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v):
                    lines.append(f"- **{k}**: {', '.join(str(x) for x in v)}")
                elif isinstance(v, list):
                    lines.append(f"- **{k}** ({len(v)} 项):")
                    for item in v:
                        if isinstance(item, dict):
                            lines.append(f"  - {_item_summary(item)}")
                        else:
                            lines.append(f"  - {item}")
                elif v is None:
                    lines.append(f"- **{k}**: (未设置)")
                else:
                    lines.append(f"- **{k}**: {v}")
        else:
            lines.append(f"### {title}")
            lines.append(f"{value}")

        return "\n".join(lines)

    # ── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for persistence or cross-process transfer)."""
        return {
            "role_id": self.role_id,
            "phase": self.phase,
            "visible_sections": self.visible_sections,
            "quality_checkpoints": self.quality_checkpoints,
            "excluded_sections": self.excluded_sections,
            "generated_at": self.generated_at,
            "source_map_hash": self.source_map_hash,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RoleProjection:
        """Deserialise from a plain dict."""
        return cls(
            role_id=d["role_id"],
            phase=d["phase"],
            visible_sections=d.get("visible_sections", {}),
            quality_checkpoints=d.get("quality_checkpoints", []),
            excluded_sections=d.get("excluded_sections", []),
            generated_at=d.get("generated_at", ""),
            source_map_hash=d.get("source_map_hash", ""),
        )


# ============================================================================
# ProjectionRule
# ============================================================================


@dataclass
class ProjectionRule:
    """A single projection rule loaded from a role's CONTRACT.yaml.

    include_patterns are ProjectMapQuery paths that extract data from
    PROJECT_MAP. exclude_patterns record which top-level sections the
    role must not see. quality_dimensions are role-specific quality
    checkpoints.
    """

    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    quality_dimensions: list[str] = field(default_factory=list)


# ============================================================================
# ProjectionEngine
# ============================================================================


class ProjectionEngine:
    """Generate per-role projections from PROJECT_MAP.

    Usage::

        engine = ProjectionEngine(Path("/project"))
        proj = engine.generate_projection("frontend-test-engineer")
        prompt_text = proj.to_prompt_context()
        # Inject prompt_text into the role's system prompt before task execution.
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = Path(project_root)
        self._query = ProjectMapQuery()

    # ── Rule Loading ─────────────────────────────────────────────────────

    def load_rules(self, role_id: str) -> ProjectionRule:
        """Load projection rules from agents/{role_id}/CONTRACT.yaml.

        If the CONTRACT.yaml does not exist or lacks projection_rules,
        returns a default rule that only includes the project's basic info.
        """
        contract_path = self._project_root / "agents" / role_id / "CONTRACT.yaml"

        if not contract_path.exists():
            return _default_rules()

        try:
            raw = contract_path.read_text(encoding="utf-8")
            contract = _parse_yaml(raw)
        except Exception:
            return _default_rules()

        if not isinstance(contract, dict):
            return _default_rules()

        pr = contract.get("projection_rules")
        if not isinstance(pr, dict):
            return _default_rules()

        return ProjectionRule(
            include_patterns=list(pr.get("include_sections", []) or []),
            exclude_patterns=list(pr.get("exclude_sections", []) or []),
            quality_dimensions=list(pr.get("quality_dimensions", []) or []),
        )

    # ── Projection Generation ────────────────────────────────────────────

    def generate_projection(
        self, role_id: str, phase: str | None = None
    ) -> RoleProjection:
        """Generate a RoleProjection for *role_id*.

        Steps:
        1. Read PROJECT_MAP.yaml from the project root.
        2. Load the role's projection_rules from CONTRACT.yaml.
        3. Use ProjectMapQuery to extract data for each include_pattern.
        4. Record which sections are explicitly excluded.
        5. Attach quality checkpoints.
        6. Compute the source map hash for staleness detection.

        Raises:
            FileNotFoundError: If PROJECT_MAP.yaml cannot be found.
            ValueError: If PROJECT_MAP.yaml does not contain a valid object.
        """
        # 1. Locate and read PROJECT_MAP
        project_map_path = _find_project_map(self._project_root)

        raw = project_map_path.read_text(encoding="utf-8")
        data = _parse_yaml(raw)
        if not isinstance(data, dict):
            raise ValueError(
                "PROJECT_MAP must contain a YAML/JSON object at the root"
            )

        # 2. Load projection rules
        rules = self.load_rules(role_id)

        # 3. Execute include_patterns queries
        visible_sections: dict[str, Any] = {}
        for pattern in rules.include_patterns:
            result = self._query.query(data, pattern)
            if result is not None:
                visible_sections[pattern] = result

        # 4. Build excluded_sections list
        excluded_sections = list(rules.exclude_patterns)

        # 5. Copy quality dimensions
        quality_checkpoints = list(rules.quality_dimensions)

        # 6. Compute source map hash
        source_map_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # 7. Determine phase
        actual_phase = phase if phase is not None else _infer_phase(self._project_root)

        generated_at = datetime.now(timezone.utc).isoformat()

        return RoleProjection(
            role_id=role_id,
            phase=actual_phase,
            visible_sections=visible_sections,
            quality_checkpoints=quality_checkpoints,
            excluded_sections=excluded_sections,
            generated_at=generated_at,
            source_map_hash=source_map_hash,
        )

    # ── Staleness Detection ──────────────────────────────────────────────

    def detect_staleness(self, role_id: str, projection: RoleProjection) -> bool:
        """Return True if *projection* is stale (PROJECT_MAP has changed).

        Compares the projection's source_map_hash with the current hash
        of PROJECT_MAP.yaml.
        """
        try:
            project_map_path = _find_project_map(self._project_root)
        except FileNotFoundError:
            # If the map is gone, the projection is definitely stale
            return True

        raw = project_map_path.read_text(encoding="utf-8")
        current_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return current_hash != projection.source_map_hash

    # ── Role Discovery ───────────────────────────────────────────────────

    def list_roles_with_projections(self) -> list[str]:
        """Return the sorted list of role IDs that have projection rules defined.

        Only directories under agents/ that contain a CONTRACT.yaml with
        a projection_rules section are included.
        """
        agents_dir = self._project_root / "agents"
        if not agents_dir.exists() or not agents_dir.is_dir():
            return []

        roles: list[str] = []
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            contract_path = agent_dir / "CONTRACT.yaml"
            if not contract_path.exists():
                continue

            try:
                raw = contract_path.read_text(encoding="utf-8")
                contract = _parse_yaml(raw)
                if isinstance(contract, dict) and "projection_rules" in contract:
                    roles.append(agent_dir.name)
            except Exception:
                continue

        return sorted(roles)


# ============================================================================
# Internal helpers (module-private)
# ============================================================================


def _find_project_map(project_root: Path) -> Path:
    """Locate PROJECT_MAP.yaml, checking both project root and .ai/ directory."""
    candidates = [
        project_root / "PROJECT_MAP.yaml",
        project_root / "PROJECT_MAP.yml",
        project_root / ".ai" / "PROJECT_MAP.yaml",
        project_root / ".ai" / "PROJECT_MAP.yml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"PROJECT_MAP.yaml not found in {project_root} or {project_root / '.ai'}"
    )


def _infer_phase(project_root: Path) -> str:
    """Try to read current_phase from state.yaml, returning 'unknown' on failure."""
    candidates = [
        project_root / ".ai" / "state.yaml",
        project_root / ".ai" / "state.yml",
        project_root / "state.yaml",
        project_root / "state.yml",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            raw = candidate.read_text(encoding="utf-8")
            state = _parse_yaml(raw)
            if isinstance(state, dict) and "current_phase" in state:
                return str(state["current_phase"])
        except Exception:
            continue
    return "unknown"


def _parse_yaml(raw: str) -> Any:
    """Parse YAML or JSON text, returning the deserialised object."""
    # Try YAML first (more common for hand-authored files)
    try:
        import yaml

        return yaml.safe_load(raw)
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to JSON
    return json.loads(raw)


def _default_rules() -> ProjectionRule:
    """Default projection rule: only project basic info, no exclusions."""
    return ProjectionRule(
        include_patterns=["project"],
        exclude_patterns=[],
        quality_dimensions=[],
    )


def _section_title(key: str) -> str:
    """Map a query path to a human-readable section title."""
    title_map: dict[str, str] = {
        "project": "项目信息",
        "pages": "页面",
        "api_endpoints": "API 端点",
        "modules": "模块",
        "database": "数据库",
    }
    if key in title_map:
        return title_map[key]

    # For sub-paths like "pages.*.elements", try the top-level key first
    top_key = key.split(".")[0]
    if top_key in title_map:
        base = title_map[top_key]
        sub = key[len(top_key) + 1:]
        # Translate common sub-field names
        sub_map = {
            "*.elements": "元素",
            "*.states": "状态",
            "*.navigation_from": "来源导航",
            "*.navigation_to": "目标导航",
            "*.depends_on": "依赖",
            "*.depended_by": "被依赖",
            "*.responsibilities": "职责",
            "*.request": "请求",
            "*.response": "响应",
            "*.method": "方法",
            "*.path": "路径",
            "tables": "数据表",
            "*.columns": "列",
        }
        sub_display = sub_map.get(sub, sub)
        return f"{base} ({sub_display})"
    return key


def _item_summary(item: dict[str, Any]) -> str:
    """Build a one-line human-readable summary of a dict item.

    Uses common identifying fields (id, name, path, title) and the
    most relevant descriptor to produce a compact summary.
    """
    ident = item.get("id") or item.get("name") or ""
    if not ident:
        ident = item.get("path") or item.get("title") or ""

    # Pick the best descriptor
    desc = ""
    if "method" in item and "path" in item:
        desc = f"{item['method']} {item['path']}"
    elif "type" in item and "label" in item:
        desc = f"[{item['type']}] {item['label']}"
    elif "description" in item:
        desc = str(item["description"])
    elif "label" in item:
        desc = str(item["label"])
    elif "title" in item:
        desc = str(item["title"])
    elif "responsibilities" in item:
        responsibilities = item["responsibilities"]
        if isinstance(responsibilities, list):
            desc = ", ".join(str(r) for r in responsibilities[:3])
        else:
            desc = str(responsibilities)
    elif "path" in item:
        desc = str(item["path"])
    elif "name" in item:
        desc = str(item["name"])

    if ident and desc:
        return f"{ident}: {desc}"
    elif ident:
        return str(ident)
    elif desc:
        return str(desc)
    else:
        # Last resort: show the whole item compactly
        return str(item)
