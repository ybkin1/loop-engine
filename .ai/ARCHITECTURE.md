# Architecture

## Current Shape

Loop Engineering 采用四层架构：MCP Server → CLI → 核心业务层 → 持久化层。

- **MCP Server 层**：`src/server/index.ts` + `src/server/tools.ts`，通过 stdio JSON-RPC 暴露 9 个工具
- **CLI 层**：`src/cli/index.ts`，提供 `loop init/gate/role/evidence/state/handoff` 命令
- **核心业务层**：`src/core/` 下 5 个模块 — state-machine（状态机+Gate）、role-engine（角色激活）、evidence（证据管理+SHA256）、freshness（TTL 新鲜度）、handoff（交接管理）
- **持久化层**：`.ai/` 下的 YAML 文件（state.yaml、gates.yaml、task_graph.yaml）+ evidence/ 目录 + HANDOFF.md
- **规范层**：`skills/` 下 15 个角色 skill + `roles/` 下 9 个角色 brief + `templates/`

详细架构设计见 `docs/architecture-design.md`（1402 行，14 章，candidate 状态）。

## Key Flows

1. **项目初始化**：`loop init` → 创建 .ai/ 目录结构 → 写入 state.yaml + gates.yaml
2. **Gate 检查**：`loop gate check` → 加载 gates.yaml → 评估每个 condition（role_required/evidence_required/phase_required/manual_approval）→ 返回 pass/block
3. **Gate 推进**：`loop gate advance` → 条件全满足 → 更新状态 → 推进到下一阶段
4. **角色激活**：`loop role activate` → 检查前置角色和 Gate 依赖 → 记录到 state.yaml
5. **证据提交**：`loop evidence submit` → SHA256 哈希绑定 → 写入 evidence/ 目录
6. **交接创建**：`loop handoff` → 记录产物哈希 → 追加到 HANDOFF.md → 更新 state

## Integration Points

- **AI Agent 宿主**：通过 MCP Protocol (stdio) 或 CLI 调用
- **Qoder Skills**：15 个 skill 文件定义角色合同和工作流
- **Python 治理工具**：`.ai/checkers/` 和 `.ai/guards/` 提供运行时检查
- **外部工具链**：archlet（架构可视化）、loopany（持久记忆）、loopbase（可观测性）、tools-registry（密钥管理）— 均为 candidate 状态
# Architecture

## Current Shape

TBD

## Key Flows

- TBD

## Integration Points

- TBD
