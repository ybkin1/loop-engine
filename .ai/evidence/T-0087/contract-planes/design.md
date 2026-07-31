# T-0087 U2 — Vertical Slice 契约平面化设计证据（design）

> **T-0087（运行时契约化）U2 工作包 | 2026-08-01 | Gate: G-T-0087-REQUIREMENTS（approved）**
> 借鉴来源：OpenBMB/StaffDeck `contracts/agent/v1`（21 JSON Schema + 17 黄金场景 GT01-17 + 5 观测平面 + 30 需求注册表 + conformance-report 带 gate_decision）——见 `.ai/evidence/T-0086/staffdeck-benchmark.md` D6/U2。
> 落地位置：`tests/vertical_slice/`（把端到端切片行为固化为可测试的契约资产，系统化检测行为漂移）。

## 1. 借鉴映射

| StaffDeck contracts/agent/v1 | loop-engine U2 落地 | 差异说明 |
|---|---|---|
| 5 观测平面（domain/sse/db-events/conversation/legacy-provider） | 4 观测平面（domain/events/conversation/state） | 按 loop-engine 治理语义收敛：无 SSE/legacy-provider 平面；新增 **state** 平面锚定 `loop_core.state_machine`（PHASE_TRANSITIONS / REENTRY_TRANSITIONS / can_approve_gate） |
| 17 黄金场景（GT01-17） | 4 黄金场景（VS-GS-001..004） | 覆盖正向端到端、负向拒绝-修复-重审、状态机合法性、角色收敛 |
| 30 需求注册表 | 12 需求（VS-REQ-001..012） | 每需求登记：ID/描述/对应平面/covered_by/状态 |
| conformance-report + gate_decision | `tests/vertical_slice/conformance.py` → `.ai/evidence/T-0087/contract-planes/conformance-report.json` | 门禁语义 fail-closed（见 §4） |

## 2. 4 观测平面定义（loop-engine 语义）

| 平面 | 定义 | 观测对象（observables） | 断言类型 |
|---|---|---|---|
| domain | 决策与产物 | 任务卡（TASK-VS-001）、AC（AC-01..05）、gate 决策（GATE-S1-001/S2-001 APPROVED + AR-ID + 时间戳）、验收结果（final_decision=GO） | file_exists / text_contains / text_matches / json_equals / count_equals |
| events | 事件流 | 关键治理事件序列：任务登记 → gate 批准 → 实现 → 验收 → 收敛；负向链：否决 → NOGO → 修复 → 重审 GO。每个事件绑定一个证据 check | event.check（任意通用断言） |
| conversation | 前后状态 | 每个阶段转换的 pre/post 状态：前阶段 gate APPROVED 才进入下一阶段；阻塞态必须列出 blocker + required_repairs；修复后收敛（全角色 PASS + 全 quality gates PASS） | stage.pre / stage.post 检查集 |
| state | 状态机迁移 | state.yaml/task_graph 的合法迁移路径：证据链相邻阶段直接迁移合法或存在合法可达路径（切片跳过 S3 时 S2→S4 经 S3 可达）；非法直跳（S1→S5）必须被禁止（负向对照）；重审/修复回环符合 REENTRY_TRANSITIONS；BLOCKED 裁决阻止 gate 批准（can_approve_gate fail-closed） | state_transition / state_transition_forbidden / state_path（BFS 可达性）/ reentry / gate_approval |

## 3. Golden 场景清单

| 场景 | 类型 | 生命周期 | 平面覆盖 |
|---|---|---|---|
| VS-GS-001 | happy-path | 需求 → 任务图 → gate 批准 → 实现 → 验收 → 收敛 | 4 平面：16 domain 断言 + 8 events + 5 stages + 4 state |
| VS-GS-002 | negative-path | gate 拒绝 → 修复 → 重审 → 收敛 | 4 平面：NOGO/GO 决策、否决事件链、阻塞态/修复态/重审收敛态、回环与批准裁决 |
| VS-GS-003 | state-legality | 状态机合法性 | 4 平面（state 为主）：13 项 state 断言（5 迁移 + 1 禁止对照 + 5 reentry + 2 gate_approval） |
| VS-GS-004 | role-convergence | 7 角色裁决 BLOCKED → 修复后全 PASS | 4 平面：缺陷按角色检出、lint 关联、复验角色、收敛态 |

## 4. 需求注册表与门禁语义

- 注册表：`tests/vertical_slice/contract_planes/requirement-registry.yaml`（权威版本），`12` 条需求 VS-REQ-001..012，每平面 ≥2 条；每条含 `requirement_id / description / plane / status / covered_by`（golden 场景 + 平面 + 断言 ref）。
- 同步镜像：`.ai/evidence/T-0087/contract-planes/requirement-registry.yaml`（byte 级一致，`test_evidence_registry_mirror_matches_canonical` 防漂移）。
- conformance 计算（`conformance.py`，纯确定性断言，不调 AI）：
  - `run_check`：9 类断言全部对真实证据文件或 `loop_core.state_machine` 执行；
  - 需求状态：covered_by 为空 → `missing`；有失败断言 → `partial`；全过 → `implemented`；
  - **gate_decision（fail-closed）**：全部需求 `implemented` 且 failed_assertions==0 → `PASS`；任一需求 `missing`/`partial` 或断言失败 → `FAIL`。CLI 退出码 0/1。
- 测试双分支：真实证据 → PASS；篡改 `delivery_decision.final_decision=NOGO` → FAIL（断言真实失败）；清空 covered_by → FAIL（missing）；ref 指向不存在断言 → FAIL。

## 5. 文件清单（U2 交付物）

| 文件 | 角色 |
|---|---|
| `tests/vertical_slice/conformance.py` | conformance 引擎 + CLI（断言执行、需求状态计算、报告生成、fail-closed 门禁） |
| `tests/vertical_slice/contract_planes/planes.yaml` | 4 观测平面定义 |
| `tests/vertical_slice/contract_planes/scenario.schema.json` | golden 场景 JSON Schema（draft 2020-12） |
| `tests/vertical_slice/contract_planes/registry.schema.json` | 需求注册表 JSON Schema |
| `tests/vertical_slice/contract_planes/golden_scenarios/VS-GS-001..004.json` | 4 个 golden 场景 fixtures（4 平面断言） |
| `tests/vertical_slice/contract_planes/requirement-registry.yaml` | 需求注册表（权威版本） |
| `tests/vertical_slice/test_contract_planes.py` | 契约平面测试（schema 校验 + golden 断言 + 门禁双分支 + 镜像防漂移） |
| `.ai/evidence/T-0087/contract-planes/requirement-registry.yaml` | 注册表证据镜像 |
| `.ai/evidence/T-0087/contract-planes/conformance-report.json` | conformance 报告（gate_decision=PASS，CLI/测试实时生成） |
| `.ai/evidence/T-0087/contract-planes/design.md` | 本设计证据 |

## 6. 验收对照（T-0087 AC-04 / AC-05）

- **AC-04**（契约平面 ≥4 + conformance 报告 + gate_decision 门禁）：✅ `planes.yaml` 4 平面；conformance.py 生成报告；PASS/FAIL 两分支均有测试（`test_real_evidence_gate_is_pass` / `test_gate_fails_closed_on_failed_assertion` / `test_gate_fails_closed_on_missing_coverage` / `test_gate_fails_closed_on_unknown_ref`）。
- **AC-05**（需求注册表落盘，含需求 ID/描述/对应平面/覆盖状态）：✅ `requirement-registry.yaml`（tests 权威版 + .ai/evidence 镜像，byte 一致防漂移）。
- 无业务源码改动；现有 `test_vertical_slice.py` 86 项全部保持通过（回归见验收证据）。
