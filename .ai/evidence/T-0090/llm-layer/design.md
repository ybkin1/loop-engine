# T-0090 D1 — LLM 接入抽象层设计证据

| 字段 | 值 |
|------|-----|
| task_id | T-0090 |
| workstream | D1: LLM access abstraction layer |
| gate | G-T-0090-REQUIREMENTS (approved) |
| 设计来源 | T-0086 staffdeck-benchmark.md D1 差距（llm/client.py 1396 行 + protocol_drivers.py 521 行 + output_policy.py 模式） |
| 前置动机 | B5 自举审计回路（docs/designs/loop-v4-ai-agent-governance.md §2.4/§3.4 judge 模型）：loop-engine 未来需自己调 LLM 做 self-audit，不能依赖宿主 |
| 实现路径 | `loop_core/llm/`（9 个模块）+ `tests/test_llm_layer.py`（52 测试，全 mock） |
| 验收 | AC-01（见下「AC-01 映射」） |

## 1. 目标与边界

- **目标**：为 loop-engine 建立自身 LLM 客户端抽象 —— 协议驱动统一接口（complete/stream）+ OpenAI 兼容驱动 + 统一错误码（retryable）+ 重试 + JSON 修复 + 敏感信息脱敏 + 操作级输出 token 钳制 + key 仅环境变量。
- **边界（安全红线）**：
  - API key 仅从环境变量读取（LLM_API_KEY 优先，其次 DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY），**无硬编码、无默认空 key**（缺失 → 显式 LLMKeyError）。
  - 测试全 mock（httpx.MockTransport + 网络封锁 guard），**不发起真实外部调用**。
  - 运行时默认不连接：提供能力（transport 可注入），连接由后续自举审计任务按需启用。

## 2. 架构

```
loop_core/llm/
├── __init__.py           # 公共 API 再导出（版本 1.0.0）
├── errors.py             # ErrorCode 枚举（retryable 标记）+ LLMError/LLMKeyError/JSONRepairError
├── keys.py               # resolve_api_key() —— 环境变量解析（无默认）
├── redaction.py          # Redactor / make_redactor / safe_fragment（StaffDeck _safe_fragment 风格）
├── json_repair.py        # repair_json() —— 多候选修复管线
├── output_policy.py      # 操作级输出 token 上限表 + clamp_output()
├── retry.py              # RetryPolicy —— 指数退避 + 空响应重试预算
├── protocol_driver.py    # ProtocolDriver 协议（complete/stream/complete_json/cancel）+ 结果类型
└── openai_driver.py      # OpenAICompatibleDriver —— Chat Completions（httpx，懒加载可选依赖）
```

依赖方向：`openai_driver` → {errors, json_repair, keys, output_policy, protocol_driver, redaction, retry}。包内无循环依赖；`loop_core` 其他模块不 import 本包（自举审计接线在后续任务）。

### 2.1 协议驱动接口（protocol_driver.py）

```python
class ProtocolDriver(Protocol):          # runtime_checkable
    name: str
    def complete(...) -> CompletionResult     # 一次性文本生成（含重试/脱敏/钳制）
    def complete_json(...) -> JSONResult       # 生成 + JSON 修复（INVALID_RESPONSE 兜底）
    def stream(...) -> Iterator[str]           # SSE 增量片段（首块前失败可重试）
    def cancel(...) -> None                    # 取消：下一检查点抛 CANCELLED（一次性）
```

结果类型携带审计元数据：`text/model/operation/attempts/usage/clamped/clamp_cap/repair_strategy`。

### 2.2 统一错误码（errors.py）

| ErrorCode | HTTP | retryable | 语义 |
|-----------|------|-----------|------|
| MODEL_AUTHENTICATION_FAILED | 401 | False | key 无效 |
| PERMISSION_DENIED | 403 | False | 无权限 |
| MODEL_NOT_FOUND | 404 | False | 模型不存在 |
| KEY_MISSING | — | False | 环境变量未设置（显式失败，不默认空 key） |
| CONFIGURATION_ERROR | — | False | 缺 httpx / 未指定 model |
| RATE_LIMITED | 429 | **True** | 限流，退避重试 |
| TIMEOUT | 408/超时 | **True** | 超时 |
| SERVER_ERROR | 5xx | **True** | 服务端错误 |
| CONNECTION_ERROR | 网络 | **True** | 连接失败 |
| CANCELLED | — | False | 调用方取消 |
| INVALID_RESPONSE | 其他 4xx/坏响应 | False | 响应不可用（空响应预算耗尽也归此） |

`LLMError` 统一异常：`code / retryable / attempts / operation / status_code / request_id` + `to_dict()` 稳定序列化（供审计事件）。参考 StaffDeck ProtocolCallError。

### 2.3 重试（retry.py + openai_driver）

- 仅 `ErrorCode.retryable` 的码被重试（429/408/5xx/网络）；401/403/404/CANCELLED/INVALID_RESPONSE 立即失败（测试证明 handler 仅被调用 1 次）。
- 指数退避：`delay = min(max_delay, base_delay * factor^(attempt-1))`，可选 jitter；`sleep_fn` 可注入（测试记录延迟序列，验证 `[0.5, 1.0, 2.0]`）。
- **空响应重试（上限可配）**：200 但无 choices/空白内容 → 独立预算 `empty_response_retries`（默认 1，可配）；耗尽 → INVALID_RESPONSE（记录总 attempts）。
- 流式：首块（first_delta）之前失败可重试；已产出部分内容后失败立即上抛（部分流不可透明重跑，已文档化）。

### 2.4 JSON 修复（json_repair.py）

多候选管线，保守优先，返回 `(data, strategy)`：

1. `identity` — 直接解析
2. `trim-fences` — 剥离 ```json 围栏与散文
3. `extract-block` — 提取首个平衡 `{…}`/`[…]`（字符串感知状态机，引号内大括号不计深度）
4. `trailing-commas` — 去尾逗号（重复应用）
5. `extract+trailing-commas` — 提取 + 去尾逗号
6. `control-chars` — 字符串内原始控制字符转义（`\n`→`\\n`、`<0x20`→`\uXXXX`）
7. `unescaped-quotes` — 未转义引号修复（字符串内 `"` 后随非终止符 → 加 `\`，如 `{"a": "he said "hi" ok"}`）
8. `unquoted-keys` — 裸键加引号（`{a: 1}` → `{"a": 1}`，字符串感知）
9. `combo` — 上述全部叠加（在提取块上）

全部失败 → `JSONRepairError`（含 strategies_tried）→ 驱动层转 `LLMError(INVALID_RESPONSE, retryable=False)`。参考 StaffDeck client.py 修复上下文模式。

### 2.5 脱敏（redaction.py）

- `Redactor`：以解析出的 key（+ `LLM_REDACT_SECRETS` 环境变量额外值）播种；`redact()` 替换为 `<REDACTED>`（长值优先、最短 6 字符防误伤）。
- `safe_fragment(payload, max_len)`：字符串化 + 控制字符清理 + 截断（`…`）+ 脱敏 —— 所有错误消息经此构建（StaffDeck `_safe_fragment` 风格）。
- `redact_url()`：清 userinfo 与 key/token/sig 等查询参数；`redact_headers()`：遮 Authorization/x-api-key/cookie。
- 测试覆盖最坏情形：provider 在 401 body 里回显 Authorization 头 —— 异常消息与 `to_dict()` 序列化均不含原始 key。

### 2.6 输出钳制（output_policy.py）

| 操作 | 上限（输出 token） |
|------|------|
| router | 4000 |
| audit | 8000 |
| self-review | 6000 |
| planner | 8000 |
| summarize | 2000 |
| classify | 1000 |
| default（未知操作） | 4000 |

- 请求级：Chat Completions body 的 `max_tokens` 取操作上限（显式传入覆盖）。
- 响应级：`clamp_output()` 防御性后钳制（4 字符 ≈ 1 token 启发式，不依赖厂商 tokenizer），截断并附加 `[clamped: ...]` 标记，`CompletionResult.clamped/clamp_cap` 可审计。
- JSON 结果**不做**文本级后钳制（会破坏结构），仅请求级上限（测试断言 8800 字符 JSON 保持完整可解析）。

### 2.7 key 管理（keys.py）

- 解析顺序：`LLM_API_KEY` → `DEEPSEEK_API_KEY` → `OPENAI_API_KEY` → `ANTHROPIC_API_KEY`（首个非空生效）。
- 缺失 → `LLMKeyError(KEY_MISSING)`，消息列出**变量名**（不列值），**不返回空 key**。
- 驱动懒解析：构造驱动无副作用；测试经 `env` 映射注入假 key 或 monkeypatch.setenv。
- httpx 为可选运行时依赖（懒导入 + CONFIGURATION_ERROR，模式同 scripts/runtime_delivery_gate.py 的 playwright；正式接线自举审计时在 pyproject 声明，本任务允许路径不含 pyproject.toml，故不改）。

## 3. AC-01 映射（测试证据）

`tests/test_llm_layer.py` — 52 测试全通过（pytest 9.0.3, Python 3.12.10, 0.8s）。

| 验收点 | 测试 | 结果 |
|--------|------|------|
| AC-01a 协议驱动接口 | test_driver_complete_returns_text_and_metadata / test_driver_stream_yields_fragments / test_driver_stream_skips_keepalive_and_null_deltas / test_protocol_driver_contract_is_satisfied | PASS |
| AC-01b 错误码+retryable+重试 | test_error_code_family_required_codes_and_retryable_flags / test_429_rate_limited_is_retried_then_succeeds / test_500_server_error_retried_twice_then_succeeds / test_backoff_delays_grow_exponentially / test_persistent_429_raises_rate_limited_with_attempts / test_401_auth_failed_never_retried / test_403_permission_denied_never_retried / test_404_model_not_found_never_retried / test_timeout_is_retried_then_succeeds / test_persistent_timeout_raises_timeout_code / test_connect_error_maps_to_connection_error / test_non_json_provider_body_raises_invalid_response / test_empty_response_retried_with_bounded_budget / test_persistent_empty_response_raises_invalid_response / test_cancel_raises_cancelled_then_one_shot_clears / test_stream_retries_on_first_chunk_failure / test_stream_cancel_midstream_raises_cancelled / test_stream_empty_raises_invalid_response | PASS |
| AC-01c JSON 修复 | test_repair_json_valid_input_identity / test_repair_json_trailing_comma / test_repair_json_unescaped_quotes / test_repair_json_extracts_balanced_block_from_prose / test_repair_json_control_chars_escaped / test_repair_json_unquoted_keys / test_repair_json_unrepairable_raises_with_strategies / test_complete_json_end_to_end_repairs_dirty_output / test_complete_json_unrepairable_raises_llm_error_invalid_response | PASS |
| AC-01d 脱敏 | test_redactor_replaces_known_secrets / test_error_message_redacts_key_echoed_by_provider / test_safe_fragment_truncates_and_redacts / test_redact_url_and_headers / test_redaction_rejects_too_short_secrets | PASS |
| AC-01e 输出钳制 | test_cap_for_operation_table / test_clamp_output_under_cap_unchanged / test_clamp_output_over_cap_truncated_with_marker / test_complete_applies_request_cap_and_post_clamp / test_explicit_max_tokens_overrides_operation_cap / test_complete_json_not_text_clamped_keeps_structure | PASS |
| AC-01f key 环境变量 | test_resolve_api_key_missing_raises_explicit_error / test_resolve_api_key_env_mapping_priority / test_resolve_api_key_deepseek_fallback / test_resolve_api_key_skips_empty_values / test_driver_resolves_key_from_environment / test_driver_without_env_key_raises_key_missing / test_driver_requires_model | PASS |
| 无硬编码密钥 | test_no_hardcoded_credentials_in_llm_source（扫描 loop_core/llm/*.py：无 `sk-` 字面量、无 `api_key = "…"` 字面量赋值） | PASS |
| 无真实外部调用 | test_no_real_network_calls + autouse _network_guard（http.client.HTTPConnection.connect 与 socket.create_connection 被封锁 → 任何真实连接尝试即失败；记录全部 httpx.Client 实例化并断言均带 transport） | PASS |

## 4. 测试隔离证明

- 全部 52 测试经 `httpx.MockTransport` 处理请求；驱动器测试的 `base_url` 使用 `https://llm.test.invalid/v1`（.invalid TLD 不可解析）。
- autouse guard：`http.client.HTTPConnection.connect` 与 `socket.create_connection` 抛 AssertionError —— 若任何测试试图建立真实连接，测试直接失败。
- 模块级记录全部 `httpx.Client` 实例化（transport/base_url），`test_no_real_network_calls` 断言**每一个**都显式带 transport（MockTransport），无一走真实网络。
- 假 key `sk-test-0123456789abcdef` 仅存在于测试文件与测试进程环境（monkeypatch/env 映射），未出现在任何源码字面量。

## 5. 风险与回滚

| 风险 | 缓解 |
|------|------|
| LLM 层引入网络面 | 测试全 mock + 网络封锁；运行时默认不连接（能力提供）；transport 显式注入才可联网 |
| httpx 未声明为正式依赖 | 懒导入（try/except ImportError）+ CONFIGURATION_ERROR 清晰报错；接线任务在 pyproject 声明（本任务路径不允许改 pyproject.toml） |
| 字符级 token 估算误差 | 保守 4 字符/token；钳制为防御性后置措施，标记可审计；请求级 max_tokens 仍由模型侧执行 |
| 回滚 | 本包与测试相互独立；删除 `loop_core/llm/` 与 `tests/test_llm_layer.py` 即完全回退，无其他模块引用 |

## 6. 文件清单

- 新增：`loop_core/llm/__init__.py`、`errors.py`、`keys.py`、`redaction.py`、`json_repair.py`、`output_policy.py`、`retry.py`、`protocol_driver.py`、`openai_driver.py`、`tests/test_llm_layer.py`、本设计文档
- 修改：无（未触碰业务源码；未改 pyproject.toml）
