# -*- coding: utf-8 -*-
"""
test_hooks.py — loop-governance 三个 hook 脚本的端到端测试。

运行方式（项目根或本目录均可）：
    C:\\Python312\\python.exe -m unittest discover -s tests -v
或：
    C:\\Python312\\python.exe tests\\test_hooks.py

每个测试用临时目录搭一个最小治理项目（.ai/state.yaml + .ai/gates.yaml），
以子进程方式运行真实 hook 脚本，断言退出码与输出——与 ZCode 实际调用
方式一致（process 类型 + args 数组 + stdin JSON + ZCODE_PROJECT_DIR 环境变量）。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
PYTHON = sys.executable

STATE_CLEAN = """\
schema_version: 1
current_phase: S1-delivery
current_task_id: T-0007
current_gate_id: null
"""

STATE_WITH_GATE = """\
schema_version: 1
current_phase: S1-delivery
current_task_id: T-0007
current_gate_id: G-T-0007-IMPLEMENTATION
"""

GATES_PENDING = """\
gates:
  - id: G-T-0007-IMPLEMENTATION
    task_id: T-0007
    gate_type: implementation
    status: pending
  - id: G-T-0006-DESIGN
    task_id: T-0006
    gate_type: design
    status: approved
"""

GATES_NONE_PENDING = """\
gates:
  - id: G-T-0006-DESIGN
    task_id: T-0006
    gate_type: design
    status: approved
"""

HANDOFF_SAMPLE = """\
# Handoff

## Current Phase

S1-delivery

## Next Session First Step

Ask the user whether to approve G-T-0007-IMPLEMENTATION.

## Other Section
"""


def make_project(tmp, state=STATE_CLEAN, gates=None, handoff=False, config=None):
    """在临时目录里搭一个最小治理项目。返回项目根 Path。"""
    root = Path(tmp)
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(state, encoding="utf-8")
    if gates is not None:
        (root / ".ai" / "gates.yaml").write_text(gates, encoding="utf-8")
    if handoff:
        (root / ".ai" / "HANDOFF.md").write_text(HANDOFF_SAMPLE, encoding="utf-8")
    if config is not None:
        cfg_dir = root / ".zcode" / "skills" / "loop-governance"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(config, encoding="utf-8")
    return root


def run_hook(script, root, hook_input=None):
    """以 ZCode 的方式调用 hook：子进程 + stdin JSON + ZCODE_PROJECT_DIR。"""
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


class GateGuardTest(unittest.TestCase):
    SCRIPT = "gate_guard.py"

    def test_non_governance_project_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # 没有 .ai/
            r = run_hook(self.SCRIPT, root, write_input(str(root / "x.py")))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_pending_gate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, gates=GATES_NONE_PENDING)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_pending_gate_blocks_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, state=STATE_WITH_GATE, gates=GATES_PENDING)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("G-T-0007-IMPLEMENTATION", r.stderr)

    def test_pending_gate_blocks_edit_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, gates=GATES_PENDING)
            r = run_hook(self.SCRIPT, root, write_input("src/a.py"))
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_decision_recording_exemption_allows_gates_yaml(self):
        """pending 期间写 gates.yaml（记录用户决策）必须放行，否则死锁。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, state=STATE_WITH_GATE, gates=GATES_PENDING)
            r = run_hook(
                self.SCRIPT, root, write_input(str(root / ".ai" / "gates.yaml"))
            )
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_corrupt_state_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            # 写入非法 UTF-8 字节，模拟编码事故
            (root / ".ai" / "state.yaml").write_bytes(b"\xff\xfe invalid \x93\x94")
            (root / ".ai" / "gates.yaml").write_text(GATES_NONE_PENDING, encoding="utf-8")
            r = run_hook(self.SCRIPT, root, write_input(str(root / "a.py")))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("fail-closed", r.stderr)

    def test_corrupt_state_fail_open_when_configured(self):
        cfg = "gate_guard:\n  fail_on_state_error: open\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir()
            (root / ".ai" / "state.yaml").write_bytes(b"\xff\xfe invalid \x93\x94")
            cfg_dir = root / ".zcode" / "skills" / "loop-governance"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "config.yaml").write_text(cfg, encoding="utf-8")
            r = run_hook(self.SCRIPT, root, write_input(str(root / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("WARN", r.stderr)


class PathGuardTest(unittest.TestCase):
    SCRIPT = "path_guard.py"

    def test_normal_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "src" / "a.py")))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_agents_md_asks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "AGENTS.md")))
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            ho = out["hookSpecificOutput"]
            self.assertEqual(ho["hookEventName"], "PreToolUse")
            self.assertEqual(ho["permissionDecision"], "ask")

    def test_stable_dir_prefix_asks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, write_input(str(root / "stable" / "doc.md"))
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "ask"
            )

    def test_deny_mode_blocks(self):
        cfg = "path_guard:\n  decision: deny\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, config=cfg)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "AGENTS.md")))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("deny", r.stderr)

    def test_non_governance_project_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = run_hook(self.SCRIPT, root, write_input(str(root / "AGENTS.md")))
            self.assertEqual(r.returncode, 0, r.stderr)


class SessionBriefTest(unittest.TestCase):
    SCRIPT = "session_brief.py"

    def test_injects_state_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, gates=GATES_NONE_PENDING, handoff=True)
            r = run_hook(self.SCRIPT, root, {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("S1-delivery", ctx)
            self.assertIn("T-0007", ctx)
            self.assertIn("pending gates: none", ctx)
            self.assertIn("Ask the user whether to approve", ctx)

    def test_pending_gates_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, state=STATE_WITH_GATE, gates=GATES_PENDING)
            r = run_hook(self.SCRIPT, root, {"source": "startup"})
            out = json.loads(r.stdout)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("PENDING GATES", ctx)
            self.assertIn("G-T-0007-IMPLEMENTATION", ctx)

    def test_non_governance_project_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_hook(self.SCRIPT, Path(tmp), {"source": "startup"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
