# Architecture

Loop Engine 采用四层插件架构。详见 `docs/02-architecture.md`（完整 11 章设计）。

**快速索引：**
- 执行层：hooks/（4 hook，机器强制，AI 不可绕过）
- 知识层：skills/ + agents/（治理启动器 + 11 角色合同）
- 工具层：tools/（MCP JSON-RPC，7 工具）
- 协议层：loop_core/（宿主无关控制内核）

**关键设计决策：**
- Hook 阻断用 exit 2（非 JSON deny），最稳定
- 角色隔离通过 ZCode Agent 工具，每次新会话
- 否决链 JSON 结构化输出，主控不可覆盖
- ENFORCEMENT_LEVEL 诚实分级：ZCode=MEDIUM, ClaudeCode=STRONG
- Bash 命令拦截已启用（hooks.json matcher 包含 Bash）
- loop_enforcement hook 强制 FULL/STANDARD 模式走任务合同

**当前阶段：** S6-delivery。全量 193 tests pass。
