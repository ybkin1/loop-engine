# -*- coding: utf-8 -*-
"""
test_bash_readonly.py — Tests for is_readonly_command() and has_write_operations()
from hook_common.py, plus end-to-end integration tests for the Bash readonly
bypass in loop_enforcement.py.

Run from project root:
    python -m unittest discover -s tests -v
or:
    python tests/test_bash_readonly.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure hook_common.py is importable
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
sys.path.insert(0, str(HOOKS_DIR))

from hook_common import has_write_operations, is_readonly_command

SCRIPTS = HOOKS_DIR
PYTHON = sys.executable


# ── Helpers ───────────────────────────────────────────────────────────

def _make_project(tmp: str, state_content: str | None = None,
                  task_files: dict[str, str] | None = None) -> Path:
    """Create a minimal governed project in a temp directory."""
    root = Path(tmp)
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    if state_content is not None:
        (ai_dir / "state.yaml").write_text(state_content, encoding="utf-8")

    if task_files:
        tasks_dir = ai_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in task_files.items():
            (tasks_dir / fname).write_text(content, encoding="utf-8")

    return root


def _run_hook(script_name: str, root: Path,
              hook_input: dict | None = None) -> subprocess.CompletedProcess:
    """Run a hook script as a subprocess, matching ZCode's invocation."""
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


def _bash_input(command: str) -> dict:
    """Build a PreToolUse hook input for a Bash operation."""
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ── State fixtures ────────────────────────────────────────────────────

STATE_FULL = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
current_task_id: T-0001
"""

TASK_IN_SCOPE = """\
# Task T-0001: Implement feature X
allowed_paths:
- src/
- tests/

developer_agent_id: "agent-001"
reviewer_agent_id: "agent-002"
"""


# ═══════════════════════════════════════════════════════════════════════
# Unit tests: has_write_operations()
# ═══════════════════════════════════════════════════════════════════════

class HasWriteOperationsTest(unittest.TestCase):
    """Tests for has_write_operations() — safety-first write detection."""

    def test_redirect_overwrite(self):
        """echo hello > file.txt — has redirect."""
        self.assertTrue(has_write_operations("echo hello > file.txt"))

    def test_redirect_append(self):
        """echo hello >> file.txt — has append redirect."""
        self.assertTrue(has_write_operations("echo hello >> file.txt"))

    def test_stderr_redirect(self):
        """cmd 2> error.log — has stderr redirect."""
        self.assertTrue(has_write_operations("cmd 2> error.log"))

    def test_tee_command(self):
        """cat file.txt | tee log — has tee."""
        self.assertTrue(has_write_operations("cat file.txt | tee log"))

    def test_cp_command(self):
        """cp a b — has cp."""
        self.assertTrue(has_write_operations("cp a b"))

    def test_mv_command(self):
        """mv a b — has mv."""
        self.assertTrue(has_write_operations("mv a b"))

    def test_mkdir_command(self):
        """mkdir newdir — has mkdir."""
        self.assertTrue(has_write_operations("mkdir newdir"))

    def test_touch_command(self):
        """touch file.txt — has touch."""
        self.assertTrue(has_write_operations("touch file.txt"))

    def test_rm_command(self):
        """rm -rf dir — has rm."""
        self.assertTrue(has_write_operations("rm -rf dir"))

    def test_chmod_command(self):
        """chmod +x script.sh — has chmod."""
        self.assertTrue(has_write_operations("chmod +x script.sh"))

    def test_chown_command(self):
        """chown user:group file — has chown."""
        self.assertTrue(has_write_operations("chown user:group file"))

    def test_git_push(self):
        """git push — write operation."""
        self.assertTrue(has_write_operations("git push"))

    def test_git_commit(self):
        """git commit -m 'msg' — write operation."""
        self.assertTrue(has_write_operations("git commit -m 'msg'"))

    def test_git_merge(self):
        """git merge feature — write operation."""
        self.assertTrue(has_write_operations("git merge feature"))

    def test_find_with_delete(self):
        """find . -name '*.py' -delete — has delete."""
        self.assertTrue(has_write_operations("find . -name '*.py' -delete"))

    def test_heredoc(self):
        """cat <<EOF > file — has heredoc + redirect."""
        self.assertTrue(has_write_operations("cat <<EOF > file.txt"))

    def test_no_write_operations(self):
        """ls -la — no write operations."""
        self.assertFalse(has_write_operations("ls -la"))

    def test_empty_command(self):
        """Empty command — safety-first, returns True."""
        self.assertTrue(has_write_operations(""))


# ═══════════════════════════════════════════════════════════════════════
# Unit tests: is_readonly_command()
# ═══════════════════════════════════════════════════════════════════════

class IsReadonlyCommandTest(unittest.TestCase):
    """Tests for is_readonly_command() on various command patterns."""

    # ── 测试运行器 ──

    def test_pytest_simple(self):
        """python -m pytest tests/ -q → False (T-0082: script execution is side-effect capable)."""
        self.assertFalse(is_readonly_command("python -m pytest tests/ -q"))

    def test_pytest_module_only(self):
        """pytest tests/ → True."""
        self.assertTrue(is_readonly_command("pytest tests/"))

    def test_pytest_with_python3(self):
        """python3 -m pytest tests/ → False (T-0082: script execution is side-effect capable)."""
        self.assertFalse(is_readonly_command("python3 -m pytest tests/"))

    # ── 文件查看 ──

    def test_ls(self):
        """ls -la → True."""
        self.assertTrue(is_readonly_command("ls -la"))

    def test_cat_simple(self):
        """cat file.txt → True."""
        self.assertTrue(is_readonly_command("cat file.txt"))

    def test_head(self):
        """head -n 10 file.txt → True."""
        self.assertTrue(is_readonly_command("head -n 10 file.txt"))

    def test_tail(self):
        """tail -f log.txt → True."""
        self.assertTrue(is_readonly_command("tail -f log.txt"))

    def test_find_basic(self):
        """find . -name '*.py' → True."""
        self.assertTrue(is_readonly_command("find . -name '*.py'"))

    def test_grep(self):
        """grep -r pattern src/ → True."""
        self.assertTrue(is_readonly_command("grep -r pattern src/"))

    # ── Git 只读 ──

    def test_git_status(self):
        """git status → True."""
        self.assertTrue(is_readonly_command("git status"))

    def test_git_log(self):
        """git log --oneline → True."""
        self.assertTrue(is_readonly_command("git log --oneline"))

    def test_git_diff(self):
        """git diff HEAD~1 → True."""
        self.assertTrue(is_readonly_command("git diff HEAD~1"))

    def test_git_show(self):
        """git show HEAD → True."""
        self.assertTrue(is_readonly_command("git show HEAD"))

    def test_git_branch(self):
        """git branch → True (list branches)."""
        self.assertTrue(is_readonly_command("git branch"))

    def test_git_ls_files(self):
        """git ls-files → True."""
        self.assertTrue(is_readonly_command("git ls-files"))

    # ── 代码检查只读（T-0082 Phase 4: python -m 脚本执行视为可写能力）──

    def test_flake8(self):
        """python -m flake8 src/ → False (script exec; may write reports/caches)."""
        self.assertFalse(is_readonly_command("python -m flake8 src/"))

    def test_mypy(self):
        """python -m mypy src/ → False (script exec; may write .mypy_cache)."""
        self.assertFalse(is_readonly_command("python -m mypy src/"))

    def test_ruff_check(self):
        """python -m ruff check → False (script exec; may write .ruff_cache)."""
        self.assertFalse(is_readonly_command("python -m ruff check"))

    def test_pylint(self):
        """pylint src/ → True."""
        self.assertTrue(is_readonly_command("pylint src/"))

    def test_black_check(self):
        """black --check src/ → True."""
        self.assertTrue(is_readonly_command("black --check src/"))

    def test_isort_check(self):
        """isort --check src/ → True."""
        self.assertTrue(is_readonly_command("isort --check src/"))

    # ── 环境信息 ──

    def test_echo(self):
        """echo hello → True."""
        self.assertTrue(is_readonly_command("echo hello"))

    def test_pwd(self):
        """pwd → True."""
        self.assertTrue(is_readonly_command("pwd"))

    def test_whoami(self):
        """whoami → True."""
        self.assertTrue(is_readonly_command("whoami"))

    def test_uname(self):
        """uname -a → True."""
        self.assertTrue(is_readonly_command("uname -a"))

    # ── 包管理只读 ──

    def test_pip_list(self):
        """pip list → True."""
        self.assertTrue(is_readonly_command("pip list"))

    def test_pip_show(self):
        """pip show package → True."""
        self.assertTrue(is_readonly_command("pip show package"))

    def test_pip_freeze(self):
        """pip freeze → True."""
        self.assertTrue(is_readonly_command("pip freeze"))

    # ── 脚本执行（T-0082 Phase 4: 解释器为可写能力，除非安全标记）──

    def test_python_script(self):
        """python script.py → False (T-0082: script execution is side-effect capable)."""
        self.assertFalse(is_readonly_command("python script.py"))

    def test_bash_script(self):
        """bash ./run_tests.sh → False (T-0086-P1: 脚本执行是写能力，fail-closed)."""
        self.assertFalse(is_readonly_command("bash ./run_tests.sh"))

    def test_node_script(self):
        """node index.js → False (T-0082: script execution is side-effect capable)."""
        self.assertFalse(is_readonly_command("node index.js"))

    # ── 执行形态（T-0086-P1: 解释器/直接脚本执行必须 fail-closed）──

    def test_sh_script(self):
        """sh ./deploy.sh → False (T-0086-P1: 脚本执行是写能力)."""
        self.assertFalse(is_readonly_command("sh ./deploy.sh"))

    def test_dash_script(self):
        """dash /tmp/script.sh → False."""
        self.assertFalse(is_readonly_command("dash /tmp/script.sh"))

    def test_zsh_script(self):
        """zsh /tmp/script.sh → False."""
        self.assertFalse(is_readonly_command("zsh /tmp/script.sh"))

    def test_dot_slash_script(self):
        """./script.sh 直接执行 → False (直接脚本执行)."""
        self.assertFalse(is_readonly_command("./script.sh"))
        self.assertFalse(is_readonly_command("./../outside/script.sh"))

    def test_abs_path_execution(self):
        """/bin/cat file → False (直接路径执行，fail-closed)."""
        self.assertFalse(is_readonly_command("/bin/cat /etc/passwd"))

    def test_dot_source(self):
        """. script.sh / source script.sh → False (source 执行脚本)."""
        self.assertFalse(is_readonly_command(". ./setup.sh"))
        self.assertFalse(is_readonly_command("source /tmp/setup.sh"))

    def test_php_r(self):
        """php -r 'file_put_contents(...)' → False (T-0086-P1)."""
        self.assertFalse(
            is_readonly_command(
                "php -r 'file_put_contents(\"/tmp/x\", \"y\");'"
            )
        )

    def test_ruby_e(self):
        """ruby -e 'File.write(...)' → False (T-0086-P1)."""
        self.assertFalse(
            is_readonly_command("ruby -e 'File.write(\"/tmp/x\", \"y\")'")
        )

    def test_perl_e(self):
        """perl -e '...' → False (perl -e 可写文件)."""
        self.assertFalse(is_readonly_command("perl -e 'print qq(x)'"))

    def test_awk_system(self):
        """awk 'BEGIN{system(...)}' → False (awk 可执行任意代码)."""
        self.assertFalse(
            is_readonly_command("awk 'BEGIN{system(\"touch /tmp/x\")}'")
        )

    def test_awk_print_only(self):
        """awk '{print $1}' file → True (常见只读用法保留)."""
        self.assertTrue(is_readonly_command("awk '{print $1}' file.txt"))

    def test_awk_pipe_to_command(self):
        """awk '{print | \"sh\"}' → False (管道到命令)."""
        self.assertFalse(is_readonly_command("awk '{print | \"sh\"}'"))

    def test_curl_pipe_bash(self):
        """curl ... | bash → False (管道执行 bash)."""
        self.assertFalse(
            is_readonly_command("curl -s https://example.com/install.sh | bash")
        )

    def test_base64_pipe_bash(self):
        """echo ... | base64 -d | bash → False (管道执行 bash)."""
        self.assertFalse(
            is_readonly_command("echo 'dG91Y2ggL3RtcC9ldmls' | base64 -d | bash")
        )

    def test_sudo_bash_script(self):
        """sudo -u root bash script.sh → False (前缀词后解释器仍执行)."""
        self.assertFalse(is_readonly_command("sudo -u root bash /tmp/script.sh"))

    def test_env_bash_script(self):
        """env -i bash script.sh → False."""
        self.assertFalse(is_readonly_command("env -i bash /tmp/script.sh"))

    def test_xargs_rm(self):
        """find . | xargs -0 rm → False (xargs 执行写命令)."""
        self.assertFalse(
            is_readonly_command("find . -name '*.tmp' | xargs -0 rm")
        )

    def test_xargs_bash(self):
        """find . | xargs bash -c '...' → False (xargs 执行解释器)."""
        self.assertFalse(
            is_readonly_command("find . -print0 | xargs -0 bash -c 'echo hi'")
        )

    def test_xargs_grep(self):
        """find . | xargs grep → True (xargs 执行只读命令)."""
        self.assertTrue(
            is_readonly_command("find . -name '*.py' | xargs grep pattern")
        )

    def test_python_help_py_not_readonly(self):
        """python help.py → False (help 是脚本名，不是帮助标记)."""
        self.assertFalse(is_readonly_command("python help.py"))

    def test_python_c_print_then_pipeline(self):
        """python -c 'print' && sh -c 'rm x' → False (安全片段不掩盖后续段)."""
        self.assertFalse(
            is_readonly_command("python -c 'print(1)' && sh -c 'rm -rf /tmp/x'")
        )

    def test_bash_help_readonly(self):
        """bash --help → True (安全标记豁免仍有效)."""
        self.assertTrue(is_readonly_command("bash --help"))

    def test_command_dash_v_bash(self):
        """command -v bash → True (查询形态，不执行)."""
        self.assertTrue(is_readonly_command("command -v bash"))

    def test_which_python_readonly(self):
        """which python → True (查询形态，不执行)."""
        self.assertTrue(is_readonly_command("which python"))

    # ── 构建只读 ──

    def test_python_build_check(self):
        """python -m build --check → False (T-0082: python invocation without safe marker)."""
        self.assertFalse(is_readonly_command("python -m build --check"))

    def test_npm_dry_run(self):
        """npm publish --dry-run → True."""
        self.assertTrue(is_readonly_command("npm publish --dry-run"))


class IsReadonlyCommandFalseTest(unittest.TestCase):
    """Tests that is_readonly_command() returns False for write commands."""

    def test_redirect_is_not_readonly(self):
        """echo hello > file.txt → False (redirect)."""
        self.assertFalse(is_readonly_command("echo hello > file.txt"))

    def test_cp_is_not_readonly(self):
        """cp a b → False."""
        self.assertFalse(is_readonly_command("cp a b"))

    def test_mv_is_not_readonly(self):
        """mv a b → False."""
        self.assertFalse(is_readonly_command("mv a b"))

    def test_python_with_redirect(self):
        """python script.py > out.txt → False (has redirect)."""
        self.assertFalse(is_readonly_command("python script.py > out.txt"))

    def test_cat_with_tee(self):
        """cat file.txt | tee log → False (has tee)."""
        self.assertFalse(is_readonly_command("cat file.txt | tee log"))

    def test_git_push_not_readonly(self):
        """git push → False."""
        self.assertFalse(is_readonly_command("git push"))

    def test_git_commit_not_readonly(self):
        """git commit -m 'msg' → False."""
        self.assertFalse(is_readonly_command("git commit -m 'msg'"))

    def test_git_merge_not_readonly(self):
        """git merge feature → False."""
        self.assertFalse(is_readonly_command("git merge feature"))

    def test_rm_is_not_readonly(self):
        """rm -rf dir → False."""
        self.assertFalse(is_readonly_command("rm -rf dir"))

    def test_find_with_delete_not_readonly(self):
        """find . -name '*.py' -delete → False."""
        self.assertFalse(is_readonly_command("find . -name '*.py' -delete"))

    def test_touch_is_not_readonly(self):
        """touch newfile.py → False."""
        self.assertFalse(is_readonly_command("touch newfile.py"))

    def test_mkdir_is_not_readonly(self):
        """mkdir newdir → False."""
        self.assertFalse(is_readonly_command("mkdir newdir"))

    def test_empty_command(self):
        """Empty string → False."""
        self.assertFalse(is_readonly_command(""))

    def test_none_command(self):
        """None → False."""
        self.assertFalse(is_readonly_command(None))  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════════════════
# Integration tests: loop_enforcement.py allows readonly Bash commands
# ═══════════════════════════════════════════════════════════════════════

class LoopEnforcementBashReadonlyIntegration(unittest.TestCase):
    """End-to-end tests: loop_enforcement.py allows readonly Bash commands
    even when FULL mode is active and the command isn't tied to an
    explicit task scope.

    T-0082 design note (hooks/scripts/loop_enforcement.py:914, _git_commit_exempt):
    git commit-ops ("git add", "git commit", "git diff", "git status",
    "git log", "git branch", "git show", "git tag", "git config") are
    intentionally EXEMPT from the DISPATCH_REQUIRED (runtime projection)
    gate — governance records must be inspectable and committable even
    before a runtime projection exists. With an active task, ALL local git
    operations pass without a projection; without a task, only
    add/commit/diff pass. All other readonly commands (ls, pytest, flake8...)
    remain fail-closed without a runtime projection.
    """

    def test_pytest_passes_in_full_mode(self):
        """python -m pytest tests/ is BLOCKED without runtime projection.

        In FULL mode with an active task, the enforcement hook now requires
        a runtime projection (fail-closed).  This test verifies that
        readonly Bash commands are blocked when the projection is missing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("python -m pytest tests/ -q"))
            self.assertEqual(r.returncode, 2,
                             f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")

    def test_git_status_passes_in_full_mode(self):
        """git status is ALLOWED (rc=0) without runtime projection.

        WHY (T-0082): git commit-ops are exempt from the DISPATCH_REQUIRED
        gate via _git_commit_exempt (loop_enforcement.py:914). With an active
        task, all local git operations (status/log/branch/show/tag/config are
        in the exempt prefix list) pass even without a runtime projection —
        governance records must be committable. This test previously expected
        EXIT_BLOCK(2); the expectation was stale after T-0082.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("git status"))
            self.assertEqual(r.returncode, 0,
                             f"Expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_git_log_passes_in_full_mode(self):
        """git log is ALLOWED (rc=0) without runtime projection.

        WHY (T-0082): same commit-op exemption as git status —
        "git log" is in the _git_commit_exempt prefix list
        (loop_enforcement.py:914), so it bypasses the DISPATCH_REQUIRED gate.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("git log --oneline -5"))
            self.assertEqual(r.returncode, 0,
                             f"Expected EXIT_PASS(0). stderr: {r.stderr}")

    def test_ls_passes_in_full_mode(self):
        """ls -la is BLOCKED without runtime projection.

        In FULL mode with an active task, the enforcement hook now requires
        a runtime projection (fail-closed).  This test verifies that
        readonly commands are blocked when the projection is missing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("ls -la"))
            self.assertEqual(r.returncode, 2,
                             f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")

    def test_flake8_passes_in_full_mode(self):
        """python -m flake8 src/ is BLOCKED without runtime projection.

        In FULL mode with an active task, the enforcement hook now requires
        a runtime projection (fail-closed).  This test verifies that
        readonly code-check commands are blocked when the projection is missing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("python -m flake8 src/"))
            self.assertEqual(r.returncode, 2,
                             f"Expected EXIT_BLOCK(2). stderr: {r.stderr}")

    def test_write_command_still_blocked_in_full_mode(self):
        """echo hello > file.txt should still be BLOCKED in FULL mode
        if file is outside task scope (this has a redirect, so it's not readonly)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            # Write to docs/ which is NOT in allowed_paths
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input(f"echo hello > {root / 'docs' / 'out.txt'}"))
            self.assertEqual(r.returncode, 2,
                             f"Write outside scope should be BLOCKED. stderr: {r.stderr}")

    def test_write_command_within_scope_still_passes_in_full_mode(self):
        """Write within task scope is BLOCKED without runtime projection.

        In FULL mode with an active task, the enforcement hook now requires
        a runtime projection (fail-closed) before it even considers task scope.
        This test verifies that writes are blocked when the projection is missing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input(f"echo hello > {root / 'src' / 'out.txt'}"))
            self.assertEqual(r.returncode, 2,
                             f"Expected EXIT_BLOCK(2) without runtime projection. stderr: {r.stderr}")

    def test_git_push_still_blocked_in_full_mode(self):
        """git push should be BLOCKED (write git operation)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("git push"))
            self.assertEqual(r.returncode, 2,
                             f"git push should be BLOCKED. stderr: {r.stderr}")

    def test_cp_still_blocked_in_full_mode(self):
        """cp a b should be BLOCKED."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input(f"cp {root / 'src' / 'a.py'} {root / 'docs' / 'b.py'}"))
            self.assertEqual(r.returncode, 2,
                             f"cp should be BLOCKED. stderr: {r.stderr}")

    def test_readonly_bash_blocked_without_task(self):
        """Readonly Bash commands must be blocked when no task_id is set.

        This is a governance hardening: project-level exploration (find, grep,
        git status, ls) requires an active task. Previously this was allowed,
        which let the main thread discover and analyze project structure
        before creating a task — bypassing the "no task = no project work" rule.

        NOTE (T-0082): git status is still blocked here — without a task only
        the minimal commit-ops ("git add", "git commit", "git diff") are
        exempt; status/log remain project-level exploration and stay blocked.
        """
        state_no_task = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
loop_mode: FULL
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=state_no_task)
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("git status"))
            self.assertEqual(r.returncode, 2,
                             f"Expected EXIT_BLOCK(2) for readonly Bash without task. stderr: {r.stderr}")

    def test_readonly_bash_allowed_with_active_task(self):
        """git status with an active task is ALLOWED (rc=0) without projection.

        WHY (T-0082): git commit-ops are exempt from the DISPATCH_REQUIRED
        (runtime projection) gate via _git_commit_exempt
        (loop_enforcement.py:914); with an active task, ALL local git
        operations pass even without a projection — governance records must
        be committable. Non-git readonly commands (ls, pytest, flake8) are
        still fail-closed without a projection, as covered by
        test_ls_passes_in_full_mode / test_pytest_passes_in_full_mode.
        """
        state_with_task = """\
schema_version: 1
project_name: test-full
current_phase: S4-implementation
current_task_id: T-0001
loop_mode: FULL
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=state_with_task,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            r = _run_hook("loop_enforcement.py", root,
                          _bash_input("git status"))
            self.assertEqual(r.returncode, 0,
                             f"Expected EXIT_PASS(0) for git commit-op with active task. stderr: {r.stderr}")

    def test_non_bash_tool_still_requires_target(self):
        """Write/Edit tools without readonly paths should still require task scope."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_project(tmp, state_content=STATE_FULL,
                                 task_files={"T-0001.md": TASK_IN_SCOPE})
            write_input = {"tool_name": "Write",
                           "tool_input": {"file_path": str(root / "docs" / "x.md")}}
            r = _run_hook("loop_enforcement.py", root, write_input)
            self.assertEqual(r.returncode, 2,
                             f"Write outside scope should be BLOCKED. stderr: {r.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
