# T-0055 基线审计：角色清单

审计对象：Loop Engine v3.11.2 当前工作树。角色数以 `agents/` 下同时存在 `SKILL.md` 与 `CONTRACT.yaml` 的目录为准。

| 角色 | SKILL | CONTRACT | 基线判断 |
|---|---|---|---|
| main-thread | present | present | 编排/汇总，不应专业裁决 |
| product-manager | present | present | 需求和验收边界 |
| project-manager | present | present | 任务、依赖、范围和治理交接 |
| system-architect | present | present | 系统级架构与非功能约束 |
| module-architect | present | present | 模块、接口和契约边界 |
| developer | present | present | 实现与实现级回归 |
| quality-engineer | present | present | 质量门禁与质量证据 |
| test-engineer | present | present | 测试策略、负面路径和回归 |
| security-engineer | present | present | 安全边界和安全证据 |
| independent-reviewer | present | present | 独立审查，不修改被审产出 |
| delivery-manager | present | present | 交付完整性和残余风险 |
| release-engineer | present | present | 制品、发布和回滚边界 |

## 关键基线结论

- 角色静态文件齐全不等于能力已验证。
- `quality-engineer`、`test-engineer`、`independent-reviewer` 的职责存在互补但没有统一的跨入口验证契约。
- 认证、profile、CONTRACT、SKILL 和 challenge 需要在后续阶段建立 canonical source-of-truth 映射。
- 本审计不改变任何角色认证状态。
