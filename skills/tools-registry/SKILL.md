# Tools-Registry (treg) - 团队工具与密钥管理 Skill

## Description

基于 [tools-registry](https://github.com/superdesigndev/tools-registry) 的团队共享工具、技能和密钥注册中心。解决代理调用外部服务时的密钥安全问题——凭证由注册中心服务端注入，调用方永远不持有密钥。

## When to Use

- 需要调用外部 API（Stripe、GitHub、PostHog 等）但不想在本地存放密钥
- 团队共享技能和工具配置
- 需要审计谁在什么时候调了什么外部服务
- 用户要求"安全地调用 X 服务"、"共享这个 API 给团队"
- Loop 工程 execute 阶段需要外部服务集成时

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## 核心概念

| 概念 | 说明 |
|------|------|
| **tool** | 注册中心代为调用的东西。分两种：endpoint（HTTP API）和 CLI（vendor 二进制） |
| **skill/bundle** | 一个完整能力 = SKILL.md 配方 + 所需密钥 + 所需工具 |
| **binding** | 把密钥注入到请求中的方式（header、query、OAuth bearer 等） |
| **org** | 一切资源归属的组织，token = (user, org) 成员关系 |

## Execution

### 1. 注册端点（Endpoint）

```bash
# 添加密钥到注册中心
treg secret add STRIPE_KEY --value sk_live_xxx

# 注册工具（把 base_url 和密钥绑定）
treg add stripe --base-url https://api.stripe.com --secret STRIPE_KEY

# 或从 .env 批量导入
treg upload env --select openai,stripe,resend
```

### 2. 安全调用（代理不持有密钥）

```bash
# CLI 方式
treg call stripe v1/balance
treg call github repos/superdesigndev/loopany

# 或直接通过代理 URL（代理自动注入凭证）
# GET https://treg.example.com/call/https://api.stripe.com/v1/balance
#   header: X-Treg-Token: <your-token>
```

### 3. CLI 工具代理

```bash
# 在本地运行 vendor CLI，密钥自动注入
treg run stripe -- get /v1/balance
treg run gh -- pr list

# 在服务器端运行（密钥完全不接触本地）
treg run --server some-cli command

# 开启自动注入 shell
treg shell start   # 之后直接用 stripe、gh 等命令
```

### 4. 技能共享

```bash
# 注册一个完整技能（配方 + 密钥 + 工具）
treg upload skills --dir ./my-skill

# 安装团队共享的技能
treg skill install seo-blog-writer
```

### 5. 与 Loop 工程集成

| Loop 阶段 | treg 的作用 |
|-----------|------------|
| plan | 识别需要的外部服务，检查注册中心是否已有 |
| execute | 通过代理安全调用外部 API/CLI |
| verify | 审计日志验证调用正确性 |
| governance | 确保密钥不泄露到代码/日志中 |

### 6. 健康检查

```bash
treg health   # 检查所有凭证是否有效
```

## 与 Loop 工程的集成规则

1. **execute 阶段**需要调用外部服务时，优先通过 treg 代理
2. 如果 treg 中未注册所需服务，标记为 gate 决策项（需用户决定是否注册）
3. 所有外部调用自动记录审计日志，作为 evidence 存入 `.ai/evidence/`
4. 密钥永远不出现在代码、日志、任务卡或评审报告中

## 输出

- 注册的工具/技能列表（通过 `treg tool ls`）
- 调用审计日志（通过 `treg calls`）
- 凭证健康报告（通过 `treg health`）

## 约束

- 密钥永远不暴露给调用方（代理/CLI/代码）
- 所有调用都有审计记录
- 注册新工具需要用户 gate 审批
- 不在代码或文档中硬编码任何密钥
- treg 服务器部署位置由用户决定（自托管或 hosted）

## 依赖

- treg CLI: `curl -fsSL https://treg.superdesign.dev/install.sh | sh`
- treg 服务器: 自托管或 `treg.superdesign.dev`
- 支持 4 种认证注入方式：env / secret_file / oauth / cli_auth
