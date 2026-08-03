# Q4 低成本原型机制设计（T-0105 批 3 / D-02 P2-2）

> 状态：已裁决（**最小落地**）+ 已落地
> 依据：`T-0103/design/D-02-gap-analysis.md` 表 1 Q4 行、表 3 P2-2
> 日期：2026-08-03

## 1. 目标

对"用户说不清要什么、但看到能判断"（Q4 未知的已知）的场景，提供**低成本原型**
机制：AI 先产出可查看/可试用的最小形态（HTML mock / CLI demo / 数据样本），
用户看到后做选择，选择后记录理由并进入**一轮**方案修正循环，再确认后才进入正式任务。

补三个具体差距（D-02 表 1 Q4 行）：
1. 无"低成本原型"任务类型（"原型"仅在 product-manager CONTRACT 出现一句）。
2. 无"用户选择后反馈"迭代循环（gate 决策记录是单向 approve/reject）。
3. 多方案呈现偏"文档化"，缺"可交互/可试用"形态。

## 2. 方案设计

### 2.1 原型任务类型（planner）

- `TaskType` 枚举：`standard`（默认）/ `prototype`；`TaskDraft` 新增
  `task_type` 与 `prototype_form` 字段（序列化向后兼容，旧 plan 文件默认 standard）。
- `Planner.generate_prototype(title, description, requirement_id, prototype_form)`
  生成**单任务** plan draft（READ-ONLY，须经 plan-approval Gate 批准），
  三种形态：`html_mock` / `cli_demo` / `data_sample`。
- 原型任务固定在 `S3-interface` 阶段（实现前最后可转向的窗口），
  复杂度 LOW、角色 developer、AC 强调"低成本可迭代、不追求完整"。
- MCP 工具：`planner_generate_prototype`。

### 2.2 任务卡"原型交付"说明（模板层）

`skills/loop-governance/templates/task-card.md` 新增"原型交付（Q4，可选）"节：
三种形态对照表 + 原型三原则（低成本 ≤20% 估算 / 可迭代默认一轮 / 不追求完整）。

### 2.3 gate-request"选择后反馈"字段（模板层）

`skills/loop-governance/templates/gate-request.md` 决策记录后新增
"选择后反馈（方案修正循环）"节：所选方案 / 选择理由（用户原话）/
AI 据此调整 / 调整结果确认；规则：理由不代编、循环默认一轮、
一轮不满意 → 重新发起 Gate。

### 2.4 chain.yaml prototype 节点（候选，本次未落地 — 见 §3 裁决）

完整版候选节点（供后续批次启用）：

```yaml
  - name: prototype
    file: ".ai/evidence/prototype/prototype_manifest.json"
    upstream: [architecture]
    required: false
```

启用前置条件（缺一不可）：
1. 同步更新安装副本 `.zcode/skills/loop-governance/chain.yaml`（两个副本必须一致）。
2. 文件路径必须为**精确路径**或先升级 `scripts/evidence_chain.py` 支持 glob
   （现实现 `Path.exists()` 对 glob 恒为 False → required 节点会误报 MISSING）。
3. required 语义：本期建议 `false`（原型是可选行为，不应阻塞主线证据链）；
   若未来要强制"有原型才放行"，需同时定义 gate 消费 strict 验证的路径
   （当前无任何 hook/gate 以 strict 模式调用证据链验证，加了也无人消费）。

## 3. 影响面评估与裁决

### 3.1 消费方盘点（chain.yaml）

| 消费方 | 位置 | 行为 | 影响 |
|---|---|---|---|
| `scripts/evidence_chain.py` verify_chain | scripts/ | 遍历 chain 全部节点；缺文件时 required+strict → MISSING(BLOCKED)，否则 SKIPPED | 加 required 节点在 strict 下会 BLOCKED；glob 路径恒 exists()=False |
| `tools/tool_evidence_chain.py` _basic_verify | tools/（fallback） | 同上语义（strict 才报） | 同上 |
| 安装副本 | `.zcode/skills/loop-governance/chain.yaml` | 与仓库副本**当前逐字节一致**；消费方优先读 `.zcode` 副本 | 只改仓库副本 → 双副本漂移，且生产验证读的是旧副本，改动无效 |
| hooks / gate_guard / runtime / dispatcher | — | 无任何代码以 strict 模式调用证据链验证 | prototype 节点无门禁联动消费方 |

### 3.2 裁决：最小落地

**结论：采用最小落地** —— 只做模板 + 提示词层（planner 原型类型 + 任务卡说明 +
gate-request 反馈字段），chain.yaml prototype 节点留档为候选（§2.4）。

理由：
1. **改动无效风险**：消费方优先读 `.zcode` 安装副本，而本任务写范围不含
   `.zcode/`（硬约束），只改仓库副本会造成双副本漂移且线上验证读旧配置。
2. **verifier 语义缺陷**：`exists()` 不支持 glob，`human_review` 节点已用
   `required: false` 规避；若 prototype 用 glob+required:true 会在 strict 模式
   恒误报 BLOCKED，等于给证据链埋定时炸弹。
3. **无门禁消费方**：没有任何 hook/gate 以 strict 调用验证，prototype 节点
   加了也只是死配置，不产生行为变化——真正的"原型门"需要 gate 类型联动，
   那是跨 hooks/内核的改动，超出本批范围。
4. **方法论核心已由模板+提示词覆盖**：原型任务类型、三原则、选择后反馈循环
   是 Q4 的行为主体；chain.yaml 只是证据留档的收尾，可后续批次补齐。

### 3.3 回退

- 模板/提示词层：删除 task-card"原型交付"节、gate-request"选择后反馈"节、
  planner `generate_prototype` 方法即可整体回退（planner 新增字段均有默认值，
  旧数据零影响）。
- 无 chain.yaml 改动 → 无证据链/验证回退面。
- fail-closed 语义全程未触碰：inbox/planner 异常路径仍抛异常返回 BLOCKED。

## 4. 落地清单（本批实际改动）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `loop_core/planner.py` | `TaskType`/`PrototypeForm` 枚举；`TaskDraft.task_type`/`prototype_form` 字段（序列化兼容）；`generate_prototype()` |
| 2 | `tools/tool_planner.py` | `planner_generate_prototype` MCP handler |
| 3 | `skills/loop-governance/templates/task-card.md` | "原型交付（Q4，可选）"节 + P2-2 引用更新 |
| 4 | `skills/loop-governance/templates/gate-request.md` | "选择后反馈（方案修正循环）"节 |
| 5 | `skills/loop-governance/chain.yaml` | **零改动**（候选设计见 §2.4） |
| 6 | `tests/test_t0105_batch3.py` | Q4 测试组（三种形态/序列化/向后兼容/模板断言） |

## 5. 与四象限方法论的关系

- Q4 闭环：多方案（gate-request A/B/C，已有）→ 低成本原型（本次）→
  用户选择 + 理由（选择后反馈，本次）→ 一轮修正 → 确认后执行。
- 与 Q2（多轮澄清，同批 P2-1）正交：Q2 问"知识缺口"，Q4 给"可看的东西"；
  两者共用 R11 的"每轮≤3"节奏约束。
