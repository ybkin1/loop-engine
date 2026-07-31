# -*- coding: utf-8 -*-
"""
test_content_guard_semantic.py — content_guard.py 语义规则引擎测试。

T-0078 P0 / T-0082 Phase 5 GAP-1:
语义规则引擎（load_semantic_rules / check_semantic_rules /
check_suspense_boundary）在 main() 中因引用未定义变量 `target` 而从未执行
（NameError 被 except Exception 吞掉）。此测试验证修复后的 BLOCKER 规则
确实阻断 Write/Edit 操作（EXIT_BLOCK=2）。

与 ZCode 实际调用方式一致：子进程 + stdin JSON + ZCODE_PROJECT_DIR。
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

# 测试语义规则：BLOCKER 规则匹配 FORBIDDEN_MARKER，WARNING 规则匹配 WARN_MARKER
TEST_RULES = """\
schema_version: 1
framework: testpy
rules:
  - id: PY-TEST-BLOCKER
    severity: BLOCKER
    pattern: "FORBIDDEN_MARKER"
    glob: "**/*.py"
    message: "Forbidden marker present in python code"
    fix_suggestion: "Remove FORBIDDEN_MARKER"
  - id: PY-TEST-WARNING
    severity: WARNING
    pattern: "WARN_MARKER"
    glob: "**/*.py"
    message: "Warning marker present"
    fix_suggestion: "Remove WARN_MARKER"
"""


def _make_project(tmp: str, rules_yaml: str = TEST_RULES) -> Path:
    """搭建最小治理项目 + .ai/checks/<framework>.rules.yaml 规则文件。"""
    root = Path(tmp)
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(
        "schema_version: 1\nloop_mode: LIGHTWEIGHT\n", encoding="utf-8"
    )
    checks_dir = root / ".ai" / "checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    (checks_dir / "testpy.rules.yaml").write_text(rules_yaml, encoding="utf-8")
    return root


def _run_hook(root: Path, hook_input: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["ZCODE_PROJECT_DIR"] = str(root)
    return subprocess.run(
        [PYTHON, str(SCRIPTS / "content_guard.py")],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


class ContentGuardSemanticRulesTest(unittest.TestCase):
    """GAP-1: 语义规则引擎修复后的行为验证。"""

    def test_blocker_rule_blocks_write(self):
        """Write 内容违反 BLOCKER 规则 → EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": "# FORBIDDEN_MARKER\nx = 1\n",
                },
            })
            self.assertEqual(
                r.returncode, 2,
                f"expected EXIT_BLOCK(2), got {r.returncode}. stderr: {r.stderr}",
            )
            self.assertIn("SEMANTIC", r.stderr)
            self.assertIn("PY-TEST-BLOCKER", r.stderr)

    def test_warning_rule_does_not_block(self):
        """WARNING 规则命中 → 只记录日志，不阻断。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": "# WARN_MARKER\nx = 1\n",
                },
            })
            self.assertEqual(
                r.returncode, 0,
                f"expected EXIT_PASS(0), got {r.returncode}. stderr: {r.stderr}",
            )
            self.assertIn("PY-TEST-WARNING", r.stderr)

    def test_clean_content_passes_with_rules_present(self):
        """规则文件存在但内容合规 → EXIT_PASS(0)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": "x = 1\n",
                },
            })
            self.assertEqual(
                r.returncode, 0,
                f"expected EXIT_PASS(0), got {r.returncode}. stderr: {r.stderr}",
            )

    def test_rule_not_matching_glob_passes(self):
        """规则 glob 不匹配（非 .py 文件）→ 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.txt"),
                    "content": "FORBIDDEN_MARKER\n",
                },
            })
            self.assertEqual(
                r.returncode, 0,
                f"expected EXIT_PASS(0), got {r.returncode}. stderr: {r.stderr}",
            )

    def test_blocker_rule_blocks_edit_of_existing_file(self):
        """Edit 合并内容违反 BLOCKER 规则 → EXIT_BLOCK(2)（GAP-4b 合并检查）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            src = root / "src"
            src.mkdir()
            (src / "demo.py").write_text("x = 1\n", encoding="utf-8")
            r = _run_hook(root, {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "old_string": "x = 1",
                    "new_string": "x = 1  # FORBIDDEN_MARKER",
                },
            })
            self.assertEqual(
                r.returncode, 2,
                f"expected EXIT_BLOCK(2), got {r.returncode}. stderr: {r.stderr}",
            )
            self.assertIn("PY-TEST-BLOCKER", r.stderr)

    def test_no_rules_dir_passes(self):
        """无 .ai/checks/ 规则目录 → 语义检查跳过，EXIT_PASS(0)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ai").mkdir(parents=True, exist_ok=True)
            (root / ".ai" / "state.yaml").write_text(
                "schema_version: 1\nloop_mode: LIGHTWEIGHT\n", encoding="utf-8"
            )
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": "# FORBIDDEN_MARKER\nx = 1\n",
                },
            })
            self.assertEqual(
                r.returncode, 0,
                f"expected EXIT_PASS(0), got {r.returncode}. stderr: {r.stderr}",
            )


class ContentGuardInjectionCheckTest(unittest.TestCase):
    """GAP-4c: 新增内容注入/动态执行检查。"""

    def test_ss011_dynamic_exec_blocks(self):
        """exec/eval 字符串插值（SS-011 high）→ EXIT_BLOCK(2)。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": 'code = eval("x + {val}")\n',
                },
            })
            self.assertEqual(
                r.returncode, 2,
                f"expected EXIT_BLOCK(2), got {r.returncode}. stderr: {r.stderr}",
            )
            self.assertIn("SS-011", r.stderr)

    def test_ss010_os_system_warns_only(self):
        """os.system（SS-010 medium）→ 只记录 warning，不阻断。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp)
            r = _run_hook(root, {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(root / "src" / "demo.py"),
                    "content": "import os\n\nos.system('echo hi')\n",
                },
            })
            self.assertEqual(
                r.returncode, 0,
                f"expected EXIT_PASS(0), got {r.returncode}. stderr: {r.stderr}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
