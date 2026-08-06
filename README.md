# Loop Engine — Loop 工程软件交付系统

ZCode 插件。把 AI 编码变成具备完整软件工程纪律的可交付系统。

## 版本

**v3.12.52** — 2026-08-02

## 安装

### 方式一：ZCode 界面

```
ZCode → Settings → Plugin Management → Discover → + → 选择本项目目录
```

### 方式二：命令行联结

```bash
mklink /J %USERPROFILE%\.zcode\plugin-workspace\loop-engine C:\Users\Administrator\ZCodeProject\loop-engine
```

### 初始化目标项目

```bash
python scripts/install.py --project-root /path/to/your/project
```

目标项目将获得 `.ai/` 治理目录（state.yaml / gates.yaml / HANDOFF.md 等模板）。

### 卸载

```bash
python scripts/uninstall.py --project-root /path/to/your/project
```

## 项目结构

```
loop-engine/
├── .zcode-plugin/          ← ZCode 插件清单
├── hooks/                  ← ZCode 执行层 hook（6 个）
│   ├── hooks.json
│   └── scripts/
│       ├── loop_auto_activate.py  ← SessionStart Loop 自动激活
│       ├── template_injector.py   ← SessionStart 模板注入
│       ├── session_brief.py       ← SessionStart 治理摘要
│       ├── loop_enforcement.py    ← PreToolUse 写入拦截
│       ├── gate_guard.py          ← PreToolUse gate 阻断
│       ├── ledger_guard.py        ← PreToolUse 账本保护
│       ├── role_isolation.py      ← PreToolUse 角色隔离 (v2.0 HARD)
│       ├── path_guard.py          ← PreToolUse 路径保护
│       └── hook_common.py         ← 共享工具库
├── skills/                 ← 治理技能（LLM 知识层）
│   └── loop-governance/
│       ├── SKILL.md            ← 治理启动器
│       ├── config.yaml         ← 行为配置
│       ├── chain.yaml          ← 证据链定义
│       ├── references/         ← 参考文档
│       ├── examples/           ← 场景示例
│       └── templates/          ← 治理模板
├── agents/                 ← 11 个专业角色合同
├── tools/                  ← MCP 工具（7 个）
│   ├── server.py               ← JSON-RPC stdio 服务器
│   └── tool_*.py               ← 7 个工具实现
├── commands/               ← 斜杠命令（3 个）
│   ├── loop-validate.md
│   ├── loop-verify-chain.md
│   └── loop-cost.md
├── loop_core/               ← Python 核心引擎
│   ├── state_machine.py         ← 阶段状态机 + gate 逻辑
│   ├── hard_constraints.py      ← 8 项硬约束（C1-C8）
│   ├── enforcement_hub.py       ← Hook↔Core 治理决策桥 (v3.0)
│   ├── intent_router.py         ← 意图识别与 Loop 路由
│   ├── executor.py              ← 阶段/角色执行引擎
│   ├── router.py                ← 项目分级路由
│   ├── agent_adapter.py         ← Agent 适配器
│   ├── approval_record.py       ← 批准记录
│   └── ...                      ← 等 20+ 模块
├── scripts/                ← 独立工具脚本
│   ├── install.py
│   ├── uninstall.py
│   ├── cost_tracker.py
│   ├── evidence_chain.py
│   └── gen_continuity.py
├── tests/                  ← 测试套件（2116 条）
├── demo/                   ← 垂直切片验证项目 (v3.0)
│   └── loop-demo-todo/         ← 完整 S1-S6 闭环 CLI 工具
├── docs/                   ← 设计文档
│   ├── 00-project-charter.md
│   ├── 01-requirements.md
│   ├── 02-architecture.md
│   ├── 03-interface-contract.md
│   └── 06-delivery.md
├── .ai/                    ← 治理数据
│   ├── state.yaml
│   ├── gates.yaml
│   ├── task_graph.yaml
│   └── HANDOFF.md
├── .zcode/                 ← 运行时工具
│   ├── tools/              ← 治理脚本（12 个）
│   └── skills/loop-governance/
├── archive/                ← 历史实验证据
└── AGENTS.md               ← 项目启动规则
```

## 核心能力

| 层 | 组件 | 功能 |
|----|------|------|
| **执行层** | 6 个 Hook | 写入拦截、gate 阻断、角色隔离(HARD)、路径保护、账本保护、自动激活 |
| **知识层** | Skill + 11 Agent | 治理启动、角色协作、状态机 |
| **工具层** | 7 个 MCP 工具 | 质量门禁、安全扫描、依赖分析、契约验证、证据链、成本报告 |
| **命令层** | 3 个 Slash 命令 | 状态校验、证据链验证、成本报告 |

## 质量

| 门禁 | 结果 |
|------|------|
| Lint (ruff) | ✅ 0 errors |
| Test (pytest) | ✅ 113 passed, 1 skipped |
| Security | ✅ PyYAML 6.0.3（无已知 CVE） |

## 依赖

Python 3.10+, PyYAML >= 6.0

## 阶段进度

| 阶段 | 任务 | 状态 |
|------|------|------|
| S0-init | 项目合并 | ✅ |
| S1-requirements | T-0022 需求规格 | ✅ |
| S2-architecture | T-0023 架构设计 | ✅ |
| S3-interface | T-0024 接口契约 | ✅ |
| S4-implementation | T-0025 代码修复 | ✅ |
| S5-quality | T-0026 质量门禁 | ✅ |
| S6-delivery | T-0027 交付准备 | ✅ |
