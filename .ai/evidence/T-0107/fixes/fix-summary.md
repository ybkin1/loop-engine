# T-0107 修复汇总（fix-summary.md）

- 任务：T-0107 设计漏洞修复（正确性）— P1 context_packager 截断 + P2 全量 + P3 首批
- 修复依据：`.ai/evidence/T-0106/design/audit-design-gaps.md`（42 项清单）
- 日期：2026-08-03
- 执行角色：developer（子智能体）
- 详细逐项记录：`../commands.md`

## 一、四组修复汇总

### 组 1：context_packager 专项（9/9 完成，`loop_core/context_packager.py`）

- D1-1（P1）任务卡 1000 字符静默截断 → **token 预算**（1500 tokens ≈ 6000 字符）+ **AC/验收节按 `## ` 节解析优先保留（永不切）** + truncated 标记
- D1-2 / D1-3 角色文件与 extra_files 截断 → `…[truncated N chars]` 显式标记
- D1-4 knowledge cases → 按 case 边界截断（JSON 语法完整）+ 标记
- D2-1 / D2-8 截断字面量与 git timeout 字面量 → 命名常量集中
- D3-2 `MAX=15000` 死护栏 → total 真实累计 + 超限截断标记（footer 保留）
- D4-1 git diff 吞错 → warning + "diff unavailable" 占位节
- D4-4 (a) knowledge cases 损坏 → warning；(b) diff 无缓存 → 进程内缓存（key=(root, HEAD, kind)）

### 组 2：P2 全量（11/11 完成）

- D1-2、D1-4、D2-1、D3-2、D4-1：随组 1 同源修复（同文件）
- D2-2 `intent_router` 中风险 ≥3 阈值 → `MEDIUM_RISK_ESCALATION_MIN` 命名常量
- D3-1 `audit_ledger` 无轮转 → 行/字节阈值轮转 + N 份归档（链哈希跨归档延续，verify 完整）
- D4-2 `loop_enforcement.is_loop_mode_enforced` state 读取失败 **fail-open → fail-closed 强化**（无法确认即按强制执行 + `STATE_UNREADABLE` 告警）
- D4-3 `tool_constraint_check` 非法 phase → `phase_problems` 告警字段
- D5-1 `context_controller._naive_yaml_parse` 静默降级 → 显式告警 + gate/state **schema 校验**（复用 `loop_core/schemas/`）+ `_load_gates` 解析失败与"无 gate"分开上报
- D5-2 双解析器分歧 → **共享契约解析模块 `loop_core/front_matter.py`**（enforcement 与 context_controller 统一调用；表格 | 与列表两种格式契约测试；退化环境本地同逻辑副本兜底）

### 组 3：P3 首批（6/6 完成）

- D3-4 `runtime_controller` journal 轮转（5MB/3 档）
- D3-5 `async_jobs` 落盘 JSONL 轮转（5MB/3 档，构造可配置）
- D4-5 `audit_ledger` 损坏行计数告警（`corrupt_line_count` + `AuditIntegrity.corrupt_lines`）
- D4-7 `loop_enforcement` 哈希跳过 → `HASH_SCAN_SKIPPED` 告警（进程内去重）
- D4-8 `transaction_registry` 裸 except + 冗余双重计算删除（Path/str root 统一）
- D5-5 `contract_verifier` fallback 收窄（仅 ImportError）+ 产出去向标注 `_parsed_by`

### hook 门禁（2 处最小 diff + D5-2 同文件接线）

- `hooks/scripts/loop_enforcement.py` 仅 3 处功能改动：**D4-2**（fail-closed 强化）、**D4-7**（哈希跳过告警）、**D5-2**（P2 项：load_task_contract 改调共享解析模块，属任务卡 P2 范围）；其他 hook 文件零改动

## 二、测试结果

| 套件 | 结果 |
|------|------|
| 新增 `tests/test_t0107_fixes.py` | **44 passed**（D1-1×4 / D1-2/3/4×3 / D2-1+D2-8 / D3-2×2 / D4-1×2 / D4-4×2 / D2-2×2 / D3-1+D4-5×4 / D4-2×3 / D4-7 / D4-3×2 / D5-1×5 / D5-2×4 / D3-4 / D3-5 / D4-8×2 / D5-5×3） |
| hook 套件（D4-2/D4-7 改动后必须全绿） | `test_enforcement.py` + `test_hooks.py` + `test_role_isolation.py` + `test_enforcement_hub.py` + `test_hook_guards.py` + `test_hook_integration.py` = **177 passed** |
| context/intent 套件 | `test_context_controller.py` + `test_context_loader.py` + `test_memory_injection.py` + `test_t0105_batch2/3.py` + `test_intent_router(upgrade).py` = **240 passed** |
| 关联模块套件 | `test_runtime_controller.py` + `test_async_jobs.py` + `test_contract_verifier.py` + `test_observability.py` + `test_execution_ledger.py` + `test_governance_metrics.py` + `test_t0104_*` = **174 passed** |
| **全量回归** `pytest tests/`（排除 seeded_defects/lab/vertical_slice） | **3696 passed, 64 skipped, 12 xfailed, 0 failed**（1 deselected，见下） |

**唯一排除项（环境性，非本次改动引入）**：`test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real` — `.ai/HANDOFF.md`（主会话在我开始前已修改）引用 `.ai/evidence/T-0107/evidence-manifest.v1.yaml`，该 manifest 由主会话在 T-0107 closeout 时生成，当前尚不存在 → dangling ref。与本次代码改动无关（该测试只读 HANDOFF.md 与 manifest 文件）。

## 三、约束自查（git diff --stat 实证）

```
 .zcode/tools/transaction_registry.py |   9 +-     ← D4-8（P3 范围，任务卡"写路径"未列 .zcode/tools/，见遗留事项 1）
 hooks/scripts/loop_enforcement.py    |  94 ++++---  ← 仅 D4-2/D4-7 两处门禁 + D5-2（P2 同文件接线）
 loop_core/async_jobs.py              |  41 ++++    ← D3-5
 loop_core/audit_ledger.py            | 142 ++++++-- ← D3-1/D4-5
 loop_core/context_controller.py      | 173 +++++--- ← D5-1/D5-2
 loop_core/context_packager.py        | 336 +++++++- ← 专项 9 处
 loop_core/contract_verifier.py       |  33 +++-    ← D5-5
 loop_core/intent_router.py           |   7 +-      ← D2-2
 loop_core/runtime_controller.py      |  34 ++++    ← D3-4
 tools/tool_constraint_check.py       |  16 +-      ← D4-3
（新增）loop_core/front_matter.py    |  新模块     ← D5-2 共享契约解析
（新增）tests/test_t0107_fixes.py    |  新测试     ← 44 项回归
```

1. **hooks/ 仅 loop_enforcement.py**：`git diff` 实证 hooks/ 下无其他文件改动（D4-2/D4-7 最小 diff；D5-2 为任务卡 P2 范围同文件接线）。
2. **治理内核零触碰**：gate_guard / enforcement 核心判定（main() 决策链、check_* 门禁函数） / hard_constraints / guard_health / state_machine / validate_state / context_loader 默认值 — `git diff` 无任何相关文件；context_controller 仅改文件 I/O 与解析层（`_load_state`/`_load_gates`/`_load_task_contract`/`_yaml_load*`），**authorize() 决策链语义零改动**。
3. **fail-closed 语义**：D4-2 为 fail-open → fail-closed **强化**（state 读取失败从"放行"改为"按强制执行"），未反向弱化任何约束；D5-5 收窄后 PyYAML 语法错误不再 pattern 降级（fail-closed 方向）。
4. 不部署/不发布/不安装；版本文件未改（bump 由主会话执行）。

## 四、遗留事项

1. **写路径偏差（2 个文件，均在任务卡 P2/P3 明确范围、KNOWN_ISSUES 登记项，故按指令修复并记录）**：
   - `tools/tool_constraint_check.py`（D4-3，P2）与 `.zcode/tools/transaction_registry.py`（D4-8，P3）不在任务卡"允许路径"清单内，但任务卡 P2/P3 范围与 KNOWN_ISSUES 均明确要求修复这两项（D4-3 为 AC-02 的 P2 11 项之一）。已按任务范围执行最小 diff，并在此显式标注偏差供独立审查确认。
2. **环境性测试**：`test_manifest_t0095` 的 HANDOFF manifest 引用测试需 T-0107 closeout 生成 manifest 后恢复全绿（主会话动作）。
3. **diff 缓存为进程内缓存**：跨进程不共享（子代理每次新进程仍会执行一次 git diff）；按任务卡 D4-4 口径（消除同进程重复派发重跑），磁盘级缓存不在本任务范围。
4. **D5-2 退化兜底**：enforcement 在陈旧插件缓存（无 loop_core.front_matter）时回退本地同逻辑副本，代码与共享模块逐行一致，契约测试覆盖两种格式一致性。
