#!/usr/bin/env python3
"""
Loop Engine dev 生命周期 — up / down / status（U9 / T-0089）。

对标 StaffDeck scripts/dev.py 的"生命周期管理"模式（up/down/status + detach +
pid 文件 + 健康轮询），为 AutoPlan 产品化提供前置的 dev 生命周期。

用法:
    python scripts/dev.py up [--detach] [--port N] [--target CMD]
                             [--health-url URL] [--no-health]
                             [--timeout SEC] [--interval SEC] [--name NAME]
    python scripts/dev.py down [--grace SEC] [--name NAME]
    python scripts/dev.py status [--no-health] [--json] [--name NAME]

运行时产物（<root>/.ai/runtime/）:
    dev-<name>.pid    管理进程 PID
    dev-<name>.port   选定的端口（默认 5173-5199 范围内取首个空闲端口）
    dev-<name>.log    进程输出（detached 模式直接落盘；attached 模式同时回显终端）
    dev-<name>.json   状态元数据（pid/port/command/health_url/started_at/mode）

目标进程:
    - 默认入口: tools/server.py（MCP stdio JSON-RPC 服务器）。
    - 可通过 --target 或环境变量 LOOP_DEV_TARGET 覆盖（shell 词法切分）。
    - stdio 目标: 健康探测 = JSON-RPC tools/list ping（等效于 HTTP /api/health）。
    - HTTP 目标: 传 --health-url（或 LOOP_DEV_HEALTH_URL），GET 2xx 视为健康。
    - detached 模式为 HTTP/网络服务（AutoPlan 产品化形态）设计：stdio 目标
      在 stdin 断开后无法存活，请使用 attached 模式（默认）运行。

Windows 兼容说明（已在本机 win32 实测验证）:
    - os.kill(pid, 0) 在 Windows 上对已死进程不抛异常，不可用作存活检测；
      process_alive() 改用 tasklist /FI "PID eq N" 判断。
    - taskkill（无 /F）对控制台进程通常返回 255（"只能强制终止"），因此
      terminate_process() 在优雅信号投递失败时跳过宽限等待直接升级 /F /T。

退出码: 0 成功；1 失败（健康轮询超时 / 前置条件不满足 / 启动失败）。
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT_RANGE = (5173, 5199)
DEFAULT_HEALTH_TIMEOUT = 30.0
DEFAULT_HEALTH_INTERVAL = 1.0
DEFAULT_KILL_GRACE = 10.0

_PING_LINE = '{"jsonrpc":"2.0","method":"tools/list","id":1}\n'


# ── 运行时产物路径 ──────────────────────────────────────────────────────

def runtime_dir(root: Path) -> Path:
    """运行时目录：<root>/.ai/runtime/。"""
    return root / ".ai" / "runtime"


def pid_file(root: Path, name: str) -> Path:
    return runtime_dir(root) / f"dev-{name}.pid"


def port_file(root: Path, name: str) -> Path:
    return runtime_dir(root) / f"dev-{name}.port"


def state_file(root: Path, name: str) -> Path:
    return runtime_dir(root) / f"dev-{name}.json"


def log_file(root: Path, name: str) -> Path:
    return runtime_dir(root) / f"dev-{name}.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    """临时文件 + os.replace 原子写入。"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_runtime_files(
    root: Path,
    name: str,
    pid: int,
    port: int,
    command: list[str],
    health_url: str | None,
    detach: bool,
) -> None:
    """写 pid 文件 + 端口文件 + 状态元数据 JSON。"""
    rt = runtime_dir(root)
    rt.mkdir(parents=True, exist_ok=True)
    _atomic_write(pid_file(root, name), f"{pid}\n")
    _atomic_write(port_file(root, name), f"{port}\n")
    state = {
        "schema_version": 1,
        "name": name,
        "pid": pid,
        "port": port,
        "command": command,
        "health_url": health_url or None,
        "started_at": _now_iso(),
        "mode": "detached" if detach else "attached",
    }
    _atomic_write(state_file(root, name), json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def remove_runtime_files(root: Path, name: str) -> None:
    """清理 pid/端口/状态文件（保留日志文件作为诊断历史）。"""
    for path in (pid_file(root, name), port_file(root, name), state_file(root, name)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def read_pid(root: Path, name: str) -> int | None:
    """读取 pid 文件；文件缺失或内容损坏返回 None。"""
    path = pid_file(root, name)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


# ── 进程工具（跨平台） ──────────────────────────────────────────────────

def process_alive(pid: int) -> bool:
    """进程存活检测。

    Windows: tasklist 查询（os.kill(pid, 0) 在 win32 上对已死进程不抛异常，
    实测不可用——见模块 docstring）。POSIX: os.kill(pid, 0) 信号探测。
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True
        ).stdout
        return str(pid) in out.decode("utf-8", errors="replace")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _run_quiet(cmd: list[str]) -> int:
    """执行命令并吞掉输出；返回退出码（异常/超时返回 -1）。"""
    try:
        return subprocess.run(cmd, capture_output=True, timeout=15).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1


def _graceful_kill(pid: int) -> bool:
    """发送优雅终止信号；返回是否成功投递。

    Windows: taskkill（无 /F）发送 WM_CLOSE；控制台进程通常返回 255（只能
    强制终止），此时返回 False 让调用方跳过宽限等待直接升级 /F。
    POSIX: SIGTERM（尽力而为，视为已投递）。
    """
    if os.name == "nt":
        return _run_quiet(["taskkill", "/PID", str(pid), "/T"]) == 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    return True


def _force_kill(pid: int) -> None:
    """强制终止。Windows: taskkill /F /T（树）；POSIX: SIGKILL。"""
    if os.name == "nt":
        _run_quiet(["taskkill", "/F", "/PID", str(pid), "/T"])
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _wait_pid_exit(pid: int, timeout: float, interval: float) -> bool:
    """在宽限期内等待进程退出。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return True
        time.sleep(interval)
    return not process_alive(pid)


def terminate_process(pid: int, grace: float = DEFAULT_KILL_GRACE, interval: float = 0.25) -> bool:
    """终止进程：优雅信号 → 宽限等待 → 强制终止（SIGTERM→SIGKILL 等价语义）。

    优雅信号未能投递（Windows 控制台进程）时跳过宽限等待，立即升级强制终止。
    """
    delivered = _graceful_kill(pid)
    if delivered and _wait_pid_exit(pid, grace, interval):
        return True
    _force_kill(pid)
    return not process_alive(pid)


# ── 端口选择 ───────────────────────────────────────────────────────────

def port_available(port: int) -> bool:
    """端口是否可绑定（127.0.0.1 bind 测试）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def find_free_port(port_range: tuple[int, int] = DEFAULT_PORT_RANGE) -> int:
    """在端口范围内选取首个空闲端口；全部占用时抛 RuntimeError。"""
    lo, hi = port_range
    for port in range(lo, hi + 1):
        if port_available(port):
            return port
    raise RuntimeError(f"端口范围 {lo}-{hi} 全部被占用")


# ── 健康探测 ───────────────────────────────────────────────────────────

class HealthTimeoutError(TimeoutError):
    """健康轮询超过总超时仍未通过。"""


class HttpProbe:
    """HTTP 健康探测：GET 目标 URL，2xx 视为健康。"""

    def __init__(self, url: str, timeout: float = 2.0) -> None:
        self.url = url
        self.timeout = timeout

    def probe(self) -> bool:
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False


def _feed_queue(stream, out_queue: queue.Queue) -> None:
    """后台线程：逐行读取 stream 并放入队列；EOF 时放入 None 哨兵。"""

    def _run() -> None:
        try:
            for line in stream:
                out_queue.put(line)
        finally:
            out_queue.put(None)

    threading.Thread(target=_run, daemon=True).start()


class StdioPingProbe:
    """MCP stdio 等效健康探测：写 JSON-RPC tools/list ping，等待响应行。

    对应 HTTP /api/health 的"等效"探针——tools/server.py 是 stdin/stdout
    JSON-RPC 服务器（无 HTTP 端口），因此以协议层 ping 判定健康。
    """

    def __init__(self, proc, line_queue: queue.Queue | None = None, timeout: float = 5.0) -> None:
        self._proc = proc
        self._timeout = timeout
        if line_queue is None:
            line_queue = queue.Queue()
            _feed_queue(proc.stdout, line_queue)
        self._queue = line_queue

    def probe(self) -> bool:
        if self._proc.poll() is not None:
            return False
        try:
            self._proc.stdin.write(_PING_LINE)
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            return False
        try:
            line = self._queue.get(timeout=self._timeout)
        except queue.Empty:
            return False
        if line is None:
            return False
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            return False
        return "result" in resp and "error" not in resp


class AliveProbe:
    """进程存活探测：detached 模式下 stdio 目标的兜底健康判定。

    要求进程在 min_life 秒内持续存活才判定健康，避免"启动即退出"的进程
    在首次探测时被误判为 healthy。
    """

    def __init__(self, proc, min_life: float = 1.0) -> None:
        self._proc = proc
        self._min_life = min_life
        self._started = time.monotonic()

    def probe(self) -> bool:
        if self._proc.poll() is not None:
            return False
        return time.monotonic() - self._started >= self._min_life


def wait_healthy(probe, timeout: float, interval: float) -> int:
    """健康轮询：重试直至通过或超时。返回通过时的探测次数。

    超时抛 HealthTimeoutError（TimeoutError 子类）。
    """
    deadline = time.monotonic() + timeout
    attempts = 0
    while True:
        attempts += 1
        if probe.probe():
            return attempts
        if time.monotonic() >= deadline:
            raise HealthTimeoutError(f"健康检查在 {int(timeout)}s 内未通过（共 {attempts} 次探测）")
        time.sleep(interval)


# ── 目标命令解析 ───────────────────────────────────────────────────────

def _looks_like_path(token: str) -> bool:
    return (
        os.sep in token
        or (os.altsep is not None and os.altsep in token)
        or token.startswith((".", "/", "\\"))
    )


def resolve_target(target_arg, root: Path) -> list[str]:
    """解析目标命令。优先级: --target > LOOP_DEV_TARGET > 默认 tools/server.py。

    字符串按 shell 词法切分（shlex.split）；相对路径 token 解析为相对项目根；
    返回可直接交给 subprocess.Popen 的命令列表。
    """
    if target_arg is None:
        target_arg = os.environ.get("LOOP_DEV_TARGET")
    if target_arg is None:
        command = [sys.executable, str(root / "tools" / "server.py")]
    elif isinstance(target_arg, str):
        command = shlex.split(target_arg)
    else:
        command = [str(tok) for tok in target_arg]
    if not command:
        raise ValueError("目标命令为空")
    for i, tok in enumerate(command):
        if _looks_like_path(tok) and not os.path.isabs(tok):
            command[i] = str(root / tok)
    return command


def start_output_monitor(proc, log_path: Path, echo: bool) -> queue.Queue | None:
    """attached 模式输出监视：单读者线程回显终端并落盘日志，同时把每一行
    放入队列供 StdioPingProbe 消费。proc.stdout 为 None（detached）时返回 None。

    注意: 必须只有这一个读者线程消费 stdout，否则管道行会被拆分。
    """
    if proc.stdout is None:
        return None
    out_queue: queue.Queue = queue.Queue()

    def _run() -> None:
        fh = open(log_path, "a", encoding="utf-8", errors="replace")
        try:
            for line in proc.stdout:
                if echo:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                fh.write(line)
                fh.flush()
                out_queue.put(line)
        finally:
            fh.close()
            out_queue.put(None)

    threading.Thread(target=_run, daemon=True).start()
    return out_queue


def default_probe_factory(
    proc, port: int, line_queue: queue.Queue | None = None, *, health_url: str | None = None, detach: bool = False
):
    """默认探针选择:
    1. --health-url → HttpProbe（HTTP GET 2xx）。
    2. detached 或 stdio 管道不可用 → AliveProbe（进程存活兜底）。
    3. 否则 → StdioPingProbe（MCP stdio JSON-RPC ping，HTTP 的等效探针）。
    """
    del port  # 保留参数位以统一 probe_factory 签名
    if health_url:
        return HttpProbe(health_url)
    if detach or line_queue is None:
        return AliveProbe(proc)
    return StdioPingProbe(proc, line_queue)


def start_target(
    command: list[str], *, cwd: Path, detach: bool, log_path: Path
) -> subprocess.Popen:
    """启动目标进程。

    - detach: 后台运行。Windows 用 CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS，
      POSIX 用 start_new_session；stdin 接 DEVNULL，stdout/stderr 追加写日志。
    - attached: 前台运行。stdin 保持管道（供 stdio 健康探测），stdout/stderr
      走管道由 start_output_monitor 回显终端并落盘。
    """
    if detach:
        log_handle = open(log_path, "ab")
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        try:
            return subprocess.Popen(command, cwd=str(cwd), text=True, **kwargs)
        except BaseException:
            log_handle.close()
            raise
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


# ── 子命令实现（可直接单测） ───────────────────────────────────────────

def up(
    root: Path,
    *,
    name: str = "dev",
    detach: bool = False,
    port: int | None = None,
    target=None,
    health_url: str | None = None,
    timeout: float = DEFAULT_HEALTH_TIMEOUT,
    interval: float = DEFAULT_HEALTH_INTERVAL,
    kill_grace: float = DEFAULT_KILL_GRACE,
    no_health: bool = False,
    probe_factory=None,
    log=None,
) -> int:
    """启动目标进程并健康轮询。返回退出码（0 成功 / 1 失败）。

    probe_factory 签名: probe_factory(proc, port, line_queue) -> probe，
    测试注入假探针（默认按 default_probe_factory 规则选择）。
    """
    log = log or print
    root = Path(root).resolve()
    if not root.is_dir():
        log(f"[dev] up: 错误: 项目根目录不存在: {root}")
        return 1
    try:
        command = resolve_target(target, root)
    except ValueError as exc:
        log(f"[dev] up: 错误: {exc}")
        return 1
    # 前置条件: 目标入口文件存在（命令中除解释器外首个路径型 token）
    path_tokens = [tok for tok in command[1:] if os.path.isabs(tok)]
    if path_tokens and not Path(path_tokens[0]).is_file():
        log(f"[dev] up: 错误: 目标入口不存在: {path_tokens[0]}")
        return 1
    # 前置条件: 已有实例幂等 / stale 清理
    runtime_dir(root).mkdir(parents=True, exist_ok=True)
    if pid_file(root, name).exists():
        existing = read_pid(root, name)
        if existing is not None and existing > 0 and process_alive(existing):
            log(f"[dev] up: 已在运行 (pid={existing})，跳过启动。")
            return 0
        log("[dev] up: 清理 stale 状态文件。")
        remove_runtime_files(root, name)
    # 前置条件: 端口
    if port is not None:
        if not port_available(port):
            log(f"[dev] up: 错误: 端口 {port} 已被占用。")
            return 1
    else:
        try:
            port = find_free_port()
        except RuntimeError as exc:
            log(f"[dev] up: 错误: {exc}")
            return 1
    # 启动
    log_path = log_file(root, name)
    try:
        proc = start_target(command, cwd=root, detach=detach, log_path=log_path)
    except OSError as exc:
        log(f"[dev] up: 错误: 启动失败: {exc}")
        return 1
    write_runtime_files(root, name, proc.pid, port, command, health_url, detach)
    log(f"[dev] up: 已启动 pid={proc.pid} port={port}（状态文件: {runtime_dir(root)}）")
    try:
        # 健康轮询
        if not no_health:
            line_queue = start_output_monitor(proc, log_path, echo=not detach)
            factory = probe_factory or (
                lambda p, pt, lq: default_probe_factory(
                    p, pt, lq, health_url=health_url, detach=detach
                )
            )
            probe = factory(proc, port, line_queue)
            try:
                attempts = wait_healthy(probe, timeout=timeout, interval=interval)
            except HealthTimeoutError as exc:
                log(f"[dev] up: 健康检查超时: {exc}")
                log("[dev] up: 正在终止进程并清理…")
                terminate_process(proc.pid, grace=kill_grace)
                remove_runtime_files(root, name)
                log("[dev] up: 启动失败（健康检查未通过）。")
                return 1
            log(f"[dev] up: 健康检查通过（第 {attempts} 次探测）。")
        # 结果与前台等待
        mode_desc = "detached" if detach else "attached（Ctrl+C 停止）"
        log(f"[dev] up: running — pid={proc.pid} port={port} mode={mode_desc}")
        if detach:
            return 0
        try:
            rc = proc.wait()
        except KeyboardInterrupt:
            log("\n[dev] up: 收到 Ctrl+C，正在停止…")
            terminate_process(proc.pid, grace=kill_grace)
            remove_runtime_files(root, name)
            return 130
        remove_runtime_files(root, name)
        log(f"[dev] up: 进程已退出 (code={rc})。")
        return rc if rc else 0
    except KeyboardInterrupt:
        log("\n[dev] up: 收到 Ctrl+C，正在停止…")
        terminate_process(proc.pid, grace=kill_grace)
        remove_runtime_files(root, name)
        return 130


def down(root: Path, *, name: str = "dev", grace: float = DEFAULT_KILL_GRACE, log=None) -> int:
    """停止目标进程：pid 文件 → 优雅终止 → 超时强制终止 → 清理产物。"""
    log = log or print
    root = Path(root).resolve()
    if not pid_file(root, name).exists():
        log("[dev] down: 未在运行（无 pid 文件）。")
        return 0
    pid = read_pid(root, name)
    if pid is None:
        log("[dev] down: pid 文件损坏，清理残留文件。")
        remove_runtime_files(root, name)
        return 0
    if not process_alive(pid):
        log(f"[dev] down: stale pid（进程 {pid} 不存在），清理残留文件。")
        remove_runtime_files(root, name)
        return 0
    log(f"[dev] down: 正在终止 pid={pid} …")
    ok = terminate_process(pid, grace=grace)
    remove_runtime_files(root, name)
    if ok:
        log("[dev] down: 已停止。")
    else:
        log(f"[dev] down: 警告: 进程 {pid} 可能仍在运行（强制终止失败）。")
    return 0


def status(root: Path, *, name: str = "dev", check_health: bool = True) -> tuple[str, dict]:
    """查询运行状态，返回 (状态, 详情)。

    三态: running（进程存活且健康）/ stopped（无 pid 文件）/ stale（pid
    文件存在但进程已死、内容损坏或健康检查失败）。
    """
    root = Path(root).resolve()
    details: dict = {
        "name": name,
        "pid": None,
        "port": None,
        "health": "n/a",
        "started_at": None,
        "command": None,
        "mode": None,
    }
    if not pid_file(root, name).exists():
        return "stopped", details
    pid = read_pid(root, name)
    if pid is None or pid <= 0:
        return "stale", details
    details["pid"] = pid
    pfile = port_file(root, name)
    if pfile.exists():
        try:
            details["port"] = int(pfile.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
    health_url: str | None = None
    sfile = state_file(root, name)
    if sfile.exists():
        try:
            state = json.loads(sfile.read_text(encoding="utf-8"))
            details["started_at"] = state.get("started_at")
            details["command"] = state.get("command")
            details["mode"] = state.get("mode")
            health_url = state.get("health_url")
        except (OSError, json.JSONDecodeError):
            pass
    if not process_alive(pid):
        return "stale", details
    if check_health:
        if health_url:
            details["health"] = "ok" if HttpProbe(health_url).probe() else "fail"
            if details["health"] == "fail":
                return "stale", details
        else:
            # stdio 目标无 HTTP 健康端点: 进程存活即健康信号
            details["health"] = "ok"
    else:
        details["health"] = "skipped"
    return "running", details


# ── CLI ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description="Loop Engine dev 生命周期 — up / down / status（U9 / T-0089）",
    )
    parser.add_argument(
        "--root", default=str(PROJECT_ROOT), help="项目根目录（默认: 脚本上级目录）"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_up = sub.add_parser("up", help="启动目标进程（默认前台，--detach 后台）")
    p_up.add_argument(
        "--root", default=argparse.SUPPRESS, help="项目根目录（默认: 脚本上级目录）"
    )
    p_up.add_argument("--detach", action="store_true", help="后台运行（stdio 目标请用前台模式）")
    p_up.add_argument("--port", type=int, default=None, help="指定端口（默认自动选择 5173-5199 空闲端口）")
    p_up.add_argument(
        "--target", default=None, help="目标命令（或 LOOP_DEV_TARGET；默认: python tools/server.py）"
    )
    p_up.add_argument("--health-url", default=None, help="HTTP 健康检查 URL（GET 2xx 视为健康）")
    p_up.add_argument("--no-health", action="store_true", help="跳过健康轮询")
    p_up.add_argument("--timeout", type=float, default=DEFAULT_HEALTH_TIMEOUT, help="健康轮询总超时秒数")
    p_up.add_argument("--interval", type=float, default=DEFAULT_HEALTH_INTERVAL, help="健康轮询间隔秒数")
    p_up.add_argument("--kill-grace", type=float, default=DEFAULT_KILL_GRACE, help="终止宽限秒数，超时强制终止")
    p_up.add_argument("--name", default=None, help="实例名（默认 dev；或 LOOP_DEV_NAME）")

    p_down = sub.add_parser("down", help="停止目标进程")
    p_down.add_argument(
        "--root", default=argparse.SUPPRESS, help="项目根目录（默认: 脚本上级目录）"
    )
    p_down.add_argument("--grace", type=float, default=DEFAULT_KILL_GRACE, help="终止宽限秒数，超时强制终止")
    p_down.add_argument("--name", default=None, help="实例名（默认 dev；或 LOOP_DEV_NAME）")

    p_status = sub.add_parser("status", help="查询运行状态（running/stopped/stale）")
    p_status.add_argument(
        "--root", default=argparse.SUPPRESS, help="项目根目录（默认: 脚本上级目录）"
    )
    p_status.add_argument("--no-health", action="store_true", help="跳过健康检查（仅按进程存活判定）")
    p_status.add_argument("--json", action="store_true", help="输出 JSON")
    p_status.add_argument("--name", default=None, help="实例名（默认 dev；或 LOOP_DEV_NAME）")
    return parser


def _env_int(key: str) -> int | None:
    raw = os.environ.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def cmd_up(root: Path, args: argparse.Namespace, name: str) -> int:
    port = args.port if args.port is not None else _env_int("LOOP_DEV_PORT")
    health_url = args.health_url or os.environ.get("LOOP_DEV_HEALTH_URL") or None
    return up(
        root,
        name=name,
        detach=args.detach,
        port=port,
        target=args.target,
        health_url=health_url,
        timeout=args.timeout,
        interval=args.interval,
        kill_grace=args.kill_grace,
        no_health=args.no_health,
    )


def cmd_down(root: Path, args: argparse.Namespace, name: str) -> int:
    return down(root, name=name, grace=args.grace)


def cmd_status(root: Path, args: argparse.Namespace, name: str) -> int:
    state, details = status(root, name=name, check_health=not args.no_health)
    if args.json:
        print(json.dumps({"state": state, **details}, ensure_ascii=False))
        return 0
    print(f"[dev] status: {state}")
    if details["pid"] is not None:
        print(f"  pid: {details['pid']}")
    if details["port"] is not None:
        print(f"  port: {details['port']}")
    if details["health"] != "n/a":
        print(f"  health: {details['health']}")
    if details["started_at"]:
        print(f"  started_at: {details['started_at']}")
    if details["command"]:
        print(f"  command: {' '.join(details['command'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # 避免中文输出在 GBK 控制台/管道下崩溃或乱码
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    args = build_parser().parse_args(argv)
    root = Path(getattr(args, "root", PROJECT_ROOT)).resolve()
    name = args.name or os.environ.get("LOOP_DEV_NAME") or "dev"
    if args.command == "up":
        return cmd_up(root, args, name)
    if args.command == "down":
        return cmd_down(root, args, name)
    return cmd_status(root, args, name)


if __name__ == "__main__":
    raise SystemExit(main())
