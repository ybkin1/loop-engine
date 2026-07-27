# Codex 侧 Loop 工程候选架构 v0.1

状态：`candidate / implementation-gate-required / Codex-only`

## 1. 目标

建立一个本地、可版本化、可测试的 Codex 侧 Loop 工程候选实现。它的职责是把用户意图转成受约束的软件工程流程和交付包，让 Codex 按软件工程角色、阶段、任务、证据和 Gate 工作；它不是一段总提示词，也不是把整个素材库一次性塞进上下文。

## 2. 第一实现形态

```text
Codex 会话
   -> codex-loop CLI / local library
   -> project store: <project>/.loop/
   -> role/phase/material registries
   -> bounded work packets
   -> Codex 执行任务
   -> deterministic checkers
   -> Human Review Packet
   -> user decision
```

第一版只在本地项目目录运行，不安装全局 skill、MCP、plugin 或 hook。Codex 侧适配只负责 Codex 能力探测、文件/命令边界、上下文包生成和结果回收。

## 3. 代码边界

```text
codex_loop/
  core/       状态、工件、角色、阶段、任务图、Gate、证据模型
  registry/   角色、阶段、材料和检查器注册
  routing/    意图、风险和项目模式路由
  planning/   Phase Profile、Task Graph、Work Packet
  context/    按需上下文选择、fingerprint、预算和隔离
  prompts/    短角色指令片段与输出约束，不存全项目长上下文
  runtime/    本地运行 envelope、权限预检、结果回收和阻断
  quality/    Schema、引用、追溯、测试、freshness、成本检查
  packets/    功能设计包、阶段评审包、交接包生成
  cli/        route/select/plan/run/verify/packet/gate 命令
tests/codex_loop/
docs/codex-loop/
```

`codex_loop` 只处理 Loop 工程机制；软件项目的业务代码仍由开发任务包在目标项目中实现。

## 4. 角色提示词架构

每次角色运行只组装以下五层，禁止把所有角色和全部素材放入一个上下文：

```text
L0 stable role contract       角色永恒立场、职责、禁止事项、否决权
L1 capability profile         工具、技能、探针、失效条件、版本
L2 project overlay            当前项目目标、风险、技术栈、用户决策
L3 phase/work packet          本阶段一个任务、输入版本、允许输出和写入边界
L4 selected evidence          仅与本任务相关的材料摘要、Schema、检查器
```

角色输出必须是结构化产物，不是只返回自然语言。每次运行都生成 `RoleRunEnvelope`，记录输入 fingerprint、角色版本、工具预检、权限预检、输出、检查、未验证项和 verdict。

### 角色隔离

- 产品经理不能读取或修改架构实现结论来替代用户目标。
- 架构师不能写业务实现代码，开发工程师不能修改已批准架构。
- 质量和安全角色默认只读实现，不能修复自己的 finding 后自证通过。
- 独立评审员使用新鲜上下文、冻结输入和只读权限。
- 主控是唯一状态编排者，但不能冒充任何专业角色签字。
- 角色之间只通过版本化 Work Packet、Artifact、Finding 和 Handoff Contract 交接，不共享自由文本记忆。

## 5. Codex 侧状态和存储

目标项目内使用 `.loop/` 保存 Loop 专属机器状态：

```text
.loop/
  project.yaml
  materials-selection.yaml
  roles/                角色合同和版本指针
  phases/               Phase Profile 和 Gate 状态
  tasks/                Work Packet 和任务图
  runs/                 RoleRunEnvelope 和工具证据
  artifacts/            候选交付物及 fingerprint
  packets/              Human Review Packet
  findings/             缺陷、修复、回归和结论
```

`.ai/` 仍是现有 Project Governor 的治理记忆；`.loop/` 是 Loop 候选运行状态。二者引用彼此但不互相覆盖，`HANDOFF.md` 不是唯一事实来源。

## 6. 用户可读功能设计包

对每个功能，Loop 必须生成 `Functional Design Packet`，以用户能理解的“软件怎么用”为入口：

1. 用户目标、角色和使用前提。
2. 页面/界面结构、页面进入路径、按钮、链接、表单、状态、错误提示和空状态。
3. 用户完整操作流程：正常、边界、失败、取消、重试和返回。
4. 后端模块、接口、数据模型、状态变化、调用关系、错误处理和幂等性。
5. 权限、内部/外部用户边界、输入校验、反自动化、密码/会话/密钥和数据保护措施。
6. 性能预算、可维护模块边界、可观测性、扩展和降级方案。
7. 需求到测试的映射：单元、组件、契约、集成、E2E、安全、性能和恢复。
8. 未决问题、取舍、剩余风险和用户要决定的事项。

以登录/注册为例，交付包必须说明页面和跳转、字段与错误、注册/登录后端流程、账户分类、密码策略、速率限制、验证码/反机器人、邮箱/手机验证、会话/令牌、审计、攻击场景、测试用例和失败恢复；用户不需要审核每个函数名。

## 7. 阶段与 Gate

Loop 内部 Gate 负责结构、质量、安全、成本、证据和权限检查。用户 Gate 只负责目标、可见功能、重大取舍、剩余风险、发布/不可逆动作和阶段是否继续。

推荐用户 Gate：

- P1/P2：目标、范围、优先级、验收。
- P3/P4：用户可见行为、重大架构取舍、成本和长期影响。
- P11：产品/交付结果是否接受，是否进入下一阶段或正式设计。

P5-P10 的技术检查默认由 Loop 内部处理；只有出现硬阻断、超出已批准预算、重大剩余风险或不可逆动作时才请求用户决定。每个阶段仍生成 Human Review Packet，但“生成给人看”不等于每项都要求人工审核技术细节。

## 8. 成本与上下文控制

- 角色合同短而稳定，项目事实只放在 Project Overlay。
- 每个 Work Packet 只加载必要素材和必要历史，不加载完整目录。
- 超出上下文预算时先压缩/重新选择，不把旧会话全文继续堆积。
- 质量、安全、角色失败和用户纠正只通过结构化 Finding/Feedback 进入后续任务。
- 以 token、工具调用、评审、返工和等待时间总和评估成本。

## 9. 代码实现后的最小验收

- 能从一个意图生成 Project Profile、Material Selection、Phase Profile 和 Task Graph。
- 能为至少 11 个角色加载隔离合同和短提示词，并拒绝缺少输入/权限/Schema 的运行。
- 能生成一个完整 Functional Design Packet，而不是只有“实现某功能”的任务描述。
- 能记录 role run、finding、repair、regression 和阶段 Gate。
- 能在本地通过确定性检查阻断越权写入、缺失证据、无效 Schema、过期输入和未决用户 Gate。
- 不修改全局 Codex 配置，不启用其他宿主适配，不进入真实业务项目。
