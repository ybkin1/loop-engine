"""
B3 (T-0083): MCP tool capability model tests.

The T-0082 fix closed the Node-REPL bypass by fail-closing ALL mcp__ tools in
FULL mode. B3 adds a scoped capability model: a task contract may grant an
explicit `mcp_allowed_tools` allow-list; the default (field absent) remains
fail-closed (no MCP tools).

Coverage (mission 3d):
  1. mcp__ tool without task -> BLOCK (existing behavior)
  2. mcp__ tool with task but tool NOT in allow-list -> BLOCK
  3. mcp__ tool with task AND tool in allow-list -> passes the mcp gate
     (may still be blocked by other gates; assert NOT blocked with the
     mcp-specific message)
  4. Task file without mcp_allowed_tools -> all mcp__ tools BLOCKED

Also covers the three parsed forms of the allow-list (inline list, 基本信息
markdown-table row, block list) via both subprocess enforcement and a direct
parser unit test.

Tests run the hook via subprocess with temp directories, matching how ZCode
invokes it (process + stdin JSON + ZCODE_PROJECT_DIR env var).
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

MCP_TOOL = "mcp__node_repl__js"
MCP_OTHER_TOOL = "mcp__filesystem__read"

# Minimal loop-governance quality gate config (same requirement as
# test_enforcement.py): the hook requires
# .zcode/skills/loop-governance/config.yaml for S4+ phases.
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

STATE_FULL_NO_TASK = """\
schema_version: 1
project_name: test-mcp
current_phase: S4-implementation
loop_mode: FULL
"""

STATE_FULL_TASK = """\
schema_version: 1
project_name: test-mcp
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

# Task WITHOUT mcp_allowed_tools -> fail-closed default.
TASK_NO_MCP = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/
"""

# Task with inline-flow allow-list.
TASK_MCP_INLINE = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

mcp_allowed_tools: [mcp__node_repl__js]
"""

# Task with a DIFFERENT tool in the allow-list.
TASK_MCP_OTHER = """\
# Task T-0001: Implement feature X
mcp_allowed_tools: [mcp__filesystem__read]
"""

# Task with the allow-list as a 基本信息 markdown-table row (the canonical
# front-matter form used by T-0082.md / T-0083.md).
TASK_MCP_TABLE = """\
# Task T-0001: Implement feature X

## 基本信息

| 字段 | 值 |
|------|-----|
| task_id | T-0001 |
| mcp_allowed_tools | mcp__node_repl__js |

## Status

in_progress

## 允许路径

- src/
- tests/
"""

# Task with the allow-list as a block list.
TASK_MCP_BLOCK = """\
# Task T-0001: Implement feature X
mcp_allowed_tools:
- mcp__node_repl__js
- mcp__diagnostics__probe
"""


def _make_project(tmp: str, task_files: dict[str, str]) -> Path:
    """Create a minimal governed project in a temp directory."""
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "state.yaml").write_text(STATE_FULL_TASK, encoding="utf-8")

    # The enforcement hook requires the quality gate config for S4+ phases.
    qg_dir = root / ".zcode" / "skills" / "loop-governance"
    qg_dir.mkdir(parents=True, exist_ok=True)
    (qg_dir / "config.yaml").write_text(GOVERNANCE_CONFIG_YAML, encoding="utf-8")

    tasks_dir = ai_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for fname, content in task_files.items():
        (tasks_dir / fname).write_text(content, encoding="utf-8")

    return root


def _run_hook(root: Path, tool_name: str) -> subprocess.CompletedProcess:
    """Run loop_enforcement.py as a subprocess with an mcp__ tool call."""
    env = dict(os.environ)
    env["ZCODE_PROJECT_DIR"] = str(root)
    hook_input = {
        "tool_name": tool_name,
        "tool_input": {"code": "1 + 1", "title": "probe"},
    }
    return subprocess.run(
        [PYTHON, str(SCRIPTS / "loop_enforcement.py")],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


MCP_NO_TASK_MSG = "MCP side-effect tools require an active task"
MCP_ALLOWLIST_MSG = "not in task T-0001 allowed list"

# ═══════════════════════════════════════════════════════════════════════
# Subprocess enforcement tests
# ═══════════════════════════════════════════════════════════════════════

class McpCapabilityEnforcement(unittest.TestCase):
    """B3 capability allow-list behavior through the real hook."""

    def test_mcp_tool_without_task_blocks(self):
        """Case 1: mcp__ tool without an active task -> BLOCK (unchanged)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir(parents=True, exist_ok=True)
            (ai_dir / "state.yaml").write_text(STATE_FULL_NO_TASK, encoding="utf-8")
            r = _run_hook(root, MCP_TOOL)
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn(MCP_NO_TASK_MSG, r.stderr)

    def test_mcp_tool_with_task_not_in_allowlist_blocks(self):
        """Case 2a: task exists but has NO mcp_allowed_tools -> BLOCK."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_NO_MCP})
            r = _run_hook(root, MCP_TOOL)
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn(MCP_ALLOWLIST_MSG, r.stderr)

    def test_mcp_tool_with_task_but_other_tool_allowed_blocks(self):
        """Case 2b: task allows a DIFFERENT mcp tool -> this tool BLOCKED."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_MCP_OTHER})
            r = _run_hook(root, MCP_TOOL)
            self.assertEqual(r.returncode, 2, f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")
            self.assertIn(MCP_ALLOWLIST_MSG, r.stderr)

    def test_mcp_tool_in_allowlist_passes_mcp_gate(self):
        """Case 3: tool in allow-list -> NOT blocked with the mcp-specific message.

        The mcp capability gate passes; the call then falls through to the
        identity/scope gates (an mcp call has no statically extractable target,
        so it may still terminate at the task-scope gate — that is a separate,
        documented gate, not an mcp-allow-list failure).
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_MCP_INLINE})
            r = _run_hook(root, MCP_TOOL)
            self.assertNotIn(MCP_ALLOWLIST_MSG, r.stderr)
            self.assertNotIn(MCP_NO_TASK_MSG, r.stderr)
            self.assertNotIn("mcp__", r.stderr)

    def test_allowlist_table_row_form_parsed(self):
        """Case 3 (基本信息 table form): tool in allow-list -> passes mcp gate."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_MCP_TABLE})
            r = _run_hook(root, MCP_TOOL)
            self.assertNotIn(MCP_ALLOWLIST_MSG, r.stderr)
            self.assertNotIn(MCP_NO_TASK_MSG, r.stderr)

    def test_allowlist_block_form_parsed(self):
        """Case 3 (block-list form): tool in allow-list -> passes mcp gate."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_MCP_BLOCK})
            r = _run_hook(root, MCP_TOOL)
            self.assertNotIn(MCP_ALLOWLIST_MSG, r.stderr)
            self.assertNotIn(MCP_NO_TASK_MSG, r.stderr)

    def test_task_without_mcp_allowed_tools_blocks_all_mcp(self):
        """Case 4: no field in task file -> every mcp__ tool is BLOCKED."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, {"T-0001.md": TASK_NO_MCP})
            for tool in (MCP_TOOL, MCP_OTHER_TOOL, "mcp__unknown__tool"):
                r = _run_hook(root, tool)
                self.assertEqual(
                    r.returncode, 2,
                    f"{tool} should BLOCK without allow-list. stderr: {r.stderr}",
                )
                self.assertIn(MCP_ALLOWLIST_MSG, r.stderr)


# ═══════════════════════════════════════════════════════════════════════
# Parser unit tests (direct import)
# ═══════════════════════════════════════════════════════════════════════

sys.path.insert(0, str(SCRIPTS))
import loop_enforcement  # noqa: E402


class McpAllowedToolsParser(unittest.TestCase):
    """load_task_contract / _task_mcp_allowed_tools parsing behavior."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tasks_dir = self.root / ".ai" / "tasks"
        self.tasks_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_inline_flow_list(self):
        (self.tasks_dir / "T-1.md").write_text(
            "mcp_allowed_tools: [mcp__node_repl__js, mcp__other__x]\n",
            encoding="utf-8",
        )
        c = loop_enforcement.load_task_contract(self.root, "T-1")
        self.assertEqual(c["mcp_allowed_tools"], ["mcp__node_repl__js", "mcp__other__x"])

    def test_markdown_table_row(self):
        (self.tasks_dir / "T-1.md").write_text(
            "| 字段 | 值 |\n|------|-----|\n| task_id | T-1 |\n"
            "| mcp_allowed_tools | mcp__node_repl__js |\n",
            encoding="utf-8",
        )
        c = loop_enforcement.load_task_contract(self.root, "T-1")
        self.assertEqual(c["mcp_allowed_tools"], ["mcp__node_repl__js"])

    def test_block_list(self):
        (self.tasks_dir / "T-1.md").write_text(
            "mcp_allowed_tools:\n- mcp__node_repl__js\n- mcp__x\n",
            encoding="utf-8",
        )
        c = loop_enforcement.load_task_contract(self.root, "T-1")
        self.assertEqual(c["mcp_allowed_tools"], ["mcp__node_repl__js", "mcp__x"])

    def test_absent_field_defaults_to_empty(self):
        (self.tasks_dir / "T-1.md").write_text(
            "allowed_paths:\n- src/\n",
            encoding="utf-8",
        )
        c = loop_enforcement.load_task_contract(self.root, "T-1")
        self.assertEqual(c["mcp_allowed_tools"], [])
        self.assertEqual(c["allowed_paths"], ["src/"])

    def test_missing_task_file_returns_none(self):
        self.assertIsNone(loop_enforcement.load_task_contract(self.root, "T-999"))
        self.assertEqual(
            loop_enforcement._task_mcp_allowed_tools(self.root, "T-999"), []
        )

    def test_helper_returns_allowlist(self):
        (self.tasks_dir / "T-1.md").write_text(
            "mcp_allowed_tools: [mcp__node_repl__js]\n",
            encoding="utf-8",
        )
        self.assertEqual(
            loop_enforcement._task_mcp_allowed_tools(self.root, "T-1"),
            ["mcp__node_repl__js"],
        )


if __name__ == "__main__":
    unittest.main()
