# Loop Core — 宿主无关的 Loop 工程控制内核

## 定位

Loop Core 是 Loop 工程中**不依赖任何特定 AI 编程宿主**的协议层和状态机。
它定义了"什么是正确的软件工程过程"——而不是"如何在 ZCode/Claude Code 中实现它"。

宿主适配器（如当前项目的 hooks/、tools/、.zcode-plugin/）负责把 Loop Core 的协议
翻译为特定宿主的能力调用。

## 架构边界

```
┌──────────────────────────────────────┐
│           AI 编程宿主                  │
│   (ZCode / Claude Code / Qoder / ...) │
├──────────────────────────────────────┤
│         Host Adapter（宿主适配器）      │  ← 当前 loop-engine 项目
│   翻译 Loop Core 协议 → 宿主能力调用     │
├──────────────────────────────────────┤
│           Loop Core（本目录）           │  ← 宿主无关
│   协议 | 状态机 | 路由 | 分级 | 证据    │
└──────────────────────────────────────┘
```

## 目录结构

```
loop_core/
├── README.md              ← 本文件
├── __init__.py
├── schemas/               ← JSON Schema 数据契约
│   ├── state.schema.json
│   ├── gate.schema.json
│   ├── task.schema.json
│   ├── role_contract.schema.json
│   ├── evidence.schema.json
│   └── phase.schema.json
├── state_machine.py       ← 阶段转换、Gate 状态机
├── router.py              ← 项目分级 + Loop 路由
├── enforcement.py         ← ENFORCEMENT_LEVEL + 硬约束校验
└── contracts.py           ← Host Adapter 必须实现的接口
```

## 核心原则

1. **宿主无关**：本目录不 import 任何 ZCode/Claude Code 特定模块
2. **纯数据协议**：所有契约用 JSON Schema 定义，任何语言/宿主可解析
3. **状态机是权威**：阶段能否进入、Gate 能否通过——由状态机判断，不由 AI 判断
4. **分级不伪装**：宿主做不到硬阻断时，标记 ADVISORY，不返回虚假的 ENFORCED

## ENFORCEMENT_LEVEL

| 级别 | 含义 | 判定条件 |
|------|------|---------|
| `STRONG` | 可硬性阻断文件写入、命令执行 | 宿主提供 Hook/拦截 API 且 exit 2 = deny |
| `MEDIUM` | 可控制大部分流程 | 宿主提供插件/MCP/工作流接入 |
| `ADVISORY` | 只能读状态、给建议 | 宿主不提供写入拦截或命令控制 |

宿主适配器启动时必须声明自己的 `ENFORCEMENT_LEVEL`。标记为 ADVISORY 的宿主
不能声称"已强制执行"——这是 Loop Core 的硬性诚实要求。
