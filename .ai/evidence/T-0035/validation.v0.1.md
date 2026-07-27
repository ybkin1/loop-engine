# T-0035 文档优化验证

## 验证范围

- v0.2 文件存在且为新增文件；
- v0.1 历史输入未被覆盖；
- 关键产品边界、硬约束、角色 Loop、阶段 Loop、长期文档和成本原则存在；
- 文档没有把提案写成已实现能力；
- 项目状态和任务证据可被治理工具识别。

## 结构化检查项

- [x] 产品身份与用户结果
- [x] 独立工具/外部 Agent 两种形态
- [x] Loop Core / Runtime / Host Adapter
- [x] `HARD` / `PARTIAL` / `ADVISORY`
- [x] 意图识别和项目分级
- [x] 角色合同和角色能力认证
- [x] 角色运行前 admission、运行中 RoleRunEnvelope 和运行后效果验证
- [x] 角色 Loop、阶段 Loop、项目 Loop
- [x] 需求到发布的阶段模型
- [x] P0-P12 稳定宏阶段和 Phase Profile 裁剪规则
- [x] 写入、命令、证据和阶段硬阻断
- [x] Quality Profile、测试可信度和 freshness
- [x] 独立评审、finding、repair、regression
- [x] 跨会话长期文档权威
- [x] Human Review Packet 通用模板和各阶段用户决策问题
- [x] token、返工和交付成本
- [x] 风险、路线和 Definition of Done

## 限制

本验证只证明设计文档的结构和边界表达，不证明 Loop Runtime、角色能力、宿主适配器或生产级交付能力已经实现。

## 本轮补强验证

- `Role Admission`、`Runtime Role Verification`、`Production Role Effectiveness` 和 `RoleRunEnvelope` 已存在。
- P0-P12 宏阶段、`Phase Profile`、阶段合并/展开/`NOT_APPLICABLE` 规则已存在。
- `Human Review Packet` 通用模板和 P0-P12 用户决策映射已存在。
- `validate_state.py` 返回 `[ok] state is usable`。
- `audit_handoff.py` 返回 `[ok] handoff audit passed`。
- `git diff --check` 通过。
