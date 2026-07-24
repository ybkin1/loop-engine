# 组件详细设计模板

> **必填表单。** 缺任何必填项 = 打回重做。开发者/系统架构师角色必须完整填写。
> 参考标准：**C4 Model**（Component 层）、**arc42**（Building Block View）。

## 1. 组件标识（必填）

| 字段 | 内容 |
|------|------|
| 组件名称 | [如：UserAuthService] |
| 所属模块 | [如：auth-module] |
| 设计者 | [角色/姓名] |
| 版本 | v1.0 |
| 创建日期 | YYYY-MM-DD |
| 最后更新 | YYYY-MM-DD |

## 2. 职责定义（必填）

### 2.1 单一职责描述
[用一句话描述该组件的唯一职责，如："负责用户身份验证与令牌管理"]

### 2.2 职责边界
| 做什么 | 不做什么 |
|--------|---------|
| [如：验证用户凭证] | [如：不负责用户注册] |
| [职责2] | [不负责2] |
| [职责3] | [不负责3] |

## 3. 接口定义（必填）

### 3.1 对外接口
| 接口名 | 输入 | 输出 | 异常 | 说明 |
|--------|------|------|------|------|
| authenticate(email, password) | email: str, password: str | AuthToken | InvalidCredentialsError | 验证用户身份并返回令牌 |
| validate_token(token) | token: str | UserInfo | TokenExpiredError, InvalidTokenError | 验证令牌有效性 |
| revoke_token(token) | token: str | None | TokenNotFoundError | 吊销指定令牌 |

### 3.2 接口契约（必填，每个公开接口一个）
```python
def authenticate(email: str, password: str) -> AuthToken:
    """
    验证用户身份并返回认证令牌。

    Args:
        email: 用户注册邮箱，格式须符合 RFC 5322
        password: 用户密码，明文（传输层已加密）

    Returns:
        AuthToken: 包含 access_token 和 refresh_token

    Raises:
        InvalidCredentialsError: 邮箱或密码不正确
        AccountLockedError: 账号已被锁定
        RateLimitError: 超过频率限制

    Preconditions:
        - 用户已注册（存在于数据库）
        - 账号未被锁定

    Postconditions:
        - 成功时返回有效的 AuthToken
        - 失败时记录失败次数（防暴力破解）

    Side Effects:
        - 写入登录日志
        - 更新最后登录时间
    """
```

## 4. 内部实现设计（必填）

### 4.1 内部结构
| 内部元素 | 类型 | 职责 | 可见性 |
|---------|------|------|--------|
| [如：password_hasher] | [工具类] | [密码哈希与比对] | private |
| [如：token_generator] | [工具类] | [JWT 生成与解析] | private |
| [如：user_repository] | [依赖接口] | [用户数据访问] | injected |

### 4.2 核心算法/流程（必填，至少核心流程）
```
[用户登录流程]
1. 接收 email + password
2. password_hasher.hash(password) → hashed
3. user_repository.find_by_email(email) → user
4. password_hasher.verify(hashed, user.password_hash) → match?
5. 如果 match:
   a. token_generator.generate(user.id, user.roles) → token
   b. 记录登录日志
   c. 返回 token
6. 如果 !match:
   a. 记录失败次数
   b. 如果失败次数 >= 5: 锁定账号
   c. 抛出 InvalidCredentialsError
```

### 4.3 状态管理
| 状态 | 描述 | 触发条件 |
|------|------|---------|
| [如：ACTIVE] | [正常运行] | [初始化完成] |
| [如：DEGRADED] | [部分功能降级] | [依赖服务不可用] |
| [如：UNAVAILABLE] | [完全不可用] | [内部错误] |

## 5. 依赖关系（必填）

### 5.1 依赖的外部组件
| 依赖组件 | 依赖类型 | 接口 | 失败影响 | 降级策略 |
|---------|---------|------|---------|---------|
| [如：UserRepository] | 数据层 | find_by_email() | 无法验证身份 | 返回503，缓存兜底 |
| [如：TokenGenerator] | 工具 | generate() | 无法生成令牌 | 直接失败 |
| [如：Logger] | 基础设施 | log() | 审计缺失 | 忽略，不影响主流程 |

### 5.2 被依赖方
| 依赖本组件的组件 | 调用接口 | 调用频率 |
|---------------|---------|---------|
| [如：AuthController] | authenticate() | 每次登录请求 |
| [如：AuthMiddleware] | validate_token() | 每次API请求 |

## 6. 错误处理（必填）

| 错误类型 | 处理方式 | 日志级别 | 用户可见信息 |
|---------|---------|---------|------------|
| InvalidCredentialsError | 返回401 + 错误提示 | WARNING | "邮箱或密码错误" |
| AccountLockedError | 返回423 + 剩余时间 | WARNING | "账号已锁定，请{minutes}分钟后重试" |
| TokenExpiredError | 返回401 + 刷新提示 | INFO | "登录已过期，请重新登录" |
| InternalError | 返回500 + 通用提示 | ERROR | "服务暂时不可用，请稍后重试" |

## 7. 性能考量

| 指标 | 目标 | 实现方案 |
|------|------|---------|
| 单次认证耗时 | < 200ms | 密码哈希使用 bcrypt(cost=10) |
| 令牌验证耗时 | < 5ms | JWT 本地验证，无需查库 |
| 并发支持 | > 1000/s | 无状态设计，水平扩展 |

## 8. 测试要求

| 测试类型 | 覆盖范围 | 示例 |
|---------|---------|------|
| 单元测试 | 所有公开接口 + 核心算法 | 正确密码登录成功 / 错误密码登录失败 |
| 集成测试 | 与 UserRepository 交互 | 真实数据库查询用户 |
| 边界测试 | 空输入 / 超长输入 / 特殊字符 | 空密码 / 1000字符密码 |

## 9. 填写示例

> 以"用户认证组件"为例的完整填写：

| 字段 | 示例值 |
|------|--------|
| 组件名称 | UserAuthService |
| 单一职责 | 负责用户身份验证与 JWT 令牌管理 |
| 对外接口1 | authenticate(email, password) → AuthToken |
| 对外接口2 | validate_token(token) → UserInfo |
| 对外接口3 | revoke_token(token) → None |
| 依赖组件 | UserRepository(数据层), TokenGenerator(工具), Logger(基础设施) |
| 核心算法 | bcrypt 密码哈希 + JWT HS256 签名 |
| 认证耗时目标 | < 200ms |

## 10. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| C4 Model - Component Diagram | https://c4model.com | 组件职责、依赖关系 |
| arc42 - Building Block View | https://arc42.org/overview | 内部结构、接口定义 |
| Google Design Docs - Design section | https://www.industrialempathy.com/posts/design-docs-at-google | 算法描述、设计选择 |
