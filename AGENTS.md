# Kimi Code 工作区 — Loop 工程治理规则

## 激活条件

当项目根存在 `.ai/state.yaml` 时，自动加载 `loop-governance` Skill 作为治理启动器。

## 启动检查清单（每次会话启动或重大操作前）

1. 读取 `.ai/state.yaml`、`.ai/HANDOFF.md`、`.ai/gates.yaml`、`.ai/task_graph.yaml`
2. 运行 `C:\Python312\python.exe .zcode/tools/validate_state.py` 校验治理状态
3. 若存在 `pending` gate：**停止**，向用户呈现 gate 内容和决策选项
4. **blindspot-brief（Q3 盲点简报）**：开工前对照任务卡盲点清单逐条确认
5. 仅在已批准的任务与 gate 范围内执行

## Loop 三层架构（Kimi Code 适配版）

### 角色 Loop（Role Loop）
- 每个角色通过独立 `Agent` 实例运行（session_id 天然隔离）
- `developer` 和 `independent-reviewer` 必须是不同的 Agent 实例
- 角色输出以结构化 JSON 归档到 `.ai/role_outputs/`

### 阶段 Loop（Phase Loop）
- 聚合角色交付物 → 生成人类可读交付包
- Gate 审批由用户决策（非 AI 自批）
- 阶段推进前运行 `validate_state.py`

### 项目 Loop（Project Loop）
- 用户意图 → `intent_router.py` 分析 → LoopMode 推荐 → 阶段序列
- 状态持久化在 `.ai/` 目录

## 逃生门（不可绕过、永不失效）

| 用户说 | 效果 |
|--------|------|
| 「**绕过 gate**」「**手工模式**」 | loop_mode → MANUAL，所有约束解除 |
| 「**关闭 Loop**」「**停用治理**」 | 删除或忽略 loop-governance Skill |
| 「**紧急修复，跳过 Loop**」 | 直接操作，事后补证据 |
| 「**本次豁免 Loop 检查**」 | 单次操作不受 gate 限制 |
| 「**Loop 状态**」 | 只报告状态，不做任何阻断 |
| 「**升级到 FULL**」 | loop_mode → FULL，启用全部硬约束 |
| 「**降到 LIGHTWEIGHT**」 | loop_mode → LIGHTWEIGHT，最小流程 |

**关键原则**：Loop 是工具，不是枷锁。用户的「绕过」指令具有最高优先级，无条件执行。没有任何 gate 或规则可以阻止用户明确指示的操作。

## 约束声明（Kimi Code 确定性验证 + 行为契约）

Kimi Code 的 Loop 工程不依赖 hook 硬阻断，而通过两层防线实现质量保障：

**第一层：Quality Brain（确定性代码验证，非 LLM）**
这是 Kimi Code 独有的核心能力——不靠 LLM 评审 LLM，靠 Python 代码确定性验证：

| 验证器 | 检测内容 | 命令 |
|--------|---------|------|
| 静态分析器 | 50+ 条规则（EH/IV/AI/SE/CQ/RP） | `python -c "from quality_brain.static_analyzer import ..."` |
| 合约验证器 | 代码是否匹配 interface_contract.yaml | `C:\Python312\python.exe quality_brain/contract_verifier.py` |
| 导入检查器 | import 是否在依赖中声明（反幻觉） | `C:\Python312\python.exe quality_brain/import_checker.py` |
| 架构扫描器 | 分层依赖是否违反 architecture.yaml | `C:\Python312\python.exe quality_brain/architecture_scanner.py` |
| 证据验证器 | 证据文件完整性、新鲜度、反伪造 | `C:\Python312\python.exe quality_brain/evidence_verifier.py` |
| Gate 聚合器 | 汇总所有报告 → GO/BLOCKED/CONDITIONAL | `C:\Python312\python.exe quality_brain/gate_aggregator.py` |

**第二层：Skill 行为契约**
| 约束 | 实现方式 |
|------|---------|
| 写入范围限制 | Agent CONTRACT.yaml 中的 can_write/cannot_write |
| Pending Gate 阻断 | Skill 启动检查 → 停止并等待用户决策 |
| 角色隔离 | 独立 Agent 实例（不同 session，物理隔离） |
| 质量门禁 | Quality Brain + pytest + lint + coverage |

### S4 阶段质量验证流程

```
Developer Agent 产出代码
  │
  ▼
Quality Brain 首轮检查（不等角色）
  ├── 静态分析器: 50+ 规则（3 秒）
  ├── 合约验证器: 代码 vs 合约（1 秒）
  └── 导入检查器: 反幻觉（1 秒）
  │
  ▼ 有 BLOCKER → 打回 Developer 修复（最多 3 轮）
  │
  ▼
AgentSwarm([quality-engineer, security-engineer]) → 并行
  │
  ▼
Agent(independent-reviewer) → 不同 session，零偏见
  │
  ▼
Quality Brain 终检 + Gate 决策矩阵 → GO / BLOCKED / CONDITIONAL

## 注意事项

- **永远不要**自行批准 gate → Gate 是用户决策
- **永远不要**在 pending gate 存在时绕过检查 → 先呈现给用户
- **永远不要**修改 `.ai/state.yaml` 绕过治理 → 使用逃生门
- **可以**在用户说「绕过」时直接切换 MANUAL 模式
- **可以**在无活跃任务时自由探索和回答问题
