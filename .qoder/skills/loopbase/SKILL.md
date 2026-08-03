# Loopbase - 跨会话代理记忆与可观测性 Skill

## Description

基于 [loopbase](https://github.com/superdesigndev/loopbase) 的跨会话代理记忆索引和可观测性技能。索引多个代理会话的 transcript，支持跨会话搜索、工作日志、成本追踪和自动化洞察，带本地 Web 仪表板。

## When to Use

- 需要查找"上次我让代理做了 X，结果是什么"
- 需要追踪每个会话/模型的 token 消耗和成本
- 需要从历史工具调用中发现可自动化的重复模式
- 用户要求"看看最近的会话"、"花了多少钱"、"有什么可以自动化"
- Loop 工程 handoff 阶段，需要完整的会话上下文交接
- 定期项目健康检查

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## 核心能力

| 命令 | 作用 |
|------|------|
| `loopbase list` | 列出所有会话，按代理/项目分组，显示工作日志目录 |
| `loopbase search "<text>"` | 跨会话按内容搜索，返回匹配的 turn 和上下文 |
| `loopbase show <id>` | 查看某个会话的结构化地图（工作日志 + turn 大纲） |
| `loopbase log "<what>"` | 在当前会话留下工作日志条目 |
| `loopbase cost` | 按会话/模型统计 token 和 USD 成本 |
| `loopbase insights` | 从工具调用中挖掘自动化候选（重复模式、高成本、频繁失败） |
| `loopbase serve` | 启动本地 Web 仪表板（localhost:4178） |

## Execution

### 1. 会话索引与搜索

```bash
# 列出所有会话
loopbase list

# 按内容搜索
loopbase search "部署失败"
loopbase search "database migration"

# 查看特定会话详情
loopbase show <session-id>
loopbase show <session-id> --turn 5   # 查看第 5 轮对话
```

### 2. 工作日志

```bash
# 在当前会话记录工作日志
loopbase log "完成了用户认证模块的重构"
loopbase log "发现 API 性能问题，需要优化数据库查询"
```

工作日志自动关联到自上次 log 以来的所有消息。

### 3. 成本追踪

```bash
# 所有会话的成本概览
loopbase cost

# 按模型汇总
loopbase cost --summary

# 单个会话的详细成本
loopbase cost <session-id>
```

### 4. 自动化洞察

```bash
# 发现可自动化的模式
loopbase insights
```

分析维度：
- **重复模式**：同一个工具调用序列反复出现
- **高成本模式**：某个操作消耗大量 token
- **频繁失败**：某个工具调用经常出错
- **组合模式**：`composio run` → 实际调用的是 Intercom 工具

每个洞察都关联到具体的会话示例。

### 5. Web 仪表板

```bash
loopbase serve              # http://localhost:4178
loopbase serve --port 8080  # 自定义端口
```

仪表板功能：
- 按成本排序的会话列表
- 按工作目录分组（git root）
- 每个会话的 per-model 成本分解
- 工作日志查看
- 自动化洞察标签页

### 6. 与 Loop 工程集成

| Loop 阶段 | Loopbase 的作用 |
|-----------|-----------------|
| plan | 搜索历史会话，找到类似任务的经验 |
| execute | 实时 log 工作进展 |
| verify | 回溯会话记录验证执行路径 |
| handoff | 提供完整会话上下文供下一会话恢复 |
| iterate | insights 发现改进机会 |

### 7. 定期健康检查

建议每 10 个任务或每周触发一次：

1. 运行 `loopbase cost --summary` 检查成本趋势
2. 运行 `loopbase insights` 发现自动化机会
3. 向用户报告：
   - 本周/本迭代成本趋势
   - 发现的可自动化模式
   - 频繁失败需要修复的工具

## 输出

- 会话索引和搜索结果
- 工作日志条目
- 成本报告（按会话/模型/时间）
- 自动化洞察报告
- Web 仪表板（本地只读）

## 约束

- loopbase 是只读索引器，不修改任何会话数据
- 成本是 list-price 估算，不是精确账单
- 所有数据留在本地，不上传到任何服务器
- 仪表板是只读的，不暴露写操作
- 需要 Bun >= 1.3 运行时

## 依赖

- Bun >= 1.3（使用 `bun:sqlite`）
- 安装: `bun add -g @superdesign/loopbase`
- 支持代理: Claude Code (read+write), Codex (read), pi (read)
