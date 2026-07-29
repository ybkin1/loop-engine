# Loop 工程 Agent 角色目录

## 两层架构

```
用户决策
  │
ZCode 会话（永久调度器 — 有 Agent 工具）
  │
  ├─ main-thread          军师：出编排计划 + 汇总结果 + 呈现 gate
  ├─ product-manager      需求分析
  ├─ project-manager      项目管理
  ├─ system-architect     系统架构设计
  ├─ module-architect     模块详细设计
  ├─ developer            代码实现
  ├─ quality-engineer     质量门禁
  ├─ security-engineer    安全审查
  ├─ independent-reviewer 独立代码评审
  ├─ delivery-manager     交付管理
  ├─ release-engineer     发布运维
  └─ test-engineer        测试工程
```

**所有角色平级，由 ZCode 会话统一调度。** 会话根据 main-thread 产出的 SubagentManifest 决定调谁、调几个、并行还是串行。

## 每个角色的合同标准

12 字段：
1. 角色身份 2. 固定立场 3. 职责范围 4. 明确禁止 5. 输入资料 6. 输出产物
7. 质量标准 8. 可否决事项 9. 上游验收 10. 下游交接 11. 冲突处理 12. 证据要求

## 运行方式

1. 会话拉起 main-thread Agent → 产出 SubagentManifest（编排计划）
2. 会话按 manifest 并行/串行调用角色 Agent
3. 每个角色 Agent 加载自己的 SKILL.md + references + scripts，**不能**访问其他角色的运行上下文
4. 会话收集所有角色产出 → 扔回 main-thread 聚合 → 呈现 gate
