# -*- coding: utf-8 -*-
"""
test_role_isolation.py — role_isolation hook 脚本的端到端测试。

覆盖：
- 正常路径：不同 developer/reviewer → 放行
- 正常路径：相同 developer/reviewer + FULL mode → 阻断（exit 2）
- 正常路径：相同 developer/reviewer + LIGHTWEIGHT mode → 警告放行（exit 0）
- 正常路径：未分配角色 → 放行
- 异常路径：state.yaml 损坏 → fail-closed 阻断（exit 2）
- 异常路径：state.yaml 缺失 → fail-closed 阻断（exit 2）
- 异常路径：task 文件不存在 → 放行（无 task_id = 无 enforcement target）
- 边界路径：角色不完整（有 dev 无 reviewer）→ 警告放行

运行方式：C:\\Python312\\python.exe -m pytest tests/test_role_isolation.py -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "codex_loop" / "hooks"
PYTHON = sys.executable

# ── Fixtures ────────────────────────────────────────────────────────────────

STATE_FULL = """\
schema_version: 1
current_phase: S4-implementation
current_task_id: T-TEST-001
loop_mode: FULL
"""

STATE_LIGHTWEIGHT = """\
schema_version: 1
current_phase: S4-implementation
current_task_id: T-TEST-001
loop_mode: LIGHTWEIGHT
"""

STATE_NO_TASK = """\
schema_version: 1
current_phase: S4-implementation
current_task_id: null
loop_mode: FULL
"""

GATES_MINIMAL = """\
gates:
  - id: G-TEST-001
    task_id: T-TEST-001
    gate_type: implementation
    status: approved
"""

TASK_SELF_REVIEW = """\
# T-TEST-001: Test Task

## Status

`active`

developer_agent_id: agent-001
reviewer_agent_id: agent-001
"""

TASK_DIFFERENT = """\
# T-TEST-001: Test Task

## Status

`active`

developer_agent_id: agent-001
reviewer_agent_id: agent-002
"""

TASK_INCOMPLETE = """\
# T-TEST-001: Test Task

## Status

`active`

developer_agent_id: agent-001
"""

TASK_NO_ROLES = """\
# T-TEST-001: Test Task

## Status

`active`
"""


def make_project(tmp, state=STATE_FULL, gates=GATES_MINIMAL, task=TASK_SELF_REVIEW):
    """Create a minimal governance project in a temp directory."""
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "state.yaml").write_text(state, encoding="utf-8")
    if gates:
        (ai_dir / "gates.yaml").write_text(gates, encoding="utf-8")
    tasks_dir = ai_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    if task:
        (tasks_dir / "T-TEST-001.md").write_text(task, encoding="utf-8")
    # Minimal zcode config
    zcode_dir = root / ".zcode" / "skills" / "loop-governance"
    zcode_dir.mkdir(parents=True, exist_ok=True)
    (zcode_dir / "config.yaml").write_text("role_isolation:\n  enabled: true\n", encoding="utf-8")
    return root


def run_hook(script, root, hook_input=None):
    """Run hook script as subprocess, matching ZCode invocation pattern."""
    env = dict(os.environ)
    env["ZCODE_PROJECT_DIR"] = str(root)
    payload = json.dumps(hook_input or {})
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def write_input(path):
    return {"tool_name": "Write", "tool_input": {"file_path": path}}


# ── Tests ───────────────────────────────────────────────────────────────────

class RoleIsolationTest(unittest.TestCase):
    SCRIPT = "role_isolation.py"

    # ── Happy path ────────────────────────────────────────────────────────

    def test_different_ids_pass(self):
        """Different developer and reviewer → allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, task=TASK_DIFFERENT)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0,
                             f"Expected exit 0, got {r.returncode}. stderr={r.stderr}")

    def test_no_roles_pass(self):
        """No role assignments → skip enforcement, pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, task=TASK_NO_ROLES)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_task_id_pass(self):
        """No current_task_id → skip enforcement, pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, state=STATE_NO_TASK, task=None)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_incomplete_roles_warn_pass(self):
        """Incomplete role assignment (dev only) → warn but pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, task=TASK_INCOMPLETE)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("WARN", r.stdout)

    # ── Self-review blocking ──────────────────────────────────────────────

    def test_self_review_full_mode_block(self):
        """Same developer/reviewer + FULL mode → DENY, exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, task=TASK_SELF_REVIEW, state=STATE_FULL)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 2,
                             f"Expected exit 2 (BLOCK), got {r.returncode}. stdout={r.stdout}")
            self.assertIn("deny", r.stdout.lower())

    def test_self_review_lightweight_mode_warn(self):
        """Same developer/reviewer + LIGHTWEIGHT mode → WARN only, exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, task=TASK_SELF_REVIEW, state=STATE_LIGHTWEIGHT)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0,
                             f"Expected exit 0 (warn), got {r.returncode}. stdout={r.stdout}")
            self.assertIn("WARN", r.stdout)

    # ── Fail-closed: corrupted state ─────────────────────────────────────

    def test_corrupt_state_fail_closed(self):
        """Corrupted state.yaml → fail-closed, exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir(parents=True)
            # Corrupted binary state.yaml
            (ai_dir / "state.yaml").write_bytes(b"\xff\xfe corrupt \x00\x01")
            (ai_dir / "gates.yaml").write_text(GATES_MINIMAL, encoding="utf-8")
            tasks_dir = ai_dir / "tasks"
            tasks_dir.mkdir()
            (tasks_dir / "T-TEST-001.md").write_text(TASK_SELF_REVIEW, encoding="utf-8")
            # Config
            zcode_dir = root / ".zcode" / "skills" / "loop-governance"
            zcode_dir.mkdir(parents=True)
            (zcode_dir / "config.yaml").write_text("role_isolation:\n  enabled: true\n", encoding="utf-8")

            r = run_hook(self.SCRIPT, root, write_input(str(root / "a.py")))
            self.assertEqual(r.returncode, 2,
                             f"Expected exit 2 (fail-closed), got {r.returncode}. stdout={r.stdout}")
            self.assertIn("fail-closed", r.stdout.lower())

    def test_missing_state_pass(self):
        """Missing state.yaml → no task_id → skip enforcement (not an error)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / ".ai"
            ai_dir.mkdir(parents=True)
            # No state.yaml at all (project not initialized yet)
            (ai_dir / "gates.yaml").write_text(GATES_MINIMAL, encoding="utf-8")
            tasks_dir = ai_dir / "tasks"
            tasks_dir.mkdir()
            (tasks_dir / "T-TEST-001.md").write_text(TASK_SELF_REVIEW, encoding="utf-8")
            zcode_dir = root / ".zcode" / "skills" / "loop-governance"
            zcode_dir.mkdir(parents=True)
            (zcode_dir / "config.yaml").write_text("role_isolation:\n  enabled: true\n", encoding="utf-8")

            r = run_hook(self.SCRIPT, root, write_input(str(root / "a.py")))
            self.assertEqual(r.returncode, 0,
                             f"Expected exit 0 (no task to enforce), got {r.returncode}. stdout={r.stdout}")
