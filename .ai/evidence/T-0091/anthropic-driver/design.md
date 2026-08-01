# T-0091 AC-01 — Anthropic Messages 协议驱动（AnthropicMessagesDriver）

- Task: T-0091（B5 自举审计回路接线）
- Gate: G-T-0091-REQUIREMENTS（approved）
- Workstream: anthropic messages driver
- 实现文件: `loop_core/llm/anthropic_driver.py`
- 测试文件: `tests/test_anthropic_driver.py`
- 日期: 2026-07-31

## 1. 背景与目标

T-0090 完成 `loop_core/llm/` 协议驱动抽象（`ProtocolDriver`：complete /
complete_json / stream / cancel + 统一 LLMError 错误族 + 重试/JSON 修复/脱敏/
输出钳制）。T-0091 目标之一：ZCode 宿主的模型 provider 均为 **anthropic kind**
（Messages API），需要新增 Anthropic Messages 协议驱动供自举审计接线使用。

本设计完全复用 T-0090 组件（`errors.py` / `retry.py` / `redaction.py` /
`output_policy.py` / `keys.py` / `json_repair.py` / `protocol_driver.py`），
风格与 `openai_driver.py` 对齐（httpx 懒加载、MockTransport 注入、SSE、
取消、错误映射、脱敏、钳制、空响应重试）。

## 2. 线协议设计

### 2.1 端点与认证

| 项 | 值 |
|----|----|
| 端点 | `POST {base_url}/v1/messages` |
| 默认 base_url | `https://api.anthropic.com`（公开端点，`base_url=` 可覆盖） |
| 认证头 | `x-api-key: <key>` |
| 协议版本头 | `anthropic-version: 2023-06-01`（ZCode 内部 SDK 同款头对） |
| 内容头 | `Content-Type: application/json` |

key 解析复用 `keys.resolve_api_key()`（env 优先：LLM_API_KEY →
DEEPSEEK_API_KEY → OPENAI_API_KEY → ANTHROPIC_API_KEY，仅环境变量，绝不硬编码）。

### 2.2 请求体

```json
{
  "model": "<model>",
  "max_tokens": <operation cap 或显式覆盖>,
  "system": "<system prompt>",          // 可选：role=system 消息提升到顶层
  "messages": [{"role": "user|assistant", "content": "..."}],
  "stream": true|false,
  "temperature": 0.7                     // 可选
}
```

- `max_tokens` 恒有值：`effective_max_tokens(operation, max_tokens)`（操作级
  输出预算，同 T-0090）。
- Messages API 无 system role：入参中 role=system 的消息被提取拼接进顶层
  `system` 字段（`\n` 连接），其余 user/assistant 消息原样透传。
- 全部为 system 消息（无 user/assistant）→ `CONFIGURATION_ERROR`（提前失败，
  不浪费请求）。

### 2.3 非流式响应解析

- 文本：`content[]` 中 `type == "text"` 块的 `text` 拼接（tool_use 等非文本
  块跳过）。
- usage：`usage.input_tokens` / `usage.output_tokens` →
  `Usage(input_tokens, output_tokens, total=input+output)`；字段缺失/非法 →
  `None`（不阻断）。

### 2.4 流式（SSE 事件转换）

解析 `data:` 行（跳过 `event:` / 注释 / 空行 / 不可解析 JSON），按 data JSON
的 `type` 字段分发：

| SSE 事件 | 处理 |
|----------|------|
| `message_start` | 忽略（含 usage 元数据，不影响文本） |
| `content_block_start` / `content_block_stop` / `message_delta` | 忽略 |
| `content_block_delta`（`delta.type == "text_delta"`） | 产出 `delta.text`（空串/None 跳过） |
| `content_block_delta`（thinking_delta / input_json_delta 等） | 跳过（非文本） |
| `error` | 按 `error.type` 映射错误码并抛 LLMError（见 2.5） |
| `message_stop` | 流结束 |
| `ping` / 未知 | 忽略（keep-alive） |

### 2.5 错误映射

HTTP 状态 → 统一错误码（与 openai_driver 完全一致，retryable 语义在
`ErrorCode` 上）：

| 状态 | 错误码 | retryable |
|------|--------|-----------|
| 401 | MODEL_AUTHENTICATION_FAILED | 否 |
| 403 | PERMISSION_DENIED | 否 |
| 404 | MODEL_NOT_FOUND | 否 |
| 408 | TIMEOUT | 是 |
| 429 | RATE_LIMITED | 是 |
| 5xx（含 529 overloaded） | SERVER_ERROR | 是 |
| 其他 4xx | INVALID_RESPONSE | 否 |
| httpx 超时 | TIMEOUT | 是 |
| 传输错误 | CONNECTION_ERROR | 是 |

流式 `error` 事件类型 → 错误码（`_STREAM_ERROR_TYPES`）：authentication_error
→ MODEL_AUTHENTICATION_FAILED、permission_error → PERMISSION_DENIED、
not_found_error → MODEL_NOT_FOUND、rate_limit_error → RATE_LIMITED、
timeout_error → TIMEOUT、api_error/overloaded_error → SERVER_ERROR、
invalid_request_error → INVALID_RESPONSE、未知 → SERVER_ERROR。

重试语义与 openai_driver 一致：retryable 错误按 `RetryPolicy`（指数退避、
max_attempts）重试；401/403/404/INVALID_RESPONSE/CANCELLED 立即失败。
流式首 delta 之前的失败可重试；产出过 delta 之后的失败立即传播（部分流
无法透明重跑）。

## 3. 复用组件

- 空响应重试：空文本（非流式）/ 零 delta 流（流式）走独立 bounded 预算
  `RetryPolicy.empty_response_retries`，耗尽 → `INVALID_RESPONSE`。
- 脱敏：`Redactor` 以已解析 key 种子化；所有错误消息经
  `redactor.safe_fragment()` 构建 —— provider 回显 key 也不会泄漏进异常/日志。
- 输出钳制：请求级 `max_tokens` = 操作预算；响应级 `clamp_output()` 防御性
  截断并标记 `clamped`（complete_json 不钳制文本，保持 JSON 结构完整）。
- 取消：`cancel()` 置位，下一个入口/每个 delta 检查点抛 `CANCELLED`（one-shot）。
- httpx 懒加载（可选依赖，缺失时构造驱动 → CONFIGURATION_ERROR）。

## 4. 测试策略（全 mock，无真实网络）

`tests/test_anthropic_driver.py`：

- httpx.MockTransport handler + fixture 响应（`_messages_response` /
  `_error_response` / `_sse_response` / `_sse_only_error`）。
- autouse 网络守卫：`http.client.HTTPConnection.connect` 与
  `socket.create_connection` 直接抛 AssertionError；记录每次
  `anthropic_driver.httpx.Client` 实例化；`test_no_real_network_calls`
  断言所有 client 均带 transport（MockTransport），且自足地跑一轮
  complete+stream。
- 假 key `sk-test-0123456789abcdef`（测试专用）；扫描证明 llm 包无硬编码
  credential 字面量；`test_driver_without_env_key_raises_key_missing`
  证明 key 只来自环境。

## 5. 验收证据（AC-01）

运行：`python -m pytest tests/test_anthropic_driver.py tests/test_llm_layer.py -q`

**90 passed in 0.63s**（anthropic_driver 38 项 + llm_layer 52 项，无回归）。

关键用例（AC 映射）：

| AC | 测试 | 结果 |
|----|------|------|
| AC-01 | `test_complete_returns_text_usage_and_anthropic_headers` | PASS（x-api-key / anthropic-version 头 + 文本 + usage） |
| AC-01 | `test_complete_lifts_system_prompt_to_top_level_field` | PASS（system 顶层字段） |
| AC-01 | `test_stream_yields_fragments_from_sse_events` | PASS（message_start → delta → message_stop） |
| AC-01 | `test_stream_skips_ping_and_non_text_deltas` | PASS（ping/thinking/input_json/null 跳过） |
| AC-01 | `test_stream_error_event_maps_authentication_error` | PASS（SSE error 事件 → 错误码，不重试） |
| AC-01 | `test_stream_error_event_overloaded_retried_then_succeeds` | PASS（overloaded → SERVER_ERROR 重试后成功） |
| AC-01 | `test_401_auth_failed_never_retried` / `test_403_permission_denied_never_retried` | PASS |
| AC-01 | `test_429_rate_limited_is_retried_then_succeeds` / `test_persistent_429_...` | PASS（指数退避 0.5） |
| AC-01 | `test_408_maps_to_timeout_and_is_retried` / `test_500_server_error_retried_twice_then_succeeds` | PASS（退避 0.5, 1.0） |
| AC-01 | `test_httpx_timeout_is_retried_then_succeeds` / `test_connect_error_maps_to_connection_error` | PASS |
| AC-01 | `test_empty_response_retried_with_bounded_budget` / `test_persistent_empty_response_raises_invalid_response` | PASS |
| AC-01 | `test_error_message_redacts_key_echoed_by_provider` / `test_stream_error_message_redacts_...` | PASS（key 不进异常/序列化） |
| AC-01 | `test_complete_applies_request_cap_and_post_clamp` / `test_explicit_max_tokens_overrides_operation_cap` | PASS |
| AC-01 | `test_cancel_raises_cancelled_then_one_shot_clears` / `test_stream_cancel_midstream_raises_cancelled` | PASS |
| AC-01 | `test_protocol_driver_contract_is_satisfied` | PASS（isinstance ProtocolDriver，name=anthropic-messages） |
| AC-01 | `test_no_real_network_calls` / `test_no_hardcoded_credentials_in_llm_source` | PASS（无真实网络、无硬编码 key） |

配套：`ruff check` 通过、`tests/test_import_checker.py` 29 passed（懒加载
httpx 不触发 import 检查）、`py_compile` 通过。

## 6. 安全约束落实

- 无硬编码 key；key 仅来自显式注入或环境变量，用后即弃。
- 错误消息/日志全经 Redactor 脱敏（含 provider 回显场景测试证明）。
- 测试零真实网络（socket/http.client 阻断 + MockTransport-only 断言）。
- 本文件/测试断言不含任何内网 baseURL；仅引用公开默认端点
  `https://api.anthropic.com` 与 `anthropic-version: 2023-06-01` 协议值。
