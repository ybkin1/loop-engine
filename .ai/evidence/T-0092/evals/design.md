# T-0092 — AI-agent eval 栈设计证据（B1 §1 落地）

| | |
|---|---|
| **Task** | T-0092 — AI-agent eval 栈 |
| **Role** | developer |
| **Basis** | docs/designs/loop-v4-ai-agent-governance.md §1 (eval gate, B1), §3.5 (guard-health battery 衔接) |
| **Status** | implemented |
| **Date** | 2026-07-31 |

## 1. 范围与定位

B1 §1 的 Wave-1 落地（"eval foundation: suite/report schema, harness, trace contract"，
§9.3 时序表）。本实现交付 **离线可运行的规则评分 eval 栈**，为后续 `eval_required`
gate 条件（§1.2）与 golden eval（§1.3/§7.2 第 3 层）提供 schema、运行器与报告基座。

**边界（eval 只评测、不改变约束语义）**：

- `loop_core/evals.py` 不接线任何 hook，不改变任何 guard 的拦截/放行行为；
- LLM 判定（§1.3 `type: model` grader 的雏形）是可选的，不可用/失败/弃权一律
  SKIPPED，绝不阻断（fail-safe，对齐 §1.3 `escape_hatch: true`）；
- 测试中 LLM 全 mock（脚本化 FakeDriver），不触碰真实 API、不处理密钥。

## 2. 构件对照（B1 设计 → 实现）

| B1 设计 | 实现 |
|---|---|
| §1.3 eval suite artifact（schema_version/suite_id/version/balance 正负） | `loop_core/evals.py` EvalCase schema + 内置正/负样例集（6 例，positive 2 / negative 4） |
| §1.3 graders: `type: code`（确定性评分） | 规则评分器：`text_contains` / `text_matches` / `json_equals` / `exit_code`（4 种断言，≥3 要求） |
| §1.3 graders: `type: model` + `escape_hatch` | `llm` 判定类型：`complete_json` 裁判（verdict PASS/FAIL/UNKNOWN）；UNKNOWN/不可用/失败 → SKIP（escape hatch） |
| §1.3 harness: sandbox/mock_tools | `executor_fn` 注入缝（测试用 fake executor；默认 executor 对 command 用例跑 subprocess，超时 + 截断 64KB） |
| §1.4 eval report artifact（ReportBinding） | `EvalReport`：ReportBinding 字段 + schema_version + stats + by_severity + 每用例明细；默认落盘 `.ai/evidence/observability/eval-report.json` |
| §1.2 gate fail-closed（缺字段 → NOT_VERIFIED） | `EvalReport.validate()` 列出缺失必填字段（task_id/phase/git_commit/timestamp/schema_version/cases） |
| §3.5 guard-health 对照电池衔接（负样例必须 block、正样例不得过度拦截） | 内置样例 `EVAL-GUARD-001..006`，每个带 `aligns:GC-xxx` 标签对应 `loop_core/guard_health.py` battery 的 control id |

## 3. EvalCase schema

```
case_id      str   必填，确定性标识（运行器拒绝重复 case_id）
title        str   必填
input        any   必填；文本/结构化 JSON；dict 含 "command" 键 → subprocess 用例
expected     any   可选（规则参数可承载期望值）
rule         dict  必填
  type       text_contains | text_matches | json_equals | exit_code | llm
  params     dict  断言参数（text_contains.value/values、text_matches.pattern、
                   json_equals.json_path/expected、exit_code.expected/timeout、
                   llm.prompt/expected_conclusion）
severity     str   必填：critical | high | medium | low
version      str   必填，默认 "1"
tags         list  可选（guard/positive/negative/aligns:GC-xxx）
```

校验策略：任何非法用例（缺字段 / 未知断言类型 / 非法 severity / 非法正则 /
exit_code 无 command / llm 缺 prompt 或缺 expected_conclusion）→ `EvalValidationError`
**明确拒绝**（AC-01），绝不静默修正或丢弃。文件加载（YAML/JSON）同样整体拒绝。

## 4. 评分语义

- 规则评分为主：`text_contains`（子串全命中）、`text_matches`（正则 search，
  编译期校验）、`json_equals`（深比较，可选 `json_path` 定位转录字段）、
  `exit_code`（子进程退出码）。
- LLM 判定可选（`llm` 类型）：裁判输出 `{"verdict": PASS|FAIL|UNKNOWN, ...}`；
  与 `expected_conclusion` 一致 → PASS，不一致 → FAIL；UNKNOWN/ABSTAIN/非对象/
  驱动异常/无驱动 → **SKIPPED 不阻断**。
- 异常隔离：单用例执行异常 → 该用例 `FAIL(ERROR: ...)`，其余用例照常执行，
  套件完整运行（AC-02）。
- severity 汇总：按 critical/high/medium/low 分别统计 pass/fail/skip；
  总体 verdict：任一 FAIL → FAIL，仅 SKIP 不降级（对齐 §1.5 pass^3 一致性维度的
  "SKIP 不阻断" 语义）。

## 5. 内置样例集与 guard_health 对照电池对齐（AC-04）

| case_id | 语义 | 正/负 | severity | guard_health 对照 |
|---|---|---|---|---|
| EVAL-GUARD-001 | 越界写入（`C:/Windows/tmp/evil.py`）必须被 path_guard 拦截 | negative | critical | GC-007 |
| EVAL-GUARD-002 | 内容含硬编码密钥必须被 content_guard 拦截 | negative | critical | GC-002 |
| EVAL-GUARD-003 | 干净内容必须放行（不过度拦截） | positive | medium | GC-003 |
| EVAL-GUARD-004 | bash 重定向写入必须被 bash_content_guard 拦截 | negative | high | GC-004 |
| EVAL-GUARD-005 | 已批准 gate 范围内治理写入必须放行 | positive | high | GC-008 |
| EVAL-GUARD-006 | ledger 编辑必须被拦截（转录含 BLOCKED 证据，text_contains 示例） | negative | high | GC-006 |

语义对齐：guard_health 在 **live hook 链** 上断言同一批正/负控制的
block/allow（`GuardControl.expect_block`）；eval 样例集在 **guard 决策转录** 上
离线断言同样的 block/allow 期望（`guard_response.decision`）。两者互相印证：
guard_health 证明 guard 活着，eval 样例证明治理期望被编码为可回归的评测断言。
样例数据文件：`.ai/evidence/T-0092/evals/builtin-cases.yaml`（由
`loop_core.evals.builtin_cases()` 嵌入式权威数据导出，round-trip 测试保证同步）。

## 6. EvalReport（ReportBinding 风格，AC-03）

```json
{
  "type": "eval_report",
  "schema_version": "1",
  "task_id": "T-0092", "phase": "S6-delivery",
  "gate_id": "G-T-0092-S5-AGENT-EVAL",
  "execution_id": null, "git_commit": "<short sha>",
  "diff_fingerprint": null, "timestamp": "<ISO-8601>",
  "tool_name": "loop-eval", "tool_version": "1.0.0",
  "suite": {"suite_id": "loop-agent-eval", "suite_version": "..."},
  "stats": {"total": 6, "passed": 6, "failed": 0, "skipped": 0},
  "by_severity": {"critical": {...}, "high": {...}, "medium": {...}, "low": {...}},
  "verdict": "PASS",
  "cases": [{"case_id": ..., "severity": ..., "result": "PASS",
             "duration_ms": ..., "rule_type": ..., "version": ..., "reason": null}]
}
```

默认落盘 `.ai/evidence/observability/eval-report.json`（B1 §1.2 gate 消费点）。
`validate()` 缺失任何必填字段 → 消费方按 NOT_VERIFIED（fail-closed，§1.2/§1.4）。

## 7. CLI

`tools/tool_eval.py`：`--cases <yaml|json>`（默认内置样例集）、`--report [PATH]`
（写报告）、`--json`（stdout JSON）、`--llm [--provider/--model]`（可选 LLM 裁判，
不可用自动 SKIP）；退出码 0 = 通过，2 = 存在 FAIL。

## 8. 验收对照

| AC | 证据 |
|---|---|
| AC-01 schema 完整 + 非法拒绝 | tests/test_evals.py::TestSchema（14 项：合法通过 + 缺字段/未知断言/非法 severity/非法正则/llm 缺参/非 dict 条目/重复 case_id 拒绝） |
| AC-02 运行器 | TestRunnerRuleScoring（4 断言类型 × pass/fail）+ TestLLMJudge（成功/不匹配/失败 SKIP/弃权 SKIP/无驱动 SKIP/不阻断）+ TestExecutorAndIsolation（默认 executor subprocess、超时→FAIL(ERROR)、异常隔离） |
| AC-03 报告 | TestReport（统计/明细/severity 汇总/binding 字段/validate/落盘 JSON） |
| AC-04 内置样例 ≥4 | TestBuiltinCases（6 例，正 2 负 4，全部离线 PASS，YAML round-trip，GC 对齐 ≥4） |

## 9. 测试隔离与回归

- LLM 判定全部走 `FakeDriver`（脚本化返回 / 注入异常），`build_llm_driver`
  的解析器被 monkeypatch，主机真实配置/密钥不进入测试；
- 默认 executor 的 subprocess 测试仅用 `sys.executable -c`（无网络、确定性）；
- 全量回归：`C:/Python312/python.exe -m pytest tests/ -q`（见任务汇报）。
