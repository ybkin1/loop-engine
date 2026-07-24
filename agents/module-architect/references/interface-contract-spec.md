# 接口契约规范——模块架构师工作指南

## 1. 类型系统规则

### 1.1 禁止的类型
- `any` — 绝不允许，任何情况下都是模糊的
- `unknown` — 等同于 any，不允许
- `object` — 必须指定具体的字段和类型
- `Function` — 必须指定具体的函数签名
- `Record<string, any>` — 必须指定具体的值类型

### 1.2 允许的模糊类型（需附说明）
- `T extends ...`（泛型约束）— 用于通用工具函数
- `Promise<T>` — T 必须是具体类型
- `Array<T>` — T 必须是具体类型

### 1.3 联合类型
如果函数可能返回多种类型，使用联合类型显式声明。
正确：`User | null`、`Result<User, ValidationError>`。错误：`object`。

## 2. 幂等性声明

| 声明 | 含义 | 示例 |
|---|---|---|
| `是` | 多次调用与一次调用效果相同 | `setUserEmail(id, email)` |
| `否` | 每次调用产生新副作用 | `sendEmail(to, body)` |
| `条件 + 说明` | 在某些条件下幂等 | `createUser(email)` — 相同 email 第二次报错 |

## 3. 错误类型声明

每个函数的 signature.errors 必须列出所有可能的错误类型。
命名规则：PascalCase + Error 后缀（如 ValidationError）。
`when` 必须描述触发条件——不能是"发生错误时"，必须是"输入 email 已存在时"。

禁止：`Error`（太模糊）、不声明任何错误（暗示永不失败）。

## 4. 副作用声明

side_effects 必须列举：数据库写入/更新/删除、文件系统操作、网络请求、消息队列发送、
缓存修改、业务日志。无副作用则标注 `side_effects: []`。

## 5. 依赖声明

dependencies 必须精确到函数/类型：`"函数名 (模块名)"`（如 `"hashPassword (auth)"`）。
禁止：`"auth"`（太模糊）、`"所有"`（不可追踪）。

## 6. 数据结构规范

每个字段包含：name、type（精确，不允许 any/object/unknown）、mutable（true/false）、
constraints（可编程验证的约束——不能是"合理的值"）。

## 7. 版本规范

- 主版本号（MAJOR）：不兼容的接口变更（删除函数、改变输入类型）
- 次版本号（MINOR）：向后兼容的新增（新函数、可选字段）
- 修订号（PATCH）：文档修正、约束澄清
