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

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
PYTHON = sys.executable


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


def _run_hook(script_name: str, root: Path, hook_input: dict | None = None) -> subprocess.CompletedProcess:
    """Run a hook script as a subprocess, similar to ZCode's invocation."""
    env = dict(os.environ)
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
            )
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 0, f"Expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_standard_mode_also_blocks(self):
        """STANDARD mode should also enforce write restrictions."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_STANDARD)
            r = _run_hook("loop_enforcement.py", root, _write_input(str(root / "src" / "main.py")))
            self.assertEqual(r.returncode, 2, f"STANDARD mode should block without task_id. stderr: {r.stderr}")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
