# T-0090 D5: 工具执行器 + MCP 客户端 — 设计证据（tool-executor）

> **T-0090 D5 交付物 | 2026-08-01 | developer 子代理 | 任务：G-T-0090-REQUIREMENTS（approved）**

## 1. 借鉴来源

StaffDeck（OpenBMB/StaffDeck）`backend/app/tools/` 工具层（tool_schema /
tool_executor / mcp_client.py 586 行，stdio/http/SSE 三传输），经 T-0086 对标
（`.ai/evidence/T-0086/staffdeck-benchmark.md` D5 + §2.2 工具层）确定落地；
B3 MCP 能力模型（`docs/designs/loop-v4-ai-agent-governance.md` §6.3）的
fail-closed 白名单哲学为执行面约束：

| StaffDeck 机制 | loop-engine 落地 |
|---|---|
| 工具白名单（allowed_skills）+ 租户可见性 | `ToolSpec.allowed_tool_ids` / `allowed_skills` + 执行器级 `allowed_tool_ids`（双闸门，未列出即 NOT_ALLOWED） |
| 错误码体系 | `ErrorCode` 统一枚举：NOT_FOUND / DISABLED / NOT_ALLOWED / TIMEOUT / EXECUTION_ERROR / UNSUPPORTED_TYPE |
| `_StdioSession`（id 匹配响应 + 超时 + 进程退出处理） | `_StdioSession`：JSON-RPC id → Future 映射，reader 线程 + stderr 排空线程 |
| stdio 传输（本地子进程） | 同：stdio 起步，无网络 socket |

解决的问题：治理系统此前无法直接调用外部检查器/工具（D5 差距），只能依赖宿主
会话的 Bash 工具。本模块让治理代码可以按统一契约（白名单 + 超时 + 错误码）执行
本地命令或驱动 MCP stdio 服务器。

## 2. 结构

### 2.1 `loop_core/tool_executor.py`（新增）

- **`ErrorCode`**（str Enum）：`OK` / `NOT_FOUND` / `DISABLED` / `NOT_ALLOWED` /
  `TIMEOUT` / `EXECUTION_ERROR` / `UNSUPPORTED_TYPE`（AC-02 统一错误码）。
- **`ExecutionType`**（str Enum）：`local_command` / `mcp` / `http`。
- **`ToolSpec`**（dataclass）：`tool_id` / `name` / `description` /
  `execution_type` / `timeout_seconds` / `enabled` / 白名单
  （`allowed_tool_ids`、`allowed_skills` + `skill_id`）/ 执行面字段
  （`command`、`mcp_server`+`mcp_tool_name`、`http_url`）。
- **`ToolResult`**（dataclass）：`ok` / `code` / `output` / `error` /
  `duration_ms` / `truncated`，`to_dict()` 供审计序列化。
- **`ToolExecutor`**：
  - `register(spec)` — 重复 tool_id 抛 `ValueError`；
  - `execute(tool_id, args, timeout_seconds=None)` — fail-closed 流水线
    （§3），**永远返回 ToolResult，不向调用方抛领域异常**；
  - `register_handler(execution_type, fn)` — 可扩展执行后端（http 预留）。

### 2.2 本地命令执行

- `build_argv()`：`command` 为 argv 列表（推荐）或带 `{placeholder}` 的模板串
  （`str.format_map` + `_SafeDict` 兜底缺失键 → 字面渲染，再 `shlex.split`）。
  **无 shell 插值**（不经过 shell）。
- `subprocess.run(..., timeout=)`：超时即 kill 子进程（`subprocess.run` 内部
  kill + communicate 排空管道，AC-02c 超时兜底 kill）。
- 输出截断：`truncate_output(text, max_output_chars)`（默认 20_000 字符），
  截断时追加 `...[truncated N chars]` 标记，`ToolResult.truncated` 置位
  （AC-02c 防巨量输出）。
- 非零退出码 → `EXECUTION_ERROR`（携带 exit code + stderr 前 500 字符）。

### 2.3 MCP 后端（经执行器）

- `mcp_sessions` 映射 `server_id → MCPSession`；`ToolSpec(mcp_server, mcp_tool_name)`
  指定目标。`MCPSessionError` 错误码映射：`MCP_TIMEOUT → TIMEOUT`，
  `MCP_ERROR / MCP_CONNECTION_FAILED → EXECUTION_ERROR`。
- 未注册 server → `EXECUTION_ERROR`；`http` 类型本波次注册为显式
  `UNSUPPORTED_TYPE`（可 `register_handler` 覆盖）。

### 2.4 `loop_core/mcp_client.py`（新增）

- **`MCPSessionError`**：携带稳定错误码
  `MCP_TIMEOUT` / `MCP_ERROR` / `MCP_CONNECTION_FAILED`（AC-02）。
- **`_StdioSession`**（对标 StaffDeck）：spawn 子进程（`subprocess.Popen`，
  stdin/stdout/stderr 管道，UTF-8 + errors=replace，行缓冲）；reader 线程按
  JSON-RPC `id` 匹配响应到 `Future`；stderr 排空线程写入有界 deque（
  `_STDERR_TAIL_LINES=50`，管道不堵死、连接失败时带 stderr 尾部诊断）；
  进程退出/EOF → 所有 pending 请求 fail-closed 置 `MCP_CONNECTION_FAILED`
  （不挂起到超时）。
- **`MCPSession`**（高层 API）：`initialize()`（protocolVersion 2024-11-05，
  服务器回显版本不匹配 → fail-closed `MCP_ERROR`；随后发
  `notifications/initialized` 单向通知）→ `list_tools()` → `call_tool()`；
  `call_tool` 结果 `isError=true` → 显式抛 `MCP_ERROR`（不把错误当成功）；
  未 initialize 调用 → `MCP_ERROR`；`close()`/上下文管理器收尾
  （terminate → wait(5s) → kill 兜底）。

## 3. fail-closed 执行流水线（AC-02a）

```
ToolExecutor.execute(tool_id, args)
├── 1. 存在性   spec 未注册                       → NOT_FOUND
├── 2. enabled   spec.enabled=False               → DISABLED
├── 3. 白名单   执行器级 allowed_tool_ids（配置即 fail-closed）
│               tool_id 未列出                     → NOT_ALLOWED
│               spec.allowed_tool_ids 未含 tool_id → NOT_ALLOWED
│               spec.allowed_skills 未含 skill_id → NOT_ALLOWED
├── 4. 类型     handler 缺失（未注册类型）         → UNSUPPORTED_TYPE
├── 5. 超时     spec.timeout_seconds 或调用覆盖    → TIMEOUT（子进程已 kill）
└── 6. 执行     local_command / mcp                 → OK / EXECUTION_ERROR
```

## 4. 安全边界（AC-02c / T-0090 红线）

1. **无真实外部连接**：`mcp_client.py` 只 spawn 本地子进程走 stdio 管道，
   无 socket/urllib/http 导入；测试用 `mock.patch("socket.socket"...)` +
   `socket.create_connection` 断言完整 initialize/list/call 流程零 socket
   调用；源码扫描断言无网络客户端导入。mock server 为本地文件
   （`tests/mcp_mock_server.py`），由 `sys.executable` 启动。
2. **无真实凭据**：实现与测试均无 key/token；测试断言环境中无 `LLM_API_KEY`。
3. **执行面白名单约束**：无白名单配置 → 工具不注册即 NOT_FOUND；配置白名单 →
   未列出即 NOT_ALLOWED；测试覆盖执行器级与 spec 级两条拒绝路径。
4. **超时兜底 kill**：超时后 `subprocess.run` kill 子进程；测试用子进程
   自报 PID 文件 + `tasklist` 断言进程已从系统消失。
5. **输出截断**：超长输出截断 + 标记，防巨量输出。

## 5. 验收映射（AC-02）

| AC 子项 | 证据（测试名，均 PASS） |
|---|---|
| 执行器错误码（AC-02a） | `test_not_found`、`test_disabled`、`test_unsupported_type`、`test_unknown_execution_type_enum_rejected`、`test_duplicate_registration_raises` |
| 白名单拒绝（AC-02a/02c） | `test_not_allowed_executor_whitelist`、`test_not_allowed_spec_whitelist`、`test_allowed_spec_whitelist_passes`、`test_not_allowed_allowed_skills`、`test_allowed_skills_passes` |
| 本地命令成功/失败/超时（AC-02a） | `test_success`、`test_failure_exit_code`、`test_spawn_failure`、`test_timeout_kills_child`、`test_timeout_override_per_call` |
| 输出截断（AC-02c） | `test_output_truncation`、`test_short_output_not_truncated`、`TestTruncate::*` |
| MCP 经执行器（AC-02a） | `test_mcp_call_success`、`test_mcp_tool_iserror_maps_to_execution_error`、`test_mcp_timeout_maps_to_timeout`、`test_mcp_server_not_registered` |
| MCP stdio 全流程（AC-02b） | `TestHandshakeAndFlow::test_initialize`、`test_initialized_notification_sent`（记录文件证明 initialized 通知已发且无 id）、`test_list_tools`、`test_call_tool_echo`、`test_call_tool_add`、`test_call_tool_without_arguments` |
| MCP 错误码（AC-02b） | `test_call_tool_iserror_raises_mcp_error`、`test_unknown_tool_raises_mcp_error`、`test_request_timeout_raises_mcp_timeout`、`test_session_recoverable_after_timeout`、`test_connection_failed_*`（spawn 退出/垃圾输出/中途退出/不存在二进制）、`test_call_before_initialize_raises`、`test_use_after_close_raises`、`test_double_close_safe`、`test_context_manager_closes` |
| 无网络证明（AC-02c） | `test_no_sockets_opened_during_full_flow`、`test_connection_is_local_subprocess_only`、`test_no_network_imports_in_client_source`、`test_no_network_imports_in_executor_source`、`test_protocol_constants` |

## 6. 变更文件

| 文件 | 变更 |
|---|---|
| `loop_core/tool_executor.py` | 新增：ToolSpec / ErrorCode / ToolExecutor（白名单 + 超时 + 错误码 + 截断） |
| `loop_core/mcp_client.py` | 新增：MCPSession / _StdioSession（stdio JSON-RPC，initialize/list/call） |
| `tests/mcp_mock_server.py` | 新增：本地 mock MCP stdio server（echo/add/fail_tool/sleep_tool + 故障模式） |
| `tests/test_tool_executor.py` | 新增：28 个测试（AC-02a/02c 执行器部分） |
| `tests/test_mcp_client.py` | 新增：22 个测试（AC-02b/02c MCP 部分） |
| `.ai/evidence/T-0090/tool-executor/design.md` | 本文档 |
