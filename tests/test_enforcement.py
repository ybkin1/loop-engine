"""
Unit tests for loop_enforcement.py and loop_auto_activate.py hooks.

Covers:
  - loop_enforcement: FULL mode blocking, LIGHTWEIGHT mode allowing,
    governance file exemptions, task scope enforcement
  - loop_auto_activate: project complexity analysis (LIGHTWEIGHT/STANDARD/FULL),
    auto-setting loop_mode in state.yaml

Tests run hooks via subprocess with temp directories, matching how ZCode
invokes them (process + stdin JSON + ZCODE_PROJECT_DIR env var).
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
PYTHON = sys.executable


def _msys(tmp: str) -> str:
    """Windows 路径 → git-bash 形态（C:/x → /c/x），主会话 Bash 命令写法。"""
    return re.sub(r"^([A-Za-z]):", lambda m: "/" + m.group(1).lower(),
                  tmp.replace("\\", "/"))


# ── Helpers ───────────────────────────────────────────────────────────

# Minimal loop-governance quality gate config. The enforcement hook
# (hooks/scripts/loop_enforcement.py, check_phase_gate_enforcement) requires
# .zcode/skills/loop-governance/config.yaml to exist for S4+ phases, otherwise
# every write is BLOCKED with "质量门禁配置不存在". Content mirrors the repo's
# real config (and hook_common.DEFAULT_CONFIG); the hook only checks existence.
GOVERNANCE_CONFIG_YAML = """\
# loop-governance behavior config (synthetic test fixture)
version: 1
gate_guard:
  enabled: true
  fail_on_state_error: closed
  decision_recording_exempt:
    - .ai/gates.yaml
    - .ai/state.yaml
    - .ai/task_graph.yaml
    - .ai/project_continuity.yaml
path_guard:
  enabled: true
  decision: ask
  protected_paths:
    - AGENTS.md
    - stable/
    - registry/
    - .zcode/config.json
    - .zcode/tools/
session_brief:
  enabled: true
  max_pending_listed: 10
"""


def _make_project(
    tmp: str,
    state_content: str | None = None,
    task_files: dict[str, str] | None = None,
    extra_files: dict[str, str] | None = None,
    gates_content: str | None = None,
    review_evidence: str | None = None,
    review_task_id: str = "T-0001",
) -> Path:
    """Create a minimal governed project in a temp directory."""
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    # T-0082: the enforcement hook requires the quality gate config to exist
    # for S4+ phases; without it all writes are BLOCKED.
    qg_dir = root / ".zcode" / "skills" / "loop-governance"
    qg_dir.mkdir(parents=True, exist_ok=True)
    (qg_dir / "config.yaml").write_text(GOVERNANCE_CONFIG_YAML, encoding="utf-8")

    if state_content is not None:
        (ai_dir / "state.yaml").write_text(state_content, encoding="utf-8")

    if gates_content is not None:
        (ai_dir / "gates.yaml").write_text(gates_content, encoding="utf-8")

    if review_evidence is not None:
        ev_dir = ai_dir / "evidence" / review_task_id
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "review-evidence.json").write_text(review_evidence, encoding="utf-8")

    if task_files:
        tasks_dir = ai_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in task_files.items():
            (tasks_dir / fname).write_text(content, encoding="utf-8")

    if extra_files:
        for fname, content in extra_files.items():
            fpath = root / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

    return root


def _run_hook(script_name: str, root: Path, hook_input: dict | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a hook script as a subprocess, similar to ZCode's invocation.

    env 覆盖：默认继承当前环境；传入 env 时整体替换（用于清除
    PYTEST_CURRENT_TEST 模拟真实宿主运行时，T-0177 C3）。
    """
    if env is None:
        env = dict(os.environ)
    else:
        env = dict(env)
    env["ZCODE_PROJECT_DIR"] = str(root)
    payload = json.dumps(hook_input or {})
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script_name)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _write_input(file_path: str) -> dict:
    """Build a PreToolUse hook input for a Write operation."""
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


# ── State fixtures ────────────────────────────────────────────────────

STATE_FULL = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

STATE_STANDARD = """\
schema_version: 1
project_name: test-standard
current_phase: S4-implementation
loop_mode: STANDARD
current_task_id: T-0001
"""

STATE_LIGHTWEIGHT = """\
schema_version: 1
project_name: test-light
current_phase: S4-implementation
loop_mode: LIGHTWEIGHT
"""

STATE_FULL_NO_TASK = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
"""


TASK_IN_SCOPE = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""

TASK_NARROW_SCOPE = """\
# Task T-0002: Fix config
allowed_paths:
- config/

developer_agent_id: "agent-003"
reviewer_agent_id: "agent-004"
"""

# ── B7 (T-0083): realistic phase-baseline governance for S4 fixtures ──
# The HardConstraints kernel is now populated with real state (current_phase
# + phase_gates + review_status).  A project in S4-implementation requires
# approved S1-requirements / S2-architecture baselines (C1/C2) and an
# independent-reviewer PASS verdict on record (C6) before writes are
# allowed.  The fixtures below mirror that real governance.
GATES_APPROVED = """\
schema_version: 1
gates:
- id: G-T-0001-REQUIREMENTS
  task_id: T-0001
  gate_type: requirements
  status: approved
- id: G-T-0001-ARCHITECTURE
  task_id: T-0001
  gate_type: architecture
  status: approved
"""

REVIEW_EVIDENCE = """\
{
  "task_id": "T-0001",
  "role": "independent-reviewer",
  "verdict": "PASS",
  "findings": [],
  "reviewer_session_id": "session-reviewer-001",
  "developer_session_id": "session-developer-001"
}
"""


# ═══════════════════════════════════════════════════════════════════════
# loop_enforcement tests
# ═══════════════════════════════════════════════════════════════════════

class LoopEnforcementFullModeBlocks(unittest.TestCase):
    """Tests that FULL mode blocks writes without active task contract."""

    def test_full_mode_blocks_write_without_task_id(self):
        """FULL mode with no current_task_id should block all non-governance writes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2), got {r.returncode}. stderr: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)

    def test_full_mode_blocks_write_outside_task_scope(self):
        """FULL mode with active task should block writes outside allowed_paths."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_files={"T-0001.md": TASK_IN_SCOPE},
                # B7: realistic S4 governance (approved S1/S2 baselines +
                # independent review on record) so C4 is the check under test.
                gates_content=GATES_APPROVED,
                review_evidence=REVIEW_EVIDENCE,
            )
            # Write to 'docs/' which is NOT in allowed_paths
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "docs" / "readme.md")))
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")

    def test_full_mode_allows_write_within_task_scope(self):
        """FULL mode with active task should allow writes within allowed_paths."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_files={"T-0001.md": TASK_IN_SCOPE},
                # B7: realistic S4 governance — the active S4 task must have
                # approved S1/S2 baselines (C1/C2) and an independent-reviewer
                # PASS on record (C6) for writes to pass the control kernel.
                gates_content=GATES_APPROVED,
                review_evidence=REVIEW_EVIDENCE,
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"Expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_standard_mode_also_blocks(self):
        """STANDARD mode should also enforce write restrictions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_STANDARD)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"STANDARD mode should block without task_id. stderr: {r.stderr}")

    def test_s4_write_without_approved_baselines_or_review_blocks(self):
        """B7: S4-implementation writes are blocked by C1/C2/C6 when the
        requirements/architecture baselines are not approved and no
        independent review is on record.

        The HardConstraints kernel is now populated with real phase state
        (gap-analysis §2.13): a bare S4 fixture WITHOUT gates.yaml and
        WITHOUT review evidence must fail the control kernel — previously
        C1/C2/C6 were dead letters that never executed.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_files={"T-0001.md": TASK_IN_SCOPE},
                # Intentionally NO gates.yaml / NO review evidence.
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("C1-no-requirements", r.stderr)
            self.assertIn("C2-no-architecture", r.stderr)
            self.assertIn("C6-no-independent-review", r.stderr)


SELF_REVIEW_EVIDENCE = """\
{
  "task_id": "T-0001",
  "role": "independent-reviewer",
  "verdict": "PASS",
  "findings": ["reviewed"],
  "reviewer_session_id": "session-dev-same-001",
  "developer_session_id": "session-dev-same-001"
}
"""

# Same project but with enforcement.self_review_block opt-out (B6).
GOVERNANCE_CONFIG_OPT_OUT_YAML = GOVERNANCE_CONFIG_YAML + """\
enforcement:
  self_review_block: false
"""


class LoopEnforcementSelfReviewBlock(unittest.TestCase):
    """B6 (T-0083): self-review evidence now BLOCKS writes in FULL mode."""

    def test_self_review_evidence_blocks_business_write_in_full_mode(self):
        """reviewer_session_id == developer_session_id → EXIT_BLOCK."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_files={"T-0001.md": TASK_IN_SCOPE},
                gates_content=GATES_APPROVED,
                review_evidence=SELF_REVIEW_EVIDENCE,
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("SELF_REVIEW", r.stderr)
            self.assertIn("BLOCKED", r.stderr)

    def test_self_review_block_opt_out_allows_write(self):
        """enforcement.self_review_block: false → trace-only, write allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(
                tmp,
                state_content=STATE_FULL,
                task_files={"T-0001.md": TASK_IN_SCOPE},
                gates_content=GATES_APPROVED,
                review_evidence=SELF_REVIEW_EVIDENCE,
            )
            # Opt out via config.yaml
            cfg = root / ".zcode" / "skills" / "loop-governance" / "config.yaml"
            cfg.write_text(GOVERNANCE_CONFIG_OPT_OUT_YAML, encoding="utf-8")
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"Expected EXIT_PASS(0). stderr: {r.stderr}")
            self.assertIn("SELF_REVIEW_TRACE", r.stderr)


class LoopEnforcementLightweightAllows(unittest.TestCase):
    """Tests that LIGHTWEIGHT mode allows writes freely."""

    def test_lightweight_mode_allows_write_without_task(self):
        """LIGHTWEIGHT mode should allow all writes (no enforcement)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_LIGHTWEIGHT)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"LIGHTWEIGHT should pass. stderr: {r.stderr}")

    def test_lightweight_mode_allows_write_anywhere(self):
        """LIGHTWEIGHT mode should allow writes to any path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_LIGHTWEIGHT)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "arbitrary" / "file.txt")))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")


class LoopEnforcementGovernanceExempt(unittest.TestCase):
    """Tests that governance files are always writable even in FULL mode."""

    def test_state_yaml_exempt_in_full(self):
        """Writing .ai/state.yaml should always be allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / ".ai" / "state.yaml")))
            self.assertEqual(r.returncode, 0, f"Governance write should pass. stderr: {r.stderr}")

    def test_task_graph_yaml_exempt_in_full(self):
        """Writing .ai/task_graph.yaml should always be allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / ".ai" / "task_graph.yaml")))
            self.assertEqual(r.returncode, 0, f"Governance write should pass. stderr: {r.stderr}")

    def test_gates_yaml_exempt_in_full(self):
        """Writing .ai/gates.yaml should always be allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / ".ai" / "gates.yaml")))
            self.assertEqual(r.returncode, 0, f"Governance write should pass. stderr: {r.stderr}")

    def test_handoff_md_exempt_in_full(self):
        """Writing .ai/HANDOFF.md should always be allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / ".ai" / "HANDOFF.md")))
            self.assertEqual(r.returncode, 0, f"Governance write should pass. stderr: {r.stderr}")

    def test_evidence_dir_exempt_in_full(self):
        """Writing to .ai/evidence/ should always be allowed (main thread)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / ".ai" / "evidence" / "test.json")))
            self.assertEqual(r.returncode, 0, f"Evidence write should pass. stderr: {r.stderr}")

    def test_non_governance_project_passes(self):
        """Hook should pass on non-governance projects (no .ai/state.yaml)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "any.py")))
            self.assertEqual(r.returncode, 0, r.stderr)


# ═══════════════════════════════════════════════════════════════════════
# loop_auto_activate tests
# ═══════════════════════════════════════════════════════════════════════

class LoopAutoActivateAnalyzeComplexity(unittest.TestCase):
    """Tests that analyze_project() correctly classifies project complexity."""

    def test_simple_project_lightweight(self):
        """A project with no risk indicators should be LIGHTWEIGHT."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            # State without loop_mode triggers analysis
            (ai_dir / "state.yaml").write_text(
                "schema_version: 1\nproject_name: simple\ncurrent_phase: S0-init\n",
                encoding="utf-8",
            )
            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)
            if r.stdout.strip():
                out = json.loads(r.stdout)
                ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
                # Should recommend LIGHTWEIGHT (no risk files present)
                self.assertIn("LIGHTWEIGHT", ctx)

    def test_moderate_project_standard(self):
        """A project with src/ and tests/ should be STANDARD."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            (ai_dir / "state.yaml").write_text(
                "schema_version: 1\nproject_name: moderate\ncurrent_phase: S0-init\n",
                encoding="utf-8",
            )
            # Create medium-risk indicators
            (root / "src").mkdir()
            (root / "tests").mkdir()
            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            out = json.loads(r.stdout) if r.stdout.strip() else {}
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("STANDARD", ctx)

    def test_complex_project_full(self):
        """A project with requirements.txt, package.json, and docker-compose should be FULL."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            (ai_dir / "state.yaml").write_text(
                "schema_version: 1\nproject_name: complex\ncurrent_phase: S0-init\n",
                encoding="utf-8",
            )
            # Create high-risk indicators (score >= 5 for FULL)
            (root / "requirements.txt").write_text("flask==2.0\n", encoding="utf-8")
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "docker-compose.yml").write_text("version: '3'\n", encoding="utf-8")
            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            out = json.loads(r.stdout) if r.stdout.strip() else {}
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("FULL", ctx)

    def test_project_with_gates_gets_full(self):
        """A project with .ai/gates.yaml (already governed) plus deps gets FULL."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            (ai_dir / "state.yaml").write_text(
                "schema_version: 1\nproject_name: governed\ncurrent_phase: S0-init\n",
                encoding="utf-8",
            )
            (ai_dir / "gates.yaml").write_text("gates: []\n", encoding="utf-8")
            # Add deps to push score >= 5: gates(3) + requirements(2) = 5 => FULL
            (root / "requirements.txt").write_text("flask\n", encoding="utf-8")
            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            out = json.loads(r.stdout) if r.stdout.strip() else {}
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("FULL", ctx)


class LoopAutoActivateSetsMode(unittest.TestCase):
    """Tests that loop_auto_activate actually sets loop_mode in state.yaml."""

    def test_auto_activate_writes_loop_mode_to_state(self):
        """When loop_mode is not set, it should be written to state.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            state_text = "schema_version: 1\nproject_name: test\ncurrent_phase: S0-init\n"
            (ai_dir / "state.yaml").write_text(state_text, encoding="utf-8")
            # Create some risk indicators to trigger STANDARD or FULL
            (root / "src").mkdir()

            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)

            # Check that state.yaml was updated with loop_mode
            updated = (ai_dir / "state.yaml").read_text(encoding="utf-8")
            self.assertIn("loop_mode:", updated)

    def test_auto_activate_does_not_overwrite_existing_mode(self):
        """When loop_mode is already set, it should not be overwritten."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            state_text = """\
schema_version: 1
project_name: test
current_phase: S0-init
loop_mode: LIGHTWEIGHT
"""
            (ai_dir / "state.yaml").write_text(state_text, encoding="utf-8")
            # Create risk indicators that would normally trigger FULL
            (root / "requirements.txt").write_text("flask==2.0\n", encoding="utf-8")

            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)

            # State should still say LIGHTWEIGHT (not overwritten)
            updated = (ai_dir / "state.yaml").read_text(encoding="utf-8")
            self.assertIn("LIGHTWEIGHT", updated)

    def test_non_governance_project_noop(self):
        """Non-governance projects should not trigger activation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)
            # Should produce no output
            self.assertEqual(r.stdout.strip(), "")

    def test_parallel_modules_trigger_full(self):
        """Multiple source modules should trigger FULL mode."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir()
            (ai_dir / "state.yaml").write_text(
                "schema_version: 1\nproject_name: parallel\ncurrent_phase: S0-init\n",
                encoding="utf-8",
            )
            # Create multiple modules (parallel indicator)
            modules_dir = root / "modules"
            modules_dir.mkdir()
            (modules_dir / "auth").mkdir()
            (modules_dir / "payment").mkdir()
            # Also add a requirements.txt for extra score
            (root / "requirements.txt").write_text("flask\n", encoding="utf-8")

            r = _run_hook("loop_auto_activate.py", root, {"source": "startup"})
            out = json.loads(r.stdout) if r.stdout.strip() else {}
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            # Multiple modules + requirements.txt should push to FULL
            self.assertIn("FULL", ctx)


# ═══════════════════════════════════════════════════════════════════════
# T-0082 Phase 5: S7-S11 阶段门禁证据 + S5/S6 安全证据
# ═══════════════════════════════════════════════════════════════════════

STATE_S7 = """\
schema_version: 1
project_name: test-s7
current_phase: S7-integration
loop_mode: FULL
current_task_id: T-0001
"""

STATE_S5 = """\
schema_version: 1
project_name: test-s5
current_phase: S5-quality
loop_mode: FULL
current_task_id: T-0001
"""

QUALITY_REPORT_PASS = """\
{
  "schema": "quality_report/v1",
  "role": "quality-engineer",
  "overall": "PASS",
  "checks": []
}
"""

SECURITY_AUDIT_PASS = """\
{
  "evidence_id": "EVID-security-audit-test",
  "type": "security_scan",
  "verdict": "PASS",
  "bindings": {"task_id": "T-0001", "phase": "S5-quality", "gate": "G-TEST"}
}
"""


class LoopEnforcementPhaseEvidence(unittest.TestCase):
    """GAP-2/GAP-3: S7-S11 阶段证据门禁与 S5/S6 安全证据。"""

    def _make_evidence(self, root: Path, rel: str, content: str) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def test_s7_blocks_without_evidence(self):
        """S7-integration 无阶段证据 → EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S7, task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("S7-integration", r.stderr)

    def test_s7_allows_with_evidence(self):
        """S7-integration 证据 overall=PASS → 范围内写入放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S7, task_files={"T-0001.md": TASK_IN_SCOPE})
            self._make_evidence(
                root, ".ai/evidence/T-0001/integration-report.json",
                '{"schema": "integration_report/v1", "overall": "PASS"}',
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_s7_integration_dir_variant(self):
        """S7 备选证据路径 .ai/evidence/integration/integration_report.json 也有效。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S7, task_files={"T-0001.md": TASK_IN_SCOPE})
            self._make_evidence(
                root, ".ai/evidence/integration/integration_report.json",
                '{"overall": "PASS"}',
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_s11_blocks_without_evidence(self):
        """S11-maintenance 无维护报告 → EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S7.replace("S7-integration", "S11-maintenance"),
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("S11-maintenance", r.stderr)

    def test_s5_blocks_without_security_evidence(self):
        """S5-quality：质量证据通过但缺少安全审计证据 → EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S5, task_files={"T-0001.md": TASK_IN_SCOPE})
            self._make_evidence(root, ".ai/evidence/quality/quality_report.json", QUALITY_REPORT_PASS)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("安全审计", r.stderr)

    def test_s5_allows_with_security_evidence(self):
        """S5-quality：质量证据 + 安全审计 verdict=PASS → 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S5, task_files={"T-0001.md": TASK_IN_SCOPE})
            self._make_evidence(root, ".ai/evidence/quality/quality_report.json", QUALITY_REPORT_PASS)
            self._make_evidence(root, ".ai/evidence/security/security_audit.json", SECURITY_AUDIT_PASS)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_s5_blocks_on_blocked_security_verdict(self):
        """安全审计 verdict=BLOCKED → EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_S5, task_files={"T-0001.md": TASK_IN_SCOPE})
            self._make_evidence(root, ".ai/evidence/quality/quality_report.json", QUALITY_REPORT_PASS)
            blocked = SECURITY_AUDIT_PASS.replace('"verdict": "PASS"', '"verdict": "BLOCKED"')
            self._make_evidence(root, ".ai/evidence/security/security_audit.json", blocked)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn("BLOCKED", r.stderr)


# ═══════════════════════════════════════════════════════════════════════
# T-0086-P2: 治理工具调用豁免（is_governance_tool_command）
# ═══════════════════════════════════════════════════════════════════════
# P1 之后 python 等解释器执行形态一律判"写能力"，主会话的治理工具调用
# （python .zcode/tools/validate_state.py 等）不再走只读通道 → 被
# DISPATCH_REQUIRED 拦截。本组用例覆盖豁免判定（单元）与 hook 端到端
# 行为（子进程）。


class GovernanceToolCommandDetection(unittest.TestCase):
    """is_governance_tool_command 单元判定：白名单形态豁免，其余不豁免。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        import loop_enforcement
        cls.mod = loop_enforcement  # 存模块而非函数：实例属性访问会绑定 self

    # ── 豁免：python 家族解释器 + 白名单目录脚本 ──

    def test_exempt_python_zcode_tools_validate_state(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "C:/Python312/python.exe .zcode/tools/validate_state.py ."))

    def test_exempt_python_repair_and_close_session(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "python .zcode/tools/repair_continuity.py ."))
        self.assertTrue(self.mod.is_governance_tool_command(
            "python .zcode/tools/close_session.py . --note done"))

    def test_exempt_python_ai_checkers(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "python .ai/checkers/compile_gate.py ."))

    def test_exempt_python_ai_guards(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "python .ai/guards/policy_guard.py check"))

    def test_exempt_python_scripts_dir(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "python scripts/runtime_delivery_gate.py ."))

    def test_exempt_python_hooks_self_test(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "python hooks/scripts/loop_enforcement.py"))

    def test_exempt_python_tools_dir(self):
        # tools/ 是项目 loop 工具 CLI 目录（tool_state/tool_handoff/
        # loop_guard_health...），与 MINIMAL_METADATA_READ 中的治理语义
        # 一致；tool_safe_bash.py 自带命令校验，豁免不放开任何写入拦截。
        self.assertTrue(self.mod.is_governance_tool_command(
            "python tools/tool_state.py status"))
        self.assertTrue(self.mod.is_governance_tool_command(
            "python tools/loop_guard_health.py"))

    def test_exempt_interpreter_variants(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            "py -3 .zcode/tools/validate_state.py ."))
        self.assertTrue(self.mod.is_governance_tool_command(
            "python3.11 .zcode/tools/validate_state.py ."))
        self.assertTrue(self.mod.is_governance_tool_command(
            "python.exe .zcode/tools/validate_state.py ."))

    def test_exempt_quoted_script(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            'python ".zcode/tools/validate_state.py" .'))

    def test_exempt_direct_execution(self):
        self.assertTrue(self.mod.is_governance_tool_command(
            ".zcode/tools/validate_state.py ."))
        self.assertTrue(self.mod.is_governance_tool_command(
            "./.zcode/tools/close_session.py ."))

    def test_exempt_absolute_script_inside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(self.mod.is_governance_tool_command(
                f"python {root.as_posix()}/.zcode/tools/validate_state.py .",
                root))

    # ── 不豁免：非脚本形态 / 白名单外脚本 / 非 python 解释器 ──

    def test_not_exempt_python_c_snippet(self):
        self.assertFalse(self.mod.is_governance_tool_command(
            'python -c "print(1)"'))

    def test_not_exempt_python_m_module(self):
        # pytest 不是治理工具，python -m 模块形态不豁免
        self.assertFalse(self.mod.is_governance_tool_command(
            "python -m pytest tests/"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "python -m pip install x"))

    def test_not_exempt_script_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(self.mod.is_governance_tool_command(
                "python /tmp/evil.py", root))
            self.assertFalse(self.mod.is_governance_tool_command(
                f"python {root.as_posix()}/../evil.py .", root))

    def test_not_exempt_arbitrary_project_script(self):
        self.assertFalse(self.mod.is_governance_tool_command(
            "python src/main.py"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "python setup.py build"))

    def test_not_exempt_shell_interpreters(self):
        # sh/bash/php/ruby 等执行形态保持 P1 拦截（不豁免）
        self.assertFalse(self.mod.is_governance_tool_command(
            "bash .zcode/tools/foo.sh"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "sh .zcode/tools/foo.sh"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "php .ai/checkers/x.php"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "ruby scripts/foo.rb"))

    def test_not_exempt_compound_or_redirect(self):
        self.assertFalse(self.mod.is_governance_tool_command(
            "python .zcode/tools/validate_state.py . && rm -rf /tmp/x"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "python .zcode/tools/validate_state.py > /tmp/out.txt"))
        self.assertFalse(self.mod.is_governance_tool_command(
            "cd .zcode/tools && python validate_state.py ."))

    # ── P3: 主会话真实形态（cd <项目根> && python 工具 | tail）──

    def test_exempt_main_session_compound_form(self):
        """主会话真实形态：cd 项目根 && python 工具 2>&1 | tail → 豁免。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cmd in (
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/validate_state.py . 2>&1 | tail -5",
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/repair_continuity.py . 2>&1 | tail -5",
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/close_session.py . --note test 2>&1 | tail -10",
            ):
                self.assertTrue(
                    self.mod.is_governance_tool_command(cmd, root), cmd)

    def test_exempt_windows_path_cd_and_pipe_display(self):
        """Windows 盘符形态 cd + 只读显示管道（head/grep/echo）→ 豁免。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            win = str(root).replace("\\", "/")
            for cmd in (
                f"cd {win} && python .zcode/tools/validate_state.py . 2>&1 | head -10",
                f"cd {win} && python .zcode/tools/validate_state.py . 2>&1 | grep -i error",
                f"cd {win} && python .zcode/tools/validate_state.py . && echo done",
            ):
                self.assertTrue(
                    self.mod.is_governance_tool_command(cmd, root), cmd)

    def test_exempt_two_governance_tools_chain(self):
        """两个治理工具连排（都受信）→ 豁免。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cmd = (f"cd {_msys(tmp)} && python .zcode/tools/validate_state.py . "
                   "&& python .zcode/tools/repair_continuity.py . 2>&1 | tail -3")
            self.assertTrue(self.mod.is_governance_tool_command(cmd, root))

    def test_not_exempt_compound_with_write_segment(self):
        """复合命令含写语义段（rm/写重定向）→ 整体不豁免。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cmd in (
                f"cd {_msys(tmp)} && python .zcode/tools/validate_state.py . "
                "&& rm -rf /tmp/x",
                f"cd {_msys(tmp)} && python .zcode/tools/validate_state.py . "
                "> /tmp/out.txt",
                f"cd {_msys(tmp)} && python .zcode/tools/validate_state.py . "
                "; touch /tmp/evil",
            ):
                self.assertFalse(
                    self.mod.is_governance_tool_command(cmd, root), cmd)

    def test_not_exempt_compound_cd_outside_root(self):
        """cd 到项目根外 → 整体不豁免（fail-closed）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cmd in (
                "cd /c/Windows && python .zcode/tools/validate_state.py .",
                "cd .. && python .zcode/tools/validate_state.py .",
                "cd ~ && python .zcode/tools/validate_state.py .",
            ):
                self.assertFalse(
                    self.mod.is_governance_tool_command(cmd, root), cmd)

    def test_not_exempt_compound_with_interpreter_display(self):
        """只读显示段不允许解释器执行（pytest/node 等不能借道豁免）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cmd in (
                f"cd {_msys(tmp)} && python -m pytest tests/ -q",
                f"cd {_msys(tmp)} && C:/Python312/python.exe -m pytest tests/ -q",
                f"cd {_msys(tmp)} && node -e 'console.log(1)'",
            ):
                self.assertFalse(
                    self.mod.is_governance_tool_command(cmd, root), cmd)

    def test_not_exempt_compound_cd_requires_root(self):
        """root 缺失时 cd 段无法验证归属 → 不豁免（fail-closed）。"""
        self.assertFalse(self.mod.is_governance_tool_command(
            "cd /c/Users/Administrator/ZCodeProject/loop-engine "
            "&& python .zcode/tools/validate_state.py ."))

    def test_not_exempt_non_python_script_path(self):
        # 白名单目录内但非 .py（shell 脚本直接执行保持 P1 拦截）
        self.assertFalse(self.mod.is_governance_tool_command(
            "./.zcode/tools/foo.sh"))

    def test_not_exempt_none_empty(self):
        self.assertFalse(self.mod.is_governance_tool_command(None))
        self.assertFalse(self.mod.is_governance_tool_command(""))
        self.assertFalse(self.mod.is_governance_tool_command("python --version"))


class LoopEnforcementGovernanceToolInvocation(unittest.TestCase):
    """hook 端到端：主会话形态的治理工具调用放行，其余形态仍拦截。"""

    def _run_bash(self, root, command):
        """与 _run_hook 相同，但弹出 PYTEST_CURRENT_TEST。

        is_legacy_synthetic_hook_fixture 会把 pytest 子进程识别为 legacy
        合成 fixture（跳过 DISPATCH 门）；真实主会话没有该环境变量。
        本类用例模拟真实主会话，故显式移除。
        """
        env = dict(os.environ)
        env.pop("PYTEST_CURRENT_TEST", None)
        env["ZCODE_PROJECT_DIR"] = str(root)
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        return subprocess.run(
            [PYTHON, str(SCRIPTS / "loop_enforcement.py")],
            input=payload, capture_output=True, text=True, env=env, timeout=30,
        )

    def test_validate_state_invocation_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = self._run_bash(
                root, "C:/Python312/python.exe .zcode/tools/validate_state.py .")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr[-800:]}")

    def test_checker_and_script_invocations_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            for cmd in (
                "python .ai/checkers/compile_gate.py .",
                "python scripts/runtime_delivery_gate.py .",
                "python tools/tool_state.py status",
            ):
                r = self._run_bash(root, cmd)
                self.assertEqual(r.returncode, 0,
                                 f"cmd={cmd} stderr: {r.stderr[-800:]}")

    def test_non_governance_invocations_still_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            for cmd in (
                'python -c "print(1)"',
                "python -m pytest tests/ -q",
                "python /tmp/evil.py",
                "bash .zcode/tools/foo.sh",
                "python .zcode/tools/validate_state.py . && rm -rf /tmp/x",
            ):
                r = self._run_bash(root, cmd)
                self.assertEqual(r.returncode, 2,
                                 f"cmd={cmd} should BLOCK. stderr: {r.stderr[-800:]}")

    def test_governance_tool_outside_target_still_blocked(self):
        # 治理工具调用的项目边界拦截保持 fail-closed
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = self._run_bash(
                root, "python .zcode/tools/validate_state.py > C:/Windows/Temp/evil.txt")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_main_session_compound_form_passes(self):
        """主会话真实形态：cd <项目根> && python 治理工具 2>&1 | tail → 放行。

        T-0086-P3 回归：P2 只豁免纯命令形态；主会话实际执行的是
        `cd ... && C:/Python312/python.exe .zcode/tools/... . 2>&1 | tail`
        复合形态 → 曾继续被 SETUP_INCOMPLETE 拦截。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            for cmd in (
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/validate_state.py . 2>&1 | tail -5",
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/repair_continuity.py . 2>&1 | tail -5",
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/close_session.py . --note test 2>&1 | tail -10",
            ):
                r = self._run_bash(root, cmd)
                self.assertEqual(r.returncode, 0,
                                 f"cmd={cmd} stderr: {r.stderr[-800:]}")

    def test_compound_with_write_still_blocked(self):
        """复合命令含写语义段 → 治理工具豁免不生效，仍拦截（fail-closed）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            for cmd in (
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/validate_state.py . && rm -rf /tmp/x",
                f"cd {_msys(tmp)} && C:/Python312/python.exe "
                ".zcode/tools/validate_state.py . > /tmp/out.txt",
            ):
                r = self._run_bash(root, cmd)
                self.assertEqual(r.returncode, 2,
                                 f"cmd={cmd} stderr: {r.stderr[-800:]}")


class LoopEnforcementGitExemptNarrowing(unittest.TestCase):
    """T-0177 C3: git 豁免收窄 — 破坏性 git 操作不再随 task_id 无条件放行。

    原实现：有 task_id 时所有本地 git 操作（含 git reset --hard / git checkout
    <path> / git restore）全豁免 → 可覆盖 .ai/、hooks/ 等受保护文件绕过逐文件
    保护。收窄后仅治理必需操作（add/commit/diff/status 等）保持豁免。
    """

    def _full_project(self, stack):
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        root = _make_project(tmp, state_content=STATE_FULL,
                             task_files={"T-0001.md": TASK_IN_SCOPE},
                             gates_content=GATES_APPROVED,
                             review_evidence=REVIEW_EVIDENCE)
        return root

    def _run_bash(self, root, command):
        # 清除 PYTEST_CURRENT_TEST：pytest 会让子进程命中
        # is_legacy_synthetic_hook_fixture 旁路（LEGACY_SYNTHETIC_FIXTURE 放行），
        # 无法验证真实宿主行为。C3 测试必须模拟真实运行时。
        env = dict(os.environ)
        env.pop("PYTEST_CURRENT_TEST", None)
        return _run_hook("loop_enforcement.py", root,
                         {"tool_name": "Bash", "tool_input": {"command": command}},
                         env=env)

    def test_git_add_allowed_with_task(self):
        """git add（治理记录必需）保持豁免。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git add file.txt")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr[-800:]}")

    def test_git_commit_allowed_with_task(self):
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git commit -m 'record'")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr[-800:]}")

    def test_git_status_allowed_with_task(self):
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git status")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr[-800:]}")

    def test_git_reset_hard_blocked_with_task(self):
        """C3 核心：git reset --hard 可丢弃工作区改动，不得再随 task_id 放行。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git reset --hard HEAD~1")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_checkout_path_blocked_with_task(self):
        """C3 核心：git checkout -- <path> 可覆盖受保护文件。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git checkout -- .ai/state.yaml")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_restore_blocked_with_task(self):
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git restore .ai/state.yaml")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_compound_git_reset_blocked(self):
        """复合命令 cd /x && git reset --hard 同样拦截（原实现全放行）。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, f"cd {_msys(str(root))} && git reset --hard")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_compound_git_reset_blocked_without_task(self):
        """T-0177 审查 P1 回归：无 task 的 FULL 项目复合命令不得放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = self._run_bash(root, f"cd {_msys(tmp)} && git reset --hard")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_c_option_restore_blocked(self):
        """T-0177 审查 P1 回归：git -C <dir> restore 参数形态不得绕过段级判定。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git -C . restore src/main.py")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_rm_blocked_with_task(self):
        """T-0177 审查 P2-1：git rm 删除文件纳入破坏性收窄（不再随 task 全豁免）。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git rm .ai/state.yaml")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_merge_blocked_with_task(self):
        """T-0177 审查 P2-1：git merge 纳入破坏性收窄。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git merge feature")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_push_blocked_with_task(self):
        """网络操作保持原有拦截（回归）。"""
        with contextlib.ExitStack() as stack:
            root = self._full_project(stack)
            r = self._run_bash(root, "git push origin main")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")

    def test_git_reset_blocked_without_task(self):
        """无 task 时 destructive git 亦拦截（fail-closed 一致性）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL_NO_TASK)
            r = self._run_bash(root, "git reset --hard")
            self.assertEqual(r.returncode, 2, f"stderr: {r.stderr[-800:]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
