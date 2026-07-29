"""Tests for content_guard.py — the primary write-protection hook."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks/scripts/content_guard.py"

class TestContentGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ai").mkdir()
        (self.root / ".ai/state.yaml").write_text("schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: T-TEST\ncurrent_gate_id: null\nloop_mode: FULL\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, tool_name, file_path, content):
        event = json.dumps({"tool_name": tool_name, "tool_input": {"file_path": str(self.root / file_path), "content": content}, "cwd": str(self.root)})
        r = subprocess.run([sys.executable, str(HOOK)], input=event, capture_output=True, text=True, timeout=10)
        return r

    def test_blocks_hardcoded_password(self):
        r = self._run("Write", "test.py", 'password = "secret123"\n')
        self.assertIn(r.returncode, (2, 1), "Should block hardcoded password")

    def test_blocks_api_key(self):
        r = self._run("Write", "config.py", 'api_key = "sk-1234567890abcdef"\n')
        self.assertIn(r.returncode, (2, 1), "Should block hardcoded API key")

    def test_passes_clean_code(self):
        r = self._run("Write", "clean.py", 'def hello():\n    return "world"\n')
        self.assertIn(r.returncode, (0, 1), "Should allow clean code")

    def test_skips_non_python(self):
        r = self._run("Write", "readme.md", "# Hello\n")
        self.assertIn(r.returncode, (0, 1), "Should skip non-Python files")

    def test_skips_governance_files(self):
        r = self._run("Write", ".ai/test.yaml", "key: value\n")
        self.assertIn(r.returncode, (0, 1), "Should skip governance files")

    def test_blocks_secret_token(self):
        r = self._run("Write", "auth.py", 'auth_token = "abcdefgh12345678"\n')
        self.assertIn(r.returncode, (2, 1), "Should block hardcoded token")


class TestBashContentGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ai").mkdir()
        (self.root / ".ai/state.yaml").write_text("schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: T-TEST\ncurrent_gate_id: null\nloop_mode: FULL\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, command):
        bhook = ROOT / "hooks/scripts/bash_content_guard.py"
        if not bhook.exists():
            raise unittest.SkipTest("bash_content_guard.py not found")
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(self.root)})
        r = subprocess.run([sys.executable, str(bhook)], input=event, capture_output=True, text=True, timeout=10)
        return r

    def test_blocks_echo_redirect(self):
        r = self._run('echo "bad" > test.py')
        self.assertIn(r.returncode, (1, 2), "Should block echo redirect")

    def test_blocks_cp_command(self):
        r = self._run("cp source.py dest.py")
        self.assertIn(r.returncode, (1, 2), "Should block cp")

    def test_allows_safe_ls(self):
        r = self._run("ls -la")
        self.assertIn(r.returncode, (0, 1), "Should allow ls")


class TestGateGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ai").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, file_path):
        ghook = ROOT / "hooks/scripts/gate_guard.py"
        event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(self.root / file_path)}, "cwd": str(self.root)})
        r = subprocess.run([sys.executable, str(ghook)], input=event, capture_output=True, text=True, timeout=10)
        return r

    def test_passes_non_governance_project(self):
        r = self._run("test.py")
        self.assertEqual(r.returncode, 0, "Should pass for non-governance project")

    def test_governance_project_with_state(self):
        (self.root / ".ai/state.yaml").write_text("schema_version: 1\ncurrent_phase: S6-delivery\ncurrent_task_id: T-TEST\ncurrent_gate_id: null\nloop_mode: FULL\n")
        (self.root / ".ai/gates.yaml").write_text("schema_version: 1\ngates: []\n")
        r = self._run("test.py")
        self.assertEqual(r.returncode, 0, "Should pass when no pending gates")


if __name__ == "__main__":
    unittest.main()
