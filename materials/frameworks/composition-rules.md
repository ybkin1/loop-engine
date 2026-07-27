# 素材组合规则

## 组合单位

一个可执行项目配置至少由以下四类素材组成：

```yaml
source_materials: ["<external source ids>"]
method_materials: ["<methodology ids>"]
artifact_templates: ["<template paths>"]
execution_controls: ["<checker, role contract, gate>"]
```

缺少来源时，规则是 Loop 自定义偏好；缺少模板时，交付物不可稳定复用；缺少执行控制时，内容只能作为建议；缺少用户 Gate 时，不能改变项目阶段状态。

## 选择顺序

1. 先按项目风险、技术栈、数据敏感性和交付目标筛选。
2. 再按来源等级和版本新鲜度排序。
3. 冲突时优先更高权威、更新版本和更贴合边界的来源；冲突不能静默覆盖。
4. 用模板生成候选交付包，保留删除项和裁剪理由。
5. 由对应专业角色独立检查，再由用户作阶段决定。

## 成本控制

- 先加载索引和适用边界，再加载模板和必要章节；不把全文资料默认塞入每个角色上下文。
- 复用稳定的来源摘要、Schema 和检查器；项目只新增差异化配置。
- 以 `Delivery-Ready Cost = token + tool + review + repair + delay` 衡量，而不是只看一次调用 token。
- 任何“省 token”方案都必须记录遗漏风险、返工率和最终交付质量。
