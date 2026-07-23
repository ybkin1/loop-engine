# Codemap

| 目录 | 职责 | 关键文件 |
|------|------|---------|
| `hooks/` | ZCode 执行层（4 hook） | gate_guard.py, loop_enforcement.py, path_guard.py, session_brief.py |
| `loop_core/` | 宿主无关控制内核 | state_machine.py, router.py, enforcement.py, contracts.py |
| `loop_engine/` | Python 核心库 + 适配器 | adapters/, cost_tracker, degradation, enforcement_degradation |
| `agents/` | 11 角色合同 | */SKILL.md（12 字段合同） |
| `tools/` | MCP 工具 | server.py + 7 tool_*.py |
| `scripts/` | CLI 工具 | install, uninstall, certification, auto_mutation, perf, security, regression |
| `skills/` | 治理技能 | SKILL.md, config.yaml, chain.yaml |
| `tests/` | 测试（193 cases） | test_hooks, test_loop_core, test_certification... |
| `docs/` | 设计文档 | 00-charter ~ 06-delivery |
| `.ai/` | 治理数据 | state.yaml, gates.yaml, task_graph.yaml, HANDOFF.md |
