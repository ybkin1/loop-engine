"""
Evidence citation resolution — truncation repair for compressed context views.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/context_loader.py 的引用解析（CitationResolver /
  repair_truncated_references / _find_citation_tokens / _truncate_citation +
  CITATION_MAX_CHARS / UNRESOLVED_MARKER / CitationResolution）逐字迁移至此
  （design-common-weakness.md 1.5 拆分边界表 :254-264,481-637 及引用常量族）。
- 依赖图：仅依赖 loader_fields（_CITATION_TOKEN_RE）；loader_summary 反向依赖本
  模块（摘要中的引用截断/保留逻辑）。
- fail-closed 语义保持：歧义/缺失引用显式标记 UNRESOLVED，绝不猜测。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loop_core.loader_fields import _CITATION_TOKEN_RE

# Max characters before a citation path is truncated during summarization;
# the truncated form keeps enough tail segments to stay uniquely recoverable.
CITATION_MAX_CHARS = 60

# Explicit marker for unrecoverable refs (never guessed).
UNRESOLVED_MARKER = "UNRESOLVED"


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
