# 设计证据：self-audit LLM 接线（loop_self_audit.py --llm）

> **T-0091（G-T-0091-REQUIREMENTS，approved）developer 工作包 | 2026-08-01 | developer 子代理**
> 落地文件：`tools/loop_self_audit.py`（修改，--llm 接线）+ `tests/test_self_audit_llm.py`（新增，AC-03a..e 全 mock）
> 验收对应：**AC-03**（--llm 启用 LLM 分析：审计摘要 → 风险发现/根因/修复建议 → 报告落盘；配置缺失/失败 → llm_status=SKIPPED/DEGRADED 明确标记，不阻断规则式审计）
> 前置依赖（并行工作包，本包只消费、不修改）：`loop_core/llm/zcode_config.py`（resolve_model_config）、`loop_core/llm/anthropic_driver.py` + `openai_driver.py`（ProtocolDriver 实现）。本包不修改 `loop_core/` 任何文件。

## 1. 借鉴映射（T-0090 D1 抽象层 → self-audit 接线）

| T-0090/T-0091 前置机制 | loop_self_audit.py 落地 |
|---|---|
| `resolve_model_config(preferred_provider, preferred_model, *, config_path, env)`：env 优先链 → `~/.zcode/v2/config.json`；`ResolvedModelConfig(api_key/provider_id/model/base_url/protocol/source)` | `--llm` 时调用；`--provider`/`--model` 原样透传（`preferred_provider`/`preferred_model`）；解析失败（KEY_MISSING/CONFIGURATION_ERROR）→ `llm_status=SKIPPED` + 解析错误消息作为启用提示（消息只含 env 变量名与配置路径，本身即脱敏） |
| 按 `protocol` 选驱动（anthropic → Messages 驱动；openai → Chat Completions 驱动） | `_make_driver(cfg)`：协议分支构造驱动，`api_key=cfg.api_key`、`base_url=cfg.base_url`（非空时）、`default_model=cfg.model`；模块级类引用便于测试 monkeypatch |
| `ProtocolDriver.complete_json(messages, operation=...)`（JSON 修复 + 统一错误码） | `operation="audit"`（OUTPUT_TOKEN_CAPS 8000 上限）、`temperature=0.2`、`model=cfg.model`；返回 `JSONResult.data` 归一化为 findings |
| T-0090 安全红线：key 用后即弃、错误消息预脱敏 | 双保险：入报告/入提示词的一切字段过 `sanitize_text`（sk- 令牌、IP 字面量/localhost URL、已知 key/endpoint 精确子串 → `<REDACTED>`）；模型信息只落 `cfg.to_dict()`（api_key 掩码）且 base_url 只记"是否配置"（`<REDACTED>`），endpoint 值永不落盘 |
| fail-safe 原则（LLM 不可用 → 规则式降级，不阻断） | 三态 `llm_status`：OK / SKIPPED / DEGRADED；LLM 环节任何异常（含未预期 bug → INTERNAL_ERROR）都不改变规则式判定、退出码与规则报告 |

## 2. 接口（tools/loop_self_audit.py 新增部分）

```
新增 CLI：
  --llm            启用 LLM 语义分析环节（默认关闭；不启用时行为与 T-0083 版逐字节一致）
  --provider ID    LLM 环节首选 provider id（透传 resolve_model_config）
  --model NAME     LLM 环节首选模型名（透传 resolve_model_config）

新增函数：
  git_commit() -> str                      # 原 main 内联逻辑抽出（测试 seam）
  rule_report_path() / llm_report_path()   # 报告路径（PROJECT_ROOT 派生，测试 seam）
  _write_json(path, payload)               # 与原有写盘语义逐字节一致
  sanitize_text(text, *, secrets=())       # sk- 令牌 / IP 字面量 / localhost URL / 已知机密子串 → <REDACTED>
  build_llm_summary(results, failed) -> dict
      # 每检查项 {rc, status(PASS/FAIL，与 failed 列表一致), stdout_tail(末800字符), stderr_tail(末400字符)}，
      # 全部过 sanitize_text；failed 去重；overall 与规则报告一致
  _model_info(cfg) -> dict                 # to_dict() 去 base_url 值，仅留 <REDACTED>/"" 指示
  normalize_findings(data) -> list[dict]   # {severity,finding,root_cause,suggestion}，severity 越界→medium，
                                           # 非 dict 项丢弃，上限 20 条，字段过 sanitize_text
  _make_driver(cfg)                        # protocol 分支构造驱动（类引用可 monkeypatch）
  run_llm_stage(summary, *, provider, model) -> dict  # 永不 raise；返回 llm_status 片段
```

## 3. 流程与三态语义

```
main() 规则式检查（原逻辑不动，输出逐字节兼容）
  → 计算 failed/overall → 写规则报告 self-audit.json（路径/格式不变）
  → 仅当 --llm：
      summary = build_llm_summary(results, failed)         # 脱敏摘要
      fragment = run_llm_stage(summary, provider, model)   # try/except 兜底
      报告 = {tool/kind=llm-analysis/version/timestamp(=规则报告时间戳)/git_commit, **fragment}
      落盘 .ai/evidence/observability/self-audit-llm.json
      stdout 追加 llm_status（仅 --llm 模式）
  退出码仍只由规则式 overall 决定（LLM 环节永不影响）
```

| 场景 | llm_status | 报告内容 | 提示 |
|---|---|---|---|
| 分析成功 | `OK` | model（脱敏）+ completion（model/attempts/repair_strategy）+ analysis_summary + findings[] | 无 |
| 配置缺失：KEY_MISSING / CONFIGURATION_ERROR | `SKIPPED` | reason + detail（解析错误消息 = 启用提示：env 变量名/配置路径）+ analysis_summary | `reason=KEY_MISSING` 时 detail 列出应设置的 env 变量名与配置路径 |
| 配置缺模型：env 命中但无 model 且未 --model | `SKIPPED` | reason=NO_MODEL + detail（提示 --model）+ model 信息 | 阻止必然失败的调用 |
| 调用失败：重试耗尽（retryable 码）/ JSON 不可修复（INVALID_RESPONSE）/ 认证等 | `DEGRADED` | llm_error{error_code, message(脱敏)} + model + analysis_summary | 规则式结果原样保留 |
| 未预期异常（非 LLMError bug） | `DEGRADED` | llm_error{error_code=INTERNAL_ERROR} | 兜底，绝不阻断 |

## 4. 安全语义（AC-03e / AC-05 证据面）

- 报告（self-audit-llm.json）与提示词中不出现 key、endpoint、内网地址：摘要构造时对 stdout/stderr 尾部脱敏；模型信息经 `to_dict()`（api_key=`<REDACTED>`）；base_url 值从不落盘（仅 `<REDACTED>` 指示存在）；DEGRADED 错误消息额外用已知 key/base_url 精确子串 + 正则双保险脱敏。
- `sanitize_text` 规则：`\bsk-[a-z0-9_-]{8,}\b` → `<REDACTED>`；`http(s)://<IP字面量>[:port]` 与 `http(s)://localhost[:port]` → `https://<REDACTED>`；调用方已知机密（api_key/base_url）完整子串替换。测试用合成值（`sk-test-*`、`llm.test.invalid`、`10.9.9.9` 合成内网占位）断言报告中三者均不可见。
- 规则报告（T-0083 self-audit.json）不因 LLM 环节改变任何字段/路径/时间戳语义（时间戳复用同一值）。

## 5. 测试设计（tests/test_self_audit_llm.py，10 例全 mock）

隔离手段：monkeypatch `PROJECT_ROOT→tmp_path`（报告全落 tmp_path，真实 .ai/ 树不可达）；monkeypatch `run`（无子进程）；monkeypatch `git_commit`（无 git 调用）；monkeypatch `resolve_model_config`（fixture `ResolvedModelConfig`：`sk-test-` 假 key + `llm.test.invalid` 域，不读真实 ~/.zcode/v2/config.json）；monkeypatch 两个驱动类（fake 驱动固定 JSON / 抛 LLMError）；`sys.argv` 注入参数。

- AC-03a：`test_ac03a_llm_stage_wires_rule_results_and_writes_report[openai|anthropic]`（参数化双协议）——规则 compile 失败 → rc=2 不变、规则报告 failed 保留；LLM 报告落盘：llm_status=OK、模型信息脱敏（api_key/base_url=`<REDACTED>`）、findings 字段齐（severity/finding/root_cause/suggestion）、"info" 归一化 medium、非 dict 项丢弃；按 protocol 选中对应驱动类；key/endpoint 到达驱动但不出现在报告/提示词；user 消息含 `"checks"`/`"compile"`/`"rc": 1`（规则结果 → LLM 分析接线）；stdout 含 llm_status。`test_ac03a_provider_model_flags_passthrough`——--provider/--model 透传断言。
- AC-03b：`test_ac03b_config_missing_skips_llm_and_keeps_rule_results`（KEY_MISSING → SKIPPED，detail 含 LLM_API_KEY 启用提示，无 findings，规则报告 PASS 保留，驱动零构造）；`test_ac03b_resolved_config_without_model_skips_llm`（NO_MODEL → SKIPPED）。
- AC-03c：`test_ac03c_llm_failure_degrades_and_keeps_rule_results[SERVER_ERROR|INVALID_RESPONSE]`（参数化重试耗尽/JSON 不可修复 → DEGRADED，error_code 记录，规则报告 FAIL 原样保留，报告无 key/endpoint）。
- AC-03d：`test_ac03d_without_llm_flag_behavior_unchanged`——无 --llm 时报告键集合/结构/退出码/stdout 与旧版一致，observability 下无 self-audit-llm.json，resolve_model_config 与驱动零接触；--quick 路径同断言。
- AC-03e：`test_ac03e_reports_contain_no_key_or_internal_address`——规则检查输出含合成机密（`sk-leak-*`、`https://10.9.9.9:3000`）→ 报告/提示词/摘要中全部 `<REDACTED>`，无 `http://`、无 endpoint 域；`test_ac03e_skipped_and_degraded_reports_also_redacted`——KEY_MISSING 消息内嵌假 key、错误消息回显 endpoint 的场景同样不泄漏。

## 6. AC-03 映射与执行记录

- 新测试：`python -m pytest tests/test_self_audit_llm.py -v` → **10 passed**（AC-03a x3（双协议+透传）/ AC-03b x2 / AC-03c x2 / AC-03d x1 / AC-03e x2）。
- 真机冒烟（无测试 mock）：`python tools/loop_self_audit.py --quick` → 规则式 PASS，stdout 与旧版一致；`LLM_API_KEY=sk-test-...(假) LLM_BASE_URL=https://llm.test.invalid/v1 python tools/loop_self_audit.py --quick --llm` → SKIPPED(NO_MODEL)；加 `--model fake-model` → 真实驱动 3 次重试后 CONNECTION_ERROR → **DEGRADED**，报告经断言无 key/endpoint 泄漏（`<REDACTED>` 生效）。冒烟产物已清理（self-audit-llm.json 删除、self-audit.json 恢复原状）。
- 全量回归：`python -m pytest tests -q` → 见工作包汇报（应 ≥3355 passed，无回归）。
