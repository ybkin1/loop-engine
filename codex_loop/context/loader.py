"""
Context Loader — Progressive role context loading with token efficiency.

Loads role context (CONTRACT + THINKING_FRAMEWORK + INTERNAL_LOOP) and project
documents progressively based on task complexity. Simple tasks get minimal
context (~200 tokens), complex tasks get full context (~2600 tokens).

Also provides a hierarchical document index so that large markdown files
(e.g. architecture.md) can be loaded by section rather than in their entirety.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ============================================================================
# Enums & Data Classes
# ============================================================================


class LoadLevel(str, Enum):
    """Progressive loading level for role context."""

    MINIMAL = "minimal"     # ~200 tokens: only fixed_stance
    STANDARD = "standard"   # ~600 tokens: stance + framework summary
    FULL = "full"           # ~2600 tokens: complete three-layer architecture


@dataclass
class LoadedContext:
    """Loaded role context ready for injection into an agent system prompt.

    Attributes:
        role_id: The role identifier (e.g. "quality-engineer").
        level: The LoadLevel used for this load.
        system_prompt: The assembled text suitable for a system prompt.
        estimated_tokens: Approximate token count of system_prompt.
        loaded_sections: Human-readable list of what was loaded.
    """

    role_id: str
    level: LoadLevel
    system_prompt: str
    estimated_tokens: int
    loaded_sections: list[str] = field(default_factory=list)


@dataclass
class DocumentIndex:
    """Hierarchical document index — maps section names to line ranges.

    Large documents (e.g. architecture.md) do not need to be loaded in full.
    This index enables loading only the sections a role needs.

    Attributes:
        doc_path: Absolute or relative path to the source document.
        sections: Mapping of section_name -> (start_line, end_line).
            Line numbers are 1-based, inclusive on both ends.
        total_lines: Total number of lines in the document.
    """

    doc_path: str
    sections: dict[str, tuple[int, int]] = field(default_factory=dict)
    total_lines: int = 0


# ============================================================================
# Complexity thresholds (extracted from IntentAnalysis / IntentRouter)
# ============================================================================

# These mirror the LIGHTWEIGHT_COMPLEXITY_MAX / STANDARD_COMPLEXITY_MAX
# thresholds in intent_router.py.  They determine how much context to load.
MINIMAL_MAX = 0.3       # complexity < 0.3  → MINIMAL
STANDARD_MAX = 0.6      # complexity < 0.6  → STANDARD  (else FULL)


def _complexity_to_level(complexity: float) -> LoadLevel:
    """Map a complexity score (0.0-1.0) to the appropriate LoadLevel."""
    if complexity < MINIMAL_MAX:
        return LoadLevel.MINIMAL
    if complexity < STANDARD_MAX:
        return LoadLevel.STANDARD
    return LoadLevel.FULL


# ============================================================================
# ContextLoader
# ============================================================================


class ContextLoader:
    """Progressive role-context loader.

    Decides how much of the three-layer role architecture (CONTRACT,
    THINKING_FRAMEWORK, INTERNAL_LOOP) to load based on task complexity.

    Usage::

        loader = ContextLoader(Path("/project"))
        ctx = loader.load_role_context("quality-engineer", complexity=0.2)
        # ctx.level == LoadLevel.MINIMAL, ctx.estimated_tokens ~ 200
        print(ctx.system_prompt)
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = Path(project_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_role_context(
        self,
        role_id: str,
        complexity: float = 0.5,
    ) -> LoadedContext:
        """Load role context at the level appropriate for *complexity*.

        Parameters:
            role_id: The role directory name under agents/.
            complexity: Task complexity score (0.0 – 1.0), typically from
                IntentAnalysis.complexity_score.

        Returns:
            LoadedContext with the assembled system_prompt and metadata.

        Raises:
            FileNotFoundError: If the role directory does not exist.
            ValueError: If the role's CONTRACT.yaml is missing or malformed
                in a way that prevents loading even MINIMAL context.
        """
        level = _complexity_to_level(complexity)
        role_dir = self._project_root / "agents" / role_id

        if not role_dir.exists() or not role_dir.is_dir():
            raise FileNotFoundError(
                f"Role directory not found: {role_dir}"
            )

        contract_path = role_dir / "CONTRACT.yaml"
        if not contract_path.exists():
            raise FileNotFoundError(
                f"CONTRACT.yaml not found for role '{role_id}': {contract_path}"
            )

        # Parse CONTRACT.yaml (needed for all levels)
        contract_raw = contract_path.read_text(encoding="utf-8")
        contract = _parse_yaml(contract_raw)

        if not isinstance(contract, dict):
            raise ValueError(
                f"CONTRACT.yaml for '{role_id}' does not contain a valid object"
            )

        # Build context according to level
        sections: list[str] = []       # human-readable section names
        content_parts: list[str] = []  # assembled prompt text

        if level == LoadLevel.MINIMAL:
            # Only fixed_stance from CONTRACT
            stance = _extract_fixed_stance(contract, role_id)
            sections.append(f"{role_id}/CONTRACT.yaml#fixed_stance")
            content_parts.append(stance)

        elif level == LoadLevel.STANDARD:
            # fixed_stance + THINKING_FRAMEWORK Step 1-4 titles
            stance = _extract_fixed_stance(contract, role_id)
            sections.append(f"{role_id}/CONTRACT.yaml#fixed_stance")
            content_parts.append(stance)

            framework_path = role_dir / "THINKING_FRAMEWORK.md"
            if framework_path.exists():
                framework_titles = _extract_framework_titles(framework_path)
                if framework_titles:
                    sections.append(f"{role_id}/THINKING_FRAMEWORK.md#titles")
                    content_parts.append(framework_titles)

        elif level == LoadLevel.FULL:
            # Complete three-layer architecture
            # 1. Full CONTRACT (stance + key responsibilities)
            stance = _extract_fixed_stance(contract, role_id)
            sections.append(f"{role_id}/CONTRACT.yaml#fixed_stance")
            content_parts.append(stance)

            # Also include responsibilities and prohibitions from CONTRACT
            extra_contract = _extract_contract_extras(contract)
            if extra_contract:
                sections.append(f"{role_id}/CONTRACT.yaml#extras")
                content_parts.append(extra_contract)

            # 2. Full THINKING_FRAMEWORK
            framework_path = role_dir / "THINKING_FRAMEWORK.md"
            if framework_path.exists():
                framework_text = framework_path.read_text(encoding="utf-8")
                sections.append(f"{role_id}/THINKING_FRAMEWORK.md")
                content_parts.append(framework_text)

            # 3. Full INTERNAL_LOOP
            loop_path = role_dir / "INTERNAL_LOOP.md"
            if loop_path.exists():
                loop_text = loop_path.read_text(encoding="utf-8")
                sections.append(f"{role_id}/INTERNAL_LOOP.md")
                content_parts.append(loop_text)

        system_prompt = "\n\n".join(content_parts).strip()
        estimated_tokens = self.estimate_tokens(system_prompt)

        return LoadedContext(
            role_id=role_id,
            level=level,
            system_prompt=system_prompt,
            estimated_tokens=estimated_tokens,
            loaded_sections=sections,
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate the token count of *text* without external tokenizer libraries.

        Rule of thumb:
        - English / Latin-script text: ~1.3 tokens per word
        - CJK characters (Chinese, Japanese, Korean): ~2 tokens per character
        - Mixed text: both counts are summed

        This is a rough approximation; real tokenizers (GPT, Claude) produce
        slightly different counts, but the estimate is close enough for the
        15% analysis-to-output ratio check in INTERNAL_LOOP.
        """
        if not text:
            return 0

        # Count CJK characters (Unicode ranges for Chinese, Japanese, Korean)
        cjk_pattern = re.compile(
            r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'
            r'\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]'
        )
        cjk_chars = len(cjk_pattern.findall(text))

        # Count "words" in non-CJK text: split on whitespace after removing
        # CJK characters (so we don't double-count)
        non_cjk_text = cjk_pattern.sub(' ', text)
        words = len(non_cjk_text.split())

        # English word → token ratio is roughly 1.3:1
        # CJK char → token ratio is roughly 2:1
        return int(words * 1.3 + cjk_chars * 2.0)

    # ------------------------------------------------------------------
    # Document Indexing
    # ------------------------------------------------------------------

    def build_document_index(self, doc_path: str) -> DocumentIndex:
        """Build a hierarchical index of a markdown document.

        Scans for ``## `` (level-2) headings and records their line ranges.
        Each section spans from its heading line to the line before the
        next heading (or end of file).

        Parameters:
            doc_path: Path to a markdown file (absolute or relative to cwd).

        Returns:
            DocumentIndex with section name → (start, end) mapping.

        Raises:
            FileNotFoundError: If *doc_path* does not exist.
        """
        path = Path(doc_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {doc_path}")

        lines = path.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)

        # Find all ## heading positions
        heading_positions: list[tuple[int, str]] = []  # (line_no, name)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## ") and not stripped.startswith("### "):
                name = stripped[3:].strip()
                # Skip empty heading names
                if name:
                    heading_positions.append((i + 1, name))

        # Build section ranges
        sections: dict[str, tuple[int, int]] = {}
        for idx, (start_line, name) in enumerate(heading_positions):
            if idx + 1 < len(heading_positions):
                end_line = heading_positions[idx + 1][0] - 1
            else:
                end_line = total_lines
            sections[name] = (start_line, end_line)

        return DocumentIndex(
            doc_path=str(path.resolve()),
            sections=sections,
            total_lines=total_lines,
        )

    def load_document_section(
        self, doc_path: str, section_name: str
    ) -> str | None:
        """Load a specific section from a document by name.

        Uses build_document_index internally to locate the section.

        Parameters:
            doc_path: Path to a markdown file.
            section_name: The name of the ``## `` section to load.

        Returns:
            The section text (including the heading line), or None if the
            section is not found.
        """
        index = self.build_document_index(doc_path)
        if section_name not in index.sections:
            return None

        start, end = index.sections[section_name]
        path = Path(doc_path)
        lines = path.read_text(encoding="utf-8").splitlines()

        # Line numbers are 1-based
        section_lines = lines[start - 1 : end]
        return "\n".join(section_lines)

    # ------------------------------------------------------------------
    # Combined loading (role context + document sections)
    # ------------------------------------------------------------------

    def load_for_role(
        self,
        role_id: str,
        doc_path: str,
        complexity: float = 0.5,
    ) -> LoadedContext:
        """Load role context plus the relevant sections of a project document.

        This is the recommended entry point: it combines progressive role
        context loading with section-level document loading for maximum
        token efficiency.

        Parameters:
            role_id: The role directory name under agents/.
            doc_path: Path to a project document (e.g. architecture.md).
            complexity: Task complexity score (0.0 – 1.0).

        Returns:
            LoadedContext with role context plus relevant document sections.
        """
        # First, load role context at the appropriate level
        ctx = self.load_role_context(role_id, complexity=complexity)

        # Then, add relevant sections from the project document
        doc_index = self.build_document_index(doc_path)

        # Select relevant sections based on the role and document
        relevant_sections = _select_relevant_sections(role_id, doc_index)

        doc_parts: list[str] = []
        for section_name in relevant_sections:
            section_text = self.load_document_section(doc_path, section_name)
            if section_text:
                doc_parts.append(section_text)
                ctx.loaded_sections.append(f"{doc_path}#{section_name}")

        if doc_parts:
            doc_context = "\n\n".join(doc_parts)
            ctx.system_prompt = (
                ctx.system_prompt + "\n\n" + doc_context
            ).strip()
            ctx.estimated_tokens = self.estimate_tokens(ctx.system_prompt)

        return ctx


# ============================================================================
# Internal helpers (module-private)
# ============================================================================


def _parse_yaml(raw: str) -> Any:
    """Parse YAML or JSON text, returning the deserialised object.

    Tries YAML first (more common for hand-authored files), falls back to
    JSON.  Returns the raw string if neither parser is available or both fail.
    """
    # Try YAML first
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to JSON
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Last resort: return raw — the caller will handle it
    return raw


def _extract_fixed_stance(contract: dict, role_id: str) -> str:
    """Extract and format the fixed_stance section from a CONTRACT dict.

    Returns a compact, token-efficient string suitable for a system prompt.
    """
    stance = contract.get("fixed_stance")
    if not stance or not isinstance(stance, list):
        # Graceful fallback: return a placeholder
        identity = contract.get("identity", {})
        title = identity.get("title", role_id) if isinstance(identity, dict) else role_id
        return f"Role: {title}\nNo fixed_stance defined."

    lines = ["## Fixed Stance"]
    for item in stance:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _extract_contract_extras(contract: dict) -> str | None:
    """Extract key non-stance sections from CONTRACT for FULL load level.

    Includes: responsibilities, prohibitions, veto_power (summarised).
    """
    parts: list[str] = []

    responsibilities = contract.get("responsibilities")
    if responsibilities and isinstance(responsibilities, list):
        lines = ["## Responsibilities"]
        for item in responsibilities:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    prohibitions = contract.get("prohibitions")
    if prohibitions and isinstance(prohibitions, list):
        lines = ["## Prohibitions"]
        for item in prohibitions:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    veto = contract.get("veto_power")
    if veto and isinstance(veto, list):
        lines = ["## Veto Power"]
        for item in veto:
            lines.append(f"- {item}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else None


def _extract_framework_titles(framework_path: Path) -> str | None:
    """Extract Step 1-4 titles from THINKING_FRAMEWORK.md.

    Returns a compact summary with just the step names, not the full
    content.  This is used for STANDARD-level loading (~300 additional
    tokens vs ~1200 for the full framework).
    """
    raw = framework_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    titles: list[str] = []
    in_step = False
    for line in lines:
        stripped = line.strip()
        # Match "### Step N: ..." headings
        if re.match(r'^###\s+Step\s+\d+:', stripped):
            titles.append(stripped)
            in_step = True
        elif stripped.startswith("## ") and in_step:
            # We've gone past the steps into a new top-level section
            break

    if not titles:
        return None

    result_lines = ["## Thinking Framework (Summary)"]
    for t in titles:
        result_lines.append(f"- {t}")
    return "\n".join(result_lines)


def _select_relevant_sections(
    role_id: str, doc_index: DocumentIndex
) -> list[str]:
    """Select document sections relevant to a given role.

    Uses keyword-based matching between the role_id and section names.
    This is a simple heuristic; a production system might use embedding
    similarity or explicit mapping rules.

    Falls back to returning all section names if no match is found (the
    caller can decide how many to include).
    """
    available = list(doc_index.sections.keys())
    if not available:
        return []

    # Map role keywords to likely section-name keywords
    role_keywords: dict[str, list[str]] = {
        "quality-engineer": ["test", "quality", "coverage", "lint", "gate"],
        "security-engineer": ["security", "auth", "encrypt", "vulnerab"],
        "frontend": ["frontend", "ui", "component", "page", "style"],
        "developer": ["implement", "code", "module", "build"],
        "architect": ["architect", "design", "pattern", "structure"],
        "system-architect": ["architect", "design", "pattern", "structure", "system"],
        "module-architect": ["architect", "design", "module", "pattern"],
        "project-manager": ["plan", "schedule", "milestone", "risk"],
        "product-manager": ["requirement", "feature", "user", "story"],
        "delivery-manager": ["deploy", "release", "delivery", "ship"],
        "release-engineer": ["deploy", "release", "ci", "pipeline"],
    }

    keywords = role_keywords.get(role_id, [])

    if not keywords:
        # Generic fallback: return first 3 sections
        return available[:3]

    matched: list[str] = []
    for section_name in available:
        lower = section_name.lower()
        if any(kw in lower for kw in keywords):
            matched.append(section_name)

    return matched if matched else available[:3]
