# Loop Engine — AI 软件工程控制与交付系统

多宿主适配的 Loop 工程内核。

## 分支

| 分支 | 宿主 | 语言 | 说明 |
|------|------|------|------|
| [main](/) | — | — | 总览 + 共享设计文档 |
| [zcode](../../tree/zcode) | ZCode (智谱 Z.AI) | Python | Hook 系统 + 11 角色 Agent |
| [qoder](../../tree/qoder) | Qoder | TypeScript | MCP 协议 + 角色引擎 |

## 核心理念

Loop 不是"建议 AI 遵守流程"的提示词，而是宿主和代码修改之间的控制层。
通过意图识别、项目分级、硬约束检查、独立评审、证据绑定和人工 Gate，
阻止没有充分依据的结果进入下一阶段。

## 文档

- [系统设计提案 v0.2](docs/loop-engineering-system-design.proposed.v0.2.md)
