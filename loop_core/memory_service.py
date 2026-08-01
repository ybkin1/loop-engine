"""
Memory Service — cross-task experience extraction and recall injection.

D3 (T-0096): StaffDeck 记忆提取/注入对标在 loop-engine 治理域的轻量落地。

数据流（单向，lessons 为源，knowledge 为派生视图）::

    .ai/evidence/feedback/gate-lessons.yaml   （T-0089 源，record_gate_lesson 写入）
    .ai/evidence/T-*/acceptance/*.md          （各任务验收报告）
                          │  extract_memories()  （规则式/确定性，无 LLM）
                          ▼
    .ai/evidence/knowledge/knowledge-store.yaml  （派生视图，knowledge_store 幂等写入）

- ``extract_memories`` 从 gate_lessons + 验收报告提取结构化经验并写入
  knowledge store（幂等：同来源+同内容指纹不重复）；不修改任何源文件。
- ``recall`` 按任务 / gate / 主题标签 / 关键词组合检索（供注入），默认
  上限 5 条（上下文注入的 top-N 约束）。
- ``memories_to_context`` 把召回条目渲染为紧凑 markdown 记忆段，供
  context_loader 可选注入（include_memories，默认关闭）。

Referenced by:
- context_loader.py — optional memory injection (T-0096)
- tests/test_knowledge_memory.py — AC-02 (extraction/recall), AC-03 (integration)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loop_core.gate_feedback import (
    DECISION_APPROVED,
    load_lessons,
)
from loop_core.knowledge_store import (
    KIND_BEST_PRACTICE,
    KIND_DECISION,
    KIND_LESSON,
    KIND_PITFALL,
    SOURCE_GATE,
    SOURCE_TASK,
    load_entries,
    put_entry,
    query,
)

DEFAULT_RECALL_LIMIT = 5
DEFAULT_MEMORY_CONTENT_MAX_CHARS = 200

# ── Acceptance report parsing (rule-based, deterministic) ──────────────────

# Standardized acceptance-report heading: "# T-0089 验收报告（acceptance-report）"
_ACCEPTANCE_HEADING_RE = re.compile(r"^#\s+(T-\d{4})\s+验收报告")
# Title line: "> **T-0089: 学习回路与工程化 — ... | 2026-08-01**"
_TITLE_LINE_RE = re.compile(r"^\s*>\s*\*\*T-\d{4}\s*:\s*(.+?)\s*\*\*")
# Gate line: "> Gate: G-T-0089-REQUIREMENTS（user 批准，approval_text="...")"
_GATE_LINE_RE = re.compile(
    r"^\s*>\s*Gate\s*:\s*(G-T-\d{4}-[A-Z0-9-]+)\s*(.*)$"
)
# Review verdict line: "> 独立审查：GO（6/6 AC，...）"
_REVIEW_LINE_RE = re.compile(r"^\s*>\s*独立审查\s*：\s*(\S.*)$")
# Fallback verdict: "**GO**（...）" / "**CONDITIONAL_GO**..."
_VERDICT_RE = re.compile(r"^\s*\*\*([A-Z][A-Z0-9_]*)\*\*\s*(.*)$")
# Legacy section heading: "## 已知遗留（P3，记录）" etc.
_LEGACY_HEADING_RE = re.compile(r"^#{1,6}\s+\S*.*(?:已知遗留|遗留)")
# Bullet line: "- ..."
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
# A date inside the title line: "| 2026-08-01"
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_TASK_ID_RE = re.compile(r"\b(T-\d{4})\b")

_LINE_CAP = 300  # content tail cap for extracted gate-line text


# ── Report ─────────────────────────────────────────────────────────────────


@dataclass
class MemoryExtractionReport:
    """Deterministic summary of one extract_memories run.

    Attributes:
        created: Number of knowledge entries newly appended.
        duplicates: Number of already-present entries skipped (idempotency).
        sources: Per-source counters, e.g. {"lessons": 3,
            "acceptance_reports": 4, "skipped_reports": 1}.
        total_entries: Knowledge store size after the run.
        created_entry_ids: entry_ids appended by this run (diagnostics).
    """
    created: int = 0
    duplicates: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    total_entries: int = 0
    created_entry_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "duplicates": self.duplicates,
            "sources": dict(self.sources),
            "total_entries": self.total_entries,
            "created_entry_ids": list(self.created_entry_ids),
        }


# ── Lesson → knowledge (gate_lessons 为源) ─────────────────────────────────


def _lesson_kind(decision: str) -> str:
    """Approved gates record positive experience; rejections record lessons."""
    if decision == DECISION_APPROVED:
        return KIND_BEST_PRACTICE
    return KIND_LESSON


def _lesson_entry_args(lesson) -> dict:
    """Map one GateLesson to knowledge_store.put_entry keyword arguments."""
    content = (
        f"{lesson.gate_id} {lesson.decision}（{lesson.reason_category}）: "
        f"{lesson.reason_text}"
    )
    if lesson.repair_suggestion:
        content += f" 修复建议: {lesson.repair_suggestion}"
    return {
        "kind": _lesson_kind(lesson.decision),
        "source_type": SOURCE_GATE,
        "source_id": lesson.gate_id,
        "task_id": lesson.task_id,
        "tags": ["gate", lesson.decision, lesson.reason_category],
        "content": content,
        "recorded_at": lesson.recorded_at,
    }


def extract_from_lessons(
    project_root: str | Path,
    *,
    task_ids: set[str] | None = None,
    relative_path: str | None = None,
    lessons_relative_path: str | None = None,
) -> MemoryExtractionReport:
    """Derive knowledge entries from recorded gate lessons (idempotent).

    Each lesson becomes one entry: rejected / repair_requested → ``lesson``,
    approved → ``best_practice``. The source file (gate-lessons.yaml) is
    read-only; knowledge is a derived view.
    """
    report = MemoryExtractionReport()
    lessons = load_lessons(project_root, lessons_relative_path)
    report.sources["lessons"] = len(lessons)
    for lesson in lessons:
        if task_ids is not None and lesson.task_id not in task_ids:
            continue
        _put_reporting(project_root, report, relative_path, **_lesson_entry_args(lesson))
    return report


# ── Acceptance reports → knowledge (验收报告为源) ───────────────────────────


def _parse_acceptance_report(text: str, task_id: str) -> list[dict]:
    """Rule-based extraction of one standardized acceptance report.

    Returns a list of put_entry keyword-arg dicts: title decision, review
    verdict decision, gate decision and legacy pitfalls. Unmatched sections
    are skipped — extraction never invents content.
    """
    lines = text.splitlines()
    entries: list[dict] = []

    # Title line → decision entry (task source).
    title: str | None = None
    date: str | None = None
    for line in lines[:12]:
        match = _TITLE_LINE_RE.match(line)
        if match:
            raw_title = match.group(1).strip()
            # Strip a trailing " | <date>" suffix if present.
            if " | " in raw_title:
                raw_title, _, date_part = raw_title.rpartition(" | ")
                raw_title = raw_title.strip()
                date = date_part.strip()
            title = raw_title
            if date is None:
                date_match = _DATE_RE.search(line)
                if date_match:
                    date = date_match.group(1)
            break
    if title is None:
        return entries  # not a standardized report — skip entirely
    recorded_at = f"{date}T00:00:00+00:00" if date else None

    entries.append({
        "kind": KIND_DECISION,
        "source_type": SOURCE_TASK,
        "source_id": task_id,
        "task_id": task_id,
        "tags": ["acceptance", "title"],
        "content": f"{task_id} 验收: {title}",
        "recorded_at": recorded_at,
    })

    # Gate line → gate entry (gate source, retrievable by by_gate).
    gate_id: str | None = None
    gate_tail: str = ""
    for line in lines:
        match = _GATE_LINE_RE.match(line)
        if match:
            gate_id = match.group(1)
            gate_tail = match.group(2).strip()[: _LINE_CAP]
            break
    if gate_id:
        tail_lower = gate_tail.casefold()
        if "批准" in tail_lower or "approve" in tail_lower:
            kind = KIND_BEST_PRACTICE
        elif "拒绝" in tail_lower or "reject" in tail_lower:
            kind = KIND_LESSON
        else:
            kind = KIND_DECISION
        gate_content = f"{gate_id}: {gate_tail}" if gate_tail else gate_id
        entries.append({
            "kind": kind,
            "source_type": SOURCE_GATE,
            "source_id": gate_id,
            "task_id": task_id,
            "tags": ["acceptance", "gate"],
            "content": gate_content,
            "recorded_at": recorded_at,
        })

    # Review verdict → decision entry (独立审查 line, verdict fallback).
    review: str | None = None
    for line in lines:
        match = _REVIEW_LINE_RE.match(line)
        if match:
            review = match.group(1).strip()
            break
    if review is None:
        for line in lines:
            match = _VERDICT_RE.match(line)
            if match:
                review = f"{match.group(1)} {match.group(2).strip()}".strip()
                break
    if review:
        entries.append({
            "kind": KIND_DECISION,
            "source_type": SOURCE_TASK,
            "source_id": task_id,
            "task_id": task_id,
            "tags": ["acceptance", "review"],
            "content": f"{task_id} 独立审查: {review[: _LINE_CAP]}",
            "recorded_at": recorded_at,
        })

    # Legacy section → pitfall entries (已知遗留 bullets).
    in_legacy = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            in_legacy = bool(_LEGACY_HEADING_RE.match(stripped))
            continue
        if stripped.startswith("|"):
            continue
        if in_legacy:
            bullet = _BULLET_RE.match(stripped)
            if bullet:
                entries.append({
                    "kind": KIND_PITFALL,
                    "source_type": SOURCE_TASK,
                    "source_id": task_id,
                    "task_id": task_id,
                    "tags": ["acceptance", "遗留"],
                    "content": (
                        f"{task_id} 已知遗留: "
                        f"{bullet.group(1)[: _LINE_CAP]}"
                    ),
                    "recorded_at": recorded_at,
                })
    return entries


def extract_from_acceptance_reports(
    project_root: str | Path,
    *,
    task_ids: set[str] | None = None,
    relative_path: str | None = None,
) -> MemoryExtractionReport:
    """Derive knowledge entries from task acceptance reports (idempotent).

    Scans ``.ai/evidence/T-*/acceptance/*.md``. Only standardized reports
    (heading "# T-XXXX 验收报告" or a "> **T-XXXX: ...**" title line) are
    parsed; other files are counted in ``sources["skipped_reports"]``.
    """
    report = MemoryExtractionReport()
    evidence_dir = Path(project_root) / ".ai" / "evidence"
    if not evidence_dir.is_dir():
        return report
    acceptance_files: list[Path] = []
    for task_dir in sorted(evidence_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        task_match = _TASK_ID_RE.search(task_dir.name)
        if not task_match:
            continue
        task_id = task_match.group(1)
        if task_ids is not None and task_id not in task_ids:
            continue
        acceptance_dir = task_dir / "acceptance"
        if not acceptance_dir.is_dir():
            continue
        for md_file in sorted(acceptance_dir.glob("*.md")):
            acceptance_files.append((task_id, md_file))

    report.sources["acceptance_reports"] = len(acceptance_files)
    skipped = 0
    for task_id, md_file in acceptance_files:
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        parsed = _parse_acceptance_report(text, task_id)
        if not parsed:
            skipped += 1
            continue
        for kwargs in parsed:
            _put_reporting(project_root, report, relative_path, **kwargs)
    report.sources["skipped_reports"] = skipped
    return report


def _put_reporting(
    project_root: str | Path,
    report: MemoryExtractionReport,
    relative_path: str | None,
    **kwargs,
) -> None:
    """put_entry + report bookkeeping (created vs idempotent duplicate)."""
    entry, created = put_entry(
        project_root, relative_path=relative_path, **kwargs
    )
    if created:
        report.created += 1
        report.created_entry_ids.append(entry.entry_id)
    else:
        report.duplicates += 1


# ── Aggregate extraction ───────────────────────────────────────────────────


def extract_memories(
    project_root: str | Path,
    *,
    task_ids: set[str] | None = None,
    relative_path: str | None = None,
    lessons_relative_path: str | None = None,
) -> MemoryExtractionReport:
    """Extract structured experience from all sources into the knowledge store.

    Sources (read-only): gate-lessons.yaml (T-0089) + task acceptance
    reports. Writes are idempotent — re-running converges and never
    duplicates. Returns a MemoryExtractionReport describing the run.
    """
    report = MemoryExtractionReport()
    lessons_report = extract_from_lessons(
        project_root,
        task_ids=task_ids,
        relative_path=relative_path,
        lessons_relative_path=lessons_relative_path,
    )
    acceptance_report = extract_from_acceptance_reports(
        project_root, task_ids=task_ids, relative_path=relative_path
    )
    report.created = lessons_report.created + acceptance_report.created
    report.duplicates = (
        lessons_report.duplicates + acceptance_report.duplicates
    )
    report.sources.update(lessons_report.sources)
    for key, value in acceptance_report.sources.items():
        report.sources[key] = report.sources.get(key, 0) + value
    report.created_entry_ids = (
        lessons_report.created_entry_ids + acceptance_report.created_entry_ids
    )
    report.total_entries = len(load_entries(project_root, relative_path))
    return report


# ── Recall (供注入) ────────────────────────────────────────────────────────


def recall(
    project_root: str | Path,
    *,
    task_id: str | None = None,
    gate_id: str | None = None,
    tag: str | None = None,
    keyword: str | None = None,
    limit: int = DEFAULT_RECALL_LIMIT,
    relative_path: str | None = None,
) -> list:
    """Recall relevant experience for injection (top-N, newest first).

    All supplied filters are AND-combined. The default limit (5) bounds
    context injection so memory never floods a prompt. Returns knowledge
    entries; an empty store yields an empty list (no error).
    """
    return query(
        project_root,
        task_id=task_id,
        gate_id=gate_id,
        tag=tag,
        keyword=keyword,
        limit=limit,
        relative_path=relative_path,
    )


def memories_to_context(
    entries: list,
    *,
    content_max_chars: int = DEFAULT_MEMORY_CONTENT_MAX_CHARS,
) -> str:
    """Render recalled entries as a compact markdown memory section.

    One bullet per entry: kind — source id [tags]: content head. Empty
    input → "" (callers render nothing, keeping default views unchanged).
    """
    if not entries:
        return ""
    lines = ["## 相关经验（Related Memories）"]
    for entry in entries:
        content = entry.content
        if len(content) > content_max_chars:
            content = content[:content_max_chars] + "…"
        tags = ", ".join(entry.tags)
        lines.append(f"- ({entry.kind}) {entry.source_id} [{tags}]: {content}")
    return "\n".join(lines)
