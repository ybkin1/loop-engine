# T-0109 F3 gates.yaml 分层 — 修复证据

## 改动

### 1. `.ai/gates.yaml`：active 域（102 → 66 条）
保留 active 域：当前治理纪元（T-0081+，29 条）+ 内核判定消费的 phase 相关
历史 gate（37 条：user-implementation×32 / user-quality / user-delivery /
real-project-*-architecture/delivery-governance-*-design/review×4）。头部注释
说明分层与归档指针。

### 2. `.ai/archive/gates-archive.yaml`（新增）：36 条历史记录
- **仅移域不删记录**：归档记录逐字段 verbatim（与迁移前快照核对 0 差异）；
  union(active, archive) == 原 102 条记录集，无删、无重、互斥。
- 归档域 = 纯历史记录（T-0002..T-0080 的 lab 纪元 gate：state-sync /
  user-activation / user-cleanup / user-design / user-repair / user-installation /
  user-closeout-review* / user-discovery-approval / user-method-repair-design /
  user-review-only / repair-only / review-rerun / baseline-approval-only /
  installation 家族 / scope-expansion / user-acceptance 等 22 类 gate_type）。

### 3. `.ai/policies/forbidden-actions.yaml`（新增）：forbidden 模板外提
- 7 个命名 policy（含 forbidden_actions 完整列表）：standard-v1（9 项标准模板）、
  standard-core-v1、agents-md-only-v1、agents-md-deploy-v1、agents-md-business-v1、
  agents-md-external-v1、agents-md-acceptance-v1。
- 外提规则：**仅 active 域精确重复 >=2 的 forbidden 集合**外提为
  `forbidden_policy: <id>` 引用（26 条 gate）；唯一（任务特有）列表保持内联
  （40 条）——记录零丢失，消费方等价。
- 引用解析 + policy 展开 == 迁移前原列表（快照逐项核对 0 差异）。

### 4. `loop_core/schemas/gate.schema.json`：gate_type 枚举化 + 兼容
- `gate_type.enum`：覆盖 active + archive 全部 29 个既有取值 + 既有设计值
  user-plan-approval（30 项）——新增取值须先过 schema 更新（gate 决策）。
- 新增 `forbidden_policy`（string）属性。
- `approval_source.enum` 补历史值：legacy_pre_field / explicit_user_plan_approval /
  explicit_user_directive（仅移域不删记录——历史记录值必须可校验）。
- `notes` / `allowed_actions` items 放宽为 string|object（历史记录存在
  inline-map 条目：G-T-0027-DELIVERY notes[0]、G-T-0055-CLOSEOUT-REVIEW /
  G-T-0080-RUNTIME-ACCEPTANCE allowed_actions 分支；不改写历史数据）。

## 归档规则（纯函数，测试可复算）
gate 满足以下**任一** → 必须留在 active 域（这些是内核判定实际消费的记录）：
1. 任务编号 >= 81（当前治理纪元）
2. status == pending（待决策）
3. id == state.current_gate_id（resolve_gate_status 交叉引用）
4. 含 phase 字段（enforcement_hub heuristic 消费）
5. id 含阶段模式（`S\d+-<phase>`，check_phase_constraints gate 前缀匹配消费）
6. gate_type 命中任一 phase heuristic（enforcement_hub._has_approved_user_gate：
   `phase_slug in gate_type or phase_value in gate_type or gate_phase in {...}`）

## 归档等价证据（AC-01）

迁移前快照（迁移脚本执行前保存，102 条含 G-T-0109）逐项核对：
- archive 36 条 vs 快照对应记录：**逐字段 diff = 0**（verbatim）
- active 66 条 vs 快照对应记录：除 forbidden_actions→forbidden_policy 外提外
  **逐字段 diff = 0**
- policy 展开 vs 快照原 forbidden_actions 列表：**mismatch = 0**
- union == 102、互斥、无重复（迁移脚本断言 OK）

## 测试（tests/test_t0109_f3_gates_layering.py，18 passed）

- **TestGateSchemaValidation（AC-01）**：active + archive 全部记录过
  `jsonschema.validate`（fail-closed）；gate_type 枚举覆盖全部记录取值；
  forbidden_policy 属性为 string。
- **TestActiveDomainEquivalence（AC-01）**：归档规则(完整记录集) == 归档后
  `.ai/gates.yaml` 逐记录等价（规则可复算 ⇒ 归档前后 load_gates active 域等价）；
  union == 102 无删无重互斥；归档记录字段完整（recorded_at 可审计：35/36，
  G-T-0055-BASELINE-AUDIT 历史本身缺 recorded_at，verbatim 保留）；
  current_gate_id 与 pending gate 留在 active。
- **TestKernelBehaviorEquivalence**：12 个 phase 的 enforcement heuristic
  （approved + explicit_user 判定）逐 phase 完整集 == active 域；check_phase_constraints
  的 gate-id 前缀匹配逐 phase 等价；resolve_gate_status(current_gate_id) 在
  active 域恰一条且 approved。
- **TestForbiddenPolicyReferences**：policy 引用全部可解析；policy 展开 ==
  预期原列表（零丢失）；外提 gate 无残留内联列表；唯一列表保持内联；
  外提仅限精确重复 >=2 集合。

## 消费方核对（先 grep 后改，行为不变）
- hooks（gate_guard/_hook_state/hook_common/loop_enforcement/session_brief/
  role_isolation/loop_auto_activate）：全部只读 `.ai/gates.yaml`；所需记录
  （current task gate G-T-0109-REQUIREMENTS、current_gate_id、pending、phase
  heuristic）全部留在 active 域 → 行为不变；hook_common 的 phase_gates 映射
  为 gate_type 精确匹配（无记录命中，前后皆空）→ 不变。
- validate_state / audit_handoff / continuity_producer：pending（无）+ 当前任务
  gate + current_gate_id 均在 active → 判定不变。
- governance_metrics / dashboard / status_dashboard 等 advisory 读方：改为
  active 域视图（分层语义本意；非判定路径，不构成行为回归）。
- 内核判定（enforcement_hub/check_phase_constraints/resolve_gate_status）：
  归档规则按消费语义逐项排除 + 等价测试逐 phase 实证（上节）。

## 约束自查

| 硬约束 | 实证 |
|--------|------|
| hooks/ 零改动 | `git diff HEAD -- hooks/` = 0 行 |
| 内核判定零触碰 | 本特性仅动 .ai/ 数据文件 + schemas + 新测试；loop_core 判定代码未触碰 |
| 归档仅移域不删记录 | union==102、无删无重、归档 verbatim 0 diff（快照证据） |
| fail-closed 不变 | gate 文件缺失/解析失败阻断语义未动（无代码改动）；schema 校验失败即测试失败 |
| 写路径限 allowed_paths | .ai/gates.yaml、.ai/archive/、.ai/policies/、loop_core/schemas/、tests/ |
| 版本文件不改 | 未触碰 |

## 回归
- 既有 gates 消费方套件全绿：test_gate_guard_lifecycle / test_governance_metrics /
  test_slo_gate / test_slo_consistency / test_status_dashboard / test_dashboard /
  test_approval_ledger / test_context_controller / test_governance_consistency
  （257 passed）；enforcement/hooks/operations/cross_layer_safety/idle_semantics
  （248 passed）；human_review_packet/resume_payload/guard_health/hard_constraints/
  role_isolation/gate_feedback/verdicts/veto/evals/certification（407 passed）。
- test_t0108_fixes 中 2 项 validate_state 实仓回归：因 gates.yaml 为 continuity
  source，F3 改动后报唯一 `PROJECT_CONTINUITY_SOURCE_DRIFT: .ai/gates.yaml`
  （exit 2）——预期 drift，主会话 repair_continuity 后恢复（HEAD 基线验证全过）。

## 遗留
1. continuity drift（预期）：主会话收尾 repair_continuity + manifest 同步
   （design F3 必须保持③：gates.yaml/archive/policies 路径变更须入 manifest）。
2. `.ai/archive/gates-archive.yaml` 与 `.ai/policies/forbidden-actions.yaml`
   是否入 continuity source_manifest 由主会话 repair/续产流程决定
   （当前 manifest 不含新文件，load 侧不校验未知文件 → 无额外 drift）。
