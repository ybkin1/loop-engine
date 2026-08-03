# Archlet - 架构治理与可视化 Skill

## Description

基于 [archlet](https://github.com/superdesigndev/archlet) 的架构治理技能。让编码代理扫描代码库，生成分层架构地图，支持 PR diff 叠加查看，确保改动不违反模块边界。

解决 Vibe Coding 时代的核心问题：代理不断改代码，架构在不知不觉中漂移。

## When to Use

- 新会话开始时，需要了解项目当前架构全貌
- PR 提交前/后，检查改动是否越界或引入架构漂移
- 用户要求"画一下架构"、"这个改动影响了哪些模块"
- Loop 工程 execute 阶段开始前，确认任务范围与架构边界一致
- 定期架构健康检查（可配合 loopany 定时循环）

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## Inputs

- 目标代码库路径（默认当前工作区）
- 可选：PR 编号或 diff 范围（用于叠加查看）
- 可选：架构约束规则（模块边界、依赖方向等）

## Execution

### 1. 架构扫描

让编码代理读取整个代码库，生成分层架构地图：

```
Follow https://raw.githubusercontent.com/superdesigndev/archlet/main/SKILL.md and build a map for this project
```

代理会：
- 扫描代码结构和 import/call graph
- 选择分层方式，命名模块
- 输出到 `.archlet/data.js`（单一事实来源，可手动编辑）

### 2. 架构地图渲染

```bash
npx archlet view          # 打开 localhost:4173 查看交互式地图
npx archlet validate      # 检查 .archlet/ 数据自洽性
```

### 3. PR Diff 叠加

```
overlay PR #<number>
```

在架构地图上叠加 diff，可视化查看改动影响了哪些模块。

### 4. 架构约束检查

在 Loop 工程 execute 阶段前：
1. 读取 `.archlet/data.js` 了解模块边界
2. 对照任务卡的 `allowed_write` 路径
3. 如果任务涉及的模块超出 `allowed_write`，标记为架构越界风险
4. 报告给用户决策

### 5. 架构漂移检测

定期（或通过 loopany 循环）：
1. 重新扫描代码库生成最新架构地图
2. 与上次存档的 `.archlet/data.js` 对比
3. 报告新增/删除/变更的模块和依赖关系
4. 标记未经 gate 审批的架构变更

## 与 Loop 工程的集成

| Loop 阶段 | Archlet 的作用 |
|-----------|---------------|
| plan | 提供架构全貌，帮助拆分任务时识别模块边界 |
| execute 前 | 检查任务范围 vs 架构边界，防止越界 |
| execute 后 | PR diff 叠加，确认改动在预期模块内 |
| review | 为 reviewer 提供架构上下文 |
| iterate | 架构漂移检测，确保迭代不破坏整体结构 |

## 输出

- `.archlet/data.js` — 架构地图数据（可编辑的事实来源）
- 架构约束检查报告（PASS / WARN / FAIL）
- 架构漂移检测报告（如有变化）

## 依赖

- [codegraph](https://www.npmjs.com/package/@colbymchenry/codegraph) — 代码图提取
- [madge](https://github.com/pahen/madge) — JS/TS import graph
- archlet CLI: `npx archlet view` / `npx archlet validate`

## Constraints

- 架构地图是代理生成的，可能偶尔误读——始终需要人工确认关键判断
- `.archlet/data.js` 是草稿，用户可以手动编辑修正
- 架构约束检查只作为 evidence，不替代用户 gate
- 不自动阻止任何改动，只报告和建议
- Token 消耗较高（代理需要读取整个代码库），按需使用
