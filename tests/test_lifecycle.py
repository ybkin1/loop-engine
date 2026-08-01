"""
test_lifecycle.py — U9 scripts 生命周期测试（T-0089, AC-04）。

AC-04: 生命周期脚本有测试（up/down/status：pid 文件 + 健康轮询逻辑）。

测试策略（不真实启动长驻服务）:
- fake 目标命令: `python -c "import time; time.sleep(N)"` 短命子进程；
- 假健康探针 FakeProbe（成功/失败序列可编排）经 probe_factory 注入；
- terminate/HTTP 探针路径用 monkeypatch 验证升级逻辑；
- 真实端口仅用于 bind 测试与 fake 进程，不触碰现有服务。
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

import pytest

from scripts import dev

# ── helpers / fakes ────────────────────────────────────────────────────

def _sleep_cmd(seconds: int = 60) -> list[str]:
    """fake 目标命令：短命 sleep 进程（非长驻服务）。"""
    return [sys.executable, "-c", f"import time; time.sleep({seconds})"]


class FakeProbe:
    """可编排的健康探针：按结果序列依次返回，耗尽后返回 default。"""

    def __init__(self, results, default: bool = True) -> None:
        self.results = list(results)
        self.default = default
        self.attempts = 0

    def probe(self) -> bool:
        self.attempts += 1
        if self.results:
            return self.results.pop(0)
        return self.default


def fake_factory(probe):
    """把固定假探针包装成 probe_factory(proc, port, line_queue) 签名。"""

    def _factory(proc, port, line_queue=None):
        return probe

    return _factory


def _spawn_sleep(seconds: int = 30) -> subprocess.Popen:
    return subprocess.Popen(
        _sleep_cmd(seconds), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


# ── AC-04a: up 逻辑 ────────────────────────────────────────────────────

class TestPortSelection:
    def test_find_free_port_in_range(self):
        port = dev.find_free_port((5200, 5206))
        assert 5200 <= port <= 5206
        assert dev.port_available(port)

    def test_find_free_port_skips_occupied(self):
        lo, hi = (5210, 5215)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", lo))
            port = dev.find_free_port((lo, hi))
            assert port == lo + 1
        assert dev.port_available(port)

    def test_find_free_port_exhausted_raises(self):
        lo, hi = (5220, 5222)
        held: list[socket.socket] = []
        try:
            for port in range(lo, hi + 1):
                sock = socket.socket()
                sock.bind(("127.0.0.1", port))
                held.append(sock)
            with pytest.raises(RuntimeError):
                dev.find_free_port((lo, hi))
        finally:
            for sock in held:
                sock.close()


class TestUpPreconditions:
    def test_up_missing_root_fails(self, tmp_path: Path):
        rc = dev.up(tmp_path / "nope", detach=True)
        assert rc == 1
        assert not dev.pid_file(tmp_path / "nope", "dev").exists()

    def test_up_missing_target_file_fails(self, tmp_path: Path):
        rc = dev.up(tmp_path, detach=True, target=[sys.executable, "tools/nope.py"])
        assert rc == 1
        assert not dev.pid_file(tmp_path, "dev").exists()

    def test_up_port_busy_fails(self, tmp_path: Path):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            rc = dev.up(
                tmp_path,
                detach=True,
                target=_sleep_cmd(),
                port=port,
                probe_factory=fake_factory(FakeProbe([True])),
            )
        assert rc == 1
        assert not dev.pid_file(tmp_path, "dev").exists()


class TestUpStart:
    def test_up_writes_pid_and_port_files(self, tmp_path: Path):
        rc = dev.up(
            tmp_path,
            detach=True,
            target=_sleep_cmd(),
            probe_factory=fake_factory(FakeProbe([True])),
        )
        assert rc == 0
        pfile = dev.pid_file(tmp_path, "dev")
        assert pfile.exists()
        pid = int(pfile.read_text(encoding="utf-8").strip())
        assert dev.process_alive(pid)
        port = int(dev.port_file(tmp_path, "dev").read_text(encoding="utf-8").strip())
        assert 5173 <= port <= 5199
        state = json.loads(dev.state_file(tmp_path, "dev").read_text(encoding="utf-8"))
        assert state["pid"] == pid
        assert state["port"] == port
        assert state["mode"] == "detached"
        assert state["command"] == _sleep_cmd()
        assert dev.down(tmp_path) == 0
        assert not pfile.exists()

    def test_up_health_timeout_terminates_and_cleans(self, tmp_path: Path, monkeypatch):
        spawned: list[subprocess.Popen] = []
        orig = dev.start_target

        def spy(command, *, cwd, detach, log_path):
            proc = orig(command, cwd=cwd, detach=detach, log_path=log_path)
            spawned.append(proc)
            return proc

        monkeypatch.setattr(dev, "start_target", spy)
        rc = dev.up(
            tmp_path,
            detach=True,
            target=_sleep_cmd(),
            probe_factory=fake_factory(FakeProbe([], default=False)),
            timeout=0.4,
            interval=0.05,
            kill_grace=1.0,
        )
        assert rc == 1
        assert len(spawned) == 1
        assert not dev.process_alive(spawned[0].pid)
        assert not dev.pid_file(tmp_path, "dev").exists()
        assert not dev.port_file(tmp_path, "dev").exists()
        assert not dev.state_file(tmp_path, "dev").exists()

    def test_up_already_running_idempotent(self, tmp_path: Path, monkeypatch):
        spawned: list[subprocess.Popen] = []
        orig = dev.start_target

        def spy(command, *, cwd, detach, log_path):
            proc = orig(command, cwd=cwd, detach=detach, log_path=log_path)
            spawned.append(proc)
            return proc

        monkeypatch.setattr(dev, "start_target", spy)
        assert (
            dev.up(
                tmp_path,
                detach=True,
                target=_sleep_cmd(),
                probe_factory=fake_factory(FakeProbe([True])),
            )
            == 0
        )
        pid1 = dev.read_pid(tmp_path, "dev")
        assert dev.up(
            tmp_path,
            detach=True,
            target=_sleep_cmd(),
            probe_factory=fake_factory(FakeProbe([True])),
        ) == 0
        assert len(spawned) == 1  # 第二次 up 未再启动进程
        assert dev.read_pid(tmp_path, "dev") == pid1
        assert dev.down(tmp_path) == 0

    def test_up_cleans_stale_then_starts(self, tmp_path: Path):
        dev.write_runtime_files(tmp_path, "dev", 999999, 5173, ["x"], None, True)
        assert (
            dev.up(
                tmp_path,
                detach=True,
                target=_sleep_cmd(),
                probe_factory=fake_factory(FakeProbe([True])),
            )
            == 0
        )
        pid = dev.read_pid(tmp_path, "dev")
        assert pid is not None and pid != 999999
        assert dev.process_alive(pid)
        assert dev.down(tmp_path) == 0


class TestHealthPolling:
    def test_wait_healthy_retries_until_success(self):
        probe = FakeProbe([False, False, True])
        attempts = dev.wait_healthy(probe, timeout=30.0, interval=0.0)
        assert attempts == 3
        assert probe.attempts == 3

    def test_wait_healthy_times_out(self):
        probe = FakeProbe([], default=False)
        with pytest.raises(dev.HealthTimeoutError):
            dev.wait_healthy(probe, timeout=0.3, interval=0.05)
        assert probe.attempts >= 1

    def test_http_probe(self, monkeypatch):
        class _FakeResponse:
            def __init__(self, status: int) -> None:
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(url, timeout=0):
            if url == "http://ok/health":
                return _FakeResponse(200)
            if url == "http://nocontent/health":
                return _FakeResponse(204)
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(dev.urllib.request, "urlopen", fake_urlopen)
        assert dev.HttpProbe("http://ok/health", timeout=0.1).probe() is True
        assert dev.HttpProbe("http://nocontent/health", timeout=0.1).probe() is True
        assert dev.HttpProbe("http://dead/health", timeout=0.1).probe() is False

    def test_http_probe_non_2xx_is_unhealthy(self, monkeypatch):
        def fake_urlopen(url, timeout=0):
            raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)

        monkeypatch.setattr(dev.urllib.request, "urlopen", fake_urlopen)
        assert dev.HttpProbe("http://x/health", timeout=0.1).probe() is False

    def test_alive_probe_requires_survival_window(self):
        class _FakeProc:
            def poll(self):
                return None

        probe = dev.AliveProbe(_FakeProc(), min_life=0.2)
        assert probe.probe() is False  # 存活窗口未过，不判健康
        time.sleep(0.3)
        assert probe.probe() is True

    def test_alive_probe_false_when_dead(self):
        class _FakeProc:
            def poll(self):
                return 1

        assert dev.AliveProbe(_FakeProc()).probe() is False

    def test_stdio_ping_probe_success(self):
        resp = '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}'
        code = f"import sys\nfor _ in sys.stdin:\n    print({resp!r}, flush=True)\n"
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            probe = dev.StdioPingProbe(proc)
            assert probe.probe() is True  # JSON-RPC ping 得到 result
            assert probe.probe() is True  # 可重复探测
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_stdio_ping_probe_dead_process(self):
        proc = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        proc.wait(timeout=5)
        probe = dev.StdioPingProbe(proc)
        assert probe.probe() is False


# ── AC-04b: down 逻辑 ──────────────────────────────────────────────────

class TestDown:
    def test_down_terminates_running_process(self, tmp_path: Path):
        assert (
            dev.up(
                tmp_path,
                detach=True,
                target=_sleep_cmd(),
                probe_factory=fake_factory(FakeProbe([True])),
            )
            == 0
        )
        pid = dev.read_pid(tmp_path, "dev")
        assert dev.process_alive(pid)
        assert dev.down(tmp_path) == 0
        assert not dev.process_alive(pid)
        assert not dev.pid_file(tmp_path, "dev").exists()
        assert not dev.port_file(tmp_path, "dev").exists()
        assert not dev.state_file(tmp_path, "dev").exists()
        assert dev.log_file(tmp_path, "dev").exists()  # 日志保留作诊断历史

    def test_down_stale_pid_cleans_files(self, tmp_path: Path):
        dev.write_runtime_files(tmp_path, "dev", 999999, 5173, ["x"], None, True)
        assert dev.down(tmp_path) == 0
        assert not dev.pid_file(tmp_path, "dev").exists()
        assert not dev.port_file(tmp_path, "dev").exists()
        assert not dev.state_file(tmp_path, "dev").exists()

    def test_down_no_pid_file_is_noop(self, tmp_path: Path):
        assert dev.down(tmp_path) == 0

    def test_terminate_process_graceful_path_no_force(self, monkeypatch):
        calls = {"graceful": [], "force": []}
        monkeypatch.setattr(dev, "_graceful_kill", lambda pid: calls["graceful"].append(pid) or True)
        monkeypatch.setattr(dev, "_wait_pid_exit", lambda pid, t, i: True)
        monkeypatch.setattr(dev, "_force_kill", lambda pid: calls["force"].append(pid))
        assert dev.terminate_process(1234, grace=1.0) is True
        assert calls["graceful"] == [1234]
        assert calls["force"] == []

    def test_terminate_process_escalates_to_force_after_grace(self, monkeypatch):
        calls = {"graceful": [], "force": []}
        monkeypatch.setattr(dev, "_graceful_kill", lambda pid: calls["graceful"].append(pid) or True)
        monkeypatch.setattr(dev, "_wait_pid_exit", lambda pid, t, i: False)
        monkeypatch.setattr(dev, "_force_kill", lambda pid: calls["force"].append(pid))
        monkeypatch.setattr(dev, "process_alive", lambda pid: False)
        assert dev.terminate_process(1234, grace=1.0) is True
        assert calls["graceful"] == [1234]
        assert calls["force"] == [1234]

    def test_terminate_process_reports_force_failure(self, monkeypatch):
        calls = {"force": []}
        monkeypatch.setattr(dev, "_graceful_kill", lambda pid: True)
        monkeypatch.setattr(dev, "_wait_pid_exit", lambda pid, t, i: False)
        monkeypatch.setattr(dev, "_force_kill", lambda pid: calls["force"].append(pid))
        monkeypatch.setattr(dev, "process_alive", lambda pid: True)
        assert dev.terminate_process(1234, grace=1.0) is False
        assert calls["force"] == [1234]

    def test_terminate_process_skips_wait_when_not_delivered(self, monkeypatch):
        waited: list = []
        monkeypatch.setattr(dev, "_graceful_kill", lambda pid: False)
        monkeypatch.setattr(dev, "_wait_pid_exit", lambda pid, t, i: waited.append(1) or True)
        monkeypatch.setattr(dev, "_force_kill", lambda pid: None)
        monkeypatch.setattr(dev, "process_alive", lambda pid: False)
        assert dev.terminate_process(1234, grace=1.0) is True
        assert waited == []  # 优雅信号未投递（Windows 控制台进程）→ 跳过宽限等待

    def test_terminate_process_real_process(self):
        proc = _spawn_sleep(30)
        pid = proc.pid
        time.sleep(0.3)
        assert dev.process_alive(pid)
        assert dev.terminate_process(pid, grace=1.0) is True
        assert not dev.process_alive(pid)


# ── AC-04c: status 逻辑 ────────────────────────────────────────────────

class TestStatus:
    def test_status_stopped_when_no_pid_file(self, tmp_path: Path):
        state, details = dev.status(tmp_path)
        assert state == "stopped"
        assert details["pid"] is None

    def test_status_running_when_alive_and_healthy(self, tmp_path: Path):
        assert (
            dev.up(
                tmp_path,
                detach=True,
                target=_sleep_cmd(),
                probe_factory=fake_factory(FakeProbe([True])),
            )
            == 0
        )
        state, details = dev.status(tmp_path)
        assert state == "running"
        assert details["pid"] == dev.read_pid(tmp_path, "dev")
        assert details["health"] == "ok"
        assert dev.down(tmp_path) == 0

    def test_status_stale_when_pid_dead(self, tmp_path: Path):
        dev.write_runtime_files(tmp_path, "dev", 999999, 5173, ["x"], None, True)
        state, details = dev.status(tmp_path)
        assert state == "stale"
        assert details["pid"] == 999999

    def test_status_stale_when_pid_malformed(self, tmp_path: Path):
        dev.runtime_dir(tmp_path).mkdir(parents=True)
        dev.pid_file(tmp_path, "dev").write_text("not-a-pid\n", encoding="utf-8")
        state, _ = dev.status(tmp_path)
        assert state == "stale"

    def test_status_stale_when_unhealthy_http(self, tmp_path: Path, monkeypatch):
        proc = _spawn_sleep(30)
        try:
            dev.write_runtime_files(
                tmp_path, "dev", proc.pid, 5173, ["x"], "http://127.0.0.1:9/health", True
            )
            monkeypatch.setattr(
                dev, "HttpProbe", lambda url, timeout=2.0: FakeProbe([], default=False)
            )
            state, details = dev.status(tmp_path)
            assert state == "stale"
            assert details["health"] == "fail"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_status_running_when_health_skipped(self, tmp_path: Path):
        proc = _spawn_sleep(30)
        try:
            dev.write_runtime_files(
                tmp_path, "dev", proc.pid, 5173, ["x"], "http://127.0.0.1:9/health", True
            )
            state, details = dev.status(tmp_path, check_health=False)
            assert state == "running"
            assert details["health"] == "skipped"
        finally:
            proc.terminate()
            proc.wait(timeout=5)


# ── 目标命令解析 ───────────────────────────────────────────────────────

class TestResolveTarget:
    def test_resolve_target_default(self, tmp_path: Path):
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "server.py").write_text("", encoding="utf-8")
        cmd = dev.resolve_target(None, tmp_path)
        assert cmd[0] == sys.executable
        assert cmd[1] == str(tmp_path / "tools" / "server.py")

    def test_resolve_target_env_override(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("LOOP_DEV_TARGET", "python tools/mcp_agent_runtime.py --serve")
        cmd = dev.resolve_target(None, tmp_path)
        assert cmd == ["python", str(tmp_path / "tools" / "mcp_agent_runtime.py"), "--serve"]

    def test_resolve_target_list_and_empty(self, tmp_path: Path):
        assert dev.resolve_target(["python", "-c", "pass"], tmp_path) == [
            "python",
            "-c",
            "pass",
        ]
        with pytest.raises(ValueError):
            dev.resolve_target("", tmp_path)


# ── CLI 接线 ───────────────────────────────────────────────────────────

class TestCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "scripts/dev.py", *args],
            cwd=dev.PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    def test_cli_status_stopped(self, tmp_path: Path):
        result = self._run("status", "--root", str(tmp_path))
        assert result.returncode == 0
        assert "stopped" in result.stdout

    def test_cli_status_json_stopped(self, tmp_path: Path):
        result = self._run("status", "--root", str(tmp_path), "--json")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["state"] == "stopped"
        assert payload["pid"] is None

    def test_cli_down_no_pid_file(self, tmp_path: Path):
        result = self._run("down", "--root", str(tmp_path))
        assert result.returncode == 0
        assert "未在运行" in result.stdout
