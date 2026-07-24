"""
Tests for loop_core.context_loader — progressive role context loading.

Covers:
  - Complexity → LoadLevel mapping (0.2→MINIMAL, 0.5→STANDARD, 0.8→FULL)
  - MINIMAL context: only fixed_stance, no framework/loop content
  - FULL context: all three files (CONTRACT + FRAMEWORK + LOOP)
  - estimate_tokens: English, Chinese, and mixed text
  - build_document_index: correctly parses ## headings
  - load_document_section: returns correct section by name
  - Edge cases: non-existent role, corrupted CONTRACT.yaml, empty files
  - load_for_role: combined role + document section loading
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Ensure the parent directory is on sys.path so we can import loop_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.context_loader import (  # noqa: E402
    ContextLoader,
    DocumentIndex,
    LoadLevel,
    LoadedContext,
    _complexity_to_level,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_project(tmp_path: str, role_id: str, **files: str) -> Path:
    """Create a minimal project directory with a role and given file contents.

    Key-value pairs: relative_path -> content.
    Directories are created automatically.
    """
    root = Path(tmp_path)
    for rel_path, content in files.items():
        fpath = root / rel_path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
    return root


def _make_contract_yaml(role_id: str, stance_items: list[str] | None = None) -> str:
    """Build a minimal CONTRACT.yaml as JSON (valid YAML subset)."""
    contract = {
        "role_id": role_id,
        "identity": {
            "title": f"Test {role_id}",
            "experience": "5 years",
            "expertise": ["testing", "quality"],
        },
        "fixed_stance": stance_items or [
            "Always verify before claiming success.",
            "Evidence over opinion.",
        ],
        "responsibilities": [
            "Write tests",
            "Review code",
        ],
        "prohibitions": [
            "Do not deploy to production",
            "Do not skip code review",
        ],
        "veto_power": [
            "Low coverage → NOGO",
            "Failing tests → NOGO",
        ],
    }
    return json.dumps(contract, ensure_ascii=False, indent=2)


def _make_framework_md() -> str:
    """Build a representative THINKING_FRAMEWORK.md."""
    return """\
# Test Role Thinking Framework

## Mandatory Thinking Order

### Step 1: Global Context (complete first)
- [ ] What is the current state?
- [ ] What are the known risks?

### Step 2: Domain Analysis
- [ ] Is this within my expertise?
- [ ] What blind spots do I have?

### Step 3: Evidence Assessment
- [ ] Is there sufficient evidence?
- [ ] Are the claims verifiable?

### Step 4: Quality Check
- [ ] Does the output meet standards?
- [ ] Are there any regressions?

### Task: Execute
- [ ] Based on Steps 1-4, proceed with the task.

## Output Requirements

Each step must have substantive content.
"""


def _make_loop_md() -> str:
    """Build a representative INTERNAL_LOOP.md."""
    return """\
# Test Role Internal Loop

## Loop 1: Contract Compliance
- [ ] Did I violate any prohibitions?
- [ ] Does my output match the contract?

## Loop 2: Quality Standards
- [ ] Does the output meet quality thresholds?
- [ ] Is every claim backed by evidence?

## Loop 3: False Positive Detection
- [ ] Is every PASS supported by real output?
- [ ] Are tool exit codes correct?

## Iteration Rules
- Max 3 iterations
- 3rd failure → output BLOCKED

## Analysis-to-Output Ratio
- Analysis (Step 1-4) tokens should be >= 15% of total output
"""


def _make_empty_framework_md() -> str:
    """Build an empty-ish framework (no Step headings)."""
    return """\
# Empty Framework

This framework has no step headings.

## Notes

Just some placeholder text.
"""


def _make_markdown_doc() -> str:
    """Build a representative multi-section markdown document."""
    return """\
# Project Architecture

## Overview

This is the overview section. It describes the project at a high level.

## Testing Strategy

Tests are organized by module. Each module has unit, integration,
and end-to-end tests as appropriate.

## Security Considerations

Authentication uses OAuth2. All endpoints require valid tokens.
Sensitive data is encrypted at rest.

## Deployment Pipeline

CI/CD runs on every push to main. Deployments to staging are automatic.
Production deployments require manual approval.

## Performance Targets

API response time must be under 200ms p95. Database queries must
complete within 50ms.
"""


# ============================================================================
# Tests: Complexity → LoadLevel
# ============================================================================


class TestComplexityToLoadLevel:
    """Verify that complexity scores map to correct LoadLevels."""

    def test_below_0_3_is_minimal(self):
        assert _complexity_to_level(0.0) == LoadLevel.MINIMAL
        assert _complexity_to_level(0.1) == LoadLevel.MINIMAL
        assert _complexity_to_level(0.2) == LoadLevel.MINIMAL
        assert _complexity_to_level(0.29) == LoadLevel.MINIMAL

    def test_between_0_3_and_0_6_is_standard(self):
        assert _complexity_to_level(0.30) == LoadLevel.STANDARD
        assert _complexity_to_level(0.40) == LoadLevel.STANDARD
        assert _complexity_to_level(0.50) == LoadLevel.STANDARD
        assert _complexity_to_level(0.59) == LoadLevel.STANDARD

    def test_0_6_and_above_is_full(self):
        assert _complexity_to_level(0.60) == LoadLevel.FULL
        assert _complexity_to_level(0.75) == LoadLevel.FULL
        assert _complexity_to_level(1.0) == LoadLevel.FULL


# ============================================================================
# Tests: ContextLoader.load_role_context
# ============================================================================


class TestLoadRoleContext:
    """Integration tests for load_role_context at different complexity levels."""

    def test_minimal_only_fixed_stance(self, tmp_path):
        """complexity 0.2 → MINIMAL: only fixed_stance, no framework/loop."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md(),
                         "agents/tester/INTERNAL_LOOP.md": _make_loop_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.2)

        assert ctx.role_id == "tester"
        assert ctx.level == LoadLevel.MINIMAL
        assert ctx.estimated_tokens > 0

        # Should contain fixed stance items
        assert "Always verify before claiming success" in ctx.system_prompt
        assert "Evidence over opinion" in ctx.system_prompt

        # Should NOT contain framework or loop content
        assert "Step 1:" not in ctx.system_prompt
        assert "Step 2:" not in ctx.system_prompt
        assert "Loop 1:" not in ctx.system_prompt
        assert "False Positive Detection" not in ctx.system_prompt

        # loaded_sections should only mention CONTRACT fixed_stance
        assert len(ctx.loaded_sections) == 1
        assert "fixed_stance" in ctx.loaded_sections[0]

    def test_standard_has_stance_and_framework_titles(self, tmp_path):
        """complexity 0.5 → STANDARD: fixed_stance + framework Step 1-4 titles."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md(),
                         "agents/tester/INTERNAL_LOOP.md": _make_loop_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.5)

        assert ctx.level == LoadLevel.STANDARD

        # Should contain fixed stance
        assert "Always verify before claiming success" in ctx.system_prompt

        # Should contain framework step titles
        assert "Step 1:" in ctx.system_prompt
        assert "Step 2:" in ctx.system_prompt
        assert "Step 4:" in ctx.system_prompt
        assert "Thinking Framework (Summary)" in ctx.system_prompt

        # Should NOT contain full loop content
        assert "Loop 1:" not in ctx.system_prompt
        assert "False Positive Detection" not in ctx.system_prompt

        # Should NOT contain detailed step content (checklist items)
        assert "What is the current state?" not in ctx.system_prompt.lower()

    def test_full_has_all_three_files(self, tmp_path):
        """complexity 0.8 → FULL: complete CONTRACT + FRAMEWORK + LOOP."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md(),
                         "agents/tester/INTERNAL_LOOP.md": _make_loop_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.8)

        assert ctx.level == LoadLevel.FULL

        # Should contain fixed stance
        assert "Always verify before claiming success" in ctx.system_prompt

        # Should contain full framework
        assert "Step 1: Global Context" in ctx.system_prompt
        assert "Step 4: Quality Check" in ctx.system_prompt
        assert "What is the current state?" in ctx.system_prompt
        assert "Output Requirements" in ctx.system_prompt

        # Should contain full loop
        assert "Loop 1: Contract Compliance" in ctx.system_prompt
        assert "Loop 3: False Positive Detection" in ctx.system_prompt
        assert "Iteration Rules" in ctx.system_prompt
        assert "Analysis-to-Output Ratio" in ctx.system_prompt

        # Should contain CONTRACT extras (responsibilities, prohibitions, veto)
        assert "## Responsibilities" in ctx.system_prompt
        assert "Write tests" in ctx.system_prompt
        assert "## Prohibitions" in ctx.system_prompt
        assert "Do not deploy to production" in ctx.system_prompt
        assert "## Veto Power" in ctx.system_prompt

    def test_framework_missing_is_graceful(self, tmp_path):
        """When THINKING_FRAMEWORK.md is missing, STANDARD still works."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/INTERNAL_LOOP.md": _make_loop_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.5)

        assert ctx.level == LoadLevel.STANDARD
        assert "Always verify before claiming success" in ctx.system_prompt
        # Framework missing → should not crash, just not include it

    def test_loop_missing_is_graceful(self, tmp_path):
        """When INTERNAL_LOOP.md is missing, FULL still works."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.8)

        assert ctx.level == LoadLevel.FULL
        assert "Step 1:" in ctx.system_prompt
        # INTERNAL_LOOP missing → should not crash, just not include it

    def test_empty_framework_no_titles(self, tmp_path):
        """Framework with no Step headings → STANDARD gracefully returns none."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_empty_framework_md()})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.5)

        assert ctx.level == LoadLevel.STANDARD
        # Should have stance but no framework titles
        assert "Fixed Stance" in ctx.system_prompt
        assert "Thinking Framework" not in ctx.system_prompt

    def test_no_fixed_stance_falls_back(self, tmp_path):
        """CONTRACT without fixed_stance → uses identity title as fallback."""
        contract_data = {
            "role_id": "bare-role",
            "identity": {"title": "Bare Role"},
        }
        contract = json.dumps(contract_data, ensure_ascii=False)
        _make_project(str(tmp_path), "bare-role",
                      **{"agents/bare-role/CONTRACT.yaml": contract})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("bare-role", complexity=0.2)

        assert "Bare Role" in ctx.system_prompt
        assert "No fixed_stance defined" in ctx.system_prompt


# ============================================================================
# Tests: Edge Cases — Role Discovery
# ============================================================================


class TestRoleEdgeCases:
    """Edge case handling for role loading."""

    def test_non_existent_role_raises(self, tmp_path):
        """Loading a role that doesn't exist should raise FileNotFoundError."""
        loader = ContextLoader(tmp_path)
        try:
            loader.load_role_context("ghost-role", complexity=0.5)
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError as e:
            assert "ghost-role" in str(e)

    def test_missing_contract_raises(self, tmp_path):
        """Role dir exists but CONTRACT.yaml is missing."""
        role_dir = tmp_path / "agents" / "no-contract"
        role_dir.mkdir(parents=True)

        loader = ContextLoader(tmp_path)
        try:
            loader.load_role_context("no-contract", complexity=0.5)
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError as e:
            assert "CONTRACT.yaml" in str(e)

    def test_corrupted_contract_yaml_raises(self, tmp_path):
        """Malformed YAML that cannot be parsed should raise ValueError."""
        _make_project(str(tmp_path), "broken",
                      **{"agents/broken/CONTRACT.yaml": "::: not valid yaml ::: {{{"})

        loader = ContextLoader(tmp_path)
        try:
            loader.load_role_context("broken", complexity=0.5)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "broken" in str(e)

    def test_contract_not_a_dict_raises(self, tmp_path):
        """CONTRACT.yaml that parses to a list instead of dict."""
        _make_project(str(tmp_path), "list-role",
                      **{"agents/list-role/CONTRACT.yaml": "- item1\n- item2"})

        loader = ContextLoader(tmp_path)
        try:
            loader.load_role_context("list-role", complexity=0.5)
            assert False, "Expected ValueError"
        except ValueError:
            pass  # Expected


# ============================================================================
# Tests: estimate_tokens
# ============================================================================


class TestEstimateTokens:
    """Token estimation accuracy tests."""

    def test_empty_text(self):
        loader = ContextLoader(Path("."))
        assert loader.estimate_tokens("") == 0

    def test_pure_english(self):
        loader = ContextLoader(Path("."))
        text = "The quick brown fox jumps over the lazy dog."  # 9 words
        tokens = loader.estimate_tokens(text)
        # 9 words * 1.3 = 11.7 → 11
        assert tokens == 11

    def test_pure_chinese(self):
        loader = ContextLoader(Path("."))
        text = "你好世界测试文本"  # 8 CJK characters
        tokens = loader.estimate_tokens(text)
        # 8 chars * 2 = 16
        assert tokens == 16

    def test_mixed_english_chinese(self):
        loader = ContextLoader(Path("."))
        text = "Hello 世界 this is 测试 mixed 文本"  # 6 CJK chars, 4 English words
        tokens = loader.estimate_tokens(text)
        # 4 words * 1.3 = 5.2 → 5, plus 6 CJK * 2 = 12, total = 17
        expected = int(4 * 1.3) + (6 * 2)
        assert tokens == expected

    def test_long_text_increases_token_count(self):
        loader = ContextLoader(Path("."))
        short = "hello"
        long = "hello world " * 100
        assert loader.estimate_tokens(long) > loader.estimate_tokens(short)
        # Sanity: 201 words * 1.3 ≈ 261
        assert loader.estimate_tokens(long) > 200


# ============================================================================
# Tests: DocumentIndex
# ============================================================================


class TestDocumentIndex:
    """Tests for build_document_index and load_document_section."""

    def test_build_index_parses_headings(self, tmp_path):
        """build_document_index correctly extracts ## heading positions."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        index = loader.build_document_index(str(doc_path))

        assert index.total_lines > 0
        assert "Overview" in index.sections
        assert "Testing Strategy" in index.sections
        assert "Security Considerations" in index.sections
        assert "Deployment Pipeline" in index.sections
        assert "Performance Targets" in index.sections

        # Verify sections are non-overlapping and ordered
        prev_end = 0
        for name, (start, end) in index.sections.items():
            assert start > prev_end, f"Section '{name}' starts before previous ends"
            assert end >= start, f"Section '{name}' has invalid range"
            prev_end = end

    def test_load_section_returns_correct_content(self, tmp_path):
        """load_document_section returns the right text for a named section."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        section = loader.load_document_section(str(doc_path), "Testing Strategy")

        assert section is not None
        assert "## Testing Strategy" in section
        assert "unit, integration," in section
        assert "end-to-end tests" in section
        # Should NOT contain the next section's heading
        assert "## Security Considerations" not in section

    def test_load_nonexistent_section_returns_none(self, tmp_path):
        """Loading a section that doesn't exist returns None."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        result = loader.load_document_section(str(doc_path), "Nonexistent Section")
        assert result is None

    def test_last_section_goes_to_end(self, tmp_path):
        """The last ## section should go to the end of the file."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        section = loader.load_document_section(str(doc_path), "Performance Targets")

        assert section is not None
        assert "200ms p95" in section
        assert "50ms" in section
        # Should be the last section, goes to EOF

    def test_missing_document_raises(self, tmp_path):
        """build_document_index on a non-existent file raises FileNotFoundError."""
        loader = ContextLoader(tmp_path)
        try:
            loader.build_document_index(str(tmp_path / "nonexistent.md"))
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_empty_document(self, tmp_path):
        """Empty document produces an index with no sections."""
        doc_path = tmp_path / "empty.md"
        doc_path.write_text("", encoding="utf-8")

        loader = ContextLoader(tmp_path)
        index = loader.build_document_index(str(doc_path))

        assert index.total_lines == 0
        assert len(index.sections) == 0

    def test_document_with_only_h1(self, tmp_path):
        """Document with only # headings (no ##) produces empty index."""
        doc_path = tmp_path / "only_h1.md"
        doc_path.write_text("# Title\n\nSome text\n\n# Another\n\nMore text\n", encoding="utf-8")

        loader = ContextLoader(tmp_path)
        index = loader.build_document_index(str(doc_path))

        assert len(index.sections) == 0

    def test_document_with_h3_headings_ignored(self, tmp_path):
        """### (h3) headings are not treated as section boundaries."""
        doc_path = tmp_path / "h3_doc.md"
        content = """\
## Main Section
Some text here.
### Sub Section
More text.
## Another Section
Final text.
"""
        doc_path.write_text(content, encoding="utf-8")

        loader = ContextLoader(tmp_path)
        index = loader.build_document_index(str(doc_path))

        assert len(index.sections) == 2
        assert "Main Section" in index.sections
        assert "Another Section" in index.sections
        assert "Sub Section" not in index.sections


# ============================================================================
# Tests: load_for_role
# ============================================================================


class TestLoadForRole:
    """Tests for the combined load_for_role method."""

    def test_combines_role_and_document(self, tmp_path):
        """load_for_role includes both role context and relevant doc sections."""
        contract = _make_contract_yaml("quality-engineer")
        _make_project(str(tmp_path), "quality-engineer",
                      **{"agents/quality-engineer/CONTRACT.yaml": contract,
                         "agents/quality-engineer/THINKING_FRAMEWORK.md": _make_framework_md(),
                         "agents/quality-engineer/INTERNAL_LOOP.md": _make_loop_md()})

        doc_path = tmp_path / "architecture.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        ctx = loader.load_for_role("quality-engineer", str(doc_path), complexity=0.8)

        # Should have role context
        assert ctx.role_id == "quality-engineer"
        assert ctx.level == LoadLevel.FULL

        # Should have document sections relevant to quality-engineer
        # "Testing Strategy" should match
        has_testing = any("Testing Strategy" in s for s in ctx.loaded_sections)
        assert has_testing, f"Expected Testing Strategy in loaded sections: {ctx.loaded_sections}"

        # System prompt should include both role and doc content
        assert "Always verify before claiming success" in ctx.system_prompt
        assert "unit, integration," in ctx.system_prompt

    def test_load_for_role_no_matching_sections(self, tmp_path):
        """When no sections match the role, falls back to first 3 sections."""
        contract = _make_contract_yaml("unknown-role")
        _make_project(str(tmp_path), "unknown-role",
                      **{"agents/unknown-role/CONTRACT.yaml": contract})

        doc_path = tmp_path / "architecture.md"
        doc_path.write_text(_make_markdown_doc(), encoding="utf-8")

        loader = ContextLoader(tmp_path)
        ctx = loader.load_for_role("unknown-role", str(doc_path), complexity=0.2)

        # Should have fallen back to some sections
        assert len(ctx.loaded_sections) >= 2  # role stance + at least 1 doc section
        # Verify doc sections were loaded (contain path#section pattern)
        doc_sections = [s for s in ctx.loaded_sections if "architecture.md#" in s]
        assert len(doc_sections) >= 1


# ============================================================================
# Tests: LoadedContext fields
# ============================================================================


class TestLoadedContext:
    """Ensure LoadedContext carries all expected metadata."""

    def test_fields_are_populated(self, tmp_path):
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract})

        loader = ContextLoader(tmp_path)
        ctx = loader.load_role_context("tester", complexity=0.5)

        assert ctx.role_id == "tester"
        assert ctx.level == LoadLevel.STANDARD
        assert isinstance(ctx.system_prompt, str)
        assert len(ctx.system_prompt) > 0
        assert isinstance(ctx.estimated_tokens, int)
        assert ctx.estimated_tokens > 0
        assert isinstance(ctx.loaded_sections, list)

    def test_estimated_tokens_recorded_for_analysis_output_ratio(self, tmp_path):
        """estimated_tokens is recorded so INTERNAL_LOOP can verify 15% rule."""
        contract = _make_contract_yaml("tester")
        _make_project(str(tmp_path), "tester",
                      **{"agents/tester/CONTRACT.yaml": contract,
                         "agents/tester/THINKING_FRAMEWORK.md": _make_framework_md(),
                         "agents/tester/INTERNAL_LOOP.md": _make_loop_md()})

        loader = ContextLoader(tmp_path)

        ctx_min = loader.load_role_context("tester", complexity=0.2)
        ctx_std = loader.load_role_context("tester", complexity=0.5)
        ctx_full = loader.load_role_context("tester", complexity=0.8)

        # Token counts should increase with load level
        assert ctx_min.estimated_tokens < ctx_std.estimated_tokens, (
            f"MINIMAL tokens ({ctx_min.estimated_tokens}) should be < "
            f"STANDARD tokens ({ctx_std.estimated_tokens})"
        )
        assert ctx_std.estimated_tokens < ctx_full.estimated_tokens, (
            f"STANDARD tokens ({ctx_std.estimated_tokens}) should be < "
            f"FULL tokens ({ctx_full.estimated_tokens})"
        )

        # Token counts should be in reasonable ranges
        assert 10 <= ctx_min.estimated_tokens <= 500, (
            f"MINIMAL tokens out of range: {ctx_min.estimated_tokens}"
        )
        assert 30 <= ctx_std.estimated_tokens <= 1200, (
            f"STANDARD tokens out of range: {ctx_std.estimated_tokens}"
        )
        assert 200 <= ctx_full.estimated_tokens <= 5000, (
            f"FULL tokens out of range: {ctx_full.estimated_tokens}"
        )
