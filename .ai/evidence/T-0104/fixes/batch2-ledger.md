# 批 2 批次证据 —— 记录层（设计-3 + 设计-4 字段）

> 任务：T-0104 | 日期：2026-08-02 | 落地依据：D-03 §3.3 / §4.3.2

## 改了什么（3 个文件 + 1 个新数据文件）

| 路径 | 改动点 | 设计编号 |
|---|---|---|
| `agents/developer/SKILL.md` | §5.1 JSON Schema 在 `known_deviations` 后新增可选数组 `deviations`（D-03 §3.3.2 候选文本原样）；`known_deviations/unimplemented/clarification_requests` 原样保留；附字段规则（reason 必填、ai_decisions 每条须含 why_not_ask + impact_if_wrong、needs_user_review:true 须进 gate 呈现、决策写入 ai-decisions.jsonl） | 3 |
| `loop_core/approval_ledger.py` | ①`AiDecisionRecord` dataclass（D-03 §3.3.4 候选代码：decision_id="AD-{uuid12}"、task_id、phase、role_id、decision、why_not_ask、impact_if_wrong、reason_ref、recorded_at；**无 human_actor 字段**——不混入 ApprovalRecord 的"Always user"语义，evidence≠approval）；②`AiDecisionLedger`（append 物理追加 + read_all/read_records + verify_chain + find_by_task；chain_hash = SHA256(prev_hash \|\| row)，root seed `LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT` 与 ExecutionLedger/ledger_guard 完全相同——照抄 execution_ledger.py L157-182 链契约；复用 _sha256/_short_uuid，新增 _utc_now_iso） | 3 |
| `loop_core/approval_ledger.py` | `ApprovalRecord` 新增可选字段 `user_comprehension_confirmed: bool \| None = None`；`create()` 增参（默认 None）；`record_approval` 仅非 None 时写键（L201-206 可选键追加风格相同）；`get_approval` 用 `.get()` 读取（存量记录无此键 → None，零数据迁移） | 4 |
| `.ai/ledger/ai-decisions.jsonl` | 新建链式 JSONL（空链起步；空链 = 合法，ledger_guard verify 空链返回 True） | 3 |

### ledger_guard 兼容验证（设计-3 §3.3.4 前置验证，只读）

- hooks/scripts/ledger_guard.py 未做任何改动；对 `.ai/ledger/` 全目录做追加+链校验，
  root seed 相同 → 新文件自动被覆盖。
- 干跑：以 ZCode hook 调用方式子进程运行 ledger_guard.py，对真实
  `.ai/ledger/ai-decisions.jsonl` 写入内容校验 → **exit 0**。
- 自动化实证：`tests/test_ai_decision_ledger.py` 中两条子进程测试
  （合法追加 exit 0 / 篡改 exit 2）→ 通过。

## 测试结果

| 文件 | 覆盖 | 结果 |
|---|---|---|
| `tests/test_ai_decision_ledger.py`（新增，14 项） | create 生成 AD-{uuid12}、JSON round-trip、无 human_actor；追加写 + 多条目链验证、空链合法、篡改/插入检测、find_by_task；ledger_guard 子进程兼容（0 / 2） | 通过 |
| `tests/test_approval_ledger.py`（更新 +4 项） | comprehension True/False round-trip、存量无键 → None、None 不写键 | 通过 |
| `tests/test_t0104_deviations.py`（新增，12 项） | schema 含 deviations + 既有字段保留、缺 reason/why_not_ask/impact_if_wrong → 无效、空数组合法、main-thread 呈现规则存在 | 通过 |

相关回归：`test_execution_ledger.py`（31 项）、`test_ledger_guard.py`（8 项）全部通过
（链契约与 hook 校验未被破坏）。

## 约束自查（git diff）

- `git diff --stat -- hooks/` → 空（**ledger_guard.py 零改动**，仅只读验证）
- `git diff --stat -- loop_core/context_loader.py` → 空
- 全量 diff 中 loop_core 仅 approval_ledger.py 一个文件（+201 行，均为新增类型/字段）

## 回退

deviations 数组为可选字段，删除即回退；ai-decisions.jsonl 为新增文件，删除即回退
（链随文件删除重置，与 ledger 恢复协议一致，ledger_guard.py L48-49）。
