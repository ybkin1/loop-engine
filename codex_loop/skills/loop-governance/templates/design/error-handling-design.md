# 错误处理设计模板

> **必填表单。** 缺任何必填项 = 打回重做。开发者/系统架构师角色必须完整填写。
> 参考标准：**Microsoft Azure API Design**（错误响应）、**OWASP Secure Coding Practices**、**Google Error Handling**。

## 1. 错误码体系设计（必填）

### 1.1 错误码格式约定
```
[项目前缀]-[模块代码]-[错误序号]
示例: APP-AUTH-001 = 应用-Auth模块-第1号错误
```

### 1.2 错误码清单（必填，至少覆盖核心流程）
| 错误码 | HTTP状态码 | 错误描述 | 用户可见信息 | 触发条件 | 处理方式 |
|--------|-----------|---------|------------|---------|---------|
| APP-AUTH-001 | 401 | 认证失败 | "邮箱或密码错误" | 凭证不匹配 | 提示重新输入 |
| APP-AUTH-002 | 423 | 账号锁定 | "账号已锁定，请{X}分钟后重试" | 连续失败5次 | 显示剩余锁定时间 |
| APP-AUTH-003 | 401 | 令牌过期 | "登录已过期，请重新登录" | JWT过期 | 引导刷新或重新登录 |
| APP-RES-001 | 404 | 资源不存在 | "请求的资源不存在" | ID无效 | 提示检查ID |
| APP-VAL-001 | 400 | 参数校验失败 | "输入不合法：{具体字段}" | 参数不符合约束 | 提示修正输入 |
| APP-SVR-001 | 500 | 服务器内部错误 | "服务暂时不可用，请稍后重试" | 未预期异常 | 记录日志+告警 |

### 1.3 错误响应统一格式（必填）
```json
{
  "error": {
    "code": "APP-AUTH-001",
    "message": "邮箱或密码错误",
    "details": [
      {
        "field": "email",
        "reason": "not_found"
      }
    ],
    "trace_id": "abc123def456",
    "timestamp": "2026-07-22T10:30:00Z"
  }
}
```

## 2. 分层错误处理策略（必填）

### 2.1 各层错误处理职责
| 层次 | 职责 | 不应该做的事 |
|------|------|------------|
| 表现层(Controller/API) | 将异常映射为HTTP状态码+用户友好信息 | 不应泄露内部堆栈 |
| 业务层(Service) | 抛出语义化业务异常 | 不应处理HTTP细节 |
| 数据层(Repository) | 包装底层异常为数据异常 | 不应吞异常 |
| 基础设施层 | 抛出明确的基础设施异常 | 不应暴露连接串/密码 |

### 2.2 异常类型定义（必填）
```python
# 基础异常类
class AppBaseError(Exception):
    """应用基础异常"""
    def __init__(self, code: str, message: str, http_status: int = 500):
        self.code = code
        self.message = message
        self.http_status = http_status

# 具体异常
class AuthenticationError(AppBaseError):
    """认证相关异常"""
    pass

class AuthorizationError(AppBaseError):
    """授权相关异常"""
    pass

class ValidationError(AppBaseError):
    """输入校验异常"""
    pass

class ResourceNotFoundError(AppBaseError):
    """资源不存在异常"""
    pass

class BusinessRuleViolationError(AppBaseError):
    """业务规则违反"""
    pass
```

## 3. 错误传播规则（必填）

### 3.1 传播路线
```
底层异常 → 包装为业务异常 → 抛到Controller → 全局ExceptionHandler → 统一JSON响应
                                                           ↓
                                                        日志系统 → 监控告警
```

### 3.2 重试策略
| 错误类型 | 是否可重试 | 重试次数 | 退避策略 | 幂等保证 |
|---------|----------|---------|---------|---------|
| 网络超时 | 是 | 3 | 指数退避(1s,2s,4s) | 请求ID去重 |
| 数据库死锁 | 是 | 3 | 随机退避(100-500ms) | 数据库事务 |
| 第三方API限流 | 是 | 5 | 根据Retry-After头 | 请求ID去重 |
| 参数校验失败 | 否 | 0 | N/A | N/A |
| 认证失败 | 否 | 0 | N/A | N/A |

## 4. 安全相关错误处理（必填）

| 要求 | 是否实施 | 说明 |
|------|---------|------|
| 生产环境不显示堆栈信息 | [是/否] | [异常信息不暴露代码路径] |
| 认证错误模糊提示 | [是/否] | [不说"用户名不存在"而说"用户名或密码错误"] |
| 错误信息不泄露数据 | [是/否] | [SQL错误不暴露表结构] |
| 异常频率限制 | [是/否] | [防止利用异常信息进行探测] |
| 敏感操作额外日志 | [是/否] | [登录失败/权限拒绝记录审计日志] |
| 速率限制错误返回429 | [是/否] | [配合Retry-After头] |

## 5. 降级与兜底策略（必填）

| 场景 | 降级策略 | 兜底方案 | 恢复条件 |
|------|---------|---------|---------|
| 数据库不可用 | 返回缓存数据 | 返回503+提示稍后重试 | 数据库恢复 |
| 第三方API超时 | 返回上次成功结果 | 返回503 | API恢复 |
| 缓存不可用 | 直查数据库 | 降低性能继续服务 | 缓存恢复 |
| 消息队列不可用 | 写本地日志待补发 | 丢弃非关键消息 | MQ恢复 |

## 6. 日志与监控（必填）

### 6.1 日志级别约定
| 级别 | 适用场景 | 示例 |
|------|---------|------|
| DEBUG | 开发调试信息 | 函数入参/出参明细 |
| INFO | 关键业务流程 | 用户登录成功/订单创建 |
| WARNING | 可恢复的异常 | 重试成功/降级启动 |
| ERROR | 需人工介入 | 数据库连接失败/第三方API不可达 |
| CRITICAL | 系统级故障 | 数据丢失/安全事件 |

### 6.2 监控告警规则
| 告警规则 | 阈值 | 通知方式 | 处理优先级 |
|---------|------|---------|----------|
| 5xx错误率 | > 1% | 钉钉/PagerDuty | P0 |
| 4xx错误率 | > 10% | 钉钉 | P1 |
| 平均响应时间 | > 2s | 钉钉 | P2 |
| 单接口异常 | > 50次/分钟 | 钉钉 | P1 |
| 磁盘/内存 | > 85% | 钉钉 | P1 |

## 7. 填写示例

> 以一个"用户登录"场景的错误处理设计为例：

| 维度 | 示例值 |
|------|--------|
| 错误码格式 | APP-AUTH-XXX |
| 主错误码 | APP-AUTH-001(认证失败), APP-AUTH-002(账号锁定), APP-AUTH-003(令牌过期) |
| 认证失败响应 | HTTP 401, {"error":{"code":"APP-AUTH-001","message":"邮箱或密码错误"}} |
| 安全策略 | 不说"用户不存在",连续5次失败锁定15分钟 |
| 日志 | INFO记录成功登录, WARNING记录失败登录, ERROR记录暴力破解检测 |
| 监控告警 | 单IP 20次/分钟登录失败 → 告警 |

## 8. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| Microsoft Azure API Design - Error Responses | https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design | 错误码格式、统一响应结构 |
| OWASP Secure Coding Practices | https://owasp.org/www-project-secure-coding-practices-quick-reference-guide | 安全错误处理、模糊提示 |
| Google Code Review - Error Handling | https://google.github.io/eng-practices/review/reviewer/looking-for | 异常处理检查清单 |
| Zalando RESTful API Guidelines | https://opensource.zalando.com/restful-api-guidelines/ | 错误响应JSON格式 |
