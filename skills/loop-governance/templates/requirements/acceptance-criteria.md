# 验收标准模板

> **必填表单。** 缺任何必填项 = 打回重做。产品经理/质量工程师角色必须完整填写。
> 参考标准：**Cucumber Gherkin BDD**、**IEEE 829 Test Plan**。

## 1. 验收概述（必填）

| 字段 | 内容 |
|------|------|
| 功能/故事编号 | [如：FR-001 / US-001] |
| 功能名称 | [如：用户登录] |
| 版本 | v1.0 |
| 负责人 | [角色/姓名] |
| 验收日期 | YYYY-MM-DD |

## 2. Gherkin 场景（必填，核心场景用 Gherkin 格式）

### 2.1 Happy Path（必填，至少 1 个场景）

```gherkin
Feature: [功能名称]

  Scenario: [正常流程场景名称]
    Given [前置条件]
    When [用户操作]
    Then [期望结果]
```

**填写示例：**
```gherkin
Feature: 用户登录

  Scenario: 用户使用正确邮箱和密码登录
    Given 用户已注册账号 "test@example.com"
    And 用户处于未登录状态
    When 用户在登录页输入邮箱 "test@example.com" 和密码 "CorrectPass123!"
    And 用户点击"登录"按钮
    Then 页面跳转至用户首页
    And 页面显示欢迎消息 "欢迎回来，测试用户"
    And 会话 token 已存储在浏览器中
```

### 2.2 Error Path（必填，至少 2 个场景）

```gherkin
  Scenario: [异常场景名称]
    Given [前置条件]
    When [异常操作]
    Then [错误处理期望]
```

**填写示例：**
```gherkin
  Scenario: 用户使用错误密码登录
    Given 用户已注册账号 "test@example.com"
    When 用户在登录页输入邮箱 "test@example.com" 和密码 "WrongPassword"
    And 用户点击"登录"按钮
    Then 页面停留在登录页
    And 显示错误提示 "邮箱或密码错误"
    And 密码输入框被清空
    And 用户未被登录

  Scenario: 用户连续5次登录失败后账号锁定
    Given 用户账号 "test@example.com" 已连续失败4次
    When 用户第5次输入错误密码
    Then 账号被锁定
    And 显示提示 "账号已被锁定，请15分钟后重试或联系管理员"
```

### 2.3 Boundary Conditions（必填，至少 2 个场景）

```gherkin
  Scenario: [边界条件场景名称]
    Given [边界前置条件]
    When [边界操作]
    Then [边界期望结果]
```

**填写示例：**
```gherkin
  Scenario: 密码长度为最小允许值（8位）
    Given 用户注册页面已打开
    When 用户输入密码 "12345678"
    Then 密码强度检查通过
    And 允许提交注册

  Scenario: 空表单提交
    Given 用户登录页面已打开
    When 用户不输入任何内容直接点击"登录"
    Then 邮箱输入框显示校验错误 "请输入邮箱"
    And 密码输入框显示校验错误 "请输入密码"
    And 表单未提交
```

## 3. 验收清单（必填）

| 编号 | 验收项 | 验证方式 | 通过标准 | 优先级(P0/P1/P2) |
|------|--------|---------|---------|-----------------|
| AC-001 | [如：登录成功后跳转首页] | [手动测试 / 自动化测试] | [跳转URL = /home] | P0 |
| AC-002 | [验收项2] | [验证方式] | [通过标准] | [优先级] |
| AC-003 | [验收项3] | [验证方式] | [通过标准] | [优先级] |

## 4. 非功能性验收（必填）

| 编号 | 验收项 | 指标 | 测量方式 | 通过标准 |
|------|--------|------|---------|---------|
| NF-001 | 响应时间 | [如：< 200ms] | [工具/方法] | [标准] |
| NF-002 | 并发能力 | [如：支持100并发] | [工具/方法] | [标准] |
| NF-003 | 浏览器兼容 | [如：Chrome/Firefox/Safari最新版] | [手动/自动] | [标准] |

## 5. 签收标准（必填）

| 条件 | 是否必须 |
|------|---------|
| 所有 P0 验收项通过 | [ ] 是 |
| 所有 P1 验收项通过或有豁免 | [ ] 是 |
| 无 P0 级缺陷未修复 | [ ] 是 |
| 产品经理签字确认 | [ ] 是 |
| 质量工程师签字确认 | [ ] 是 |

## 6. 参考标准

| 标准 | 来源 | 与模板对应 |
|------|------|----------|
| Cucumber Gherkin Reference | https://cucumber.io/docs/gherkin/reference/ | Gherkin 场景格式（Given/When/Then） |
| IEEE 829 - Test Plan | https://www.softwaretestinghelp.com/test-plan-template/ | 验收清单、签收标准 |
| Mountain Goat Software - Acceptance Criteria | https://www.mountaingoatsoftware.com/agile/user-stories | 用户故事验收条件 |
