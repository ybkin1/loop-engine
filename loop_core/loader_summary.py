"""
Loader summarization — deterministic rule-based context compression helpers.

T-0110 批 B-2 拆分（行为等价，纯外提 re-export）：
- 原 loop_core/context_loader.py 的摘要级别/行选择（_level_line_params /
  _level_body_cap / _select_body_lines / _split_sentences / _truncate_line /
  summarize_text / estimate_tokens + CITATION_LINE_CAP）逐字迁移至此
  （design-common-weakness.md 1.5 拆分边界表 :212-479）。
- 依赖图：依赖 loader_fields（决策/标题/关键字段正则）与 citation_resolver
  （引用 token/截断 + CITATION_MAX_CHARS）。
- 纯函数保持：从不读写文件；确定性、无 LLM 依赖。
"""
from __future__ import annotations

import re

from loop_core.citation_resolver import (
    CITATION_MAX_CHARS,
    _find_citation_tokens,
    _truncate_citation,
)
from loop_core.loader_fields import (
    _ABBREV_RE,
    _DECISION_RE,
    _HEADING_RE,
    _KEY_FIELD_LINE_RE,
    _SENTENCE_SPLIT_RE,
    _format_key_fields,
    extract_key_fields,
)

# Max evidence-reference lines kept verbatim per summary level.  Citation
# lines are reserved outside the body-line budget so decision-heavy prose
# can never starve the evidence trail out of the compressed view.
CITATION_LINE_CAP = 8


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
