# 模块设计模板

> **必填表单。** 缺任何必填项 = 打回重做。系统架构师角色必须完整填写。
> 参考标准：**C4 Model**（Container/Component 层）、**arc42**（Building Block View）。

## 1. 模块标识（必填）

| 字段 | 内容 |
|------|------|
| 模块名称 | [如：用户认证模块(auth-module)] |
| 模块缩写 | [如：auth] |
| 所属系统 | [系统名称] |
| 设计者 | [角色/姓名] |
| 版本 | v1.0 |
| 创建日期 | YYYY-MM-DD |
| 最后更新 | YYYY-MM-DD |

## 2. 模块职责（必填）

### 2.1 核心职责
[一句话描述模块存在的理由，如："负责用户身份注册、登录、令牌管理和权限验证"]

### 2.2 职责边界
| 做什么 | 不做什么 |
|--------|---------|
| [如：用户注册、登录、登出] | [如：不管理用户个人资料] |
| [如：JWT 令牌签发与验证] | [如：不处理OAuth第三方登录] |
| [如：密码重置流程] | [如：不发送邮件/短信（委托通知模块）] |
| [职责4] | [不负责4] |

## 3. 模块组件清单（必填）

### 3.1 组件列表
| 组件名 | 类型 | 职责 | 可见性 | 技术选型 |
|--------|------|------|--------|---------|
| [如：AuthController] | Controller | 接收HTTP请求，参数校验 | public | [FastAPI Router] |
| [如：AuthService] | Service | 认证业务逻辑 | public | [纯Python] |
| [如：TokenManager] | Utility | JWT生成/验证/刷新 | internal | [PyJWT] |
| [如：UserRepository] | Repository | 用户数据访问 | internal | [SQLAlchemy] |
| [如：PasswordHasher] | Utility | 密码哈希与验证 | internal | [bcrypt] |

### 3.2 组件依赖关系
```
AuthController → AuthService → UserRepository → Database
                    ↓              ↓
              TokenManager    PasswordHasher
```

## 4. 对外接口（必填，至少列出模块级公开接口）

### 4.1 模块公开 API
| 接口标识 | HTTP方法+路径 | 输入 | 输出 | 认证 | 说明 |
|---------|-------------|------|------|------|------|
| auth.register | POST /api/v1/auth/register | {email, password, name} | {user_id, token} | 否 | 用户注册 |
| auth.login | POST /api/v1/auth/login | {email, password} | {access_token, refresh_token} | 否 | 用户登录 |
| auth.logout | POST /api/v1/auth/logout | - | {} | 是 | 用户登出 |
| auth.refresh | POST /api/v1/auth/refresh | {refresh_token} | {access_token, refresh_token} | 否 | 刷新令牌 |
| auth.reset_password | POST /api/v1/auth/reset-password | {email} | {} | 否 | 发起密码重置 |
| auth.verify | GET /api/v1/auth/verify | - | {user_id, roles} | 是 | 验证令牌有效 |

### 4.2 模块间接口
| 接口名 | 提供方 | 消费方 | 协议 | 说明 |
|--------|--------|--------|------|------|
| AuthService.verify() | auth-module | 所有需认证的模块 | 函数调用(进程内) | 验证用户身份 |
| UserEvent.created | auth-module | notification-module | 消息队列 | 通知新用户注册 |

## 5. 数据模型（必填，至少核心实体）

### 5.1 模块拥有数据
| 实体 | 核心字段 | 存储 | 说明 |
|------|---------|------|------|
| User | id, email, password_hash, name, status, created_at, updated_at | PostgreSQL: users 表 | 用户账号 |
| Session | id, user_id, token_hash, expires_at, created_at | Redis | 活跃会话 |
| PasswordReset | id, user_id, token_hash, expires_at, used | PostgreSQL: password_resets 表 | 密码重置令牌 |

### 5.2 数据流转
```
注册流程：Client → AuthController.register() → AuthService.create_user() → PasswordHasher → UserRepository → Database → TokenManager → Response
登录流程：Client → AuthController.login() → AuthService.authenticate() → UserRepository.find() → PasswordHasher.verify() → TokenManager.generate() → Response
```

## 6. 模块间依赖（必填）

### 6.1 依赖的外部模块
| 依赖模块 | 依赖内容 | 依赖方式 | 失败影响 | 降级策略 |
|---------|---------|---------|---------|---------|
| [如：notification-module] | 发送验证邮件 | 异步消息 | 用户收不到邮件 | 提示用户手动验证 |
| [如：logging-module] | 审计日志 | 同步调用 | 审计缺失 | 忽略(非阻塞) |
| [如：rate-limit-module] | 限制请求频率 | 同步调用 | 无法限制频率 | 允许所有请求 |

### 6.2 被依赖方
| 依赖本模块的模块 | 使用的接口 | 说明 |
|---------------|----------|------|
| [如：order-module] | AuthService.verify() | 验证下单用户身份 |
| [如：profile-module] | UserRepository.find_by_id() | 获取用户基本信息 |

## 7. 非功能约束（必填）

| 约束项 | 要求 | 实现方式 |
|--------|------|---------|
| 认证延迟 | [如：< 200ms] | [bcrypt cost=10, JWT本地验证] |
| 令牌安全 | [如：Access 15min + Refresh 7d] | [JWT HS256 + 刷新轮换] |
| 并发支持 | [如：> 1000 验证/秒] | [无状态设计, 水平扩展] |
| 密码安全 | [如：≥ 8位，至少3种字符类型] | [前端+后端双重校验] |
| 防暴力破解 | [如：5次失败锁15分钟] | [Redis计数器+定时解锁] |

## 8. 错误处理约定（必填）

| 错误码 | 含义 | HTTP状态 | 用户提示 |
|--------|------|---------|---------|
| AUTH-001 | 认证失败 | 401 | "邮箱或密码错误" |
| AUTH-002 | 账号锁定 | 423 | "账号已锁定，请{X}分钟后重试" |
| AUTH-003 | 令牌过期 | 401 | "登录已过期，请重新登录" |
| AUTH-004 | 令牌无效 | 401 | "无效的认证信息" |
| AUTH-005 | 用户已存在 | 409 | "该邮箱已注册" |
| AUTH-006 | 密码太弱 | 400 | "密码至少8位，包含大小写字母和数字" |

## 9. 测试策略

| 测试类型 | 覆盖范围 | 工具 | 目标覆盖率 |
|---------|---------|------|----------|
| 单元测试 | Service/Manager/Util 全部逻辑 | pytest + unittest.mock | ≥ 90% |
| 集成测试 | Controller + Service + Repository | pytest + testcontainers | 核心流程 |
| E2E 测试 | 注册 → 登录 → 验证 → 登出 | pytest + requests | 全流程 |
| 安全测试 | SQL注入/暴力破解/令牌篡改 | OWASP ZAP / 手动 | 全部检查项 |

## 10. 填写示例

> 以"用户认证模块"为例：

| 字段 | 示例值 |
|------|--------|
| 模块名称 | 用户认证模块 (auth-module) |
| 核心职责 | 负责用户注册、登录、令牌管理和权限验证 |
| 内部组件 | AuthController, AuthService, TokenManager, UserRepository, PasswordHasher |
| 公开API | POST /register, POST /login, POST /logout, POST /refresh, POST /reset-password, GET /verify |
| 拥有数据 | User(users表), Session(Redis), PasswordReset(password_resets表) |
| 外部依赖 | notification-module(异步), rate-limit-module(同步) |
| 认证延迟 | < 200ms，JWT本地验证 |
| 防暴力破解 | 5次失败锁15分钟，Redis计数器 |
| 错误码 | AUTH-001~AUTH-006 覆盖所有异常场景 |

## 11. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| C4 Model - Container/Component | https://c4model.com | 模块组件清单、依赖关系图 |
| arc42 - Building Block View | https://arc42.org/overview | 模块职责、内部结构 |
| Google Design Docs | https://www.industrialempathy.com/posts/design-docs-at-google | 设计理由、替代方案 |
