"""
Tests for loop_core.knowledge_store + loop_core.memory_service (D3, T-0096).

Covers T-0096 AC-01..AC-04:
- AC-01: knowledge storage — schema validation (fail-closed), idempotent
  writes, multi-axis retrieval (by_task / by_gate / by_tag / keyword) with
  search caps
- AC-02: memory service — rule-based extraction from gate_lessons +
  acceptance reports; recall filters and top-N limit
- AC-03: gate_feedback integration — lessons are the *source*, knowledge is
  the derived view; record_gate_lesson has no knowledge coupling; extraction
  is idempotent (no duplicates)
- AC-04: context_loader optional memory injection — default unchanged,
  opt-in injection bounded by memory_limit
"""
from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from loop_core.context_loader import ContextLoader
from loop_core.gate_feedback import (
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_REPAIR_REQUESTED,
    DEFAULT_LESSONS_RELATIVE_PATH,
    load_lessons,
    record_gate_lesson,
)
from loop_core.knowledge_store import (
    DEFAULT_KNOWLEDGE_RELATIVE_PATH,
    DEFAULT_SEARCH_LIMIT,
    KIND_BEST_PRACTICE,
    KIND_DECISION,
    KIND_LESSON,
    KIND_PITFALL,
    KNOWLEDGE_SCHEMA,
    KNOWLEDGE_SCHEMA_VERSION,
    SOURCE_GATE,
    SOURCE_TASK,
    InvalidKnowledgeEntryError,
    KnowledgeEntry,
    KnowledgeStoreError,
    by_gate,
    by_tag,
    by_task,
    load_entries,
    make_entry_id,
    put_entry,
    query,
    search,
)
from loop_core.memory_service import (
    extract_from_acceptance_reports,
    extract_from_lessons,
    extract_memories,
    memories_to_context,
    recall,
)

GATE_ID = "G-T-0100-CLOSEOUT-REVIEW"
TASK_ID = "T-0100"


# ── Fixtures / helpers ─────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """A scratch project root; all stores live under tmp_path/.ai."""
    return tmp_path


def _put(project, **overrides):
    kwargs = {
        "kind": KIND_LESSON,
        "source_type": SOURCE_GATE,
        "source_id": GATE_ID,
        "task_id": TASK_ID,
        "tags": ["gate", "rejected", "evidence"],
        "content": "Closeout review failed because the evidence trail was stale.",
        "recorded_at": "2026-07-01T01:00:00+00:00",
    }
    kwargs.update(overrides)
    return put_entry(project, **kwargs)


def _seed_store(project, n=6, task_id=TASK_ID):
    """n gate-sourced lesson entries with distinct timestamps/content."""
    for i in range(n):
        _put(
            project,
            source_id=f"G-T-0100-REVIEW-{i}",
            task_id=task_id,
            content=f"Rejection reason number {i} for the closeout review.",
            recorded_at=f"2026-07-0{i + 1}T01:00:00+00:00",
        )


def _seed_lessons(project, task_id="T-0102"):
    """Three gate lessons across the decision spectrum."""
    record_gate_lesson(
        project, gate_id="G-T-0102-REVIEW-1", task_id=task_id,
        decision=DECISION_REJECTED, reason_category="evidence",
        reason_text="Evidence attachments missing from the packet.",
        repair_suggestion="Attach evidence then rerun.",
        recorded_at="2026-07-10T01:00:00+00:00",
    )
    record_gate_lesson(
        project, gate_id="G-T-0102-REVIEW-2", task_id=task_id,
        decision=DECISION_REPAIR_REQUESTED, reason_category="wording",
        reason_text="Registry wording conflicts with AGENTS.md.",
        recorded_at="2026-07-11T01:00:00+00:00",
    )
    record_gate_lesson(
        project, gate_id="G-T-0102-REVIEW-3", task_id=task_id,
        decision=DECISION_APPROVED, reason_category="scope",
        reason_text="Scope matched the approved gate.",
        recorded_at="2026-07-12T01:00:00+00:00",
    )


_ACCEPTANCE_SAMPLE = """\
# T-0102 验收报告（acceptance-report）

> **T-0102: 知识记忆试点 — 提取与注入 | 2026-07-30**
> Gate: G-T-0102-REQUIREMENTS（user 批准，approval_text="批准 T-0102 需求"）
> 独立审查：GO（6/6 AC，约束零弱化，2 项 P3）

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | 知识存储 | ✅ PASS | 有测试 |
| AC-02 | 记忆服务 | ✅ PASS | 有测试 |

## 最终裁决

**GO**（独立审查 GO，6/6 AC 全 PASS）

## 已知遗留（P3，记录）

- 遗留项一：知识存储轮转待后续处理
- 遗留项二：注入上限需要监控
"""


def _seed_acceptance(project, task_id="T-0102", text=None):
    text = text if text is not None else _ACCEPTANCE_SAMPLE
    path = project / ".ai" / "evidence" / task_id / "acceptance" / "acceptance-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _role_project(tmp_path):
    """A project with a minimal role directory for ContextLoader."""
    role_dir = tmp_path / "agents" / "quality-engineer"
    role_dir.mkdir(parents=True)
    (role_dir / "CONTRACT.yaml").write_text(
        "role_id: quality-engineer\n"
        "identity:\n"
        "  title: 资深质量工程师\n"
        "fixed_stance:\n"
        '  - "我的职责是找问题，不是证明没问题"\n'
        "responsibilities:\n"
        "  - 设计测试策略\n"
        "prohibitions:\n"
        "  - 禁止凭空断言\n",
        encoding="utf-8",
    )
    (role_dir / "THINKING_FRAMEWORK.md").write_text(
        "# 框架\n\n### Step 1: 质量全局视角\n内容\n", encoding="utf-8"
    )
    (role_dir / "INTERNAL_LOOP.md").write_text(
        "# 内部 Loop\n\n- 合同合规自检\n", encoding="utf-8"
    )
    (tmp_path / "architecture.md").write_text(
        "## Quality Gate\n质量门禁说明。\n\n## Deployment\n部署说明。\n",
        encoding="utf-8",
    )
    return tmp_path


def _store_data(project):
    path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════
# AC-01: 知识存储 — schema / 幂等 / 多维检索
# ═══════════════════════════════════════════════════════════════════════


class TestAC01Schema:
    """put_entry creates a fully structured, schema-valid store."""

    def test_put_creates_store_file(self, project):
        entry, created = _put(project)
        assert created is True
        path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
        assert path.exists()
        data = _store_data(project)
        assert data["schema"] == KNOWLEDGE_SCHEMA
        assert data["schema_version"] == KNOWLEDGE_SCHEMA_VERSION
        assert len(data["entries"]) == 1
        assert data["entries"][0]["entry_id"] == entry.entry_id

    def test_put_fields_complete(self, project):
        entry, _ = _put(project)
        assert entry.entry_id.startswith("KE-")
        assert entry.kind == KIND_LESSON
        assert entry.source_type == SOURCE_GATE
        assert entry.source_id == GATE_ID
        assert entry.task_id == TASK_ID
        assert entry.tags == ["gate", "rejected", "evidence"]
        assert entry.content
        assert entry.version == 1
        assert entry.schema_version == KNOWLEDGE_SCHEMA_VERSION
        datetime.fromisoformat(entry.recorded_at)
        assert entry.recorded_at.endswith("+00:00")

    def test_entry_id_deterministic(self, project):
        entry1, created1 = _put(project)
        entry2, created2 = _put(project)
        assert created1 is True and created2 is False
        assert entry1.entry_id == entry2.entry_id
        # Deterministic across processes: recompute and compare
        assert entry1.entry_id == make_entry_id(
            KIND_LESSON, SOURCE_GATE, GATE_ID,
            "Closeout review failed because the evidence trail was stale.",
        )

    def test_roundtrip_load_keeps_fields(self, project):
        entry, _ = _put(project)
        loaded = load_entries(project)
        assert len(loaded) == 1
        assert loaded[0].to_dict() == entry.to_dict()
        assert KnowledgeEntry.from_dict(entry.to_dict()).to_dict() == entry.to_dict()

    def test_unknown_kind_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, kind="anecdote")

    def test_unknown_source_type_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, source_type="email")

    def test_empty_content_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, content="   ")

    def test_empty_source_id_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, source_id="")

    def test_empty_task_id_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, task_id="  ")

    def test_bad_tags_rejected(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, tags=["bad tag"])
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, tags=[""])
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, tags=["a,b"])
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, tags=["x" * 41])
        with pytest.raises(InvalidKnowledgeEntryError):
            _put(project, tags="not-a-list")

    def test_tags_normalized_and_deduped(self, project):
        entry, _ = _put(project, tags=[" gate ", "Gate", "evidence", "gate"])
        assert entry.tags == ["gate", "evidence"]

    def test_malformed_store_fails_closed(self, project):
        path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("entries: [not-a-dict]\n", encoding="utf-8")
        with pytest.raises(InvalidKnowledgeEntryError):
            load_entries(project)

    def test_unsupported_schema_fails_closed(self, project):
        path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump({"schema": "other", "entries": []}), encoding="utf-8"
        )
        with pytest.raises(KnowledgeStoreError):
            load_entries(project)

    def test_missing_file_loads_empty(self, project):
        assert load_entries(project) == []


class TestAC01Idempotency:
    """Same source + same content fingerprint records at most once."""

    def test_identical_put_is_idempotent(self, project):
        entry1, created1 = _put(project)
        entry2, created2 = _put(project)
        entry3, created3 = _put(project)
        assert (created1, created2, created3) == (True, False, False)
        assert entry1.entry_id == entry2.entry_id == entry3.entry_id
        assert len(load_entries(project)) == 1

    def test_fingerprint_ignores_whitespace_and_case(self, project):
        entry1, created1 = _put(
            project, content="  Evidence   Missing. "
        )
        entry2, created2 = _put(project, content="evidence missing.")
        assert created1 is True and created2 is False
        assert entry1.entry_id == entry2.entry_id

    def test_different_content_records_separately(self, project):
        _put(project)
        entry2, created2 = _put(
            project, content="A completely different lesson body."
        )
        assert created2 is True
        assert entry2.entry_id != load_entries(project)[0].entry_id
        assert len(load_entries(project)) == 2

    def test_different_source_records_separately(self, project):
        _put(project)
        entry2, created2 = _put(project, source_id="G-T-0100-REVIEW-2")
        assert created2 is True
        assert len(load_entries(project)) == 2

    def test_different_kind_records_separately(self, project):
        _put(project, kind=KIND_LESSON)
        entry2, created2 = _put(project, kind=KIND_BEST_PRACTICE)
        assert created2 is True
        assert entry2.kind == KIND_BEST_PRACTICE
        assert len(load_entries(project)) == 2

    def test_duplicate_across_append_generations(self, project):
        _put(project)
        _put(project, source_id="G-T-0100-REVIEW-2", content="In between.")
        entry, created = _put(project)
        assert created is False
        assert entry.source_id == GATE_ID
        assert len(load_entries(project)) == 2


class TestAC01Retrieval:
    """by_task / by_gate / by_tag / search + combined query work."""

    def _seed(self, project):
        _seed_store(project, n=4)
        # A task-source decision entry for the same task
        put_entry(
            project, kind=KIND_DECISION, source_type=SOURCE_TASK,
            source_id=TASK_ID, task_id=TASK_ID,
            tags=["acceptance", "title"],
            content=f"{TASK_ID} 验收: 试点任务完成",
            recorded_at="2026-07-05T01:00:00+00:00",
        )
        # An unrelated task
        _put(
            project, source_id="G-T-0200-X", task_id="T-0200",
            content="Unrelated task lesson.",
            recorded_at="2026-07-06T01:00:00+00:00",
        )

    def test_by_task_matches_owned_and_task_source(self, project):
        self._seed(project)
        entries = by_task(project, TASK_ID)
        assert len(entries) == 5  # 4 gate lessons + 1 task-source entry
        assert all(e.task_id == TASK_ID for e in entries)

    def test_by_task_no_match(self, project):
        self._seed(project)
        assert by_task(project, "T-NOPE") == []

    def test_by_task_unknown_id_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            by_task(project, "")

    def test_by_gate(self, project):
        self._seed(project)
        entries = by_gate(project, "G-T-0100-REVIEW-1")
        assert [e.source_id for e in entries] == ["G-T-0100-REVIEW-1"]
        assert len(entries) == 1

    def test_by_tag_case_insensitive(self, project):
        self._seed(project)
        assert len(by_tag(project, "EVIDENCE")) == 5
        assert len(by_tag(project, "acceptance")) == 1

    def test_by_tag_bad_tag_raises(self, project):
        with pytest.raises(InvalidKnowledgeEntryError):
            by_tag(project, "bad tag")

    def test_search_content_case_insensitive(self, project):
        self._seed(project)
        assert len(search(project, "REJECTION")) == 4
        assert search(project, "rejection")[0].source_id == "G-T-0100-REVIEW-3"

    def test_search_tags_and_source(self, project):
        self._seed(project)
        assert len(search(project, "验收")) == 1
        assert len(search(project, "G-T-0200-X")) == 1

    def test_search_no_match_empty(self, project):
        self._seed(project)
        assert search(project, "nonexistent-keyword") == []

    def test_search_empty_keyword_returns_all_capped(self, project):
        self._seed(project)
        assert len(search(project, "")) == 6

    def test_search_respects_limit(self, project):
        self._seed(project)
        assert len(search(project, "", limit=2)) == 2
        assert len(search(project, "", limit=0)) == 0

    def test_default_search_cap(self, project):
        """search 返回上限: >20 entries → exactly 20."""
        _seed_store(project, n=25)
        results = search(project, "")
        assert len(results) == DEFAULT_SEARCH_LIMIT == 20

    def test_query_combined_filters_and(self, project):
        self._seed(project)
        # task + tag AND
        assert len(query(project, task_id=TASK_ID, tag="evidence")) == 4
        # task + keyword AND
        assert len(query(project, task_id=TASK_ID, keyword="验收")) == 1
        # gate + keyword AND
        assert len(query(project, gate_id="G-T-0100-REVIEW-1",
                         keyword="number 1")) == 1
        # conflicting filters → empty
        assert query(project, task_id=TASK_ID, gate_id="G-T-0200-X") == []

    def test_query_no_filters_newest_first_capped(self, project):
        self._seed(project)
        results = query(project, limit=3)
        assert len(results) == 3
        # newest first
        assert results[0].recorded_at == "2026-07-06T01:00:00+00:00"

    def test_query_keyword_empty_string_is_noop(self, project):
        self._seed(project)
        assert len(query(project, keyword="")) == 6


# ═══════════════════════════════════════════════════════════════════════
# AC-02: 记忆服务 — 提取（lessons/验收）+ recall 过滤与上限
# ═══════════════════════════════════════════════════════════════════════


class TestAC02ExtractionFromLessons:
    """gate_lessons 为源 → knowledge 派生（规则式映射）。"""

    def test_kind_mapping(self, project):
        _seed_lessons(project)
        report = extract_from_lessons(project)
        assert report.created == 3
        kinds = {e.kind for e in load_entries(project)}
        assert kinds == {KIND_LESSON, KIND_BEST_PRACTICE}

    def test_fields_propagated(self, project):
        _seed_lessons(project)
        extract_from_lessons(project)
        entries = load_entries(project)
        rejected = next(
            e for e in entries if e.source_id == "G-T-0102-REVIEW-1"
        )
        assert rejected.kind == KIND_LESSON
        assert rejected.source_type == SOURCE_GATE
        assert rejected.task_id == "T-0102"
        assert rejected.tags == ["gate", "rejected", "evidence"]
        assert "Evidence attachments missing" in rejected.content
        assert "修复建议: Attach evidence then rerun." in rejected.content
        assert rejected.recorded_at == "2026-07-10T01:00:00+00:00"

    def test_approved_becomes_best_practice(self, project):
        _seed_lessons(project)
        extract_from_lessons(project)
        approved = next(
            e for e in load_entries(project)
            if e.source_id == "G-T-0102-REVIEW-3"
        )
        assert approved.kind == KIND_BEST_PRACTICE
        assert approved.tags == ["gate", "approved", "scope"]

    def test_extract_is_idempotent(self, project):
        _seed_lessons(project)
        report1 = extract_from_lessons(project)
        report2 = extract_from_lessons(project)
        assert report1.created == 3
        assert report2.created == 0
        assert report2.duplicates == 3
        assert len(load_entries(project)) == 3

    def test_source_file_never_modified(self, project):
        _seed_lessons(project)
        path = project / DEFAULT_LESSONS_RELATIVE_PATH
        before = path.read_bytes()
        extract_from_lessons(project)
        assert path.read_bytes() == before
        assert len(load_lessons(project)) == 3


class TestAC02ExtractionFromAcceptance:
    """验收报告（标题/裁决/遗留）→ knowledge（规则式解析）。"""

    def test_title_decision_entry(self, project):
        _seed_acceptance(project)
        report = extract_from_acceptance_reports(project)
        assert report.created == 5  # title + gate + review + 2 pitfalls
        title = next(
            e for e in load_entries(project) if "title" in e.tags
        )
        assert title.kind == KIND_DECISION
        assert title.source_type == SOURCE_TASK
        assert title.source_id == "T-0102"
        assert title.content == "T-0102 验收: 知识记忆试点 — 提取与注入"
        assert title.recorded_at == "2026-07-30T00:00:00+00:00"

    def test_gate_entry(self, project):
        _seed_acceptance(project)
        extract_from_acceptance_reports(project)
        gate_entries = by_gate(project, "G-T-0102-REQUIREMENTS")
        assert len(gate_entries) == 1
        gate_entry = gate_entries[0]
        assert gate_entry.kind == KIND_BEST_PRACTICE  # user 批准
        assert gate_entry.task_id == "T-0102"
        assert "user 批准" in gate_entry.content

    def test_review_verdict_entry(self, project):
        _seed_acceptance(project)
        extract_from_acceptance_reports(project)
        review = next(
            e for e in load_entries(project) if "review" in e.tags
        )
        assert review.kind == KIND_DECISION
        assert "GO（6/6 AC，约束零弱化，2 项 P3）" in review.content

    def test_legacy_pitfalls(self, project):
        _seed_acceptance(project)
        extract_from_acceptance_reports(project)
        pitfalls = [
            e for e in load_entries(project) if e.kind == KIND_PITFALL
        ]
        assert len(pitfalls) == 2
        assert all("已知遗留" in e.content for e in pitfalls)
        assert "遗留项一" in pitfalls[0].content
        assert pitfalls[0].tags == ["acceptance", "遗留"]

    def test_rejected_gate_line_becomes_lesson(self, project):
        _seed_acceptance(
            project,
            text=_ACCEPTANCE_SAMPLE.replace(
                '> Gate: G-T-0102-REQUIREMENTS（user 批准，approval_text="批准 T-0102 需求"）',
                "> Gate: G-T-0102-REQUIREMENTS（user 拒绝，approval_text=\"拒绝 T-0102 需求\"）",
            ),
        )
        extract_from_acceptance_reports(project)
        gate_entries = by_gate(project, "G-T-0102-REQUIREMENTS")
        assert gate_entries[0].kind == KIND_LESSON

    def test_nonstandard_reports_skipped(self, project):
        _seed_acceptance(project)
        extra = project / ".ai" / "evidence" / "T-0103" / "acceptance"
        extra.mkdir(parents=True)
        (extra / "regression-results.md").write_text(
            "# T-0103 Regression Results\n\nnot a standardized report\n",
            encoding="utf-8",
        )
        (extra / "acceptance-report.md").write_text(
            "no recognizable structure at all\n", encoding="utf-8"
        )
        report = extract_from_acceptance_reports(project)
        assert report.created == 5  # only T-0102's entries
        assert report.sources["skipped_reports"] == 2
        assert len(load_entries(project)) == 5

    def test_missing_acceptance_dir_is_empty(self, project):
        report = extract_from_acceptance_reports(project)
        assert report.created == 0
        assert report.sources.get("acceptance_reports", 0) == 0
        assert load_entries(project) == []


class TestAC02ExtractMemoriesAndRecall:
    """extract_memories 聚合 + recall 过滤与上限。"""

    def test_extract_memories_aggregates_sources(self, project):
        _seed_lessons(project)
        _seed_acceptance(project)
        report = extract_memories(project)
        assert report.created == 8  # 3 lessons + 5 acceptance-derived
        assert report.sources["lessons"] == 3
        assert report.sources["acceptance_reports"] == 1
        assert report.total_entries == 8
        assert len(report.created_entry_ids) == 8

    def test_extract_memories_task_filter(self, project):
        _seed_lessons(project)                     # T-0102 lessons
        _seed_acceptance(project, task_id="T-0102")
        _seed_acceptance(
            project, task_id="T-0104",
            text=_ACCEPTANCE_SAMPLE.replace("T-0102", "T-0104"),
        )
        report = extract_memories(project, task_ids={"T-0104"})
        assert report.created == 5  # only T-0104 acceptance entries
        assert all(e.task_id == "T-0104" for e in load_entries(project))

    def test_extract_memories_empty_project(self, project):
        report = extract_memories(project)
        assert report.created == 0
        assert report.duplicates == 0
        assert report.total_entries == 0

    def test_recall_default_limit_is_5(self, project):
        _seed_store(project, n=8)
        entries = recall(project)
        assert len(entries) == 5
        assert entries[0].recorded_at == "2026-07-08T01:00:00+00:00"

    def test_recall_filters(self, project):
        _seed_store(project, n=4)          # T-0100 gate lessons
        _seed_acceptance(project)          # T-0102 report
        extract_memories(project)
        assert len(recall(project, task_id="T-0102")) == 5
        assert len(recall(project, gate_id="G-T-0102-REQUIREMENTS")) == 1
        assert len(recall(project, tag="遗留")) == 2
        assert len(recall(project, keyword="遗留项一")) == 1

    def test_recall_combined_filters_and_limit(self, project):
        _seed_store(project, n=4)          # T-0100 gate lessons
        _seed_acceptance(project)          # T-0102 report
        extract_memories(project)
        assert recall(project, task_id="T-0100", tag="遗留") == []
        combined = recall(
            project, task_id="T-0100", tag="gate", limit=2
        )
        assert len(combined) == 2
        assert recall(project, limit=0) == []

    def test_recall_empty_store(self, project):
        assert recall(project) == []
        assert recall(project, task_id="T-0102") == []

    def test_memories_to_context_rendering(self, project):
        _seed_store(project, n=2)
        entries = recall(project, limit=2)
        section = memories_to_context(entries)
        assert section.startswith("## 相关经验（Related Memories）")
        assert "(lesson) G-T-0100-REVIEW-1" in section
        assert "gate, rejected, evidence" in section
        assert "Rejection reason number 1" in section

    def test_memories_to_context_truncates_long_content(self, project):
        _put(project, content="长" * 500)
        section = memories_to_context(load_entries(project),
                                      content_max_chars=50)
        assert "…" in section
        assert len(section.split("]: ", 1)[1]) <= 60

    def test_memories_to_context_empty(self, project):
        assert memories_to_context([]) == ""


# ═══════════════════════════════════════════════════════════════════════
# AC-03: 与 gate_feedback 整合 — lessons 为源，knowledge 为派生视图
# ═══════════════════════════════════════════════════════════════════════


class TestAC03Integration:
    """Data flow: lessons 写入 → extract → knowledge 派生；无重复、无反向耦合。"""

    def test_record_gate_lesson_does_not_touch_knowledge(self, project):
        """record_gate_lesson 内部不写 knowledge（无耦合）。"""
        _seed_lessons(project)
        assert not (project / DEFAULT_KNOWLEDGE_RELATIVE_PATH).exists()

    def test_extract_memories_twice_no_duplicates(self, project):
        _seed_lessons(project)
        _seed_acceptance(project)
        first = extract_memories(project)
        second = extract_memories(project)
        assert first.created == 8
        assert second.created == 0
        assert second.duplicates == 8
        assert second.total_entries == first.total_entries == 8

    def test_derived_entries_match_lesson_source(self, project):
        _seed_lessons(project)
        extract_memories(project)
        lessons = load_lessons(project)
        entries = load_entries(project)
        assert len(entries) == len(lessons) == 3
        for lesson in lessons:
            derived = next(
                e for e in entries if e.source_id == lesson.gate_id
            )
            assert derived.source_type == SOURCE_GATE
            assert derived.task_id == lesson.task_id
            assert lesson.reason_text in derived.content
            assert derived.recorded_at == lesson.recorded_at

    def test_extraction_never_writes_source_files(self, project):
        _seed_lessons(project)
        _seed_acceptance(project)
        lessons_before = (project / DEFAULT_LESSONS_RELATIVE_PATH).read_bytes()
        acceptance_before = (
            project / ".ai" / "evidence" / "T-0102" / "acceptance"
            / "acceptance-report.md"
        ).read_bytes()
        extract_memories(project)
        assert (project / DEFAULT_LESSONS_RELATIVE_PATH).read_bytes() == (
            lessons_before
        )
        assert (
            project / ".ai" / "evidence" / "T-0102" / "acceptance"
            / "acceptance-report.md"
        ).read_bytes() == acceptance_before
        # the only knowledge write lands in the derived store
        assert (project / DEFAULT_KNOWLEDGE_RELATIVE_PATH).exists()

    def test_end_to_end_feedback_to_memory_flow(self, project):
        """拒绝 → lesson → extract → recall(task) 可注入。"""
        record_gate_lesson(
            project, gate_id="G-T-0102-REVIEW-1", task_id="T-0102",
            decision=DECISION_REJECTED, reason_category="evidence",
            reason_text="Stale evidence blocked the closeout.",
            repair_suggestion="Refresh evidence then rerun.",
            recorded_at="2026-07-10T01:00:00+00:00",
        )
        extract_memories(project)
        memories = recall(project, task_id="T-0102", limit=5)
        assert len(memories) == 1
        assert memories[0].source_id == "G-T-0102-REVIEW-1"
        assert "Stale evidence blocked" in memories[0].content
        assert "Refresh evidence" in memories[0].content
        # 同一 lesson 源再次 extract 不重复
        assert extract_memories(project).created == 0


# ═══════════════════════════════════════════════════════════════════════
# AC-04: context_loader 可选记忆注入 — 默认不变，开启注入有上限
# ═══════════════════════════════════════════════════════════════════════


class TestAC04ContextLoader:
    """include_memories 默认关闭；开启时按任务召回并受 memory_limit 约束。"""

    def _loader(self, project):
        return ContextLoader(project)

    def test_default_load_unchanged(self, tmp_path):
        project = _role_project(tmp_path)
        loader = self._loader(project)
        default = loader.load_role_context("quality-engineer", complexity=0.9)
        explicit_off = loader.load_role_context(
            "quality-engineer", complexity=0.9, include_memories=False
        )
        assert default.system_prompt == explicit_off.system_prompt
        assert default.loaded_sections == explicit_off.loaded_sections
        assert "Related Memories" not in default.system_prompt

    def test_default_load_for_role_unchanged(self, tmp_path):
        project = _role_project(tmp_path)
        loader = self._loader(project)
        default = loader.load_for_role(
            "quality-engineer", str(project / "architecture.md"),
            complexity=0.9,
        )
        explicit_off = loader.load_for_role(
            "quality-engineer", str(project / "architecture.md"),
            complexity=0.9, include_memories=False,
        )
        assert default.system_prompt == explicit_off.system_prompt
        assert "Related Memories" not in default.system_prompt

    def test_include_memories_injects_section(self, tmp_path):
        project = _role_project(tmp_path)
        _seed_store(project, n=3)
        loader = self._loader(project)
        ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9,
            include_memories=True, memory_limit=5,
        )
        assert "## 相关经验（Related Memories）" in ctx.system_prompt
        assert "[memories: 3 recalled]" in ctx.loaded_sections
        assert ctx.estimated_tokens > 0

    def test_memory_limit_respected(self, tmp_path):
        project = _role_project(tmp_path)
        _seed_store(project, n=8)
        loader = self._loader(project)
        ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9,
            include_memories=True, memory_limit=2,
        )
        section = ctx.system_prompt.split(
            "## 相关经验（Related Memories）", 1
        )[1]
        assert section.count("\n- (lesson)") == 2
        assert "[memories: 2 recalled]" in ctx.loaded_sections

    def test_memory_task_filter(self, tmp_path):
        project = _role_project(tmp_path)
        _seed_store(project, n=3, task_id="T-0100")
        _put(
            project, source_id="G-T-0200-X", task_id="T-0200",
            content="Other task memory.",
            recorded_at="2026-07-09T01:00:00+00:00",
        )
        loader = self._loader(project)
        ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9,
            include_memories=True, memory_task_id="T-0100",
        )
        section = ctx.system_prompt.split(
            "## 相关经验（Related Memories）", 1
        )[1]
        assert "G-T-0200-X" not in section
        assert section.count("\n- (lesson)") == 3

    def test_memory_limit_zero_disables_injection(self, tmp_path):
        project = _role_project(tmp_path)
        _seed_store(project, n=3)
        loader = self._loader(project)
        ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9,
            include_memories=True, memory_limit=0,
        )
        assert "Related Memories" not in ctx.system_prompt

    def test_absent_store_no_section_no_error(self, tmp_path):
        project = _role_project(tmp_path)
        loader = self._loader(project)
        ctx = loader.load_role_context(
            "quality-engineer", complexity=0.9, include_memories=True
        )
        assert "Related Memories" not in ctx.system_prompt
        assert ctx.role_id == "quality-engineer"

    def test_malformed_store_fails_closed_when_enabled(self, tmp_path):
        project = _role_project(tmp_path)
        path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("entries: [broken!!!]\n", encoding="utf-8")
        loader = self._loader(project)
        with pytest.raises(KnowledgeStoreError):
            loader.load_role_context(
                "quality-engineer", complexity=0.9, include_memories=True
            )

    def test_malformed_store_ignored_when_default(self, tmp_path):
        """默认关闭时 store 根本不被读取（默认行为不受影响）。"""
        project = _role_project(tmp_path)
        path = project / DEFAULT_KNOWLEDGE_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("entries: [broken!!!]\n", encoding="utf-8")
        loader = self._loader(project)
        ctx = loader.load_role_context("quality-engineer", complexity=0.9)
        assert "Related Memories" not in ctx.system_prompt
        assert "[memories" not in "".join(ctx.loaded_sections)

    def test_load_for_role_memory_injection(self, tmp_path):
        project = _role_project(tmp_path)
        _seed_store(project, n=3)
        loader = self._loader(project)
        ctx = loader.load_for_role(
            "quality-engineer", str(project / "architecture.md"),
            complexity=0.9,
            include_memories=True, memory_limit=5,
        )
        assert "## 相关经验（Related Memories）" in ctx.system_prompt
        assert "[memories: 3 recalled]" in ctx.loaded_sections
        assert "architecture.md#" in " ".join(ctx.loaded_sections)

    def test_default_full_load_sections_unchanged(self, tmp_path):
        """FULL 加载的既有 section 清单不因可选参数存在而改变。"""
        project = _role_project(tmp_path)
        loader = self._loader(project)
        ctx = loader.load_role_context("quality-engineer", complexity=0.9)
        assert "quality-engineer/CONTRACT.yaml#fixed_stance" in ctx.loaded_sections
        assert "quality-engineer/CONTRACT.yaml#extras" in ctx.loaded_sections
        assert "quality-engineer/THINKING_FRAMEWORK.md" in ctx.loaded_sections
        assert "quality-engineer/INTERNAL_LOOP.md" in ctx.loaded_sections
        assert len(ctx.loaded_sections) == 4
