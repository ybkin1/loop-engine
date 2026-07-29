# T-0055 角色设计一致性矩阵

## 角色数量核对

当前 `agents/` 实际发现 **12** 个同时具备 `SKILL.md` 和 `CONTRACT.yaml` 的角色目录：

`main-thread`, `product-manager`, `project-manager`, `system-architect`, `module-architect`, `developer`, `quality-engineer`, `test-engineer`, `security-engineer`, `independent-reviewer`, `delivery-manager`, `release-engineer`。

这纠正了早期“11 个角色”的基线描述。后续任务和证据必须以 12 个实际角色为准，不能继续沿用 11 这一旧数字。

## 设计覆盖

| 角色 | 12 字段覆盖 | 关键新增能力 | challenge 数 | 认证状态变更 |
|---|---:|---|---:|---|
| main-thread | 12/12 | 冲突保留、批准边界 | 2 | 否 |
| product-manager | 12/12 | 歧义、验收反例 | 2 | 否 |
| project-manager | 12/12 | 依赖、范围漂移、投影一致性 | 2 | 否 |
| system-architect | 12/12 | 失效、降级、可观测性 | 2 | 否 |
| module-architect | 12/12 | 空集合/未知状态、契约兼容 | 2 | 否 |
| developer | 12/12 | 异常、原子性、资源和回归 | 2 | 否 |
| quality-engineer | 12/12 | 0/0、退出码、证据 hash、skip 语义 | 2 | 否 |
| test-engineer | 12/12 | 负面、TOCTOU、缓存、测试有效性 | 2 | 否 |
| security-engineer | 12/12 | fail-open、扫描范围、证据篡改 | 2 | 否 |
| independent-reviewer | 12/12 | 证据真实性、范围覆盖、NOT_VERIFIED | 2 | 否 |
| delivery-manager | 12/12 | 版本/证据/交付完整性 | 2 | 否 |
| release-engineer | 12/12 | 制品、迁移风险、回滚 | 2 | 否 |

## 设计约束验证

- 没有修改现有角色 `SKILL.md` 或 `CONTRACT.yaml`。
- 没有改变 `.ai/certifications` 中任何认证状态。
- 没有将设计候选包解释为能力认证或生产准入。
- 通用状态语义只在 canonical schema 定义一次。
- 角色设计只保留差异化内容，避免重复百科式规则。
- 每角色 2 个高信息量 challenge，未超过 3 个上限。

## 待后续 gate 处理

角色设计与现有 CONTRACT/SKILL/profile/challenge/certification 实际内容的一致性修复，属于 `G-T-0055-CONTRACT-RECONCILIATION`，不在本 gate 内完成。
