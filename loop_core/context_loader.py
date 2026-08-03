"""
Context Loader — Progressive role context loading with token efficiency.

Loads role context (CONTRACT + THINKING_FRAMEWORK + INTERNAL_LOOP) and project
documents progressively based on task complexity. Simple tasks get minimal
context (~200 tokens), complex tasks get full context (~2600 tokens).

Also provides a hierarchical document index so that large markdown files
(e.g. architecture.md) can be loaded by section rather than in their entirety.

U3 (T-0088) — Context budget compression:
  - ContextCompressor: token-budget-triggered compression of the *loaded view*
    only (never touches source files).  Compression fires when
    estimate_tokens(text) > budget_tokens * trigger_ratio (default 70%).
  - summarize_text: deterministic rule-based summarization that keeps key
    fields (task IDs / gates / phases / decision points) and can be applied
    recursively ("summary of the summary", max_levels configurable, default 2).
  - CitationResolver / repair_truncated_references: restores evidence
    citations (e.g. .ai/evidence/T-xxxx/...) truncated during compression,
    using unique-prefix/suffix recovery against the filesystem; ambiguous or
    missing references are marked UNRESOLVED rather than guessed.

D3 (T-0096) — Optional memory injection:
  - load_role_context / load_for_role accept optional keyword-only params
    ``include_memories`` (default False), ``memory_limit`` (default 5) and
    ``memory_task_id``.  When enabled, the loaded view appends a
    "相关经验（Related Memories）" section recalled from the knowledge store
    (loop_core.memory_service.recall — lessons/acceptance-derived entries).
  - Default behavior is unchanged: include_memories=False never reads the
    knowledge store, so existing callers are byte-for-byte compatible.

T-0110 批 B-2（行为等价拆分）：本文件为瘦身壳 —— 字段解析 / 摘要 / 引用解析 /
节选择已外提至 loader_fields.py / loader_summary.py / citation_resolver.py /
loader_sections.py（design-common-weakness.md 1.5 边界表），全部公开+私有符号
经 re-export 保持公开面逐名一致（含正则族、_ROUTING_CACHE 同一 dict 对象、
标准库绑定，dir()/import * 与拆分前相同）；LoadLevel/LoadedContext/
DocumentIndex/CompressionResult/ContextCompressor/ContextLoader 主加载流程
（含 D3 记忆注入默认 False 语义）保留在本壳，行为不变。
"""
from __future__ import annotations

import json
import logging
import re  # noqa: F401 — 保持拆分前模块命名空间（dir() 逐名一致）
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any  # noqa: F401 — 保持拆分前模块命名空间（dir() 逐名一致）

from loop_core.citation_resolver import (  # noqa: F401 — re-export，公开面保持
    CITATION_MAX_CHARS,
    UNRESOLVED_MARKER,
    CitationResolution,
    CitationResolver,
    _find_citation_tokens,
    _truncate_citation,
    repair_truncated_references,
)
from loop_core.loader_fields import (  # noqa: F401 — re-export，公开面保持
    _ABBREV_RE,
    _CITATION_TOKEN_RE,
    _DECISION_RE,
    _GATE_ID_RE,
    _HEADING_RE,
    _KEY_FIELD_LINE_RE,
    _PHASE_RE,
    _SENTENCE_SPLIT_RE,
    _TASK_ID_RE,
    _format_key_fields,
    extract_key_fields,
)
from loop_core.loader_sections import (  # noqa: F401 — re-export，公开面保持
    _ROUTING_CACHE,
    _extract_framework_titles,
    _load_section_routing,
    _parse_front_matter_yaml,
    _select_relevant_sections,
)
from loop_core.loader_summary import (  # noqa: F401 — re-export，公开面保持
    CITATION_LINE_CAP,
    _level_body_cap,
    _level_line_params,
    _select_body_lines,
    _split_sentences,
    _truncate_line,
    estimate_tokens,
    summarize_text,
)

logger = logging.getLogger(__name__)


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
    # U3: set only when load_role_context / load_for_role ran with a token
    # budget; records the compression applied to this *view* of the context.
    compression: CompressionResult | None = None


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
# U3 (T-0088) — Context budget compression, hierarchical summary and
# evidence citation truncation repair.
#
# StaffDeck mapping (T-0086 staffdeck-benchmark.md, U3):
#   - context_projection.py / conversation_context.py "cursor summary" with a
#     70% token-budget trigger  -> ContextCompressor below.
#   - "summary of the summary" (hierarchical) -> max_levels parameter.
#   - citations.py unique-prefix recovery   -> CitationResolver below.
#
# Principles:
#   - Compression only ever affects the *loaded view* returned to callers.
#     It is a pure function of its input text; no source file (evidence,
#     task files, .ai/ documents) is read-write or modified.
#   - Summarization is deterministic and rule-based (no LLM dependency).
#   - Truncated evidence citations are restored via unique filesystem
#     matching; ambiguous / missing references are explicitly marked
#     UNRESOLVED instead of being guessed.
# ============================================================================

# 模块级类型注解保留：原文件 _ROUTING_CACHE 的注解赋值创建了模块 __annotations__
# 属性（dir() 成员之一）；拆分后该常量迁至 loader_sections.py，此处以既有常量
# 的注解赋值保持模块 __annotations__ 存在（T-0110 批 B-2 dir() 逐名一致）。
DEFAULT_BUDGET_TOKENS: int = 2600      # matches FULL load level (~2600 tokens)
DEFAULT_TRIGGER_RATIO = 0.7       # compress when estimate > budget * 0.7
DEFAULT_MAX_SUMMARY_LEVELS = 2    # "summary of the summary" depth

# D3 (T-0096): default memory-injection bound for optional context loading.
DEFAULT_MEMORY_LIMIT = 5          # top-N recalled entries injected at most


@dataclass
class CompressionResult:
    """Outcome of budget-triggered compression of a loaded context view.

    Attributes:
        text: The (possibly compressed) view text.
        original_tokens: estimate_tokens of the input text.
        estimated_tokens: estimate_tokens of ``text``.
        triggered: True when the input exceeded budget_tokens * trigger_ratio.
        levels_applied: How many summarization levels were applied (0 if the
            trigger never fired or no reduction was possible).
        budget_tokens: The budget threshold used for this run.
        trigger_ratio: The ratio used for this run.
        max_levels: The level cap used for this run.
        citations: Citation resolutions for citations found in the
            compressed text (populated when a project_root was supplied).
    """

    text: str
    original_tokens: int
    estimated_tokens: int
    triggered: bool
    levels_applied: int
    budget_tokens: int
    trigger_ratio: float
    max_levels: int
    citations: list[CitationResolution] = field(default_factory=list)


class ContextCompressor:
    """Token-budget-triggered compression of loaded context views.

    Compression is a pure transformation of the input text: the original
    files that the context was loaded from are never touched.

    Usage::

        compressor = ContextCompressor(budget_tokens=2000, trigger_ratio=0.7)
        result = compressor.compress_if_needed(ctx.system_prompt)
        if result.triggered:
            view = result.text          # compressed loaded view
            print(result.levels_applied)
    """

    def __init__(
        self,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        trigger_ratio: float = DEFAULT_TRIGGER_RATIO,
        max_levels: int = DEFAULT_MAX_SUMMARY_LEVELS,
        project_root: Path | None = None,
    ) -> None:
        self._budget_tokens = budget_tokens
        self._trigger_ratio = trigger_ratio
        self._max_levels = max_levels
        self._project_root = Path(project_root) if project_root is not None else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress_if_needed(
        self,
        text: str,
        *,
        budget_tokens: int | None = None,
        trigger_ratio: float | None = None,
        max_levels: int | None = None,
    ) -> CompressionResult:
        """Compress *text* only when it exceeds budget_tokens * trigger_ratio.

        Hierarchical summarization ("summary of the summary") applies up to
        *max_levels* rounds; each round must actually reduce the token
        estimate, otherwise compression stops.  When *project_root* was
        provided to the constructor, truncated evidence citations in the
        compressed text are repaired and the resolutions recorded.

        Raises:
            ValueError: If budget_tokens <= 0, trigger_ratio not in (0, 1],
                or max_levels < 1.
        """
        budget = self._budget_tokens if budget_tokens is None else budget_tokens
        ratio = self._trigger_ratio if trigger_ratio is None else trigger_ratio
        cap = self._max_levels if max_levels is None else max_levels
        _validate_budget_params(budget, ratio, cap)

        original_tokens = estimate_tokens(text)
        threshold = budget * ratio

        if original_tokens <= threshold:
            return CompressionResult(
                text=text,
                original_tokens=original_tokens,
                estimated_tokens=original_tokens,
                triggered=False,
                levels_applied=0,
                budget_tokens=budget,
                trigger_ratio=ratio,
                max_levels=cap,
            )

        current = text
        applied = 0
        for level in range(1, cap + 1):
            prev_tokens = estimate_tokens(current)
            candidate = summarize_text(current, level=level)
            cand_tokens = estimate_tokens(candidate)
            if cand_tokens >= prev_tokens:
                break  # no token reduction — do not grow or oscillate
            current = candidate
            applied = level
            if cand_tokens <= threshold:
                break

        citations: list[CitationResolution] = []
        if applied > 0 and self._project_root is not None:
            current, citations = repair_truncated_references(
                current, self._project_root
            )

        return CompressionResult(
            text=current,
            original_tokens=original_tokens,
            estimated_tokens=estimate_tokens(current),
            triggered=True,
            levels_applied=applied,
            budget_tokens=budget,
            trigger_ratio=ratio,
            max_levels=cap,
            citations=citations,
        )


def _validate_budget_params(
    budget_tokens: int, trigger_ratio: float, max_levels: int
) -> None:
    """Validate compression parameters, raising ValueError on misuse."""
    if not isinstance(budget_tokens, int) or budget_tokens <= 0:
        raise ValueError(f"budget_tokens must be a positive int, got {budget_tokens!r}")
    if not 0.0 < trigger_ratio <= 1.0:
        raise ValueError(f"trigger_ratio must be in (0, 1], got {trigger_ratio!r}")
    if not isinstance(max_levels, int) or max_levels < 1:
        raise ValueError(f"max_levels must be >= 1, got {max_levels!r}")


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
        *,
        budget_tokens: int | None = None,
        trigger_ratio: float = DEFAULT_TRIGGER_RATIO,
        max_levels: int = DEFAULT_MAX_SUMMARY_LEVELS,
        include_memories: bool = False,
        memory_limit: int = DEFAULT_MEMORY_LIMIT,
        memory_task_id: str | None = None,
    ) -> LoadedContext:
        """Load role context at the level appropriate for *complexity*.

        Parameters:
            role_id: The role directory name under agents/.
            complexity: Task complexity score (0.0 – 1.0), typically from
                IntentAnalysis.complexity_score.
            budget_tokens: Optional U3 token budget.  When given, the loaded
                view is compressed (hierarchical summary + citation repair)
                whenever it exceeds ``budget_tokens * trigger_ratio``.  The
                compression is applied to the returned view only; source
                files are never modified.  Default None keeps the legacy
                behaviour (no compression).
            trigger_ratio: Fraction of the budget that triggers compression
                (default 0.7 — StaffDeck's 70% trigger).
            max_levels: Maximum number of "summary of the summary" levels
                (default 2).
            include_memories: D3 (T-0096) optional memory injection.  When
                True, a "相关经验（Related Memories）" section recalled from
                the knowledge store is appended to the loaded view.  Default
                False keeps the legacy behaviour (the knowledge store is not
                even read).
            memory_limit: Cap on how many recalled entries are injected
                (top-N, newest first; default 5).
            memory_task_id: Optional task filter for recall — only memories
                associated with this task are injected.  Default None
                recalls across the whole store.

        Returns:
            LoadedContext with the assembled system_prompt and metadata.
            When compression ran, ``ctx.compression`` describes it.

        Raises:
            FileNotFoundError: If the role directory does not exist.
            ValueError: If the role's CONTRACT.yaml is missing or malformed
                in a way that prevents loading even MINIMAL context, or if
                compression parameters are invalid.
            KnowledgeStoreError: Only when include_memories=True and the
                knowledge store file exists but is malformed (fail-closed —
                the machine never guesses about its own memory).
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

        ctx = LoadedContext(
            role_id=role_id,
            level=level,
            system_prompt=system_prompt,
            estimated_tokens=estimated_tokens,
            loaded_sections=sections,
        )

        if budget_tokens is not None:
            self._apply_budget_compression(
                ctx, budget_tokens, trigger_ratio, max_levels
            )

        self._apply_memory_injection(
            ctx, include_memories, memory_limit, memory_task_id
        )

        return ctx

    def _apply_memory_injection(
        self,
        ctx: LoadedContext,
        include_memories: bool,
        memory_limit: int,
        memory_task_id: str | None,
    ) -> None:
        """D3 (T-0096): optionally append recalled memories to the view.

        Default-off: when ``include_memories`` is False this is a no-op and
        the knowledge store is never touched.  When enabled, recall() is
        bounded by ``memory_limit`` (top-N); an empty or absent store simply
        contributes no section.  A malformed store raises (fail-closed).
        """
        if not include_memories:
            return
        try:
            if not isinstance(memory_limit, int) or memory_limit <= 0:
                return
            from loop_core.memory_service import memories_to_context, recall
        except ImportError:  # pragma: no cover — memory_service is in-package
            return
        entries = recall(
            self._project_root,
            task_id=memory_task_id,
            limit=memory_limit,
        )
        section = memories_to_context(entries)
        if not section:
            return
        if ctx.system_prompt:
            ctx.system_prompt = (ctx.system_prompt + "\n\n" + section).strip()
        else:
            ctx.system_prompt = section
        ctx.estimated_tokens = self.estimate_tokens(ctx.system_prompt)
        ctx.loaded_sections.append(f"[memories: {len(entries)} recalled]")

    def _apply_budget_compression(
        self,
        ctx: LoadedContext,
        budget_tokens: int,
        trigger_ratio: float,
        max_levels: int,
    ) -> None:
        """Compress the loaded view of *ctx* in place when over budget.

        Only the view (ctx.system_prompt) is rewritten; the source files
        the context was loaded from are never touched.
        """
        compressor = ContextCompressor(
            budget_tokens=budget_tokens,
            trigger_ratio=trigger_ratio,
            max_levels=max_levels,
            project_root=self._project_root,
        )
        result = compressor.compress_if_needed(ctx.system_prompt)
        if not result.triggered or result.levels_applied == 0:
            # Under budget, or over budget but nothing reducible: keep the
            # original view untouched.
            return
        ctx.system_prompt = result.text
        ctx.estimated_tokens = result.estimated_tokens
        ctx.compression = result
        ctx.loaded_sections.append(
            f"[compressed: {result.levels_applied} level(s), "
            f"{result.original_tokens} → {result.estimated_tokens} tokens]"
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate the token count of *text* without external tokenizer libraries.

        Delegates to the module-level :func:`estimate_tokens` (shared with
        ContextCompressor so budget triggers use the same estimator).

        Rule of thumb:
        - English / Latin-script text: ~1.3 tokens per word
        - CJK characters (Chinese, Japanese, Korean): ~2 tokens per character
        - Mixed text: both counts are summed

        This is a rough approximation; real tokenizers (GPT, Claude) produce
        slightly different counts, but the estimate is close enough for the
        15% analysis-to-output ratio check in INTERNAL_LOOP.
        """
        return estimate_tokens(text)

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
        *,
        budget_tokens: int | None = None,
        trigger_ratio: float = DEFAULT_TRIGGER_RATIO,
        max_levels: int = DEFAULT_MAX_SUMMARY_LEVELS,
        include_memories: bool = False,
        memory_limit: int = DEFAULT_MEMORY_LIMIT,
        memory_task_id: str | None = None,
    ) -> LoadedContext:
        """Load role context plus the relevant sections of a project document.

        This is the recommended entry point: it combines progressive role
        context loading with section-level document loading for maximum
        token efficiency.

        Parameters:
            role_id: The role directory name under agents/.
            doc_path: Path to a project document (e.g. architecture.md).
            complexity: Task complexity score (0.0 – 1.0).
            budget_tokens: Optional U3 token budget applied to the *final*
                assembled view (role context + document sections).  When
                given and exceeded, the returned view is compressed; source
                files are never modified.  Default None keeps the legacy
                behaviour (no compression).
            trigger_ratio: Fraction of the budget that triggers compression.
            max_levels: Maximum number of "summary of the summary" levels.
            include_memories: D3 (T-0096) optional memory injection —
                same semantics as load_role_context (default False keeps
                the legacy behaviour byte-for-byte).
            memory_limit: Cap on recalled entries injected (default 5).
            memory_task_id: Optional task filter for memory recall.

        Returns:
            LoadedContext with role context plus relevant document sections.
        """
        # First, load role context at the appropriate level
        ctx = self.load_role_context(role_id, complexity=complexity)

        # Then, add relevant sections from the project document
        doc_index = self.build_document_index(doc_path)

        # Select relevant sections based on the role and document.
        # T-0108 F4 (D5-3): routed via .ai/README.md section_routing table
        # when present; legacy keyword heuristic otherwise (with warning).
        relevant_sections = _select_relevant_sections(
            role_id, doc_index, project_root=self._project_root
        )

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

        # U3: compress the final assembled view when a budget is configured
        if budget_tokens is not None:
            self._apply_budget_compression(
                ctx, budget_tokens, trigger_ratio, max_levels
            )

        # D3: optional memory injection (default off — no-op when disabled)
        self._apply_memory_injection(
            ctx, include_memories, memory_limit, memory_task_id
        )

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
        logging.getLogger("context_loader").debug(
            "YAML not available, falling back to JSON")
    except Exception as _e:
        logging.getLogger("context_loader").debug("Parse error: %s", _e)

    # Fall back to JSON
    try:
        return json.loads(raw)
    except Exception as _e:
        logging.getLogger("context_loader").debug("Parse error: %s", _e)

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
