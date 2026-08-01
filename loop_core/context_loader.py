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

DEFAULT_BUDGET_TOKENS = 2600      # matches FULL load level (~2600 tokens)
DEFAULT_TRIGGER_RATIO = 0.7       # compress when estimate > budget * 0.7
DEFAULT_MAX_SUMMARY_LEVELS = 2    # "summary of the summary" depth
UNRESOLVED_MARKER = "UNRESOLVED"  # explicit marker for unrecoverable refs

# Max characters before a citation path is truncated during summarization;
# the truncated form keeps enough tail segments to stay uniquely recoverable.
CITATION_MAX_CHARS = 60


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


@dataclass
class CitationResolution:
    """Result of resolving a (possibly truncated) evidence citation.

    Attributes:
        original: The reference as found in the text.
        status: One of RESOLVED / AMBIGUOUS / NOT_FOUND.
        resolved: Canonical project-root-relative reference
            (e.g. ".ai/evidence/T-0088/approval-evidence.json") when RESOLVED.
        matches: Candidate references found (diagnostics).
    """

    original: str
    status: str  # RESOLVED | AMBIGUOUS | NOT_FOUND
    resolved: str | None = None
    matches: list[str] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return self.status == "RESOLVED"


# --------------------------------------------------------------------------
# Key-field extraction (task ID / gate / phase / decision points) — these
# fields are preserved verbatim at every summary level.
# --------------------------------------------------------------------------

_TASK_ID_RE = re.compile(r"\bT-\d{4}\b")
_GATE_ID_RE = re.compile(r"\bG-T-\d{4}-[A-Z0-9-]+\b")
_PHASE_RE = re.compile(r"\bS(?:0|[1-9]\d?)\b")
_DECISION_RE = re.compile(
    r"\b(APPROVED|PASS|FAIL|NOGO|BLOCKED|REJECTED|ACCEPTED|COMPLETED|"
    r"approved|passed|failed|blocked|rejected|accepted|completed|"
    r"in_progress)\b"
)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
# Lines that carry key context fields verbatim (kept at every summary level).
# Also matches the "- task_ids: ..." field lines of previous summary headers
# so that "summary of the summary" keeps the full key-field trail.
_KEY_FIELD_LINE_RE = re.compile(
    r"^\s*(?:-?\s*)?(?:task[_ -]?id|task_ids|gate|gates|phase|phases|decision|decisions)"
    r"\s*[:：]",
    re.IGNORECASE,
)
# Whitespace-delimited path-like tokens that look like evidence citations.
_CITATION_TOKEN_RE = re.compile(
    r"[^\s\"'(),;\[\]]*(?:\.ai/|evidence/|T-\d{4}/|…/)[^\s\"'(),;\[\]]*"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。．！？!?])\s*|(?<=\.)\s+")
# Common abbreviations after which a period is not a sentence boundary.
_ABBREV_RE = re.compile(r"\b(?:e\.g|i\.e|etc|vs|Mr|Ms|Dr|St|No)\.$")


def _level_line_params(level: int) -> tuple[int, int]:
    """(max_line_chars, keep_sentences) — deeper levels truncate harder."""
    if level >= 3:
        return 80, 1
    if level == 2:
        return 110, 1
    return 160, 2


def _level_body_cap(level: int) -> int:
    """Max body lines kept at a given summary level (headings/key fields exempt)."""
    return {1: 64, 2: 32, 3: 16}.get(level, 8)


def _select_body_lines(lines: list[str], cap: int) -> list[str]:
    """Pick up to *cap* body lines, preserving document order.

    Decision-point lines (decision keywords or the word "decision") are
    prioritised so that every summary level keeps the salient decision
    content; the remaining slots are filled with the earliest lines.
    """
    chosen_idx: list[int] = []
    for i, line in enumerate(lines):
        if len(chosen_idx) >= cap:
            break
        if _DECISION_RE.search(line) or "decision" in line.lower():
            chosen_idx.append(i)
    for i in range(len(lines)):
        if len(chosen_idx) >= cap:
            break
        if i not in chosen_idx:
            chosen_idx.append(i)
    chosen_idx.sort()
    return [lines[i] for i in chosen_idx]


# Max evidence-reference lines kept verbatim per summary level.  Citation
# lines are reserved outside the body-line budget so decision-heavy prose
# can never starve the evidence trail out of the compressed view.
CITATION_LINE_CAP = 8


def _find_citation_tokens(text: str) -> list[str]:
    """Return unique citation-like tokens found in *text*, longest first.

    Longest-first ordering keeps replacement of overlapping tokens safe
    (e.g. a full path and its truncated tail appearing together).
    """
    tokens = {m for m in _CITATION_TOKEN_RE.findall(text) if m}
    return sorted(tokens, key=len, reverse=True)


def _truncate_citation(path: str, max_chars: int = CITATION_MAX_CHARS) -> str:
    """Truncate an over-long citation path, keeping its tail segments.

    ``.ai/evidence/T-0088/context-compression/design.md`` becomes
    ``…/context-compression/design.md``.  The ``…`` prefix marks the
    reference as truncated; CitationResolver strips it and matches the
    remaining suffix uniquely against the filesystem.
    """
    if len(path) <= max_chars:
        return path
    parts = [p for p in path.split("/") if p]
    kept = parts[-2:] if len(parts) >= 2 else parts
    return "…/" + "/".join(kept)


def _split_sentences(line: str) -> list[str]:
    """Split *line* into sentences at punctuation boundaries.

    Latin periods are only treated as boundaries when followed by
    whitespace, and splits after common abbreviations (e.g., i.e., etc.)
    are merged back so "e.g. .ai/evidence/..." stays one sentence.
    """
    parts = _SENTENCE_SPLIT_RE.split(line)
    sentences: list[str] = []
    for part in parts:
        if sentences and _ABBREV_RE.search(sentences[-1]):
            sentences[-1] += (" " if sentences[-1].endswith(".") else "") + part
        else:
            sentences.append(part)
    return sentences


def _truncate_line(
    line: str,
    max_chars: int = 160,
    keep_sentences: int = 2,
) -> str:
    """Keep the first *keep_sentences* sentences of *line*, capped at *max_chars*."""
    line = line.strip()
    if len(line) <= max_chars:
        return line
    sentences = _split_sentences(line)
    kept = sentences[0]
    for sentence in sentences[1:keep_sentences]:
        # Re-insert the separator: Latin periods were consumed by the split.
        kept += (" " if kept.endswith(".") else "") + sentence
    if len(kept) > max_chars:
        cut = kept[:max_chars]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        kept = cut + "…"
    return kept


def extract_key_fields(text: str) -> dict[str, list[str]]:
    """Extract key context fields (task IDs / gates / phases / decisions).

    These fields are what every summary level preserves, so that even the
    deepest "summary of the summary" stays traceable to its task/gate/phase
    and to the decision points recorded in the original context.
    """
    fields: dict[str, list[str]] = {
        "task_ids": [],
        "gate_ids": [],
        "phases": [],
        "decisions": [],
    }

    def _add(key: str, value: str) -> None:
        if value and value not in fields[key] and len(fields[key]) < 5:
            fields[key].append(value)

    for m in _GATE_ID_RE.finditer(text):
        _add("gate_ids", m.group(0))
    # Strip gate spans first so "T-0088" inside "G-T-0088-REQUIREMENTS"
    # is not double-counted as a task ID.
    text_without_gates = _GATE_ID_RE.sub(" ", text)
    for m in _TASK_ID_RE.finditer(text_without_gates):
        _add("task_ids", m.group(0))
    for m in _PHASE_RE.finditer(text):
        _add("phases", m.group(0))
    for m in _DECISION_RE.finditer(text):
        _add("decisions", m.group(0))
    return fields


def _format_key_fields(fields: dict[str, list[str]], level: int) -> str:
    """Render the key-field header prepended to every summary level."""
    lines = [f"[CONTEXT SUMMARY L{level}]"]
    for label, key in (
        ("task_ids", "task_ids"),
        ("gates", "gate_ids"),
        ("phases", "phases"),
        ("decisions", "decisions"),
    ):
        values = fields[key]
        if values:
            lines.append(f"- {label}: {', '.join(values)}")
    return "\n".join(lines)


def summarize_text(
    text: str,
    level: int = 1,
    *,
    citation_max_chars: int = CITATION_MAX_CHARS,
) -> str:
    """Deterministic, rule-based summarization of *text* (level 1..N).

    Every level keeps:
      - the key-field header (task IDs / gates / phases / decisions),
      - all headings,
      - lines that carry key fields verbatim (``task_id: ...`` etc.),
      - evidence-reference lines (up to a small cap, outside the body
        budget), so the evidence trail survives compression and can be
        repaired later,
      - decision-point lines first, then the earliest body lines, up to a
        per-level cap (deeper levels keep fewer body lines and truncate
        sentences harder, so "summary of the summary" keeps shrinking).

    Over-long evidence citations are truncated to their tail (restorable
    via CitationResolver / repair_truncated_references).  Pure function:
    never reads or writes files.
    """
    fields = extract_key_fields(text)
    max_line_chars, keep_sentences = _level_line_params(level)
    body_cap = _level_body_cap(level)

    headings: list[str] = []
    key_field_lines: list[str] = []
    citation_lines: list[str] = []
    body_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING_RE.match(stripped):
            headings.append(stripped)
        elif _KEY_FIELD_LINE_RE.match(stripped):
            key_field_lines.append(stripped)
        else:
            # Truncate over-long citations before sentence-level cutting so
            # citation tails are never split mid-path.
            citation_tokens = _find_citation_tokens(stripped)
            for token in citation_tokens:
                if len(token) > citation_max_chars:
                    stripped = stripped.replace(
                        token, _truncate_citation(token, citation_max_chars)
                    )
            # Citation-bearing lines are key content: keep them whole (only
            # their over-long path tails are shortened above) so the
            # evidence trail survives compression and can be repaired.
            if citation_tokens:
                citation_lines.append(stripped)
            elif len(stripped) > max_line_chars:
                truncated = _truncate_line(stripped, max_line_chars, keep_sentences)
                if truncated:
                    body_lines.append(truncated)
            elif stripped:
                body_lines.append(stripped)

    # Cap body lines: never keep more than half of what the previous level
    # kept, which guarantees each level strictly reduces the view.
    cap = min(body_cap, max(1, (len(body_lines) + 1) // 2))
    selected = _select_body_lines(body_lines, cap)

    out_lines: list[str] = []
    seen: set[str] = set()
    for block in (
        headings,
        key_field_lines,
        citation_lines[:CITATION_LINE_CAP],
        selected,
    ):
        for line in block:
            if line not in seen:
                out_lines.append(line)
                seen.add(line)

    header = _format_key_fields(fields, level)
    body = "\n".join(out_lines)
    return header + "\n" + body if body else header


def estimate_tokens(text: str) -> int:
    """Estimate the token count of *text* without external tokenizer libraries.

    Rule of thumb:
    - English / Latin-script text: ~1.3 tokens per word
    - CJK characters (Chinese, Japanese, Korean): ~2 tokens per character
    - Mixed text: both counts are summed

    This is a rough approximation; real tokenizers (GPT, Claude) produce
    slightly different counts, but the estimate is close enough for budget
    triggers and for the 15% analysis-to-output ratio check in INTERNAL_LOOP.
    """
    if not text:
        return 0

    # Count CJK characters (Unicode ranges for Chinese, Japanese, Korean)
    cjk_pattern = re.compile(
        r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
        r"\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
    )
    cjk_chars = len(cjk_pattern.findall(text))

    # Count "words" in non-CJK text: split on whitespace after removing
    # CJK characters (so we don't double-count)
    non_cjk_text = cjk_pattern.sub(" ", text)
    words = len(non_cjk_text.split())

    # English word → token ratio is roughly 1.3:1
    # CJK char → token ratio is roughly 2:1
    return int(words * 1.3 + cjk_chars * 2.0)


class CitationResolver:
    """Resolve truncated evidence citations via unique filesystem matching.

    Handles, in order:
      1. Exact references that already exist on disk (full
         ``.ai/evidence/T-xxxx/...`` paths).
      2. References whose ``.ai/`` prefix was dropped
         (``evidence/T-xxxx/file.json``).
      3. Truncated suffixes (``…/T-xxxx/file.json`` or
         ``T-xxxx/file.json``) matched against files under the search roots.
      4. Bare file names (``file.json``) matched by basename.

    A reference is RESOLVED only when exactly one file matches.  Multiple
    matches are AMBIGUOUS (never guessed); no match is NOT_FOUND.
    """

    def __init__(
        self,
        project_root: Path,
        search_roots: list[Path] | None = None,
    ) -> None:
        self._project_root = Path(project_root)
        if search_roots is not None:
            self._search_roots = [Path(r) for r in search_roots]
        else:
            self._search_roots = self._default_search_roots()

    def _default_search_roots(self) -> list[Path]:
        evidence_dir = self._project_root / ".ai" / "evidence"
        if evidence_dir.exists():
            return [evidence_dir]
        ai_dir = self._project_root / ".ai"
        if ai_dir.exists():
            return [ai_dir]
        return [self._project_root]

    def _all_relative_files(self) -> list[str]:
        """All files under the search roots, project-root-relative, posix form."""
        files: list[str] = []
        for root in self._search_roots:
            if not root.exists():
                continue
            for p in root.rglob("*"):
                if p.is_file():
                    files.append(p.relative_to(self._project_root).as_posix())
        return sorted(set(files))

    def resolve(self, truncated: str) -> CitationResolution:
        """Resolve *truncated* to a full project-relative reference.

        Never guesses: AMBIGUOUS / NOT_FOUND results are returned as-is and
        callers are expected to mark them UNRESOLVED.
        """
        token = str(truncated).strip().strip('"\'`[](){}<>')
        token = token.replace("\\", "/").rstrip(".,;:!?")
        if not token:
            return CitationResolution(original=str(truncated), status="NOT_FOUND")

        # 1+2. Exact path (with or without the .ai/ prefix)
        norm = token.lstrip("/")
        candidates: list[Path] = []
        if norm:
            candidates.append(self._project_root / norm)
            if not norm.startswith(".ai"):
                candidates.append(self._project_root / ".ai" / norm)
        for cand in candidates:
            if cand.is_file():
                rel = cand.relative_to(self._project_root).as_posix()
                return CitationResolution(
                    original=str(truncated),
                    status="RESOLVED",
                    resolved=rel,
                    matches=[rel],
                )

        # 3+4. Truncated suffix / bare basename
        suffix = token
        for marker in ("…", "..."):
            if marker in suffix:
                suffix = suffix.split(marker)[-1].lstrip("/")
        suffix = suffix.lstrip("/")
        if not suffix:
            return CitationResolution(original=str(truncated), status="NOT_FOUND")

        files = self._all_relative_files()
        if "/" in suffix:
            matches = [
                rel for rel in files if rel == suffix or rel.endswith("/" + suffix)
            ]
        else:
            matches = [rel for rel in files if rel.rsplit("/", 1)[-1] == suffix]

        matches = sorted(set(matches))
        if len(matches) == 1:
            return CitationResolution(
                original=str(truncated),
                status="RESOLVED",
                resolved=matches[0],
                matches=matches,
            )
        if len(matches) > 1:
            return CitationResolution(
                original=str(truncated),
                status="AMBIGUOUS",
                matches=matches,
            )
        return CitationResolution(original=str(truncated), status="NOT_FOUND")


def repair_truncated_references(
    text: str, project_root: Path
) -> tuple[str, list[CitationResolution]]:
    """Restore truncated evidence citations inside *text*.

    Resolved references are replaced with their canonical
    ``.ai/evidence/T-xxxx/...`` path.  References that cannot be uniquely
    recovered are explicitly wrapped as ``[UNRESOLVED: <ref>]`` — never
    guessed.

    T-0095 substring-boundary guard: tokens are processed longest-first, and
    a token that is a *substring of a longer token already resolved* is
    skipped.  Without this, a full path and its prefix-dropped sibling
    appearing in the same text would corrupt each other on replacement
    (``str.replace`` rewrites inside the already-repaired span, producing a
    ``.ai/.ai/`` double prefix).

    Returns:
        (repaired_text, resolutions) where resolutions records every
        citation token found and its resolution status.
    """
    resolver = CitationResolver(project_root)
    resolutions: list[CitationResolution] = []
    repaired = text
    resolved_tokens: list[str] = []
    for token in _find_citation_tokens(repaired):
        # Skip tokens covered by a longer already-resolved token: replacing
        # them would rewrite inside the repaired canonical path.
        if any(token in resolved for resolved in resolved_tokens
               if len(resolved) > len(token)):
            continue
        result = resolver.resolve(token)
        resolutions.append(result)
        if result.status == "RESOLVED":
            # Record the canonical form even when no replacement was needed
            # (token was already canonical): its prefix-dropped substring
            # must still be skipped by the guard above.
            if result.resolved != token:
                repaired = repaired.replace(token, result.resolved)
            resolved_tokens.append(result.resolved)
        elif result.status != "RESOLVED":
            repaired = repaired.replace(
                token, f"[{UNRESOLVED_MARKER}: {token}]"
            )
            resolved_tokens.append(f"[{UNRESOLVED_MARKER}: {token}]")
    return repaired, resolutions


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

        Returns:
            LoadedContext with the assembled system_prompt and metadata.
            When compression ran, ``ctx.compression`` describes it.

        Raises:
            FileNotFoundError: If the role directory does not exist.
            ValueError: If the role's CONTRACT.yaml is missing or malformed
                in a way that prevents loading even MINIMAL context, or if
                compression parameters are invalid.
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

        return ctx

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

        # U3: compress the final assembled view when a budget is configured
        if budget_tokens is not None:
            self._apply_budget_compression(
                ctx, budget_tokens, trigger_ratio, max_levels
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
                import logging; logging.getLogger("context_loader").debug("YAML not available, falling back to JSON")
    except Exception as _e:
                import logging; logging.getLogger("context_loader").debug("Parse error: %s", _e)

    # Fall back to JSON
    try:
        return json.loads(raw)
    except Exception as _e:
                import logging; logging.getLogger("context_loader").debug("Parse error: %s", _e)

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
