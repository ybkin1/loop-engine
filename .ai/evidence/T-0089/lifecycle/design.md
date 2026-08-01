# U9 生命周期脚本（scripts/dev.py）设计证据

> T-0089（U9）| 2026-08-01 | developer 子代理 | 状态: 已实现 + 测试通过

## 1. 背景与对标

T-0086 staffdeck-benchmark.md 确定 U9：把 StaffDeck `scripts/dev.py` 的
"生命周期管理"模式（up/down/status + detach + pid 文件 + 健康轮询）应用于
loop-engine `scripts/`，为 AutoPlan 产品化提供前置的 dev 生命周期。

StaffDeck 模式（T-0086 证据）：
- 子命令 up/down/status；`--detach` 后台运行
- pid 文件管理进程；`_wait_for_url` 健康轮询（重试 N 次超时报错）
- down 时 SIGTERM → 超时 SIGKILL 升级

## 2. 实现文件

| 文件 | 内容 |
|---|---|
| `scripts/dev.py`（新） | 生命周期 CLI：up / down / status |
| `tests/test_lifecycle.py`（新） | AC-04 测试（38 项，全部通过） |
| 本文件 | 设计证据 |

运行时产物目录：`<root>/.ai/runtime/`（.ai/ 允许路径内）：
- `dev-<name>.pid` — 管理进程 PID
- `dev-<name>.port` — 选定端口
- `dev-<name>.json` — 状态元数据（pid/port/command/health_url/started_at/mode，原子写入）
- `dev-<name>.log` — 进程输出（down 时保留作诊断历史）

## 3. 关键设计决策

### 3.1 目标进程（TARGET_COMMAND 可配置）

- 默认入口：`tools/server.py`（MCP stdio JSON-RPC 服务器，无 HTTP 端口）。
- 优先级：`--target` > 环境变量 `LOOP_DEV_TARGET` > 默认值。
- 字符串命令按 `shlex.split` 切分；相对路径 token 解析为相对项目根；
  前置条件检查"命令中除解释器外首个路径型 token"必须存在（CLI 实测拦截缺失入口）。

### 3.2 健康探测三策略（"HTTP /api/health 或等效"）

| 探针 | 适用 | 语义 |
|---|---|---|
| `HttpProbe` | `--health-url URL`（或 `LOOP_DEV_HEALTH_URL`） | GET 2xx 视为健康（AutoPlan HTTP 服务形态） |
| `StdioPingProbe` | 默认 attached 模式（stdio 目标） | JSON-RPC `tools/list` ping，收到含 result 的响应即健康 —— 对 MCP stdio 服务器是 HTTP 健康检查的"等效"探针 |
| `AliveProbe` | detached 模式无 health-url 时的兜底 | 进程在 `min_life`（默认 1s）存活窗口内持续存活才判健康，避免"启动即退出"被误判 |

`wait_healthy(probe, timeout, interval)`：重试至通过或超时抛
`HealthTimeoutError`；up 收到超时后终止进程并清理全部运行时文件，返回 1。

### 3.3 跨平台进程管理（win32 实测验证）

- **存活检测**：`os.kill(pid, 0)` 在 Windows 上对已死进程**不抛异常**
  （本机实测），不可用；改用 `tasklist /FI "PID eq N" /NH` 输出包含 pid 判断。
- **终止升级**：`terminate_process` = 优雅信号 → 宽限等待（默认 10s）→ 强制终止。
  - POSIX：SIGTERM → grace → SIGKILL。
  - Windows：`taskkill /PID /T`（无 /F 对控制台进程实测返回 255"只能强制终止"）
    → 优雅信号未投递时**跳过宽限等待**直接 `taskkill /F /T`（树级强制），
    down 不因无意义的宽限等待变慢。
- detached 后台：Windows `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`，
  POSIX `start_new_session`；stdin DEVNULL，stdout/stderr 落日志文件。
- attached 前台：stdin 保持管道（供 stdio ping），stdout 经单读者线程
  回显终端 + 落盘 + 供探针消费；`up` 在 `proc.wait()` 上等待，Ctrl+C 触发
  终止 + 清理，返回 130。

### 3.4 端口选择

`find_free_port((5173, 5199))` 取首个可绑定（127.0.0.1 bind 测试）端口；
`--port` / `LOOP_DEV_PORT` 显式指定时校验占用，被占用直接报错返回 1。
测试用临时端口范围（5200-5222），不触碰真实服务。

### 3.5 up 幂等与 stale 清理

- 已运行（pid 存活）→ "已在运行" 跳过启动，返回 0（幂等）。
- pid 文件存在但进程已死/内容损坏 → 清理后全新启动。
- 健康超时 → 终止 + 清理 + 返回 1。

### 3.6 status 三态

| 状态 | 判定 |
|---|---|
| `running` | pid 文件存在 + 进程存活 + 健康通过（HTTP URL 取自状态 JSON；stdio 目标进程存活即健康信号） |
| `stopped` | 无 pid 文件 |
| `stale` | pid 文件存在但进程已死 / 内容损坏 / 健康检查失败 |

`--json` 输出机器可读；`--no-health` 仅按进程存活判定。

### 3.7 安全

- 不处理任何密钥/凭据；仅管理本地 dev 进程与端口。
- 运行时文件全部落在 `.ai/runtime/`（允许路径内），原子写入（tmp + os.replace）。

## 4. AC-04 映射

AC-04：生命周期脚本有测试（up/down/status：pid 文件 + 健康轮询逻辑）。

| AC 项 | 测试覆盖 |
|---|---|
| up：前置检查 | `test_up_missing_root_fails`、`test_up_missing_target_file_fails`、`test_up_port_busy_fails` |
| up：端口选择 | `test_find_free_port_in_range`、`test_find_free_port_skips_occupied`、`test_find_free_port_exhausted_raises` |
| up：pid 写入 | `test_up_writes_pid_and_port_files`（pid/port/json 三文件 + 内容断言） |
| up：健康轮询成功/超时 | `test_wait_healthy_retries_until_success`、`test_wait_healthy_times_out`、`test_up_health_timeout_terminates_and_cleans`、`test_http_probe*`、`test_stdio_ping_probe*`、`test_alive_probe*` |
| up：幂等/stale | `test_up_already_running_idempotent`、`test_up_cleans_stale_then_starts` |
| down：正常终止 | `test_down_terminates_running_process`、`test_terminate_process_real_process` |
| down：SIGTERM→SIGKILL 升级 | `test_terminate_process_graceful_path_no_force`、`test_terminate_process_escalates_to_force_after_grace`、`test_terminate_process_reports_force_failure`、`test_terminate_process_skips_wait_when_not_delivered` |
| down：stale 清理 / 无 pid | `test_down_stale_pid_cleans_files`、`test_down_no_pid_file_is_noop` |
| status：三态 | `test_status_stopped_when_no_pid_file`、`test_status_running_when_alive_and_healthy`、`test_status_stale_when_pid_dead`、`test_status_stale_when_pid_malformed`、`test_status_stale_when_unhealthy_http`、`test_status_running_when_health_skipped` |
| CLI 接线 | `test_cli_status_stopped`、`test_cli_status_json_stopped`、`test_cli_down_no_pid_file`、`test_resolve_target_*` |

测试约束落实：不启动项目真实长驻服务（tools/server.py 等），全部使用
fake 目标命令（`python -c "time.sleep(N)"`）与注入探针；真实端口仅用于
bind 测试。

## 5. 手工 E2E 验证记录（CLI，非测试代码）

1. HTTP detached 全流程（`python -m http.server` + 真实 `--health-url`）：
   `up --detach` → 健康检查通过 → `status` running/health ok → `--json` 输出
   → `down` 已停止 → `status` stopped（仅日志文件保留）。
2. attached + stdio 默认形态（fake stdio 服务器 + 真实 JSON-RPC ping）：
   `up` → pid 文件写入 + 探测响应回显 → `status` running → `down` 正常终止。
3. detached + stdio 目标（进程 0.3s 后自退）：AliveProbe 存活窗口捕获 →
   健康超时 → 报错退出 1 + 运行时文件清理。
4. 缺入口前置条件：`up` 报"目标入口不存在"，退出 1，不产生文件。
5. stale 清理：预写死 pid 文件 → `status` stale → `down` 清理 → `status` stopped。

## 6. 已知限制（文档化）

- detached 模式为 HTTP/网络服务（AutoPlan 产品化形态）设计；stdio MCP 目标
  在 stdin 断开后无法存活，请使用默认 attached 模式。
- pid 复用理论上可能造成误判（dev 工具可接受，已在 status 以健康检查缓解）。
- 测试/开发环境为 win32（Windows 10 + Python 3.12）；POSIX 路径（SIGTERM/
  SIGKILL/start_new_session）经代码注释与单元测试覆盖（monkeypatch 分支），
  未在真实 POSIX 主机上执行。
