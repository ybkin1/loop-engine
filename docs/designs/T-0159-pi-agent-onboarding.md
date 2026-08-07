# T-0159: Pi Agent 学习 Loop 工程引导 + 执行委派试点（候选）

> 性质：**引导文档**（新会话提示词 + Pi 纠正引导），candidate-only 设计，
> 不落地代码。用户将开新会话（Pi agent）继续。
> 日期：2026-08-07

---

## 第一部分：新会话启动提示词（复制给 Pi agent）

```
你是 Pi agent，将接管 Loop 工程（C:\Users\Administrator\ZCodeProject\loop-engine）
的设计与执行委派试点。项目根：C:\Users\Administrator\ZCodeProject\loop-engine

## 启动检查（必须按序执行）
1. 读 C:\Users\Administrator\ZCodeProject\loop-engine\AGENTS.md（项目治理规则）
2. 运行状态校验：
   C:\Python312\python.exe .zcode\tools\validate_state.py .
   （期望 [ok] state is usable；当前任务 T-0158 completed，无 pending gate）
3. 读 .ai/state.yaml、.ai/HANDOFF.md、.ai/gates.yaml、.ai/task_graph.yaml
4. 读 .ai/KNOWN_ISSUES.md（Open 区含 execution-delegation 留档项）

## 本次会话目标
在 Pi agent 上验证「执行委派」演进（ZCode 上因宿主约束未落地）：
1. 深度阅读 Loop 工程（docs/ 架构 + loop_core/ + .zcode/tools/ + .ai/ 治理）
2. 对照本引导文档第三部分「Pi 纠正点」，理解哪些设计是 ZCode 宿主约束
   的妥协、Pi 的 3 层递归子代理可以如何突破
3. 产出执行委派试点设计（candidate-only，不落地）：任务卡 executor 标记 →
   上下文打包 → 递归子代理派发 → 产物回收校验 → 质量闭环
4. 试点：选 1 个低风险任务类型（如模板填用/报告生成）用递归子代理执行，
   验证质量与失控防护
5. 向用户汇报结论（可复用的执行委派方案 + 哪些可回灌 ZCode Loop 工程）

## 硬边界（不可违反）
- hooks/ 零改动、loop_core 内核零触碰（设计/试点均在临时目录或新增文件）
- 不进入真实业务项目、不部署、不迁移、不碰生产数据
- 不安装/启用新 skill/MCP/agent（Pi 自有递归能力不算外部启用）
- reviewer PASS / 测试通过 ≠ 用户批准；gate 仍须用户显式批准
- 试点产物不写入 .ai/ 治理文件（除非用户批准登记任务）

## Loop 工程速览（启动参考）
- 治理：gate 注册表（任务级 REQUIREMENTS 待用户批准）+ 阶段机 S0~S10 +
  证据链（SHA256 锚定）+ HANDOFF 投影 + 委托链（C-001~C-005，授权拓扑）
- 质量：三层质量线程（quality_pair 强制 + 独立审查 + CHECK_RECOMPUTE
  抽样复算 fail-closed）+ 变异测试（M1/M2 6/6）+ 防御演练（R1~R6/E1~E5）
- 运行时：loop_core（100+ 模块）+ hooks（7 个进程级守卫）+ MCP tools +
  13 角色 agents（SKILL 契约）
- 版本：v3.12.67；全量回归 4404 passed 0 failed；release check 7/7
- 最近落地：T-0155 事件溯源影子层 / T-0156 配额决策 / T-0157 风险分级 /
  T-0158 遗留收尾（顶层迁 src 布局）
```

---

## 第二部分：Loop 工程设计意图（先理解再纠正）

### 为什么 ZCode 上是「主会话执行 + 子代理审查」

| 约束 | 影响 | Loop 的妥协设计 |
|------|------|----------------|
| 子代理不能拉子孙代理（ZCode 宿主限制） | 无法构建多层执行树 | T-0054 MCP Agent Runtime 绕过尝试；最终保守为单层审查 |
| 子代理上下文不跨会话共享、无持久状态 | 子代理无法独立推进多步任务 | 主会话持有全程上下文（context_budget 预算管控） |
| 子代理产物可信度 | 子代理输出不可直接入账 | subagent_evidence_verifier 反伪造 + 主会话回收校验 |
| 无子代理级心跳/租约 | 无法安全委派长任务 | dispatch_lease（task×role 租约）+ rounds_heartbeat（主会话级） |

**结论**：不是没设计执行委派，是 ZCode 宿主不支持「可靠委派」的前置条件。
委托链 C-001~C-005 解决的是**授权拓扑**（免逐任务 gate），不是**执行拓扑**。

### 已有可复用组件（执行委派试点可直接用）

- `loop_core/context_packager.py`：上下文打包（token 预算/截断标记）
- `loop_core/context_budget.py`：上下文预算
- `loop_core/quality_pair` + `CHECK_RECOMPUTE`：质量闭环机制
- `.zcode/tools/rounds_heartbeat.py`：心跳/悬空检测
- `loop_core/dispatch_lease.py`：任务×角色租约
- `subagent_manifest.py`：SubagentSpec（is_weighted/quality_pair 强制配对）
- `event_log.py`（T-0155）：事件溯源影子层（委派轨迹可审计）

---

## 第三部分：Pi 纠正点（Pi 支持 3 层子代理递归，如何突破）

### Pi 的能力差异

Pi agent 支持 **3 层子代理递归** —— 这是 ZCode 没有的，意味着 Loop 工程
中「因宿主约束妥协」的设计在 Pi 上应**纠正为真正多代理执行**：

### 纠正点对照表

| # | Loop 现状（ZCode 妥协） | Pi 应纠正为 | 复用组件 |
|---|------------------------|-------------|---------|
| 1 | 主会话执行全部主任务 | **执行委派**：任务卡 `executor: subagent` 标记 → 主会话打包上下文派发 → 子代理执行 → 产物回收校验 | context_packager + subagent_manifest |
| 2 | 质量审查 = 主会话派 1 层子代理 | **递归质量闭环**：执行子代理 → 测试子代理（第 2 层）→ 审查子代理（第 3 层），每层独立上下文 | quality_pair + CHECK_RECOMPUTE |
| 3 | 上下文全程在主会话 | **分层上下文**：主会话只留编排上下文；每层子代理独立预算（打包传递，不用全程持有） | context_budget |
| 4 | 无子代理级失控防护 | **委派租约 + 心跳**：子代理任务带租约（超时回收）+ 心跳（悬空 fail-stop）；Pi 若有子代理取消能力则用 | dispatch_lease + rounds_heartbeat |
| 5 | 产物由主会话直接写 | **子代理产物签名回收**：子代理输出 → 主会话校验（哈希/契约）→ 写入 | evidence_verifier + event_log |
| 6 | 主会话是唯一执行者 | **多代理并行**：独立任务可并行派发多个执行子代理（Pi 若支持并行） | dispatch_lease 租约防重 |

### Pi 试点建议步骤

1. **不改 Loop 内核**：试点在 Pi 侧写「委派编排器」脚本（读 .ai/tasks 任务卡
   → 按 executor 标记派发），Loop 侧零改动
2. **选低风险任务**：模板填用（capacity-estimate 填示例）、报告生成、
   文档同步 —— 无产品代码风险
3. **质量闭环前置**：每个委派任务必须带 quality_pair（第 2/3 层递归审查），
   否则不派发（复用 SubagentSpec.is_weighted 强制语义）
4. **审计**：委派轨迹写 event_log（或 Pi 侧等价 JSONL），回灌时对齐
   event_log schema
5. **结论回灌**：试点成功后，把「执行委派方案」作为 candidate 设计文档
   交用户 gate，评估 ZCode 侧是否可实现（未来宿主若支持递归）

### Pi 必须保留的 Loop 治理底线（不可因递归而丢）

- **gate 批准**：用户仍是唯一批准者（EVIDENCE_ONLY_BOUNDARY）
- **证据链**：子代理产物必须过校验才能入账（防伪造）
- **升级协议**：仅 4 类价值问题升级用户（产品取舍/新目标/外部边界/目标冲突）
- **规则层不豁免**：AGENTS.md / forbidden 语义 / 委托链外不创建 gate

---

## 第四部分：试点后可能的排布（供用户裁决）

| 候选 | 内容 | 优先级 |
|------|------|--------|
| T-0160 | 执行委派编排器设计（Pi 试点验证后，回灌 candidate 方案） | P2 |
| T-0161 | 子代理产物签名回收规范（哈希+契约校验标准化） | P2 |
| T-0162 | 递归质量闭环（3 层 quality_pair 模板化） | P2 |

---

## 边界确认

- 本文件为引导/设计文档，零产品代码改动
- 未安装/启用任何 skill/MCP/agent（Pi 递归能力为宿主固有）
- 版本保持 3.12.67；KNOWN_ISSUES 已留档 execution-delegation 项
