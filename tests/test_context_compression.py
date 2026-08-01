"""
Tests for U3 (T-0088) — context budget compression in loop_core.context_loader.

Covers:
  - AC-01: token-budget-triggered compression (threshold config takes
    effect; output shrinks after the trigger; under-budget views are
    untouched; evidence-chain integrity is preserved — compression never
    modifies source files).
  - AC-02: hierarchical summarization ("summary of the summary") — the
    compressed result can be compressed again; the level count is
    configurable; key fields (task ID / gate / phase / decision points)
    survive every level.
  - AC-03: evidence citation truncation repair — truncated references are
    restored via unique filesystem matching; ambiguous / missing
    references are marked UNRESOLVED instead of guessed.
  - Backward compatibility: default ContextLoader behaviour is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.context_loader import (  # noqa: E402
    CITATION_MAX_CHARS,
    DEFAULT_BUDGET_TOKENS,
    DEFAULT_MAX_SUMMARY_LEVELS,
    DEFAULT_TRIGGER_RATIO,
    UNRESOLVED_MARKER,
    CitationResolution,
    CitationResolver,
    CompressionResult,
    ContextCompressor,
    ContextLoader,
    LoadLevel,
    _truncate_citation,
    estimate_tokens,
    repair_truncated_references,
    summarize_text,
)

# ============================================================================
# Helpers
# ============================================================================


def _sha256(path: Path) -> str:
    """SHA-256 of a file's bytes (for evidence-chain integrity checks)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_big_prompt(paragraphs: int = 40) -> str:
    """A context-view text comfortably above a 100-token budget.

    Contains headings, key fields (task/gate/phase), decision-point lines
    and an evidence citation so every summary level has salient content.
    """
    body = "\n".join(
        f"Paragraph {i}: The quick brown fox jumps over the lazy dog. "
        f"Decision point {i} was APPROVED with evidence from the quality "
        f"checks performed by the engineering team."
        for i in range(paragraphs)
    )
    return (
        "# Task Context\n"
        "task_id: T-0088\n"
        "gate: G-T-0088-REQUIREMENTS\n"
        "phase: S6\n"
        "decision: BLOCKED because the evidence chain is incomplete.\n"
        + body
        + "\n"
        "See .ai/evidence/T-0088/approval-evidence.json for the gate record."
    )


def _make_project(tmp_path, role_id: str = "tester", **files: str) -> Path:
    """Create a minimal project directory with the given files."""
    root = Path(tmp_path)
    for rel_path, content in files.items():
        fpath = root / rel_path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
    return root


def _make_contract_yaml(role_id: str = "tester") -> str:
    """Build a CONTRACT.yaml (JSON, a valid YAML subset) with rich content."""
    contract = {
        "role_id": role_id,
        "identity": {"title": f"Test {role_id}", "experience": "5 years"},
        "fixed_stance": [
            f"Stance point {i}: always verify evidence before claiming "
            f"success in this workflow context."
            for i in range(20)
        ],
        "responsibilities": [
            f"Responsibility {i}: review the deliverables against the "
            f"contract requirements and record the outcome."
            for i in range(20)
        ],
        "prohibitions": [
            f"Prohibition {i}: never modify source files or skip the gate "
            f"approval process."
            for i in range(20)
        ],
        "veto_power": ["Failing tests lead to a NOGO verdict."],
    }
    return json.dumps(contract, ensure_ascii=False, indent=2)


def _make_framework_md() -> str:
    """THINKING_FRAMEWORK.md with steps, key fields and an evidence citation."""
    steps = "\n".join(
        f"### Step {i}: Analyze the context and evidence thoroughly "
        f"before deciding."
        for i in range(1, 9)
    )
    return (
        "# Test Role Thinking Framework\n\ntask_id: T-0088\n"
        "gate: G-T-0088-REQUIREMENTS\nphase: S6\n\n## Mandatory Thinking Order\n"
        + steps
        + "\n\nEvidence must be cited, e.g. "
        ".ai/evidence/T-0099/approval-evidence.json records the gate "
        "decision and .ai/evidence/T-0099/context-compression/design.md "
        "holds the design."
    )


def _make_t0099_evidence(tmp_path: Path) -> None:
    """Create the T-0099 evidence files referenced by _make_framework_md."""
    for rel in (
        ".ai/evidence/T-0099/approval-evidence.json",
        ".ai/evidence/T-0099/context-compression/design.md",
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}" if rel.endswith(".json") else "# design", encoding="utf-8")


def _make_loop_md() -> str:
    """INTERNAL_LOOP.md with several loop sections."""
    loops = "\n".join(
        f"## Loop {i}: Contract compliance re-check with evidence chain "
        f"verification."
        for i in range(1, 9)
    )
    return "# Test Role Internal Loop\n\n" + loops


def _make_evidence_tree(tmp_path: Path) -> dict[str, Path]:
    """Create .ai/evidence files; returns path -> file map."""
    files = {
        ".ai/evidence/T-0100/approval-evidence.json": '{"status": "approved"}',
        ".ai/evidence/T-0200/approval-evidence.json": '{"status": "approved"}',
        ".ai/evidence/T-0300/unique-report.md": "# unique report",
        ".ai/evidence/T-0300/context-compression/design.md": "# design",
    }
    paths: dict[str, Path] = {}
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        paths[rel] = p
    return paths


# ============================================================================
# AC-01: Budget-triggered compression
# ============================================================================


class TestBudgetTrigger:
    """Token-budget threshold configuration and trigger semantics."""

    def test_threshold_configuration_takes_effect(self):
        """Same text, different budgets: a low budget triggers, a high one does not."""
        text = _make_big_prompt()
        compressor = ContextCompressor(trigger_ratio=DEFAULT_TRIGGER_RATIO)

        low = compressor.compress_if_needed(text, budget_tokens=100)
        high = compressor.compress_if_needed(text, budget_tokens=100_000)

        assert low.triggered is True
        assert high.triggered is False
        assert high.text == text
        assert high.levels_applied == 0

    def test_trigger_fires_when_over_budget_and_output_shrinks(self):
        """Over budget * ratio -> triggered, and the output length drops."""
        text = _make_big_prompt()
        compressor = ContextCompressor(budget_tokens=100, trigger_ratio=0.7)

        result = compressor.compress_if_needed(text)

        assert result.triggered is True
        assert result.levels_applied >= 1
        assert result.estimated_tokens < result.original_tokens
        assert len(result.text) < len(text)
        # Compression metadata recorded
        assert result.budget_tokens == 100
        assert result.trigger_ratio == 0.7

    def test_no_compression_below_threshold(self):
        """Under the trigger threshold the view is returned untouched."""
        text = "Small context that fits comfortably inside the budget."
        compressor = ContextCompressor(budget_tokens=10_000, trigger_ratio=0.7)

        result = compressor.compress_if_needed(text)

        assert result.triggered is False
        assert result.levels_applied == 0
        assert result.text == text
        assert result.estimated_tokens == result.original_tokens

    def test_trigger_ratio_configures_threshold(self):
        """trigger_ratio shifts the threshold: 1.0 never fires, 0.1 fires."""
        text = _make_big_prompt()
        tokens = estimate_tokens(text)

        # ratio=1.0 -> threshold == budget; budget slightly above tokens -> no trigger
        lenient = ContextCompressor(budget_tokens=tokens + 10, trigger_ratio=1.0)
        assert lenient.compress_if_needed(text).triggered is False

        # ratio=0.1 -> threshold == 10% of budget, far below tokens -> trigger
        strict = ContextCompressor(budget_tokens=tokens + 10, trigger_ratio=0.1)
        result = strict.compress_if_needed(text)
        assert result.triggered is True
        assert result.levels_applied >= 1

    def test_invalid_parameters_raise_valueerror(self):
        """budget <= 0, ratio out of (0, 1], max_levels < 1 are rejected."""
        text = _make_big_prompt()
        compressor = ContextCompressor()

        for kwargs in (
            {"budget_tokens": 0},
            {"budget_tokens": -5},
            {"trigger_ratio": 0.0},
            {"trigger_ratio": 1.5},
            {"max_levels": 0},
        ):
            try:
                compressor.compress_if_needed(text, **kwargs)
            except ValueError:
                pass  # expected
            else:
                raise AssertionError(f"Expected ValueError for {kwargs}")

    def test_defaults_are_sane(self):
        """Factory defaults match the documented StaffDeck mapping."""
        assert DEFAULT_BUDGET_TOKENS == 2600  # FULL level ~2600 tokens
        assert DEFAULT_TRIGGER_RATIO == 0.7   # StaffDeck 70% trigger
        assert DEFAULT_MAX_SUMMARY_LEVELS == 2


class TestLoaderBudgetIntegration:
    """load_role_context / load_for_role with a budget (AC-01 + AC-02)."""

    def test_loader_compresses_over_budget_view(self, tmp_path):
        _make_project(
            str(tmp_path),
            tester="x",
            **{
                "agents/tester/CONTRACT.yaml": _make_contract_yaml(),
                "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md(),
                "agents/tester/INTERNAL_LOOP.md": _make_loop_md(),
            },
        )
        _make_t0099_evidence(tmp_path)

        loader = ContextLoader(tmp_path)
        full = loader.load_role_context("tester", complexity=0.8)
        compressed = loader.load_role_context(
            "tester", complexity=0.8, budget_tokens=200, max_levels=2
        )

        # Same level, compressed view strictly smaller
        assert compressed.level == LoadLevel.FULL
        assert compressed.compression is not None
        assert compressed.compression.triggered is True
        assert compressed.estimated_tokens < full.estimated_tokens
        assert len(compressed.system_prompt) < len(full.system_prompt)
        # The compression is recorded in loaded_sections
        assert any("compressed" in s for s in compressed.loaded_sections)
        # Key fields survive the compressed view
        assert "T-0088" in compressed.system_prompt
        assert "G-T-0088-REQUIREMENTS" in compressed.system_prompt
        assert "S6" in compressed.system_prompt
        # Evidence citations survive compression and are repaired
        assert ".ai/evidence/T-0099/approval-evidence.json" in compressed.system_prompt
        assert ".ai/evidence/T-0099/context-compression/design.md" in compressed.system_prompt
        statuses = {c.status for c in compressed.compression.citations}
        assert "RESOLVED" in statuses

    def test_loader_no_budget_is_legacy_behaviour(self, tmp_path):
        """Without budget_tokens, compression never runs (backward compat)."""
        _make_project(
            str(tmp_path),
            tester="x",
            **{"agents/tester/CONTRACT.yaml": _make_contract_yaml()},
        )
        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.8)
        assert ctx.compression is None
        assert "## Fixed Stance" in ctx.system_prompt

    def test_load_for_role_compresses_final_view(self, tmp_path):
        """load_for_role applies the budget to the final assembled view."""
        _make_project(
            str(tmp_path),
            quality_engineer="x",
            **{
                "agents/quality-engineer/CONTRACT.yaml": _make_contract_yaml("quality-engineer"),
                "agents/quality-engineer/THINKING_FRAMEWORK.md": _make_framework_md(),
                "agents/quality-engineer/INTERNAL_LOOP.md": _make_loop_md(),
            },
        )
        doc = tmp_path / "architecture.md"
        doc.write_text(
            "# Architecture\n\n## Testing Strategy\n\n"
            + "This section describes the testing strategy in great detail "
            + "for the purposes of token budget testing. " * 30,
            encoding="utf-8",
        )

        loader = ContextLoader(tmp_path)
        plain = loader.load_for_role("quality-engineer", str(doc), complexity=0.8)
        budgeted = loader.load_for_role(
            "quality-engineer",
            str(doc),
            complexity=0.8,
            budget_tokens=200,
            max_levels=2,
        )

        assert budgeted.compression is not None
        assert budgeted.estimated_tokens < plain.estimated_tokens


class TestEvidenceChainIntegrity:
    """Compression only affects the loaded view — source files never change."""

    def test_compression_does_not_modify_evidence_files(self, tmp_path):
        """Hashes of evidence/task files are identical before and after."""
        files = _make_evidence_tree(tmp_path)
        before = {rel: _sha256(p) for rel, p in files.items()}
        count_before = len(list((tmp_path / ".ai").rglob("*")))

        text = _make_big_prompt()
        text += (
            "\n\nReferences: .ai/evidence/T-0300/unique-report.md and "
            ".ai/evidence/T-0300/context-compression/design.md"
        )
        compressor = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=2,
            project_root=tmp_path,
        )
        result = compressor.compress_if_needed(text)

        # Compression ran and repaired citations against the evidence tree
        assert result.triggered is True
        assert result.citations, "expected citation resolutions"

        after = {rel: _sha256(p) for rel, p in files.items()}
        count_after = len(list((tmp_path / ".ai").rglob("*")))
        assert before == after, "evidence files were modified by compression"
        assert count_before == count_after, "compression created/deleted files"

    def test_loader_with_budget_keeps_evidence_intact(self, tmp_path):
        """End-to-end: loader + budget + citation repair leaves hashes equal."""
        files = _make_evidence_tree(tmp_path)
        before = {rel: _sha256(p) for rel, p in files.items()}

        _make_project(
            str(tmp_path),
            tester="x",
            **{"agents/tester/CONTRACT.yaml": _make_contract_yaml()},
        )
        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context(
            "tester", complexity=0.8, budget_tokens=200, max_levels=2
        )
        assert ctx.compression is not None

        after = {rel: _sha256(p) for rel, p in files.items()}
        assert before == after


# ============================================================================
# AC-02: Hierarchical summarization ("summary of the summary")
# ============================================================================


class TestHierarchicalSummary:
    """Multi-level summarization with configurable depth."""

    def test_summary_can_be_summarized_again(self):
        """The compressed result is itself compressible (multi-round)."""
        text = _make_big_prompt()
        compressor = ContextCompressor(budget_tokens=100, trigger_ratio=0.7)

        first = compressor.compress_if_needed(text)
        assert first.levels_applied >= 1

        # Round two: compress the summary of the summary with a tight budget
        second = compressor.compress_if_needed(
            first.text, budget_tokens=50, max_levels=2
        )
        assert second.triggered is True
        assert second.levels_applied >= 1
        assert second.estimated_tokens < first.estimated_tokens
        assert len(second.text) < len(first.text)

    def test_level_count_configuration_takes_effect(self):
        """max_levels caps the depth: 1 level vs. more levels."""
        text = _make_big_prompt()
        one = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=1
        ).compress_if_needed(text)
        many = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=3
        ).compress_if_needed(text)

        assert one.levels_applied == 1
        assert many.levels_applied >= 2
        # Deeper summarization yields a smaller view
        assert many.estimated_tokens < one.estimated_tokens
        assert len(many.text) <= len(one.text)

    def test_key_fields_preserved_at_every_level(self):
        """Task ID / gate / phase / decision points survive all levels."""
        text = _make_big_prompt()  # T-0088, G-T-0088-REQUIREMENTS, S6, decisions
        result = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=3
        ).compress_if_needed(text)

        assert result.levels_applied >= 2
        view = result.text
        assert "T-0088" in view          # task ID
        assert "G-T-0088-REQUIREMENTS" in view  # gate
        assert "S6" in view              # phase
        # Decision points: both keywords and decision-point lines survive
        assert "BLOCKED" in view
        assert "decision" in view.lower()

    def test_decision_point_lines_survive_compression(self):
        """Lines recording decisions are prioritised over plain prose."""
        text = (
            "# Context\n"
            + "\n".join(f"Filler prose line {i} with no decision content at all." for i in range(30))
            + "\ndecision: NOGO because coverage fell below the threshold.\n"
        )
        result = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=2
        ).compress_if_needed(text)

        assert result.triggered is True
        assert "NOGO" in result.text
        assert "coverage fell below" in result.text

    def test_summarize_is_pure_function(self):
        """summarize_text returns a new string and never mutates input."""
        text = _make_big_prompt()
        snapshot = text
        summary = summarize_text(text, level=1)
        assert text == snapshot
        assert isinstance(summary, str)
        assert len(summary) <= len(text)


# ============================================================================
# AC-03: Citation truncation repair
# ============================================================================


class TestCitationResolver:
    """Unique-prefix/suffix recovery of truncated evidence references."""

    def test_exact_reference_resolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        ref = ".ai/evidence/T-0300/unique-report.md"
        result = resolver.resolve(ref)
        assert result.status == "RESOLVED"
        assert result.is_resolved
        assert result.resolved == ref

    def test_dropped_ai_prefix_resolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("evidence/T-0300/unique-report.md")
        assert result.status == "RESOLVED"
        assert result.resolved == ".ai/evidence/T-0300/unique-report.md"

    def test_ellipsis_truncated_suffix_resolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("…/T-0300/unique-report.md")
        assert result.status == "RESOLVED"
        assert result.resolved == ".ai/evidence/T-0300/unique-report.md"

    def test_plain_truncated_suffix_resolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("T-0300/unique-report.md")
        assert result.status == "RESOLVED"
        assert result.resolved == ".ai/evidence/T-0300/unique-report.md"

    def test_bare_unique_basename_resolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("unique-report.md")
        assert result.status == "RESOLVED"
        assert result.resolved == ".ai/evidence/T-0300/unique-report.md"

    def test_ambiguous_basename_is_not_guessed(self, tmp_path):
        """Two files with the same basename -> AMBIGUOUS, never guessed."""
        _make_evidence_tree(tmp_path)  # approval-evidence.json in T-0100 and T-0200
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("approval-evidence.json")
        assert result.status == "AMBIGUOUS"
        assert result.is_resolved is False
        assert result.resolved is None
        assert len(result.matches) == 2

    def test_ambiguous_suffix_is_not_guessed(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("…/approval-evidence.json")
        assert result.status == "AMBIGUOUS"
        assert result.is_resolved is False
        assert result.resolved is None

    def test_missing_reference_is_not_found(self, tmp_path):
        _make_evidence_tree(tmp_path)
        resolver = CitationResolver(tmp_path)
        result = resolver.resolve("no-such-file.md")
        assert result.status == "NOT_FOUND"
        assert result.is_resolved is False
        assert result.resolved is None

    def test_long_citation_truncate_and_repair_roundtrip(self, tmp_path):
        """A path truncated by the summarizer is restored to its full form."""
        _make_evidence_tree(tmp_path)
        deep = (
            ".ai/evidence/T-0300/context-compression/implementation/"
            "notes/summary-report.md"
        )
        path = tmp_path / deep
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# report", encoding="utf-8")

        assert len(deep) > CITATION_MAX_CHARS
        truncated = _truncate_citation(deep)
        assert truncated.startswith("…/")
        assert "summary-report.md" in truncated

        result = CitationResolver(tmp_path).resolve(truncated)
        assert result.status == "RESOLVED"
        assert result.resolved == deep


class TestTextRepair:
    """repair_truncated_references on whole text."""

    def test_text_repair_restores_unique_references(self, tmp_path):
        _make_evidence_tree(tmp_path)
        text = (
            "The gate record is …/T-0300/unique-report.md and the design "
            "lives in evidence/T-0300/context-compression/design.md."
        )
        repaired, resolutions = repair_truncated_references(text, tmp_path)

        assert ".ai/evidence/T-0300/unique-report.md" in repaired
        assert ".ai/evidence/T-0300/context-compression/design.md" in repaired
        assert "…/" not in repaired
        assert all(r.status == "RESOLVED" for r in resolutions)

    def test_text_repair_marks_ambiguous_as_unresolved(self, tmp_path):
        """Ambiguous references become an explicit [UNRESOLVED: ...] marker."""
        _make_evidence_tree(tmp_path)
        text = (
            "Approval was recorded in …/approval-evidence.json — which "
            "approval is ambiguous across tasks."
        )
        repaired, resolutions = repair_truncated_references(text, tmp_path)

        assert f"[{UNRESOLVED_MARKER}:" in repaired
        assert "approval-evidence.json" in repaired
        assert "…/approval-evidence.json" in repaired
        statuses = {r.status for r in resolutions}
        assert "AMBIGUOUS" in statuses
        # The ambiguous reference was NOT replaced by a guessed path
        assert ".ai/evidence/T-0100/approval-evidence.json" not in repaired

    def test_text_repair_marks_missing_as_unresolved(self, tmp_path):
        _make_evidence_tree(tmp_path)
        text = "See …/T-0300/missing-report.md for details."
        repaired, resolutions = repair_truncated_references(text, tmp_path)
        assert f"[{UNRESOLVED_MARKER}:" in repaired
        assert any(r.status == "NOT_FOUND" for r in resolutions)

    def test_resolution_list_has_full_diagnostics(self, tmp_path):
        _make_evidence_tree(tmp_path)
        _, resolutions = repair_truncated_references(
            "…/T-0300/unique-report.md and …/approval-evidence.json", tmp_path
        )
        assert isinstance(resolutions, list)
        assert all(isinstance(r, CitationResolution) for r in resolutions)
        statuses = {r.status for r in resolutions}
        assert "RESOLVED" in statuses
        assert "AMBIGUOUS" in statuses

    def test_full_path_and_dropped_prefix_no_double_prefix(self, tmp_path):
        """T-0095 item 5: 完整路径与丢前缀引用同文本时不得产生 .ai/.ai/ 双前缀。

        The dropped-prefix token is a substring of the already-resolved full
        path; naive str.replace would rewrite inside the repaired span and
        corrupt it into ``.ai/.ai/evidence/...``.
        """
        _make_evidence_tree(tmp_path)
        text = (
            "See .ai/evidence/T-0300/unique-report.md and also "
            "evidence/T-0300/unique-report.md (dropped prefix)."
        )
        repaired, resolutions = repair_truncated_references(text, tmp_path)

        assert ".ai/.ai/" not in repaired
        assert "evidence/evidence/" not in repaired
        assert repaired.count(".ai/evidence/T-0300/unique-report.md") == 1
        # the full path survives exactly once; the covered dropped-prefix
        # token is skipped, so no duplicated prefix anywhere
        assert repaired.count(".ai/evidence/") == 1
        assert "evidence/T-0300/unique-report.md" in repaired
        assert any(r.status == "RESOLVED" for r in resolutions)

    def test_dropped_prefix_already_repaired_span_untouched(self, tmp_path):
        """Same scenario via a deeper path: the repaired text must not
        contain a doubled ``.ai/`` prefix."""
        _make_evidence_tree(tmp_path)
        text = (
            "Files: .ai/evidence/T-0300/context-compression/design.md and "
            "evidence/T-0300/context-compression/design.md"
        )
        repaired, _ = repair_truncated_references(text, tmp_path)
        assert ".ai/.ai/" not in repaired
        assert repaired.count(".ai/evidence/T-0300/context-compression/design.md") == 1


# ============================================================================
# Backward compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Existing ContextLoader behaviour is unchanged without budget params."""

    def test_load_role_context_signature_unchanged(self, tmp_path):
        """Positional call (role_id, complexity) still works."""
        _make_project(
            str(tmp_path),
            tester="x",
            **{"agents/tester/CONTRACT.yaml": _make_contract_yaml()},
        )
        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", 0.5)
        assert ctx.level == LoadLevel.STANDARD
        assert ctx.compression is None
        assert "Fixed Stance" in ctx.system_prompt

    def test_estimate_tokens_module_function_matches_method(self):
        """Module-level estimate_tokens == ContextLoader.estimate_tokens."""
        loader = ContextLoader(Path("."))
        samples = [
            "",
            "The quick brown fox jumps over the lazy dog.",  # 9 words -> 11
            "你好世界测试文本",  # 8 CJK chars -> 16
            "Hello 世界 this is 测试 mixed 文本",
        ]
        for sample in samples:
            assert estimate_tokens(sample) == loader.estimate_tokens(sample)
        assert estimate_tokens("The quick brown fox jumps over the lazy dog.") == 11
        assert estimate_tokens("你好世界测试文本") == 16

    def test_loaded_context_extra_field_has_default(self):
        """LoadedContext.compression defaults to None (dataclass default)."""
        from loop_core.context_loader import LoadedContext

        ctx = LoadedContext(
            role_id="r", level=LoadLevel.MINIMAL, system_prompt="x",
            estimated_tokens=1,
        )
        assert ctx.compression is None

    def test_compression_result_repr_fields(self):
        """CompressionResult carries the documented metadata."""
        text = _make_big_prompt()
        result = ContextCompressor(
            budget_tokens=100, trigger_ratio=0.7, max_levels=2
        ).compress_if_needed(text)
        assert isinstance(result, CompressionResult)
        assert isinstance(result.text, str)
        assert isinstance(result.levels_applied, int)
        assert isinstance(result.estimated_tokens, int)
        assert result.original_tokens == estimate_tokens(text)
