# 接口契约模板

> **必填表单。** 缺任何必填项 = 打回重做。系统架构师/开发者角色必须完整填写。
> 参考标准：**OpenAPI/Swagger v3**、**Zalando RESTful API Guidelines**、**Microsoft Azure API Design**。

## 1. 契约标识（必填）

| 字段 | 内容 |
|------|------|
| 接口名称 | [如：用户认证接口] |
| 接口标识 | [如：auth-api-v1] |
| 提供方(Provider) | [如：auth-module] |
| 消费方(Consumer) | [如：web-client, mobile-client] |
| 协议 | [HTTP/REST / gRPC / GraphQL / 消息队列] |
| 版本 | v1.0 |
| 生效日期 | YYYY-MM-DD |
| 废弃日期 | [如适用] |
| 负责人 | [角色/姓名] |

## 2. 接口端点定义（必填）

### 2.1 REST/HTTP 接口

| 方法 | 路径 | 说明 | 认证 | 限流(QPS) | 超时 |
|------|------|------|------|----------|------|
| POST | /api/v1/auth/login | 用户登录 | 否 | 10/ip | 5s |
| POST | /api/v1/auth/register | 用户注册 | 否 | 3/ip | 5s |
| POST | /api/v1/auth/refresh | 刷新令牌 | 否 | 20/ip | 3s |
| GET | /api/v1/users/{id} | 获取用户信息 | Bearer | 100/ip | 2s |
| PUT | /api/v1/users/{id} | 更新用户信息 | Bearer | 20/ip | 3s |

### 2.2 gRPC 接口（如适用）

```protobuf
service AuthService {
  rpc Login(LoginRequest) returns (LoginResponse);
  rpc Register(RegisterRequest) returns (RegisterResponse);
  rpc RefreshToken(RefreshRequest) returns (RefreshResponse);
  rpc VerifyToken(VerifyRequest) returns (VerifyResponse);
}
```

### 2.3 消息队列接口（如适用）

| 消息类型 | Topic/Queue | 方向 | Schema | 说明 |
|---------|------------|------|--------|------|
| UserCreated | user.created | 发布 | user-created-v1.avsc | 用户注册成功后发布 |
| UserDeleted | user.deleted | 发布 | user-deleted-v1.avsc | 用户注销后发布 |
| SendEmail | notification.email | 订阅(消费) | send-email-v1.avsc | 监听发送邮件命令 |

## 3. 请求规格（必填，每个端点一个）

### 示例：POST /api/v1/auth/login

#### 3.1 请求
```json
{
  "email": "string (必填, RFC 5322 email格式, 最大255字符)",
  "password": "string (必填, 8-128字符)"
}
```

| 参数 | 类型 | 必填 | 约束 | 示例 |
|------|------|------|------|------|
| email | string | 是 | RFC 5322, max 255 | "test@example.com" |
| password | string | 是 | 8-128字符 | "CorrectPass123!" |
| device_info | object | 否 | 设备指纹信息 | {"os":"iOS17","model":"iPhone15"} |

**请求 Headers：**
| Header | 必填 | 值 | 说明 |
|--------|------|-----|------|
| Content-Type | 是 | application/json | |
| User-Agent | 否 | string | 客户端标识 |
| X-Request-ID | 建议 | UUID | 请求追踪ID |

#### 3.2 成功响应

**HTTP 200 OK**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "usr_abc123",
      "name": "测试用户",
      "email": "test@example.com",
      "roles": ["user"]
    }
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-07-22T10:30:00Z"
  }
}
```

**响应 Headers：**
| Header | 值 | 说明 |
|--------|-----|------|
| X-Request-ID | 回显请求ID | 用于追踪 |

#### 3.3 错误响应

**HTTP 401 Unauthorized**
```json
{
  "error": {
    "code": "AUTH-001",
    "message": "邮箱或密码错误",
    "details": [],
    "trace_id": "abc123def456",
    "timestamp": "2026-07-22T10:30:00Z"
  }
}
```

**HTTP 429 Too Many Requests**
```json
{
  "error": {
    "code": "RATE-001",
    "message": "请求过于频繁，请稍后重试",
    "details": [],
    "trace_id": "abc123def456",
    "timestamp": "2026-07-22T10:30:00Z"
  }
}
```
| Header | 值 | 说明 |
|--------|-----|------|
| Retry-After | 60 | 多少秒后可重试 |

#### 3.4 错误码清单（此端点相关）

| HTTP状态 | 错误码 | 说明 | 是否可重试 |
|---------|--------|------|----------|
| 400 | VAL-001 | 请求参数校验失败 | 否（修正参数后） |
| 401 | AUTH-001 | 认证失败 | 是（修正密码后） |
| 423 | AUTH-002 | 账号已锁定 | 是（等待解锁后） |
| 429 | RATE-001 | 超过频率限制 | 是（等待后） |
| 500 | SVR-001 | 服务器内部错误 | 是（幂等请求） |
| 503 | SVR-002 | 服务暂时不可用 | 是 |

## 4. 契约兼容性规则（必填）

### 4.1 向前兼容（非 Breaking Change）
以下变更视为向前兼容，无需升级主版本号：
- [ ] 新增可选字段（请求体）
- [ ] 新增响应字段（消费方应忽略未知字段）
- [ ] 新增端点（不影响已有端点）
- [ ] 新增可选的查询参数
- [ ] 放宽校验规则（如密码最大长度从20增到128）
- [ ] 新增 HTTP 方法（已有路径）

### 4.2 不向前兼容（Breaking Change）
以下变更必须升级主版本号：
- [ ] 删除或重命名字段
- [ ] 修改字段类型
- [ ] 新增必填字段
- [ ] 删除端点
- [ ] 修改认证方式
- [ ] 修改错误码含义
- [ ] 收紧校验规则（如密码最小长度从6增到8）

## 5. 契约测试（必填）

| 测试类型 | 工具 | 覆盖范围 | 通过标准 |
|---------|------|---------|---------|
| Schema 验证 | [OpenAPI validator / protoc] | 所有端点请求/响应 | Schema 匹配 |
| 功能测试 | [pytest / Postman Collection] | 所有端点正常+异常流程 | 全部通过 |
| 契约测试 | [Pact / Spring Cloud Contract] | 提供方-消费方一致性 | 契约匹配 |
| 性能测试 | [k6 / JMeter] | P95延迟/QPS达标 | 满足 SLA |

## 6. 版本与废弃策略（必填）

| 策略项 | 约定 |
|--------|------|
| 版本号格式 | v{major}.{minor}，路径携带版本号 |
| 主版本升级 | Breaking Change 触发 |
| 次版本升级 | 新增功能（非Breaking） |
| 旧版本废弃期 | [如：新版本发布后 6 个月] |
| 废弃通知方式 | [如：HTTP Deprecation Header + API文档标注] |
| 废弃期后处理 | [如：返回 410 Gone] |

## 7. 填写示例

> 以"用户认证 REST API v1"为例的完整契约：

```yaml
# OpenAPI 3.0 片段
openapi: "3.0.3"
info:
  title: Auth API
  version: "1.0.0"
  description: 用户认证与令牌管理接口
paths:
  /api/v1/auth/login:
    post:
      summary: 用户登录
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email:
                  type: string
                  format: email
                  maxLength: 255
                password:
                  type: string
                  minLength: 8
                  maxLength: 128
      responses:
        '200':
          description: 登录成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LoginResponse'
        '401':
          description: 认证失败
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '423':
          description: 账号锁定
        '429':
          description: 请求过于频繁
```

## 8. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| OpenAPI/Swagger v3 | https://swagger.io/docs/specification/v3_0/basic-structure/ | 接口描述格式、Schema 定义 |
| Zalando RESTful API Guidelines | https://opensource.zalando.com/restful-api-guidelines/ | REST 设计原则、版本管理 |
| Microsoft Azure API Design | https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design | 错误响应、异步操作、版本控制 |
| elsewhencode/project-guidelines | https://raw.githubusercontent.com/elsewhencode/project-guidelines/master/README.md | 资源导向设计、命名规范 |
