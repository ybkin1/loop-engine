# 阶段 Loop 正式状态机

本文定义 Loop 工程治理的阶段级状态机。它是角色间交接协议（`handoff-standard.md`）
的上层——角色 Loop 在阶段内部运行，阶段 Loop 在角色之上编排。

与任务状态、gate 状态、产物生命周期三者的关系见 `references/governance-lifecycle.md`。
阶段状态机不替代这四套状态，而是把它们串成"一个阶段从哪里开始、到哪里算结束"的完整流程。

---

## 1. 阶段状态枚举

```
PHASE_START
    → ENTRY_CHECK
        → [入口条件不满足] → BLOCKED_AT_ENTRY（升级给用户）
        → [入口条件满足] → ROLE_EXECUTION

ROLE_EXECUTION
    → [所有角色完成其 Loop] → INTEGRATION
    → [角色产出存在冲突] → ROLE_EXECUTION（打回相关角色返工）

INTEGRATION
    → [集成检查通过] → QUALITY_CHECK
    → [集成检查失败] → ROLE_EXECUTION（打回相关角色，附冲突详情）

QUALITY_CHECK
    → [质量门全部 PASS] → HUMAN_REVIEW_PACKET
    → [质量门存在 BLOCKED] → ROLE_EXECUTION（打回对应角色修复）

HUMAN_REVIEW_PACKET
    → [包已组装] → WAITING_FOR_HUMAN_REVIEW

WAITING_FOR_HUMAN_REVIEW（阻塞态——gate_guard hook 阻断一切写入）
    → [用户决定 APPROVE_NEXT_PHASE] → APPROVED_NEXT_PHASE（阶段结束，进入下一阶段）
    → [用户决定 RETURN_FOR_REWORK] → 回到 ROLE_EXECUTION（指定返工角色和范围）
    → [用户决定 CHANGE_DIRECTION] → CHANGE_DIRECTION（阶段终止，重新规划）
```

---

## 2. 每个状态的定义

### 2.1 PHASE_START

- **含义**：阶段已被主控会话启动。stage-summary 文件初始化，Handoff 已更新阶段名。
- **触发条件**：上一阶段的 gate 被用户 APPROVE_NEXT_PHASE；或项目首次启动时用户指定起始阶段。
- **退出条件**：主控已完成启动检查（读取 state.yaml、gates.yaml、task_graph.yaml，运行 validate_state.py 且 exit 0），立即进入 ENTRY_CHECK。
- **不允许停留**：PHASE_START 是瞬时状态，不得在此状态等待任何异步操作。

### 2.2 ENTRY_CHECK

- **含义**：主控验证当前阶段的所有入口条件是否满足。
- **触发条件**：PHASE_START 完成启动检查后自动进入。
- **检查清单**（每个阶段有独立子集，此处为通用清单）：
  1. 上一阶段的交付物文件全部存在且可读（路径引用不悬空）
  2. 上一阶段的 Human Review Packet 中 APPROVE_NEXT_PHASE 记录存在
  3. 本阶段所依赖的角色代理（subagent）配置文件齐全（SKILL.md + references 目录存在）
  4. 不存在与本阶段冲突的 pending gate（例如上一阶段留下了未决 gate）
  5. validate_state.py exit 0
- **退出条件**：
  - 全部检查通过 → 进入 ROLE_EXECUTION
  - 任一检查失败 → 进入 BLOCKED_AT_ENTRY（升级给用户，附具体缺失项列表）
- **BLOCKED_AT_ENTRY** 是终止态：在用户决策前不得继续。用户的选项：补充缺失项并重试，或跳过该阶段（需明确 gate）。

### 2.3 ROLE_EXECUTION

- **含义**：阶段内各角色并行或串行执行自己的角色 Loop。主控负责启动角色 subagent、收集产出、检测冲突。
- **触发条件**：ENTRY_CHECK 通过。
- **角色 Loop**（每个角色内部的小循环）：
  1. 角色读取输入（上游交付物 + 自己的合同标准）
  2. 角色执行专业工作（设计/编码/测试/…）
  3. 角色产出交付物（按合同"输出产物"节）
  4. 角色按合同"质量标准"自检
  5. 角色把产出签名为 PASS / BLOCKED / PASS_WITH_DEBT
- **主控的编排规则**：
  - 角色启动顺序由阶段计划（project-manager 产出）决定
  - 如果一个角色的输入依赖另一个角色的输出，必须等上游角色签名后才能启动
  - 没有依赖的角色可以并行启动
- **退出条件**：
  - 所有角色完成其 Loop 且至少一份产出签名不为空 → 进入 INTEGRATION
  - 角色产出中存在冲突（A 角色 PASS 但引用了 B 角色尚未完成的产物） → 打回相关角色，继续 ROLE_EXECUTION
  - 角色报告 BLOCKED（因自身输入不满足） → 主控评估是否打回上游角色或升级给用户

### 2.4 INTEGRATION

- **含义**：主控对阶段内所有角色产出做跨角色兼容性检查。这是阶段状态机独有的检查——角色内部不负责与其他角色的兼容性。
- **触发条件**：ROLE_EXECUTION 完成（所有角色已签名）。
- **集成检查清单**：
  1. **需求一致性**：产品经理的需求文档版本与架构师引用的需求版本是否一致
  2. **架构一致性**：系统架构师的模块清单是否与模块架构师的接口契约一一对应（无遗漏、无多余）
  3. **实现一致性**：开发工程师的代码是否落在模块架构师定义的模块边界内（依赖方向不违反架构师的依赖规则）
  4. **质量一致性**：质量工程师的测试范围是否覆盖了开发工程师提交的全部模块（无"没测过的代码"）
  5. **版本一致性**：所有角色引用的外部依赖版本是否一致（架构师选的版本 = 开发工程师锁定的版本 = 安全工程师审计的版本）
  6. **冲突已解决**：阶段内发生的角色冲突是否全部有用户裁决记录（无"待定"状态冲突）
- **退出条件**：
  - 全部 6 项通过 → 进入 QUALITY_CHECK
  - 任一失败 → 打回 ROLE_EXECUTION，附带"哪个角色、哪个产出、与哪个角色的哪个产出不一致"的精确描述
- **集成检查的执行者**：主控（不是任何专业角色）。主控只做"引用是否匹配"这种可机械验证的检查，不做专业判断。

### 2.5 QUALITY_CHECK

- **含义**：运行质量门禁（质量工程师 + 安全工程师 + 独立评审员的自动化/半自动化检查）。
- **触发条件**：INTEGRATION 通过。
- **检查清单**：
  1. 质量工程师的 run_quality_gates.py 执行结果：lint / typecheck / test / coverage / audit / build，overall 必须 PASS
  2. 安全工程师的 run_security_scan.py 执行结果：HIGH 和 CRITICAL 漏洞数必须为 0
  3. 独立评审员的 review-checklist.md 检查结果：无 unreviewed 的文件
  4. 架构师的依赖分析结果：无循环依赖
- **退出条件**：
  - 全部 PASS → 进入 HUMAN_REVIEW_PACKET
  - 任何 BLOCKED → 打回 ROLE_EXECUTION（精确定位到需要返工的角色和文件）
- **QUALITY_CHECK 不替代角色自检**：角色在 ROLE_EXECUTION 内应已完成自检。QUALITY_CHECK 是跨角色的质量汇总，不是替角色跑测试。

### 2.6 HUMAN_REVIEW_PACKET

- **含义**：主控把本阶段所有角色的产物、集成检查结果、质量检查结果组装成一份人类可读的交付包。这是给用户看的 gate 材料——不是给 AI 看的。
- **触发条件**：QUALITY_CHECK 通过。
- **包的内容**（基于 `templates/human-review-packet.md` 模板）：
  1. 这个阶段做了什么（三句话以内）
  2. 完成了什么（3-5 个要点）
  3. 没有完成什么（如实列出，附原因）
  4. 质量状态（小表格：质量门 / 安全门 / 架构一致性）
  5. 关键决策（附理由和备选方案）
  6. 风险（已知风险 + 不管会怎样）
  7. 下一步需要你决定（3-5 个非技术用户能回答的问题）
- **退出条件**：包已写入 `.ai/evidence/<phase>/human-review-packet.md`，且内容无空字段 → 进入 WAITING_FOR_HUMAN_REVIEW。
- **主控的义务**：写完包之后不得继续推进。必须立即转为 WAITING_FOR_HUMAN_REVIEW。

### 2.7 WAITING_FOR_HUMAN_REVIEW

- **含义**：阶段暂停，等待用户阅读 Human Review Packet 并做出决定。这是**全停状态**——gate_guard hook 阻断一切写入。
- **触发条件**：HUMAN_REVIEW_PACKET 完成。
- **用户的三类决定**（精确语法——用户消息中必须包含以下三组关键词之一）：
  1. **APPROVE_NEXT_PHASE**：用户认可本阶段成果，批准进入下一阶段。
     - 关键词：`批准下一阶段` / `进入下一阶段` / `继续`
     - 效果：阶段状态变为 APPROVED_NEXT_PHASE，主控在用户发出"执行下一阶段"后初始化下一阶段的 PHASE_START。
  2. **RETURN_FOR_REWORK**：用户认为本阶段有不足，要求特定角色返工。
     - 关键词：`返工` / `重新做` / `补充` + 角色或文件
     - 效果：回到 ROLE_EXECUTION，但只重新执行用户指定的角色范围。返工完成后重新走 INTEGRATION → QUALITY_CHECK → HUMAN_REVIEW_PACKET。
  3. **CHANGE_DIRECTION**：用户认为本阶段方向错误，要求重新规划。
     - 关键词：`改方向` / `重新规划` / `换方案` / `不做这个阶段了`
     - 效果：阶段标记为 CHANGE_DIRECTION，当前阶段产物归档（不删除），项目回到规划态。用户需重新指定起始阶段。
- **注意**：用户说了"批准"但三个关键词都不匹配的，主控必须追问："你是在批准当前阶段进入下一阶段（APPROVE_NEXT_PHASE）、要求返工（RETURN_FOR_REWORK）、还是改变方向（CHANGE_DIRECTION）？"
- **退出条件**：用户发出匹配的消息 → 进入对应的终止态。

### 2.8 APPROVED_NEXT_PHASE（终止态）

- **含义**：本阶段已被用户批准，阶段完结。主控等待用户发出"执行下一阶段"的指令后，启动下一阶段的 PHASE_START。
- 记录：gates.yaml 增加 APPROVE_NEXT_PHASE 决策记录，包含用户原消息、时间戳。

### 2.9 RETURN_FOR_REWORK（回退态）

- **含义**：回到 ROLE_EXECUTION，按用户指定的范围返工。不是状态的终点，是回到 ROLE_EXECUTION 之前的"标记"。

### 2.10 CHANGE_DIRECTION（终止态）

- **含义**：本阶段被用户终止，项目方向改变。当前阶段的所有产物归档到 `.ai/evidence/<phase>/archived/`，gates.yaml 记录 CHANGE_DIRECTION 决策和原因。

---

## 3. 阶段不能自动跳转的规则

以下规则是硬性的——不可通过任何手段绕过：

1. **PHASE_START 后不能跳过 ENTRY_CHECK**。即使主控"觉得入口条件肯定满足"，也必须逐一验证并记录。
2. **ROLE_EXECUTION 后不能跳过 INTEGRATION**。角色独立 PASS 不等于彼此兼容。
3. **INTEGRATION 后不能跳过 QUALITY_CHECK**。集成一致性不等于质量门通过。
4. **QUALITY_CHECK 后不能跳过 HUMAN_REVIEW_PACKET 直接进入下一阶段**。这是最关键的规则：无论质量门多绿、测试全过、架构多完美，**必须停在人工评审点**。用户必须阅读交付包并做出决定。
5. **在 WAITING_FOR_HUMAN_REVIEW 期间不得进行任何写入性工作**（gate_guard hook 强制）。唯一例外是写 gates.yaml 决策记录（决策记录豁免，`references/decision-rules.md` 说明原因）。
6. **用户批准后不得自动进入下一阶段**。批准 ≠ 执行。用户必须再发出一条明确的"执行"指令，主控才能开始下一阶段的 PHASE_START。

---

## 4. 人的三类决定

阶段 Loop 的终局永远是人的决定。以下是三种决定及其语义：

| 决定 | 用户说什么 | 系统做什么 | 阶段状态 |
|---|---|---|---|
| APPROVE_NEXT_PHASE | "批准下一阶段" / "进入下一阶段" / "继续" | 记录批准，等待执行指令后启动下一阶段 | APPROVED_NEXT_PHASE |
| RETURN_FOR_REWORK | "返工 <角色>" / "重新做 <文件>" / "补充 <内容>" | 回到 ROLE_EXECUTION，仅执行用户指定范围的返工，返工完成后重新走完整状态链 | ROLE_EXECUTION（重入） |
| CHANGE_DIRECTION | "改方向" / "重新规划" / "换方案" / "不做这个阶段了" | 归档当前阶段产物，项目回到规划态，等待用户指定新方向 | CHANGE_DIRECTION |

### 决定记录的格式

每个决定记录在 gates.yaml 中，必须包含以下字段：

```yaml
- gate_id: "G-PHASE-<阶段编号>"
  phase: "<阶段名称>"
  decision: "approved_next_phase | return_for_rework | change_direction"
  approval_text: "<用户原消息>"
  approval_actor: "user"
  approval_source: "explicit_user_message"
  timestamp: "<ISO 8601>"
  rework_scope: "<仅 RETURN_FOR_REWORK 时填写：返工的精确角色和文件范围>"
  direction_change_reason: "<仅 CHANGE_DIRECTION 时填写：用户说明的方向变更原因>"
```

---

## 5. 十二个软件工程阶段定义

以下 12 个阶段覆盖一个软件项目的完整生命周期。每个阶段的定义包含：阶段编号与名称、阶段目的、参与角色、角色 Loop 重点、阶段交付物、放行条件。

每个阶段进入 ENTRY_CHECK 时，除通用入口条件外，还有阶段特定的入口条件。

---

### 阶段 1：需求分析

- **编号**：PHASE-01
- **目的**：把用户的业务需求转化为结构化的需求文档，确定功能范围、优先级和非功能性需求。
- **参与角色**：产品经理（主导）
- **角色 Loop 重点**：
  - 产品经理：收集需求 → 整理功能清单 → 确定优先级 → 产出需求文档
- **阶段交付物**：
  - `requirements.md` — 功能需求清单、非功能性需求、范围边界
  - `feature-priority.csv` — 功能优先级矩阵
- **入口条件**：无（这是第一个阶段，或用户明确要求"从需求开始"）
- **放行条件**：
  - 需求文档章节完整（功能需求 / 非功能需求 / 范围边界 / 成功标准）
  - 至少一项功能有明确的 User Outcome（用户能得到什么）
  - 非功能需求包含 QPS / 延迟 / 可用性 / 安全等级中至少三项

---

### 阶段 2：架构设计

- **编号**：PHASE-02
- **目的**：基于需求文档设计系统整体架构——模块划分、依赖方向、技术选型。
- **参与角色**：系统架构师（主导）、产品经理（提供需求澄清）
- **角色 Loop 重点**：
  - 系统架构师：分析需求 → 设计模块清单 → 定义依赖规则 → 技术选型 → 产出 architecture.md + dependency_report.json
- **阶段交付物**：
  - `architecture.md` — 架构概览、模块清单、数据流、依赖规则、ADR
  - `dependency_report.json` — 依赖分析结果（初始基线）
- **入口条件**：需求分析阶段 APPROVED_NEXT_PHASE 且 requirements.md 存在
- **放行条件**：
  - architecture.md 7 个章节齐全（架构概览 / 模块清单 / 数据流 / 依赖规则 / 技术约束 / 演进路线 / ADR）
  - 每个技术选型至少有 1 条可验证理由
  - 依赖分析工具可运行（初始状态无循环依赖或循环依赖被标注为 baseline）

---

### 阶段 3：详细设计

- **编号**：PHASE-03
- **目的**：基于系统架构，把每个模块的内部拆解为接口契约和组件设计。
- **参与角色**：模块架构师（主导）、系统架构师（架构一致性审查）
- **角色 Loop 重点**：
  - 模块架构师：接收模块清单 → 拆解接口 → 设计组件 → 产出 interface-contract-spec.md
  - 系统架构师：审查接口是否违反依赖方向规则
- **阶段交付物**：
  - `interface-contract-spec.md` — 每个模块的接口定义、数据模型、错误类型
  - `module-component-map.json` — 模块到组件的映射
- **入口条件**：架构设计阶段 APPROVED_NEXT_PHASE 且 architecture.md 存在
- **放行条件**：
  - 架构师定义的每个模块都有对应的接口契约（无遗漏）
  - 接口契约中不存在循环依赖（模块 A 的接口依赖模块 B，模块 B 的接口又依赖模块 A）
  - 每个接口定义了输入、输出、错误类型

---

### 阶段 4：测试设计

- **编号**：PHASE-04
- **目的**：基于需求文档和接口契约设计测试策略——测试用例、覆盖率目标、安全测试范围。
- **参与角色**：质量工程师（主导）、安全工程师（安全测试范围）
- **角色 Loop 重点**：
  - 质量工程师：分析需求和接口 → 设计测试用例 → 定义覆盖率目标 → 产出 test-plan.md
  - 安全工程师：分析接口 → 确定安全测试范围 → 产出 security-test-scope.md
- **阶段交付物**：
  - `test-plan.md` — 测试策略、用例清单、覆盖率目标、质量门配置
  - `security-test-scope.md` — 安全测试范围、OWASP 覆盖项
- **入口条件**：详细设计阶段 APPROVED_NEXT_PHASE 且 interface-contract-spec.md 存在
- **放行条件**：
  - 测试计划覆盖了接口契约中定义的全部接口
  - 覆盖率目标不低于 config.yaml 中 quality_gates.coverage_threshold
  - 安全测试范围覆盖了所有涉及用户输入、认证、授权的接口

---

### 阶段 5：编码

- **编号**：PHASE-05
- **目的**：按照架构设计和接口契约实现代码。
- **参与角色**：开发工程师（主导）、模块架构师（接口实现一致性检查）
- **角色 Loop 重点**：
  - 开发工程师：接收接口契约 → 实现代码 → 自检（按 coding-standards.md） → 产出源代码 + implementation-notes.md
- **阶段交付物**：
  - 源代码文件（按架构定义的模块目录结构）
  - `implementation-notes.md` — 实现决策记录、已知限制、与接口契约的偏差说明
- **入口条件**：测试设计阶段 APPROVED_NEXT_PHASE 且 test-plan.md 存在
- **放行条件**：
  - 架构定义的每个模块至少有一个源文件
  - 所有源文件的依赖方向不违反架构师的依赖规则（可由 dependency_report.json 验证）
  - 没有 TODO 标记留在代码中（或每个 TODO 在 implementation-notes.md 中有解释）

---

### 阶段 6：单元测试

- **编号**：PHASE-06
- **目的**：为编码阶段产出的源代码编写并运行单元测试，确保代码符合接口契约。
- **参与角色**：开发工程师（编写测试）、质量工程师（验证覆盖率和测试质量）
- **角色 Loop 重点**：
  - 开发工程师：为每个模块编写单元测试 → 运行测试 → 自检覆盖率
  - 质量工程师：运行 run_quality_gates.py → 检查覆盖率、lint、typecheck → 签名
- **阶段交付物**：
  - 测试代码文件
  - `unit-test-report.md` — 测试执行结果、覆盖率报告
- **入口条件**：编码阶段 APPROVED_NEXT_PHASE 且源代码存在
- **放行条件**：
  - 所有单元测试通过（exit 0）
  - 覆盖率 >= config.yaml 中 quality_gates.coverage_threshold
  - lint 和 typecheck 通过（threshold 均为 0）

---

### 阶段 7：集成

- **编号**：PHASE-07
- **目的**：验证各模块在实际组合时能正常工作，模块间的接口调用正确。
- **参与角色**：开发工程师（编写集成测试）、模块架构师（接口契约一致性审查）、质量工程师（运行集成测试和门禁）
- **角色 Loop 重点**：
  - 开发工程师：编写集成测试 → 运行集成测试
  - 模块架构师：审查集成测试是否覆盖了接口契约中的每个接口
  - 质量工程师：运行门禁（含集成测试），签名
- **阶段交付物**：
  - 集成测试代码
  - `integration-test-report.md` — 集成测试结果、接口覆盖率
- **入口条件**：单元测试阶段 APPROVED_NEXT_PHASE 且 unit-test-report.md 全部 PASS
- **放行条件**：
  - 所有集成测试通过
  - 每个接口契约定义的接口至少有一个集成测试覆盖
  - 质量门 overall: PASS

---

### 阶段 8：功能测试

- **编号**：PHASE-08
- **目的**：从用户视角验证系统是否满足需求文档中定义的功能。
- **参与角色**：质量工程师（主导）、产品经理（需求满足度确认）
- **角色 Loop 重点**：
  - 质量工程师：按 test-plan.md 执行功能测试 → 记录测试结果 → 产出 functional-test-report.md
  - 产品经理：逐项确认需求是否被满足 → 签名
- **阶段交付物**：
  - `functional-test-report.md` — 功能测试结果、每个需求项的覆盖状态
- **入口条件**：集成阶段 APPROVED_NEXT_PHASE 且 integration-test-report.md 全部 PASS
- **放行条件**：
  - requirements.md 中每个功能项都有对应的功能测试结果
  - 无 CRITICAL 或 HIGH 级别的功能缺陷
  - 产品经理对至少 80% 的功能项签名确认

---

### 阶段 9：修改优化

- **编号**：PHASE-09
- **目的**：根据功能测试反馈进行修改和优化——修复缺陷、优化性能、改进代码质量。
- **参与角色**：开发工程师（执行修改）、独立代码评审员（审查每次修改）、质量工程师（回归测试）
- **角色 Loop 重点**：
  - 开发工程师：接收缺陷列表 → 修复 → 补充测试 → 自检
  - 独立代码评审员：审查每处修改 → 按 review-checklist.md 逐项验收 → 签名
  - 质量工程师：执行回归测试 → 确认原有功能未被破坏
- **阶段交付物**：
  - 修改后的源代码
  - `rework-tracker.md` — 每条缺陷的修复记录（缺陷 ID → 修改 → 评审 → 回归）
  - `review-report.md` — 独立评审员的评审结果
- **入口条件**：功能测试阶段 APPROVED_NEXT_PHASE 且 functional-test-report.md 存在
- **放行条件**：
  - 所有 HIGH 和 CRITICAL 缺陷已修复并通过评审
  - 回归测试全部通过
  - 独立评审员对所有修改签名 PASS

---

### 阶段 10：压力测试

- **编号**：PHASE-10
- **目的**：验证系统在预期负载和极端条件下的性能和稳定性。
- **参与角色**：质量工程师（定义压力场景并执行）、发布工程师（环境准备）、系统架构师（性能与架构一致性的分析）
- **角色 Loop 重点**：
  - 质量工程师：按非功能需求设计压力测试场景 → 执行 → 记录 → 产出 stress-test-report.md
  - 发布工程师：准备测试环境（与生产环境一致）
  - 系统架构师：分析性能瓶颈是否与架构设计一致（预期的 vs 实际的）
- **阶段交付物**：
  - `stress-test-report.md` — 压力测试结果、性能曲线、瓶颈分析
  - `environment-spec.md` — 测试环境配置
- **入口条件**：修改优化阶段 APPROVED_NEXT_PHASE 且所有缺陷已修复
- **放行条件**：
  - 系统在目标负载下满足非功能需求中的 QPS 和延迟指标
  - 无内存泄漏、无连接泄漏
  - 架构师确认性能瓶颈在预期范围内

---

### 阶段 11：阶段交付

- **编号**：PHASE-11
- **目的**：把当前阶段的成果整理成可交付给用户或下一团队的完整包。
- **参与角色**：交付经理（主导）、发布工程师（打包和部署脚本）、安全工程师（最终安全审计）
- **角色 Loop 重点**：
  - 交付经理：汇总所有交付物 → 生成交付索引 → 确认完整性
  - 发布工程师：生成部署脚本 → 确认可部署
  - 安全工程师：执行最终安全扫描 → 确认无高危漏洞
- **阶段交付物**：
  - `stage-delivery-index.md` — 阶段交付物标准索引（基于 `templates/stage-delivery-index.md`）
  - `deployment-script.sh` 或等效部署文件
  - `final-security-report.md` — 最终安全审计结果
- **入口条件**：压力测试阶段 APPROVED_NEXT_PHASE 且 stress-test-report.md 通过
- **放行条件**：
  - stage-delivery-index.md 中所有文件路径可解析（文件真实存在）
  - 部署脚本可在目标环境中运行
  - 最终安全扫描 HIGH=0, CRITICAL=0

---

### 阶段 12：维护

- **编号**：PHASE-12
- **目的**：项目进入持续维护期——监控、问题修复、小版本迭代。
- **参与角色**：发布工程师（运维监控）、安全工程师（持续安全审计）、开发工程师（按需修复）
- **角色 Loop 重点**：
  - 发布工程师：持续监控系统运行状态 → 产出监控报告
  - 安全工程师：定期安全扫描 → 发现新 CVE 时通知
  - 开发工程师：接收问题工单 → 修复 → 走简化版状态链（跳过架构设计等非必需阶段）
- **阶段交付物**（持续产出，非一次性）：
  - `monitoring-report.md` — 定期监控摘要
  - `security-scan-report.md` — 定期安全扫描结果
  - `incident-log.md` — 事故记录和根因分析
- **入口条件**：阶段交付 APPROVED_NEXT_PHASE 且部署成功
- **放行条件**：本阶段无终点——持续运行直到用户决定结束项目或进入新一轮大版本迭代（回到阶段 1）

---

## 6. 阶段团队总表

| 阶段 | 编号 | 主导角色 | 参与角色（审查/验收） |
|---|---|---|---|
| 需求分析 | PHASE-01 | 产品经理 | — |
| 架构设计 | PHASE-02 | 系统架构师 | 产品经理（需求澄清） |
| 详细设计 | PHASE-03 | 模块架构师 | 系统架构师（架构一致性审查） |
| 测试设计 | PHASE-04 | 质量工程师 | 安全工程师（安全测试范围） |
| 编码 | PHASE-05 | 开发工程师 | 模块架构师（接口一致性检查） |
| 单元测试 | PHASE-06 | 开发工程师 | 质量工程师（覆盖率和门禁） |
| 集成 | PHASE-07 | 开发工程师 | 模块架构师 + 质量工程师 |
| 功能测试 | PHASE-08 | 质量工程师 | 产品经理（需求满足度确认） |
| 修改优化 | PHASE-09 | 开发工程师 | 独立代码评审员 + 质量工程师 |
| 压力测试 | PHASE-10 | 质量工程师 | 发布工程师 + 系统架构师 |
| 阶段交付 | PHASE-11 | 交付经理 | 发布工程师 + 安全工程师 |
| 维护 | PHASE-12 | 发布工程师 | 安全工程师 + 开发工程师 |

---

## 7. 阶段状态流转约束总结

```
PHASE_START → ENTRY_CHECK → [PASS] → ROLE_EXECUTION → INTEGRATION → QUALITY_CHECK
                                                                              ↓
                                                                    HUMAN_REVIEW_PACKET
                                                                              ↓
                                                                  WAITING_FOR_HUMAN_REVIEW
                                                                        ↙   ↓    ↘
                              APPROVED_NEXT_PHASE    RETURN_FOR_REWORK    CHANGE_DIRECTION
                                   ↓                       ↓                    ↓
                              下一阶段                ROLE_EXECUTION         归档终止
                              PHASE_START              （重入）
```

**关键约束重申**：
- 状态流转方向不可逆——除 RETURN_FOR_REWORK 可回到 ROLE_EXECUTION 外，任何状态不能跳回更早的状态（例如 INTEGRATION 失败不能直接回到 PHASE_START）。
- HUMAN_REVIEW_PACKET → WAITING_FOR_HUMAN_REVIEW 之后，只有用户能驱动下一步。系统不得自动推进。
- 每次从 RETURN_FOR_REWORK 回到 ROLE_EXECUTION 之后，必须重新走完 INTEGRATION → QUALITY_CHECK → HUMAN_REVIEW_PACKET 的完整链路。不得"返工只做一半就交差"。
