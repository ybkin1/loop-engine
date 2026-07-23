# 编码规范——开发工程师必读

## 1. 命名规范
| 元素 | 规范 | 示例 |
|---|---|---|
| 函数 | camelCase（TS）/ snake_case（Python） | createUser / create_user |
| 类 | PascalCase | UserService |
| 接口/类型 | PascalCase | User, CreateUserInput |
| 常量 | UPPER_SNAKE_CASE | MAX_RETRY_COUNT |
| 文件 | kebab-case（TS）/ snake_case（Python） | user-service.ts |
| 布尔变量 | is/has/should 前缀 | isActive, hasPermission |
| 私有成员 | _ 前缀（Python）/ private（TS） | _internal_state |

## 2. 函数规范
- 单一职责：一个函数只做一件事。如果函数名里有"and"，考虑拆分
- 长度上限：单个函数不超过 40 行（不含注释和空行）
- 参数数量：不超过 4 个。超过 = 用对象/结构体封装
- 返回值：所有代码路径必须显式返回或抛出声明的错误
- 副作用：有副作用的函数在函数名中体现（如 createUserAndSendEmail）

## 3. 错误处理
- 不吞错误：不得 `catch (e) { /* ignore */ }` 或 `except: pass`。安全忽略须加注释
- 错误类型：必须使用契约声明的错误类型，不得抛出未声明的错误
- 错误信息：必须包含足够上下文——"操作失败"不够

## 4. 注释规范
- 契约引用：每个 export 函数上方注明 `// @contract: exports[0] createUser`
- 为什么而非是什么：注释解释 Why，不重复代码做了什么
- 不注释掉死代码：直接删除，版本管理会记住历史

## 5. 类型使用
- 禁止 `any`：任何情况下不得使用
- 禁止类型断言绕过：`as Type` 或 `# type: ignore` 需注释说明为何
- 可选字段：只有契约声明为可选的才能标记可选

## 6. 导入规范
- 只从架构允许的模块导入
- 禁止深层相对导入：`../../../some-module`
- 禁止循环导入

## 7. 测试规范
- 每函数必有测试：每个 export 函数至少一个测试用例
- 幂等性测试：声明幂等的函数必须验证多次调用结果相同
- 错误路径测试：每种错误至少一个测试用例
- 测试命名：`test_{函数名}_{场景}_{期望结果}`

## 8. 禁止事项
| 禁止行为 | 说明 |
|---|---|
| 自行修改接口签名 | 不得添加、删除、修改任何参数/返回值类型 |
| 自行添加依赖 | 不得引入契约未声明的外部依赖 |
| 实现契约未声明的公开函数 | 不得 export 契约以外的函数（内部辅助用 _ 前缀） |
| 吞错误 | 不得捕获错误后不做任何处理 |
| 使用 `any` 类型 | 绝对禁止 |
| 跨模块硬编码 | 不得直接使用其他模块的内部实现细节 |
| 忽略 linter 警告 | 所有 warning 必须清零或附理由放行 |
