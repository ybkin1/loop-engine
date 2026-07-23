# 模板库索引

Loop Engine 内置的软件工程模板库。每个模板是**必填表单**，不是参考文档。角色启动时自动加载对应模板，主控验收时逐项检查。

## 使用方式

角色 Agent 启动时，提示词中自动注入对应模板。角色必须在输出中逐项填写，主控验收时检查完整性。**缺任何必填项 = 打回重做。**

## 模板清单

### 1. 需求类（requirements/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [user-profile.md](requirements/user-profile.md) | 用户画像模板 | S1 |
| [functional-requirements.md](requirements/functional-requirements.md) | 功能需求规格 | S1 |
| [non-functional-requirements.md](requirements/non-functional-requirements.md) | 非功能需求 | S1 |
| [acceptance-criteria.md](requirements/acceptance-criteria.md) | 验收标准清单 | S1 |

### 2. 架构类（architecture/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [system-architecture.md](architecture/system-architecture.md) | 系统整体架构 | S2 |
| [module-design.md](architecture/module-design.md) | 模块/组件设计 | S2 |
| [interface-contract.md](architecture/interface-contract.md) | 接口契约定义 | S2, S3 |
| [data-model.md](architecture/data-model.md) | 数据模型设计 | S2, S3 |
| [architecture-decision-record.md](architecture/architecture-decision-record.md) | 架构决策记录(ADR) | S2 |

### 3. 详细设计类（design/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [component-design.md](design/component-design.md) | 组件详细设计 | S3 |
| [function-spec.md](design/function-spec.md) | 函数/方法规格 | S3 |
| [error-handling-design.md](design/error-handling-design.md) | 错误处理设计 | S3 |

### 4. 测试类（testing/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [test-strategy.md](testing/test-strategy.md) | 测试策略 | S5 |
| [test-case.md](testing/test-case.md) | 测试用例模板 | S5, S8 |
| [regression-checklist.md](testing/regression-checklist.md) | 回归测试清单 | S9 |

### 5. 安全类（security/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [security-review.md](security/security-review.md) | 安全审查清单 | S5, S10 |
| [vulnerability-assessment.md](security/vulnerability-assessment.md) | 漏洞评估报告 | S5 |

### 6. 部署类（deployment/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [deployment-plan.md](deployment/deployment-plan.md) | 部署方案 | S10 |
| [rollback-plan.md](deployment/rollback-plan.md) | 回滚方案 | S10 |
| [release-checklist.md](deployment/release-checklist.md) | 发布检查清单 | S10 |

### 7. 评审类（review/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [code-review-checklist.md](review/code-review-checklist.md) | 代码审查清单 | S4, S8 |
| [design-review-checklist.md](review/design-review-checklist.md) | 设计审查清单 | S2, S3 |

### 8. 编码类（coding/）

| 文件 | 用途 | 使用阶段 |
|------|------|---------|
| [coding-standards.md](coding/coding-standards.md) | 编码规范 | S4 |
| [naming-conventions.md](coding/naming-conventions.md) | 命名约定 | S4 |
