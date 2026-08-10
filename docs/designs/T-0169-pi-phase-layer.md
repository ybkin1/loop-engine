# T-0169: Pi mini-loop Phase 层（项目级生命周期）详细拆解

> 性质：设计 + 实施拆解（P0 全量，非壳子）
> 日期：2026-08-10 | 来源：pi agent 审计（Phase 层为核心差距）+ 用户确认
> 原则：**阶段是质量载体不是流程关卡**——阶段流转由机器质量门判定自动进行，
> 用户只审批价值决策（技术选型/需求取舍/边界）。

---

## 0. 完成保障机制（回答"怎么保证 100%，不是壳子"）

**不能靠承诺，靠机器可判定的完成标准**。本升级完成后用 loop 工程自身工具链
自我验证（dogfooding）：

1. **追溯矩阵**（trace.ts）：AC ↔ 实现文件 ↔ 测试用例逐条映射，断链 = 未完成，
   完成报告逐 AC 列证据（文件路径 + 测试名）
2. **质量门 L1/L2**：tsc 全绿 + node --test 全绿（每 AC 必有测试）+ health_check
3. **验收清单**：交付时逐 AC 给出"实现位置 + 测试证据 + 演示输出"，未完成的
   **明确列出"未完成"**（不模糊、不省略）
4. **用户验收权**：你可要求任何演示；发现壳子指出来，补齐后再交付

**"完整"的定义**（每组件）：
- 数据结构：字段落地 + 迁移兼容（旧数据不破坏）
- 状态机：转换逻辑 + 非法转换拒绝（测试覆盖）
- 质量门：机器检查产出物清单（缺文件 FAIL / 全齐 PASS，测试覆盖）
- 集成：命令可调 + 注入生效 + validate 一致（测试覆盖）
- 文档：拆解文档 + README 更新

---

## 1. 数据结构（state.json 扩展）

```json
{
  "schema_version": 1,
  "project_name": "...",
  "phase": "S1-requirements",
  "phase_status": "in_progress",
  "phase_gates": {
    "S1-requirements": { "status": "completed", "completed_at": "..." }
  },
  "current_task_id": "...",
  "loop_mode": "STANDARD"
}
```
- `phase`：当前阶段（S1~S6 主链；S7+ 可选扩展）
- `phase_gates`：各阶段门状态（completed 后不可回退——只进不退，对齐 fail-closed）
- 任务挂阶段：`task.phase`（task-start 自动挂当前 phase）
- 迁移：旧 state.json 无 phase → 默认 `S1-requirements`（或按已有任务推断，有任务且 approved → S4）

## 2. 阶段定义（对齐 zcode 语义的精简主链）

| 阶段 | 产出物（templates/ 下模板定义） | 阶段完成判定（机器检查） |
|------|-------------------------------|------------------------|
| S1-requirements | `requirements.md`（功能/非功能需求 + AC 清单） | 文件存在 + 含 `## 功能需求` + `## 验收标准` 节 |
| S2-architecture | `architecture.md`（系统架构 + 技术选型 ADR） | 文件存在 + 含 `## 架构` + `## 决策` 节 |
| S3-detail-design | `interface-contract.md` + `data-model.md` | 两文件存在 + 非空 |
| S4-implementation | 代码 + 测试（任务级，无阶段文件） | 该阶段任务 ≥1 且全部终态（done/review_passed） |
| S5-testing | `test-report.md`（用例数/覆盖/结果） | 文件存在 + 含 `## 结果` 节 |
| S6-delivery-ready | `deployment-plan.md` + `release-checklist.md` | 两文件存在 + 非空 |

**阶段完成判定是文件清单机器检查**（checkPhaseOutputs），不是"AI 说完成了"。

## 3. 阶段状态机（phase.ts）

```
S1 → S2 → S3 → S4 → S5 → S6（顺序，只进不退）
转换条件：checkPhaseOutputs(当前阶段) 全过 → 自动进入下一阶段
例外：S4-implementation 的完成 = 阶段任务全部终态
非法转换（跳级/回退）→ 拒绝 + 事件留痕
```

## 4. 模板注入

- 模板源：本拆解第 2 节产出物结构（精简版；zcode 39 模板的适配后续按需扩充）
- 位置：`~/.pi/agent/loop/<project>/templates/<phase>/<file>.md`（首次 /phase-start 自动生成）
- 注入：before_agent_start 按当前 phase 注入"本阶段产出要求"（文件清单 + 结构要求）
  ——agent 知道"应该产出什么"，不是自由发挥

## 5. 命令

| 命令 | 功能 |
|------|------|
| `/phase-start <phase>` | 进入阶段（生成模板文件 + 更新 state + 事件） |
| `/phase-complete [phase]` | 触发阶段质量门（checkPhaseOutputs）→ 通过自动进下一阶段 / 不通过列出缺失 |
| `/phase-status` | 当前阶段 + 各阶段 gate 状态 |
| `/project-status` | 阶段进度 + 任务完成率 + 各阶段任务数（审计 P3 仪表盘的基础版） |

## 6. 集成

- migrate：旧 state 补 phase 字段（默认 S1；有终态任务推断 S4）
- before_agent_start：注入当前阶段 + 产出要求（替代/增强现有注入）
- task-start：新任务自动挂 `task.phase = 当前阶段`
- validate：phase 一致性检查（phase_gates 记录与 state.phase 一致；S4 阶段完成需任务终态）
- /quality：阶段维度（各阶段任务数/完成率）
- 事件溯源：phase_started/phase_completed/phase_gate_failed 事件类型

## 7. 测试（phase.test.ts，每 AC 必有测试）

1. 阶段定义完整性（6 阶段产出物清单非空）
2. 转换逻辑：顺序转换 ✓ / 跳级拒绝 / 回退拒绝
3. checkPhaseOutputs：缺文件 FAIL / 全齐 PASS（构造样例验证）
4. S4 完成判定：阶段任务终态 → 完成
5. 迁移：旧 state 无 phase → 默认值；有终态任务 → S4
6. 命令注册（smoke 风格）
7. 注入内容含阶段产出要求

## 8. AC 清单（交付验收用）

- [AC-01] state.json phase/phase_gates 字段 + 迁移兼容（旧数据可读）
- [AC-02] phase.ts 状态机：顺序转换/非法转换拒绝（测试）
- [AC-03] checkPhaseOutputs 机器判定（缺文件 FAIL/全齐 PASS，测试）
- [AC-04] 模板生成：/phase-start 生成模板文件（6 阶段产出物结构）
- [AC-05] 命令：/phase-start /phase-complete /phase-status /project-status 可用
- [AC-06] before_agent_start 注入当前阶段 + 产出要求
- [AC-07] task-start 自动挂 phase；S4 完成 = 任务终态
- [AC-08] validate 扩展 phase 一致性；事件类型 phase_*
- [AC-09] 测试全绿（node --test）+ tsc + health_check
- [AC-10] 追溯矩阵：AC↔实现↔测试无断链（自查）
- [AC-11] 端到端演示：模拟 S1→S6 全链（构造数据，不真实跑 LLM）

## 9. 边界

- P0 只做阶段主链 S1~S6；S7+（集成/性能/维护）后续
- 模板为精简版（结构要求），zcode 39 模板深度适配后续
- 阶段流转自动（质量门），不新增用户审批点（对齐"反流程"原则）
