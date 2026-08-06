"""
test_release.py — T-0098 (D8) 发布/产物体系验收测试（AC-01 ~ AC-04）。

- AC-01 版本同步：pyproject 版本 == git HEAD 版本；CHANGELOG 含 v3.12.25~36 条目；
        test_version_consistency 全绿。
- AC-02 构建产物：真实构建 wheel+sdist（session fixture 一次）；产物清单 + SHA256
        校验和可复验；--dry-run 不落盘。
- AC-03 release 流程：check 失败阻断（mock 质量门失败）；release 证据结构正确
        （.ai/evidence/release/<version>/ 三件套）；dry-run 不写证据。
- AC-04 冒烟：临时 venv 安装 wheel → import 成功（真实或 SKIP 标记）；环境不可用
        （无 pip/venv）→ SKIP 明确标记。

不执行真实发布/上传；release 决策仅生成候选（release-decision.request.json，
status=requested）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import release as rel  # noqa: E402, I001


# ── fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def built_dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """隔离构建一次 wheel + sdist 并生成清单（AC-02/AC-04 共用）。

    独立审查修复（P1-2）：此前真实构建到 dist/（非隔离），测试运行会
    改写真实 dist/，导致 .ai/evidence/release/<version>/ 证据与最终产物
    不一致。现构建到 pytest 临时目录（tmp_path_factory），绝不触碰真实
    dist/ —— 真实产物仅由 scripts/release.py release 生成。
    """
    dist_dir = tmp_path_factory.mktemp("built_dist")
    ok, message = rel.build_artifacts(PROJECT_ROOT, dist_dir)
    assert ok, message
    rel.write_manifest(dist_dir, rel.load_version(PROJECT_ROOT), rel.git_head_commit(PROJECT_ROOT))
    return dist_dir


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """迷你项目根（仅 pyproject.toml），用于隔离 check/release 流程测试。"""
    return _tmp_root_pyproject(tmp_path / "project")


def _tmp_root_pyproject(root: Path) -> Path:
    """迷你项目根（仅 pyproject.toml），用于隔离 check/release 流程测试。"""
    root.mkdir()
    shutil.copy(PROJECT_ROOT / "pyproject.toml", root / "pyproject.toml")
    return root


# ── AC-01: 版本同步 ──────────────────────────────────────────────────────

class TestAC01VersionSync:
    def test_pyproject_version_matches_git_head(self):
        version = rel.load_version(PROJECT_ROOT)
        git_ver = rel.git_head_version(PROJECT_ROOT)
        assert git_ver is not None, "git HEAD 提交信息中无版本号"
        assert version == git_ver, f"pyproject={version} vs git HEAD={git_ver}"

    def test_changelog_has_25_to_36_entries(self):
        content = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for version in ("3.12.36", "3.12.30", "3.12.25"):
            assert f"## v{version}" in content, f"CHANGELOG 缺少 v{version} 条目"
        assert content.index("## v3.12.36") < content.index("## v3.12.25"), (
            "CHANGELOG 条目须按版本降序（v3.12.36 在前）"
        )

    def test_version_consistency_suite_passes(self):
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/test_version_consistency.py"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]


# ── AC-02: 构建产物 + 清单 + 校验和 ──────────────────────────────────────

class TestAC02BuildArtifacts:
    def test_build_produces_wheel_and_sdist(self, built_dist: Path):
        wheels = list(built_dist.glob("*.whl"))
        sdists = list(built_dist.glob("*.tar.gz"))
        assert wheels and sdists, "dist/ 下应同时有 wheel 与 sdist"
        for path in wheels + sdists:
            assert rel.load_version(PROJECT_ROOT) in path.name

    def test_manifest_sha256_recomputable(self, built_dist: Path):
        manifest = json.loads(
            (built_dist / rel.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert manifest["version"] == rel.load_version(PROJECT_ROOT)
        assert manifest["git_commit"] == rel.git_head_commit(PROJECT_ROOT)
        assert manifest["generated_at"]
        assert manifest["artifacts"]
        for art in manifest["artifacts"]:
            path = built_dist / art["name"]
            assert path.exists(), f"清单产物缺失: {art['name']}"
            assert rel.sha256_file(path) == art["sha256"], f"sha256 不可复验: {art['name']}"
            assert path.stat().st_size == art["size_bytes"]

    def test_sha256sums_file_matches_manifest(self, built_dist: Path):
        sums_path = built_dist / rel.SHA256SUMS_NAME
        raw = sums_path.read_bytes()
        assert b"\r" not in raw, "SHA256SUMS 必须 LF 换行（Windows CRLF 会导致 sha256sum -c 失败）"
        sums: dict[str, str] = {}
        for line in raw.decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            sums[name] = digest
        manifest = json.loads(
            (built_dist / rel.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert sums, "SHA256SUMS 为空"
        for art in manifest["artifacts"]:
            assert sums[art["name"]] == art["sha256"], f"SHA256SUMS 与清单不一致: {art['name']}"

    def test_dry_run_writes_nothing(self, tmp_root: Path):
        for command in (rel.cmd_build, rel.cmd_manifest, rel.cmd_release):
            assert command(tmp_root, dry_run=True) == 0
        assert not (tmp_root / "dist").exists(), "--dry-run 不应创建 dist/"
        assert not (tmp_root / ".ai").exists(), "--dry-run 不应创建 .ai/"

    def test_build_tool_missing_clear_error(self, tmp_root: Path, monkeypatch):
        monkeypatch.setattr(rel.importlib.util, "find_spec", lambda name: None)
        ok, message = rel.build_artifacts(tmp_root)
        assert ok is False
        assert "构建工具缺失" in message


# ── AC-03: release 流程（质量门前置 + 证据结构 + dry-run）────────────────

class TestAC03ReleaseFlow:
    def test_check_failure_blocks(self, tmp_root: Path, monkeypatch, capsys):
        monkeypatch.setattr(rel, "step_key_tests", lambda root: (False, "mocked gate failure"))
        assert rel.cmd_check(tmp_root) == 1, "质量门失败必须退出码非 0"
        assert "阻断" in capsys.readouterr().out

    def test_release_blocked_no_evidence(self, tmp_root: Path, monkeypatch):
        monkeypatch.setattr(rel, "step_key_tests", lambda root: (False, "mocked gate failure"))
        monkeypatch.setattr(rel, "git_head_commit", lambda root: "deadbeef12ab")
        assert rel.cmd_release(tmp_root) == 1, "check 失败时 release 必须阻断"
        assert not (tmp_root / ".ai" / "evidence" / "release").exists(), (
            "阻断时不得写 release 证据"
        )
        assert not (tmp_root / "dist").exists(), "阻断时不得构建产物"

    def test_release_evidence_structure(self, tmp_root: Path, monkeypatch):
        for name in rel.PREFLIGHT_STEPS:
            monkeypatch.setattr(rel, f"step_{name}", lambda root: (True, "mocked ok"))
        monkeypatch.setattr(rel, "git_head_commit", lambda root: "deadbeef12ab")
        version = rel.load_version(PROJECT_ROOT)  # T-0100: 跟随 pyproject（不再硬编码）

        def fake_build(root, dist_dir=None):
            dist = dist_dir or (root / "dist")
            dist.mkdir(parents=True, exist_ok=True)
            (dist / f"loop_engine-{version}-py3-none-any.whl").write_bytes(b"fake wheel")
            (dist / f"loop_engine-{version}.tar.gz").write_bytes(b"fake sdist")
            return True, "mocked build ok"

        monkeypatch.setattr(rel, "build_artifacts", fake_build)
        assert rel.cmd_release(tmp_root) == 0

        version_dir = tmp_root / ".ai" / "evidence" / "release" / version
        for name in (rel.DECISION_REQUEST_NAME, rel.MANIFEST_NAME, rel.SHA256SUMS_NAME):
            assert (version_dir / name).exists(), f"release 证据缺失: {name}"

        req = json.loads((version_dir / rel.DECISION_REQUEST_NAME).read_text(encoding="utf-8"))
        for key in ("version", "task_id", "owners", "deadline", "status", "requested_at"):
            assert key in req, f"release-decision.request.json 缺字段: {key}"
        assert req["version"] == version
        assert req["status"] == "requested", "候选决策 status 应为 requested"

        manifest = json.loads((version_dir / rel.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert manifest["git_commit"] == "deadbeef12ab"
        assert len(manifest["artifacts"]) == 2
        sums_text = (version_dir / rel.SHA256SUMS_NAME).read_text(encoding="utf-8")
        for art in manifest["artifacts"]:
            # 清单 path 相对项目根（dist/...），校验和针对真实产物文件可复验
            artifact_path = tmp_root / art["path"]
            assert artifact_path.exists(), f"清单产物缺失: {art['path']}"
            assert rel.sha256_file(artifact_path) == art["sha256"], (
                f"校验和不可复验: {art['name']}"
            )
            assert f"{art['sha256']}  {art['name']}" in sums_text

    def test_release_dry_run_no_evidence(self, tmp_root: Path):
        assert rel.cmd_release(tmp_root, dry_run=True) == 0
        assert not (tmp_root / ".ai").exists(), "--dry-run 不得写 release 证据"
        assert not (tmp_root / "dist").exists(), "--dry-run 不得构建产物"


# ── 独立审查放行条件修复（T-0098 CONDITIONAL_GO 复审）─────────────────────
# P1-1: step_validate_state 必须调用真实校验器（退出码非 0/超时/缺失 → 阻断）；
#       check 增补 SLO 门禁步骤（step_slo_gate）。P2: SHA256SUMS 必须 LF。

class TestReviewFixes:
    def test_preflight_includes_slo_gate(self):
        assert "slo_gate" in rel.PREFLIGHT_STEPS, "check 必须含 SLO 门禁步骤"
        assert callable(getattr(rel, "step_slo_gate", None))

    def test_validate_state_invokes_real_validator(self, tmp_root: Path, monkeypatch):
        """step_validate_state 必须 subprocess 调用真实 validate_state.py。"""
        stub = tmp_root / ".zcode" / "tools" / "validate_state.py"
        stub.parent.mkdir(parents=True)
        stub.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        class FakeProc:
            returncode = 0
            stdout = "[ok] state is usable\n"
            stderr = ""

        def fake_run(args, **kwargs):
            calls.append(list(args))
            assert "validate_state.py" in args[-2], f"未调用真实校验器: {args}"
            assert str(tmp_root) == args[-1]
            assert kwargs.get("timeout"), "必须保留超时"
            return FakeProc()

        monkeypatch.setattr(rel.subprocess, "run", fake_run)
        ok, message = rel.step_validate_state(tmp_root)
        assert ok, message
        assert calls, "未发起校验器 subprocess 调用"

    def test_validate_state_nonzero_blocks(self, tmp_root: Path, monkeypatch):
        stub = tmp_root / ".zcode" / "tools" / "validate_state.py"
        stub.parent.mkdir(parents=True)
        stub.write_text("", encoding="utf-8")

        class FakeProc:
            returncode = 2
            stdout = "[error] state broken\n"
            stderr = ""

        monkeypatch.setattr(rel.subprocess, "run", lambda *a, **k: FakeProc())
        ok, message = rel.step_validate_state(tmp_root)
        assert ok is False, "校验器退出码非 0 必须阻断"
        assert "validate_state.py" in message and "exit=2" in message

    def test_validate_state_rc3_idle_passes(self, tmp_root: Path, monkeypatch):
        """T-0101: 校验器 rc=3（idle 合法阻塞态，current_task_id=null）→ PASS
        并标注"合法阻塞态"，不阻断（真实损坏仍为 rc=2 阻断，见上个测试）。"""
        stub = tmp_root / ".zcode" / "tools" / "validate_state.py"
        stub.parent.mkdir(parents=True)
        stub.write_text("", encoding="utf-8")

        class FakeProc:
            returncode = 3
            stdout = "[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：等待任务发起；state 不可开工）\n"
            stderr = ""

        monkeypatch.setattr(rel.subprocess, "run", lambda *a, **k: FakeProc())
        ok, message = rel.step_validate_state(tmp_root)
        assert ok is True, "校验器 rc=3（idle 合法阻塞态）不得阻断 check"
        assert "rc=3" in message and "idle 合法阻塞态" in message

    def test_check_validate_state_rc3_passes(self, tmp_root: Path, monkeypatch, capsys):
        """T-0101: check 在 idle 稳态（validate_state rc=3）下整体 PASS。"""
        for name in ("version_sync", "validate_state", "compile", "guard_health",
                     "slo_gate", "key_tests", "mutation_gate"):
            if name == "validate_state":
                monkeypatch.setattr(
                    rel, "step_validate_state",
                    lambda root: (True, "rc=3 idle 合法阻塞态（mocked）"))
            else:
                monkeypatch.setattr(rel, f"step_{name}",
                                    lambda root: (True, "mocked ok"))
        assert rel.cmd_check(tmp_root) == 0, "idle 稳态下 check 必须 PASS（7/7 可达）"
        assert "PASS" in capsys.readouterr().out

    def test_validate_state_timeout_blocks(self, tmp_root: Path, monkeypatch):
        stub = tmp_root / ".zcode" / "tools" / "validate_state.py"
        stub.parent.mkdir(parents=True)
        stub.write_text("", encoding="utf-8")

        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=120)

        monkeypatch.setattr(rel.subprocess, "run", boom)
        ok, message = rel.step_validate_state(tmp_root)
        assert ok is False, "校验器超时必须 fail-closed 阻断"
        assert "超时" in message

    def test_validate_state_missing_validator_blocks(self, tmp_root: Path):
        ok, message = rel.step_validate_state(tmp_root)
        assert ok is False, "校验器缺失必须 fail-closed 阻断"
        assert "validate_state.py" in message

    def test_check_validate_state_failure_blocks(self, tmp_root: Path, monkeypatch, capsys):
        monkeypatch.setattr(rel, "step_version_sync", lambda root: (True, "mocked ok"))
        monkeypatch.setattr(rel, "step_validate_state", lambda root: (False, "mocked validator failure"))
        assert rel.cmd_check(tmp_root) == 1, "validate_state 失败时 check 必须阻断"
        assert "阻断" in capsys.readouterr().out

    def test_step_slo_gate_pass_and_block(self, tmp_root: Path, monkeypatch):
        class FakeGate:
            def __init__(self, passed, reason):
                self.passed = passed
                self.reason = reason

        fake = FakeGate(True, "error budget healthy — release allowed")
        monkeypatch.setattr("loop_core.slo_gate.check_slo_gate", lambda *a, **k: fake)
        ok, message = rel.step_slo_gate(tmp_root)
        assert ok and "通过" in message

        fake = FakeGate(False, "ERROR_BUDGET_EXHAUSTED: release frozen")
        ok, message = rel.step_slo_gate(tmp_root)
        assert ok is False, "SLO 门禁 BLOCK 必须阻断 check"
        assert "阻断" in message

    def test_check_slo_gate_failure_blocks(self, tmp_root: Path, monkeypatch, capsys):
        for name in ("version_sync", "validate_state", "compile", "guard_health"):
            monkeypatch.setattr(rel, f"step_{name}", lambda root: (True, "mocked ok"))
        monkeypatch.setattr(rel, "step_slo_gate", lambda root: (False, "mocked slo gate failure"))
        assert rel.cmd_check(tmp_root) == 1, "SLO 门禁失败时 check 必须阻断"
        assert "阻断" in capsys.readouterr().out


# ── AC-04: 冒烟安装（临时 venv → wheel → import；环境不可用 → SKIP）─────

class TestAC04Smoke:
    def test_smoke_venv_real_or_skip(self, built_dist: Path):
        """真实临时 venv 冒烟；环境不可用（无 venv/pip）→ 明确 SKIP。"""
        result = rel.run_smoke(built_dist, rel.load_version(PROJECT_ROOT))
        if result["status"] == "SKIP":
            pytest.skip(f"环境不可用，冒烟标记 SKIP：{result['detail']}")
        assert result["status"] == "PASS", result["detail"]

    def test_wheel_target_install_and_import_real(self, built_dist: Path, tmp_path: Path):
        """venv-less 环境下的真实安装验证：pip --target 安装 wheel → import。"""
        wheel = sorted(built_dist.glob("*.whl"))[-1]
        target = tmp_path / "site"
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps",
             "--disable-pip-version-check", "--target", str(target), str(wheel)],
            capture_output=True, text=True,
        )
        if install.returncode != 0:
            pytest.skip(f"环境不可用：pip --target 安装失败（{install.stderr.strip()[:200]}）")
        # 本机 Python 以 safe_path 构建（忽略 PYTHONPATH/''），故在代码内显式注入安装目录
        code = (
            "import sys; sys.path.insert(0, " + repr(str(target)) + "); "
            "import loop_engine, loop_core; "
            "print(loop_engine.__version__, loop_core.__version__)"
        )
        check = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert check.returncode == 0, check.stderr
        ver_engine, ver_core = check.stdout.strip().split()
        assert ver_engine == rel.load_version(PROJECT_ROOT), "wheel 内 loop_engine 版本不符"
        assert ver_core == rel.load_version(PROJECT_ROOT), "wheel 内 loop_core 版本不符"

    def test_smoke_skip_when_env_unavailable(self, built_dist: Path, tmp_path: Path):
        """venv 创建失败（环境不可用）→ SKIP 且原因明确。"""
        stub = tmp_path / "no_venv_python.py"
        stub.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        result = rel.run_smoke(built_dist, "3.12.36", python=str(stub))
        assert result["status"] == "SKIP"
        assert "环境不可用" in result["detail"]

    def test_smoke_pass_logic_mocked(self, built_dist: Path, monkeypatch):
        """安装→import 全链路逻辑（脚本化子进程）：PASS + 版本一致。"""
        calls: list[list[str]] = []

        class FakeProc:
            def __init__(self, rc, out="", err=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = err

        def fake_run(args, **kwargs):
            calls.append(list(args))
            joined = " ".join(args)
            if "--version" in joined:
                return FakeProc(0, "pip 26.0 from fake env")
            if "install" in joined:
                return FakeProc(0)
            if "-c" in joined:
                return FakeProc(0, "loop_engine 3.12.36\nloop_core 3.12.36\n")
            return FakeProc(0)  # python -m venv ...

        monkeypatch.setattr(rel.subprocess, "run", fake_run)
        result = rel.run_smoke(built_dist, "3.12.36")
        assert result["status"] == "PASS", result["detail"]
        assert any("install" in " ".join(c) for c in calls), "应执行 pip install"

    def test_smoke_skip_no_pip_mocked(self, built_dist: Path, monkeypatch):
        """venv 内无 pip → SKIP 明确标记。"""

        class FakeProc:
            def __init__(self, rc, out="", err=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = err

        def fake_run(args, **kwargs):
            if "--version" in " ".join(args):
                return FakeProc(1, "", "No module named pip")
            return FakeProc(0)

        monkeypatch.setattr(rel.subprocess, "run", fake_run)
        result = rel.run_smoke(built_dist, "3.12.36")
        assert result["status"] == "SKIP"
        assert "pip" in result["detail"]
