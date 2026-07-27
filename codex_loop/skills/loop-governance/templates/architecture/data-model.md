# 数据模型模板

> **必填表单。** 缺任何必填项 = 打回重做。系统架构师/数据工程师角色必须完整填写。
> 参考标准：**arc42**（Building Block View - 数据部分）、**C4 Model**（Code 层）。

## 1. 模型标识（必填）

| 字段 | 内容 |
|------|------|
| 模型名称 | [如：用户与权限数据模型] |
| 所属领域 | [如：用户管理域] |
| 设计者 | [角色/姓名] |
| 版本 | v1.0 |
| 创建日期 | YYYY-MM-DD |
| 最后更新 | YYYY-MM-DD |

## 2. 实体清单（必填）

### 2.1 核心实体列表
| 实体名 | 中文名 | 说明 | 预估数据量 | 增长速度 |
|--------|--------|------|----------|---------|
| User | 用户 | 系统注册用户 | [如：10万] | [如：1000/天] |
| Role | 角色 | 系统角色定义 | [如：10] | [几乎不增长] |
| Permission | 权限 | 细粒度权限项 | [如：50] | [几乎不增长] |
| UserRole | 用户-角色关联 | 多对多关联表 | [如：10万] | [增长率] |

### 2.2 实体关系图（ER Diagram）
```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│   User   │────→│  UserRole    │←────│   Role   │
└──────────┘     └──────────────┘     └──────────┘
     │                                      │
     │ 1:N                                  │ N:M
     ▼                                      ▼
┌──────────┐                        ┌──────────────┐
│ Session  │                        │  Permission  │
└──────────┘                        └──────────────┘
```

## 3. 实体详细定义（必填，每个核心实体一个表）

### 3.1 实体：User

| 字段名 | 类型 | 长度 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|------|--------|------|------|
| id | UUID | - | 是 | gen_random_uuid() | PK | 用户唯一标识 |
| email | VARCHAR | 255 | 是 | - | UNIQUE, NOT NULL | 登录邮箱 |
| password_hash | VARCHAR | 255 | 是 | - | NOT NULL | bcrypt 哈希 |
| name | VARCHAR | 100 | 是 | - | NOT NULL | 显示名称 |
| status | VARCHAR | 20 | 是 | 'active' | CHECK(status IN ('active','locked','disabled')) | 账号状态 |
| email_verified | BOOLEAN | - | 是 | false | - | 邮箱是否已验证 |
| failed_login_count | INTEGER | - | 是 | 0 | CHECK(>=0) | 连续登录失败次数 |
| locked_until | TIMESTAMP | - | 否 | NULL | - | 锁定解除时间 |
| last_login_at | TIMESTAMP | - | 否 | NULL | - | 最后登录时间 |
| created_at | TIMESTAMP | - | 是 | NOW() | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | - | 是 | NOW() | NOT NULL | 更新时间 |

**索引：**
| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| idx_users_email | email | UNIQUE | 登录查找 |
| idx_users_status | status | BTREE | 按状态查询 |
| idx_users_created_at | created_at | BTREE | 按时间范围查询 |

**填写示例（DDL）：**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'locked', 'disabled')),
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_count INTEGER NOT NULL DEFAULT 0
        CHECK (failed_login_count >= 0),
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 3.2 实体：Role

| 字段名 | 类型 | 长度 | 必填 | 说明 |
|--------|------|------|------|------|
| id | UUID | - | 是 | PK |
| name | VARCHAR | 50 | 是, UNIQUE | 角色名(如：admin, user, moderator) |
| description | VARCHAR | 200 | 否 | 角色说明 |
| created_at | TIMESTAMP | - | 是 | 创建时间 |

### 3.3 实体：UserRole (关联表)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_id | UUID | FK → users.id |
| role_id | UUID | FK → roles.id |
| assigned_at | TIMESTAMP | 授权时间 |

**约束：** PRIMARY KEY (user_id, role_id)

### 3.4 实体：Session

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| token_hash | VARCHAR | 256 | 令牌哈希 |
| refresh_token_hash | VARCHAR | 256 | 刷新令牌哈希 |
| expires_at | TIMESTAMP | 过期时间 |
| created_at | TIMESTAMP | 创建时间 |

## 4. 数据存储策略（必填）

### 4.1 存储引擎选择
| 数据 | 存储引擎 | 选择理由 |
|------|---------|---------|
| users, roles, permissions | PostgreSQL | 事务支持、强一致性 |
| sessions, rate_limit_counters | Redis | 高性能、TTL支持、原子操作 |
| 用户头像 | S3/OSS 对象存储 | 适合非结构化数据 |
| 审计日志 | Elasticsearch | 全文检索、时序查询 |
| 操作日志（归档） | S3/OSS（Parquet格式） | 低成本、列式存储 |

### 4.2 数据生命周期
| 数据类型 | 热存储期 | 温存储期 | 冷存储期 | 删除策略 |
|---------|---------|---------|---------|---------|
| 用户数据 | 永久 | 永久 | - | 用户注销后30天删除 |
| 会话数据 | 15分钟(活跃) | - | - | 过期自动删除(TTL) |
| 审计日志 | 30天 | 90天 | 1年 | 1年后归档删除 |
| 操作日志 | 7天 | 30天 | 180天 | 180天后归档或删除 |

## 5. 数据迁移策略（必填，首次可填"不适用"）

| 迁移原则 | 说明 |
|---------|------|
| 所有迁移有回滚脚本 | [是] |
| 迁移不与旧代码冲突 | [是（前向兼容）] |
| 大表变更用在线迁移 | [是（如：pt-online-schema-change）] |
| 迁移前有备份 | [是] |
| 迁移工具 | [如：Flyway / Alembic / golang-migrate] |

## 6. 数据安全（必填）

| 安全措施 | 是否采用 | 说明 |
|---------|---------|------|
| 敏感字段加密(存储) | [是/否] | [如：password_hash bcrypt, PII字段 AES-256] |
| 传输加密(TLS) | [是/否] | [TLS 1.3] |
| 数据库访问控制 | [是/否] | [应用账户最小权限，仅SELECT/INSERT/UPDATE/DELETE] |
| 备份加密 | [是/否] | [备份文件 AES-256 加密] |
| 数据脱敏(测试环境) | [是/否] | [生产数据脱敏后导入测试] |
| 审计日志 | [是/否] | [关键表变更记录审计] |

## 7. 性能考量

| 实体 | 预估数据量 | 查询模式 | 优化策略 |
|------|----------|---------|---------|
| users | 100万+ | 按email精确查询(高频)、按状态列表(中频) | email唯一索引、status索引 |
| sessions | 50万+(活跃) | 按token_hash精确查询(超高频)、按过期时间清理 | token_hash索引、TTL自动清理 |
| user_roles | 100万+ | 按user_id查询(高频) | 联合主键(user_id, role_id) |

## 8. 填写示例

> 以"用户与权限数据模型"为例：

| 维度 | 示例值 |
|------|--------|
| 核心实体 | User, Role, Permission, UserRole, Session |
| User最核心字段 | id(UUID), email(VARCHAR255,UNIQUE), password_hash(VARCHAR255), status(ENUM) |
| 存储引擎 | PostgreSQL(用户/角色), Redis(会话), S3(头像), ES(审计日志) |
| 安全措施 | bcrypt密码哈希, TLS1.3, 最小权限, 备份加密, 测试环境脱敏 |
| 迁移工具 | Alembic, 前向兼容, 有回滚脚本, 大表在线迁移 |
| 性能优化 | email唯一索引, token_hash索引, Redis TTL自动清理 |
| 生命周期 | 用户永久(注销30天删), 会话15分钟TTL, 审计日志30天热/1年归档 |

## 9. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| arc42 - Building Block View | https://arc42.org/overview | 数据实体定义、存储策略 |
| C4 Model - Code Level | https://c4model.com | 实体关系、数据流 |
| 12-Factor App - Backing Services | https://12factor.net/backing-services | 存储引擎作为附加资源 |
| Google Design Docs - Data Model | https://www.industrialempathy.com/posts/design-docs-at-google | 数据模型设计、存储选择 |
