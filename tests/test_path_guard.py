# -*- coding: utf-8 -*-
"""
test_path_guard.py — T-0086 回归测试：只读操作访问项目外路径 → 放行；
写入操作访问项目外路径 → 拦截。

覆盖两个 hook：
- hooks/scripts/path_guard.py        （写入边界 + 保护区）
- hooks/scripts/loop_enforcement.py  （Loop 模式强制执行，含同款边界检查）

T-0086 背景：主会话用 Read 读取插件缓存中的 hook-protocol.md 等外部参考
文档时被误报 "Writing outside the project boundary is not allowed" ——
只读操作不应受写入边界拦截。本文件锁定修复后的行为：

  a) 只读工具（Read/WebFetch/WebSearch/只读 Bash）访问项目外路径 → 放行
  b) 写入工具（Write/Edit/写类 Bash）访问项目外路径 → 仍拦截

T-0086-P1（P1 安全缺陷修复）：is_readonly_command 曾把 sh/bash/dash/./、
php/ruby 等"执行形态"误判为只读 → 被 a) 的只读豁免放行（绕过 DISPATCH
门与项目外边界）。修复后执行形态一律判为写能力（fail-closed）：

  c) `sh <项目外脚本>` / `bash <项目外脚本>` / `./脚本` / `php <项目外脚本>`
     → 拦截（exit 2）
  d) `php -r '...'` / `ruby -e '...'`（loop_enforcement 经 DISPATCH 门
     拦截；path_guard 因命令内路径不可提取，由 c) 的脚本文件形态覆盖）
  e) 只读 Bash（cat/ls/grep/head）访问项目外路径 → 仍放行（不回归）

运行方式：
    C:\\Python312\\python.exe -m pytest tests/test_path_guard.py -q
"""

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

STATE_FULL = """\
schema_version: 1
current_phase: S6-delivery
current_task_id: T-TEST
current_gate_id: null
loop_mode: FULL
"""


def make_project(tmp):
    """搭一个最小治理项目（.ai/state.yaml + 一个普通文件）。"""
    root = Path(tmp)
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(STATE_FULL, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    return root


def run_hook(script, root, tool_name, tool_input):
    """以 ZCode 的方式调用 hook：子进程 + stdin JSON + ZCODE_PROJECT_DIR。"""
    env = dict(os.environ)
    env["ZCODE_PROJECT_DIR"] = str(root)
    payload = json.dumps(
        {"tool_name": tool_name, "tool_input": tool_input, "cwd": str(root)}
    )
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def outside_path(tmp):
    """构造项目根之外的路径。

    统一用正斜杠：hook 的 Bash 写入目标提取用 shlex.split（POSIX 模式），
    反斜杠会被当转义符吃掉导致路径损坏（既有缺陷，不在本任务范围）；
    正斜杠形式能稳定断言"写入项目外路径被拦截"。
    """
    return str(Path(tmp) / ".." / "outside_ref.txt").replace("\\", "/")


class PathGuardReadAllowWriteBlockTest(unittest.TestCase):
    """path_guard.py：只读放行 / 写入拦截（T-0086 核心回归）。"""

    SCRIPT = "path_guard.py"

    def test_read_outside_project_passes(self):
        """Read 项目外路径 → 放行（此前误报 'Writing outside the project boundary'）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "Read", {"file_path": outside_path(tmp)})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_read_protected_path_passes_without_ask(self):
        """Read 保护区（AGENTS.md）→ 放行且不弹 ask（只读不触发写入确认）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "Read", {"file_path": str(root / "AGENTS.md")})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_webfetch_passes(self):
        """WebFetch（无文件语义）→ 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "WebFetch", {"url": "https://example.com"})
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_bash_readonly_outside_passes(self):
        """只读 Bash（cat/ls/head）访问项目外路径 → 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            for cmd in (
                f"cat {outside_path(tmp)}",
                f"ls {outside_path(tmp)}",
                f"head -5 {outside_path(tmp)}",
                f"grep -r x {outside_path(tmp)}",
            ):
                r = run_hook(self.SCRIPT, root, "Bash", {"command": cmd})
                self.assertEqual(r.returncode, 0, f"{cmd}: {r.stderr}")

    def test_bash_execution_form_outside_blocked(self):
        """执行形态 Bash（sh/bash/dash/./php/ruby 脚本）引用项目外路径 → 拦截（exit 2）。

        T-0086-P1 回归：is_readonly_command 曾把 sh/bash/dash/./ 等执行形态
        误判为只读 → 被 T-0086 只读豁免放行；修复后这些形态是写能力，
        path_guard 对引用项目外路径的执行形态 fail-closed 拦截。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            outside_script = str(Path(tmp) / ".." / "outside_script.sh").replace("\\", "/")
            outside_php = str(Path(tmp) / ".." / "outside_script.php").replace("\\", "/")
            outside_rb = str(Path(tmp) / ".." / "outside_script.rb").replace("\\", "/")
            for cmd in (
                f"sh {outside_script}",
                f"bash {outside_script}",
                f"dash {outside_script}",
                f"./../outside_script.sh",
                f"php {outside_php}",
                f"ruby {outside_rb}",
            ):
                r = run_hook(self.SCRIPT, root, "Bash", {"command": cmd})
                self.assertEqual(r.returncode, 2, f"{cmd}: {r.stderr}")

    def test_governance_tool_invocation_passes(self):
        """治理工具调用（解释器在项目外 + 脚本在 .zcode/tools/）→ 放行。

        T-0086-P3 回归：`C:/Python312/python.exe .zcode/tools/validate_state.py .`
        曾被 P1 执行形态检查误拦——"项目外引用"只是解释器二进制路径
        （Windows 上解释器几乎总在项目外），脚本本身在白名单目录内。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Bash",
                {"command": "C:/Python312/python.exe .zcode/tools/validate_state.py ."},
            )
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_governance_tool_compound_form_passes(self):
        """治理工具复合形态（cd 项目根 && python 工具 | tail）→ 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            msys = re.sub(r"^([A-Za-z]):", lambda m: "/" + m.group(1).lower(),
                          tmp.replace("\\", "/"))
            r = run_hook(
                self.SCRIPT, root, "Bash",
                {"command": f"cd {msys} && C:/Python312/python.exe "
                            ".zcode/tools/validate_state.py . 2>&1 | tail -5"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_non_governance_script_outside_still_blocked(self):
        """非治理工具（脚本在项目外白名单外）→ 执行形态检查仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Bash",
                {"command": "C:/Python312/python.exe /tmp/evil.py"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_write_outside_project_blocked(self):
        """Write 项目外路径 → 仍拦截（写入边界 fail-closed 不弱化）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Write",
                {"file_path": outside_path(tmp), "content": "x"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("outside the project root", r.stderr)

    def test_edit_outside_project_blocked(self):
        """Edit 项目外路径 → 仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Edit",
                {"file_path": outside_path(tmp), "old_string": "a", "new_string": "b"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_apply_patch_outside_project_blocked(self):
        """ApplyPatch 项目外路径 → 仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "ApplyPatch",
                {"file_path": outside_path(tmp), "patch": "--- a\n+++ b\n"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_bash_write_outside_project_blocked(self):
        """写类 Bash（touch/cp 重定向到项目外）→ 仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            outside = outside_path(tmp)
            src_posix = str(root / "src" / "a.py").replace("\\", "/")
            for cmd in (
                f"touch {outside}",
                f"cp {src_posix} {outside}",
                f"echo hi > {outside}",
            ):
                r = run_hook(self.SCRIPT, root, "Bash", {"command": cmd})
                self.assertEqual(r.returncode, 2, f"{cmd}: {r.stderr}")

    def test_write_protected_path_still_asks(self):
        """Write 保护区（AGENTS.md）→ 仍 ask（回归：写入确认未被弱化）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "Write", {"file_path": str(root / "AGENTS.md")})
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(
                out["hookSpecificOutput"]["permissionDecision"], "ask"
            )

    def test_deny_mode_write_protected_still_blocked(self):
        """deny 模式下 Write 保护区 → 仍 exit 2（回归）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            cfg_dir = root / ".zcode" / "skills" / "loop-governance"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "config.yaml").write_text(
                "path_guard:\n  decision: deny\n", encoding="utf-8"
            )
            r = run_hook(self.SCRIPT, root, "Write", {"file_path": str(root / "AGENTS.md")})
            self.assertEqual(r.returncode, 2, r.stderr)


class LoopEnforcementReadAllowWriteBlockTest(unittest.TestCase):
    """loop_enforcement.py：同款只读误伤修复（T-0086）。"""

    SCRIPT = "loop_enforcement.py"

    def test_read_outside_project_passes(self):
        """Read 项目外路径 → 放行（此前边界检查误报）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "Read", {"file_path": outside_path(tmp)})
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_bash_readonly_outside_passes(self):
        """只读 Bash（cat/ls/head/grep）访问项目外路径 → 放行。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            for cmd in (
                f"cat {outside_path(tmp)}",
                f"ls {outside_path(tmp)}",
                f"head -5 {outside_path(tmp)}",
                f"grep -r x {outside_path(tmp)}",
            ):
                r = run_hook(self.SCRIPT, root, "Bash", {"command": cmd})
                self.assertEqual(r.returncode, 0, f"{cmd}: {r.stderr}")

    def test_bash_execution_form_outside_blocked(self):
        """执行形态 Bash 引用项目外路径 → DISPATCH 门拦截（exit 2）。

        T-0086-P1 回归：`sh /outside/script.sh` 曾被 is_readonly_command
        误判为只读 → EXTERNAL_READ 豁免放行（绕过 DISPATCH_REQUIRED 门）；
        修复后不再是只读 → DISPATCH 门 fail-closed 拦截。php -r / ruby -e
        的命令内路径无法由 path_guard 提取，这里同样经 DISPATCH 门拦截。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            outside = outside_path(tmp)
            outside_script = str(Path(tmp) / ".." / "outside_script.sh").replace("\\", "/")
            for cmd in (
                f"sh {outside_script}",
                f"bash {outside_script}",
                f"./../outside_script.sh",
                f"php -r 'file_put_contents(\"{outside}\", \"y\");'",
                f"ruby -e 'File.write(\"{outside}\", \"y\")'",
            ):
                r = run_hook(self.SCRIPT, root, "Bash", {"command": cmd})
                self.assertEqual(r.returncode, 2, f"{cmd}: {r.stderr}")

    def test_read_governance_metadata_passes(self):
        """Read 治理元数据（.ai/state.yaml）→ 放行（回归）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(self.SCRIPT, root, "Read", {"file_path": str(root / ".ai" / "state.yaml")})
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_write_outside_project_blocked(self):
        """Write 项目外路径 → 仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Write",
                {"file_path": outside_path(tmp), "content": "x"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("outside the project root", r.stderr)

    def test_edit_outside_project_blocked(self):
        """Edit 项目外路径 → 仍拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Edit",
                {"file_path": outside_path(tmp), "old_string": "a", "new_string": "b"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_bash_write_outside_project_blocked(self):
        """写类 Bash（touch 项目外）→ 仍拦截（fail-closed 保持）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            r = run_hook(
                self.SCRIPT, root, "Bash",
                {"command": f"touch {outside_path(tmp)}"},
            )
            self.assertEqual(r.returncode, 2, r.stderr)


if __name__ == "__main__":
    unittest.main()
