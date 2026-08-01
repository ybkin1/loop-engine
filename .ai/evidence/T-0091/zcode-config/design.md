# 设计证据：ZCode 模型配置解析（zcode_config）

> **T-0091（G-T-0091-REQUIREMENTS，approved）developer 工作包 | 2026-08-01 | developer 子代理**
> 落地文件：`loop_core/llm/zcode_config.py`（新增）+ `tests/test_zcode_config.py`（新增，AC-02a..e 全 fixture）
> 验收对应：**AC-02**（env 优先链 + `~/.zcode/v2/config.json` provider 解析；key 选择正确；key 不落日志/错误消息）
> 本工作包只覆盖配置解析；Anthropic 协议驱动与 self-audit 接线由并行子代理承载（互不重叠，本模块不修改 `loop_core/llm/__init__.py` 导出，避免与并行工作包合并冲突，导入路径 `from loop_core.llm.zcode_config import ...`）。

## 1. 借鉴映射（ZCode 宿主 → loop-engine）

| ZCode 机制（调研事实） | loop-engine 落地 |
|---|---|
| 桌面端权威配置 `~/.zcode/v2/config.json`：`provider.<id>.options.{apiKey,baseURL}`、`kind`（anthropic/openai/openai-compatible）、`enabled`、`source`、`models` | `resolve_zcode_provider(config_path=None)` 解析同构结构 → `ZCodeProvider` 候选列表（缺失文件 → `[]`；损坏 JSON / 无 `provider` 段 → 明确 `CONFIGURATION_ERROR`，绝不静默） |
| ZCode CLI env 优先链（kind=openai→OPENAI_API_KEY、kind=anthropic→ANTHROPIC_API_KEY、兜底 ZCODE_API_KEY、baseURL 同理） | `ENV_TIERS` 成对链条：`LLM_API_KEY/LLM_BASE_URL` → `ANTHROPIC_API_KEY/ANTHROPIC_BASE_URL` → `OPENAI_API_KEY/OPENAI_BASE_URL` → `ZCODE_API_KEY/ZCODE_BASE_URL`；命中 tier 决定 `protocol`（openai/anthropic）。provider 名推导变量（如 `<NAME>_API_KEY`）留作扩展点，本期不实现（保持链条确定性可测） |
| 当前宿主 provider 为 anthropic kind（ZCode 主流） | `select_provider` 无显式指定时：先扫 anthropic kinds，再扫 openai/openai-compatible kinds；取第一个 `enabled` 且 `apiKey` 非空者 |
| T-0090 `keys.py` 语义（env 只读、缺失 → `LLMKeyError(KEY_MISSING)`、消息只列变量名） | `resolve_model_config` 全缺 → `LLMKeyError(KEY_MISSING)`，消息只列 env 变量**名**与配置文件路径；key 值绝不进入任何消息 |

## 2. 接口

```
loop_core/llm/zcode_config.py
├─ 常量
│  ENV_TIERS: (key_var, base_url_var, protocol) x4   # LLM→ANTHROPIC→OPENAI→ZCODE
├─ default_config_path() -> Path                     # ~/.zcode/v2/config.json（测试 monkeypatch 隔离）
├─ @dataclass(frozen) ZCodeProvider
│  provider_id / name / kind / api_key / base_url /
│  enabled / source / models(tuple[str,...])
│  .to_dict() -> api_key 以 <REDACTED> 掩码（空 key 保持 ""）
├─ @dataclass(frozen) ResolvedModelConfig
│  api_key / provider_id / model / base_url / protocol / source
│  .is_env_only  .to_dict() -> api_key 掩码
├─ resolve_zcode_provider(config_path=None) -> list[ZCodeProvider]
├─ select_provider(providers, preferred=None) -> ZCodeProvider | None
└─ resolve_model_config(preferred_provider=None, preferred_model=None, *,
                        config_path=None, env=None) -> ResolvedModelConfig
```

## 3. 解析语义

- **候选解析**：`models` 接受 dict（取键列表，保持插入序）或 list；`kind` 归一化为小写；`options` 非 dict 视为空；`enabled` 非 bool 默认 True；禁用/无 key 的 provider 也进入候选列表（过滤是选择阶段的职责，AC-02a 两条都验证）。
- **选择（AC-02b）**：
  - `preferred` 显式指定 → 该 provider 直接胜出（kind 优先级让位于显式意图）；id 不存在 → `CONFIGURATION_ERROR`（消息列出可用 id，id 非机密）；存在但 `apiKey` 为空 → `KEY_MISSING`（不静默空 key）。
  - 未指定 → 按 kind 两轮扫描：先 anthropic，再 openai/openai-compatible；每轮内取文件顺序第一个 `enabled && apiKey 非空` 者；无匹配 → `None`（上层转 `KEY_MISSING`）。
- **env 优先链（AC-02c）**：逐 tier 检查，key 非空（strip 后）即命中；base_url 同 tier 变量或空（空则交给驱动默认）；`LLM_API_KEY` tier 协议为 openai（T-0090 规范 env key 喂 OpenAI 兼容驱动）；`preferred_provider` 不越过 env 链（env 绝对最高优先级）。全空 → 读文件 → 选 provider → 仍无 → `LLMKeyError(KEY_MISSING)`。
- **模型选择**：`preferred_model`（非空白）优先；否则 `provider.models` 第一个；env 命中时无文件 models，返回 `model=""`（显式"未配置"，由驱动在调用时给出 `CONFIGURATION_ERROR`，不猜测默认模型）。
- **protocol 映射**：文件 provider `kind == "anthropic"` → `anthropic`；其余 → `openai`。`source` 字段记录来源（`env:LLM_API_KEY` / `file:acme`），供审计追踪。

## 4. 安全语义（AC-02d / AC-05 证据面）

- 返回的 `api_key` 是唯一机密字段：`to_dict()` 一律掩码为 `<REDACTED>`（keyless 保持 `""`，不伪装）；错误消息只含 env 变量名、provider id、文件路径，结构上不含 key 值。
- 损坏文件错误消息只带 JSON 解析器位置信息（`str(JSONDecodeError)` 不含文件内容），不echo文件正文。
- 测试断言：`FAKE_KEY`/`sk-` 不出现在任何错误消息与 `json.dumps(to_dict())` 中（AC-02d 三组用例 + KEY_MISSING/CONFIGURATION_ERROR 各覆盖）。
- 测试全 fixture：autouse fixture `isolate_zcode_config` monkeypatch `default_config_path()` 指向 `tmp_path`，并清空全部相关 env 变量；`test_default_config_path_is_isolated` 证明默认路径已被重定向，真实 `~/.zcode/v2/config.json` 在测试中不可达。fixture 中 baseURL 一律用 `.invalid` 保留 TLD（不可解析），key 用 `sk-test-*` 假值。

## 5. 边界与失败语义（AC-02e）

| 场景 | 行为 |
|---|---|
| 文件不存在 | `resolve_zcode_provider` → `[]`；`resolve_model_config`（env 全空）→ `KEY_MISSING`（消息含路径） |
| 文件损坏（非 JSON） | → `CONFIGURATION_ERROR`（含路径）；若 env 有 key，env 先于文件命中，损坏文件不阻断 |
| 文件无 `provider` 段 | → `CONFIGURATION_ERROR` |
| `provider` 为空对象 | → `[]` → 上层 `KEY_MISSING` |
| 全部 provider 禁用/无 key | → `KEY_MISSING` |
| `preferred_provider` 不存在 | → `CONFIGURATION_ERROR` |
| `preferred_provider` 无 key | → `KEY_MISSING` |
| env key 为空白 | 跳过该 tier 继续链 |

## 6. AC-02 映射（tests/test_zcode_config.py，36 例全通过）

- AC-02a：`test_resolve_zcode_provider_parses_fixture_fields`、`test_resolve_zcode_provider_missing_file_returns_empty`、`test_resolve_zcode_provider_default_path_is_fixture_path`、`test_explicit_config_path_parameter_wins`、`test_default_config_path_is_isolated`
- AC-02b：`test_select_provider_default_prefers_anthropic_kind`、`test_select_provider_preferred_wins_over_kind_priority`、`test_select_provider_skips_disabled_and_keyless`、`test_select_provider_accepts_openai_compatible_kind`、`test_select_provider_none_when_no_eligible`、`test_select_provider_preferred_unknown_raises_configuration_error`、`test_select_provider_preferred_keyless_raises_key_missing`
- AC-02c：`test_env_llm_tier_wins`、`test_env_anthropic_tier_second`、`test_env_openai_tier_third`、`test_env_zcode_tier_fourth`、`test_env_whitespace_key_skipped`、`test_env_mapping_injection_without_process_env`、`test_env_priority_order_llm_over_anthropic_over_openai`、`test_file_fallback_when_env_missing`、`test_file_model_default_and_preferred_model`、`test_file_preferred_provider_and_model`、`test_file_preferred_provider_skips_kind_priority`、`test_file_without_usable_provider_raises_key_missing`、`test_file_preferred_provider_unknown_raises_configuration_error`、`test_all_missing_raises_key_missing`
- AC-02d：`test_resolved_config_to_dict_redacts_key`、`test_provider_to_dict_redacts_key`、`test_key_missing_error_message_never_contains_key`、`test_configuration_error_message_never_contains_key`、`test_corrupt_file_error_message_never_contains_key`
- AC-02e：`test_corrupt_file_raises_configuration_error`、`test_corrupt_file_with_env_key_still_resolves_from_env`、`test_corrupt_file_without_env_raises_explicit_error`、`test_config_without_provider_section_raises_configuration_error`、`test_config_with_empty_provider_object_returns_empty_list`

执行记录：`python -m pytest tests/test_zcode_config.py tests/test_llm_layer.py -q` → **88 passed**（36 新增 + 52 既有 llm 层无回归，含 `test_no_hardcoded_credentials_in_llm_source` 对 `loop_core/llm/*.py` 的密钥字面量扫描）。
