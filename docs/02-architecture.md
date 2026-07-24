# 02 — 架构设计

> Loop Engine v1.0 架构设计 | 状态: draft | 对应需求: docs/01-requirements.md

---

## 1. 架构总览

Loop Engine 采用**四层插件架构**，每层在 ZCode 插件体系中承担不同职责：

```
┌─────────────────────────────────────────────────────┐
│                    ZCode 客户端                       │
├─────────────────────────────────────────────────────┤
│  命令层  │ /loop-validate  /loop-verify-chain  /loop-cost  │
├─────────────────────────────────────────────────────┤
│  工具层  │ MCP Server (JSON-RPC) → 7 工具               │
├─────────────────────────────────────────────────────┤
│  知识层  │ loop-governance Skill + 11 角色 Agent         │
├─────────────────────────────────────────────────────┤
│  执行层  │ SessionStart Hook    PreToolUse Hook ×2       │
│          │ session_brief.py     gate_guard.py            │
│          │                      path_guard.py            │
├─────────────────────────────────────────────────────┤
│           .ai/ 治理数据 (state / gates / tasks)         │
└─────────────────────────────────────────────────────┘
```

| 层 | 触发方式 | 对 AI 可见 | 可否被绕过 |
|----|---------|-----------|-----------|
| **执行层** (hooks) | ZCode 事件自动触发 | 否（在工具调用前执行） | 否（exit 2 硬阻断） |
| **知识层** (skill) | AI 模型按需加载 | 是（注入上下文） | 是（AI 需遵守） |
| **工具层** (MCP) | AI 调用 `tools/call` | 是 | 是（AI 可决定不调） |
| **命令层** (commands) | 用户输入斜杠命令 | 是 | — |

核心设计原则：**执行层是强制性的（机器裁决），知识层是指导性的（AI 自律），两者互补。**

---

## 2. 执行层：Hook 系统

### 2.1 架构定位

Hook 是唯一不能被 AI 绕过的层。它们运行在 ZCode 进程空间内，在 AI 工具调用之前和会话启动时由 ZCode 引擎直接触发。

### 2.2 Hook 拓扑

```
ZCode 事件流
  │
  ├─ SessionStart ──→ session_brief.py
  │   ├─ 读取 .ai/state.yaml + .ai/gates.yaml + .ai/HANDOFF.md
  │   ├─ 构建治理状态摘要
  │   └─ 输出 JSON → additionalContext 注入会话
  │
  └─ PreToolUse (Write|Edit) ──→ gate_guard.py ──→ path_guard.py
        │                           │                    │
        │                           ├─ pass              ├─ pass (非保护区)
        │                           ├─ exit 2 (pending)  └─ ask / exit 2 (保护区)
        │                           └─ 豁免: .ai/gates.yaml
        │
        └─ ZCode 根据 exit code + stdout JSON 决定放行/阻断/询问
```

### 2.3 三个 Hook 详解

#### H-01: session_brief.py

| 属性 | 值 |
|------|-----|
| **事件** | SessionStart |
| **Matcher** | `startup\|resume` |
| **超时** | 10s |
| **失败策略** | fail-open（exit 0 + stderr 警告） |
| **前置条件** | `.ai/state.yaml` 存在 |

**输出协议**（SessionStart JSON）：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<治理状态摘要文本>"
  }
}
```

#### H-02: gate_guard.py

| 属性 | 值 |
|------|-----|
| **事件** | PreToolUse |
| **Matcher** | `Write\|Edit` |
| **超时** | 5s |
| **失败策略** | fail-closed（状态不可读 → exit 2，安全默认） |
| **前置条件** | `.ai/state.yaml` 存在 |

**阻断条件**：`gates.yaml` 中存在 `status: pending` 的 gate，或 `state.yaml` 的 `current_gate_id` 非空。

**豁免规则**：对 `.ai/gates.yaml` 的写入始终放行——这是决策记录豁免，防止死锁（用户批准 gate 后 AI 无法将决定写入 gates.yaml）。

**退出码语义**：0 = 放行，2 = 阻断（ZCode deny）。

#### H-03: path_guard.py

| 属性 | 值 |
|------|-----|
| **事件** | PreToolUse |
| **Matcher** | `Write\|Edit` |
| **超时** | 5s |
| **失败策略** | fail-open（内部异常 → exit 0 + stderr 警告） |
| **前置条件** | `.ai/state.yaml` 存在 |

**保护区**（`config.yaml` 可配置）：
```
AGENTS.md          — 项目启动规则（精确文件匹配）
stable/            — 稳定产物目录（前缀匹配）
registry/          — 注册表目录（前缀匹配）
.zcode/config.json — ZCode 配置（精确文件匹配）
.zcode/tools/      — 治理工具脚本（前缀匹配）
```

**两种模式**：
- `ask`（默认）：输出 JSON `permissionDecision: ask`，用户客户端弹窗确认
- `deny`：exit 2 硬阻断，需先取得 gate

**输出协议**（PreToolUse ask JSON）：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "[path_guard] 目标 <path> 命中保护区规则 <rule>。..."
  }
}
```

### 2.4 共享模块 hook_common.py

三个 hook 的公共工具库（纯标准库 + 可选 PyYAML）：

| 函数 | 职责 |
|------|------|
| `read_stdin_json()` | 读取 hook 标准输入 |
| `project_root()` | 解析项目根（ZCODE_PROJECT_DIR → cwd） |
| `is_governance_project()` | 检查 `.ai/state.yaml` 是否存在 |
| `load_config()` | 读取 `config.yaml` 并与 DEFAULT_CONFIG 合并 |
| `load_state()` | 解析 `.ai/state.yaml`（PyYAML 或退化行扫描） |
| `pending_gates()` | 从 `.ai/gates.yaml` 提取 pending gate ID 列表 |
| `extract_target_path()` | 从 PreToolUse 输入提取被写文件路径 |
| `normalize_rel()` | 路径规范化为项目相对路径 |
| `matches_protected()` | 检查路径是否命中保护区 |

---

## 3. 知识层：Skill 系统

### 3.1 loop-governance Skill

**入口**：`skills/loop-governance/SKILL.md`

启动检查清单：
1. 读取用户最新请求
2. 确认项目根（`.ai/state.yaml` 存在）
3. 读取 state.yaml、HANDOFF.md、当前任务文件、gates.yaml、task_graph.yaml
4. 运行 `validate_state.py`
5. 存在 pending gate → 停止并展示
6. 只在批准范围内继续

**配置**：`config.yaml`（约 300 行 YAML）
- `gate_guard`：启用/失败策略/豁免路径
- `path_guard`：启用/决策模式/保护区列表
- `session_brief`：启用/最大 pending 列表长度
- `quality_gates`：六项检查模板（lint/typecheck/test/coverage/audit/build）
- `certification`：角色认证系统（认证要求/降级规则 14 条）
- `degradation`：从 CAPABILITY_UNAVAILABLE 到 ROLE_BLOCKED 的状态机

**参考文档**：
- `governance-lifecycle.md` — 任务/Gate/产物状态机
- `decision-rules.md` — evidence vs 批准的边界
- `hook-protocol.md` — ZCode hook 协议与排障

### 3.2 证据链定义

`chain.yaml` 定义从需求到交付的证据链拓扑：

```
requirements ──→ architecture ──→ interface_contract ──→ source_code
                                                              │
                                              ┌───────────────┤
                                              ▼               ▼
                                       quality_report   security_report
                                              │               │
                                              └───────┬───────┘
                                                      ▼
                                                human_review
```

### 3.3 11 角色 Agent 体系

`agents/` 目录包含 11 个专业化角色，每个角色有独立的 SKILL.md 和参考文档：

| 角色 | 职责 | 状态 |
|------|------|------|
| `main-thread` | 编排者、记录官 | SKILL.md |
| `product-manager` | 产品需求管理 | SKILL.md |
| `project-manager` | 任务拆分与追踪 | SKILL.md |
| `system-architect` | 系统架构设计 | SKILL.md + checklist |
| `module-architect` | 模块接口契约 | SKILL.md + contract spec |
| `developer` | 代码实现 | SKILL.md + coding standards |
| `quality-engineer` | 质量门禁 | SKILL.md + scripts（原型） |
| `security-engineer` | 安全审计 | SKILL.md |
| `independent-reviewer` | 独立代码评审 | SKILL.md |
| `delivery-manager` | 交付管理 | SKILL.md |
| `release-engineer` | 发布部署 | SKILL.md |

---

## 4. 工具层：MCP 系统

### 4.1 服务器架构

`tools/server.py` 是 MCP JSON-RPC 2.0 over stdio 服务器：

```
ZCode AI agent
  │ tools/call { "name": "quality_gates_run", "arguments": {...} }
  ▼
server.py (main loop)
  │ handle_request()
  │   ├─ tools/list → 返回 7 工具 schema
  │   └─ tools/call  → _dispatch()
  ▼
tool_*.py (各自独立实现)
  │ 返回 dict
  ▼
server.py
  │ {"result": {"content": [{"type": "text", "text": "<json>"}]}}
  ▼
ZCode AI agent
```

### 4.2 工具接口契约

| 工具 | 输入 | 输出 |
|------|------|------|
| `quality_gates_run` | project_root, output_dir? | `{overall, lint, typecheck, test, coverage, audit, build}` |
| `security_scan_run` | project_root, output_dir? | `{overall, cve_count, secret_leaks, injection_surfaces}` |
| `dependency_analysis` | project_root, rules_file? | `{graph, cycles[], boundary_violations[]}` |
| `contract_validate` | project_root, contract_file, check_actual? | `{valid, errors[], warnings[]}` |
| `evidence_verify` | project_root, strict? | `{overall, nodes[{name, status, stale_reason?}]}` |
| `evidence_freeze` | project_root, file | `{frozen, sha256, path}` |
| `cost_report` | project_root | `{total_tokens, by_role{}, by_phase{}}` |

### 4.3 工具实现策略

- 每个工具独立 `.py` 文件 (`tools/tool_*.py`)
- 通过 `server.py` 的 `_dispatch()` 统一分发
- 共享 `hook_common.py` 的项目检测能力
- 当前为**薄包装**层——部分工具（如 `quality_gates_run`）通过 subprocess 调用外部脚本

---

## 5. 命令层：斜杠命令

三个自定义斜杠命令，用户可直接输入调用：

| 命令 | 功能 | 实现 |
|------|------|------|
| `/loop-validate` | 运行状态校验 | 调用 `validate_state.py` |
| `/loop-verify-chain` | 验证证据链完整性 | 调用 `evidence_chain.py` |
| `/loop-cost` | 生成 token 成本报告 | 聚合 session 统计 |

每个命令文件（`commands/*.md`）包含：
- `description`：命令描述
- `argument-hint`：参数提示
- `allowed-tools`：命令可用的工具白名单
- 执行逻辑（Markdown 指令）

---

## 6. 数据架构

### 6.1 治理数据模型

```
.ai/
├── state.yaml            # 当前阶段/任务/gate
├── gates.yaml            # 所有 gate 的注册表和状态
├── task_graph.yaml       # 任务 DAG（节点+边）
├── HANDOFF.md            # 跨会话交接
├── PROGRESS.md           # 进度日志
├── PROJECT.md            # 项目一句话定义
├── DECISIONS.md          # 架构决策记录
├── CONTRACTS.md          # 治理契约
├── ACCEPTANCE.md         # 验收标准
├── CODING_STANDARDS.md   # 编码规范
├── CONVENTIONS.md        # 约定
├── ARCHITECTURE.md       # 架构文档
├── KNOWN_ISSUES.md       # 已知问题
├── NON_GOALS.md          # 非目标
├── project_continuity.yaml  # 项目连续性（审计快照）
├── tasks/                # 任务文件 T-XXXX.md
├── evidence/             # 证据目录 <task-id>/commands.md
├── checkers/             # 校验器
├── guards/               # 策略守卫
├── handoffs/             # 交接记录
├── policies/             # 策略定义
├── reviews/              # 评审记录
├── schemas/              # JSON Schema
└── tests/                # 治理测试
```

### 6.2 运行时数据模型

```
.zcode/                        # 目标项目中的安装目录
├── config.json                # ZCode hook 注册（hooks.enabled + events）
├── skills/
│   └── loop-governance/
│       ├── config.yaml        # 行为配置（从插件复制）
│       └── chain.yaml         # 证据链定义（从插件复制）
└── tools/
    ├── validate_state.py      # 状态校验
    ├── audit_handoff.py       # 交接审计
    ├── close_session.py       # 会话关闭
    ├── governor_lib.py        # 治理核心库
    ├── continuity_auditor.py   # 连续性审计
    ├── continuity_producer.py  # 连续性生成
    └── ...                    # 其他治理脚本
```

---

## 7. 数据流

### 7.1 会话启动流

```
ZCode 启动会话
  │
  ├─ SessionStart 事件触发
  │
  ├─ session_brief.py 执行
  │   ├─ 读取 .ai/state.yaml
  │   ├─ 读取 .ai/gates.yaml (提取 pending gates)
  │   ├─ 读取 .ai/HANDOFF.md (提取 Next Session First Step)
  │   └─ 输出 JSON → additionalContext
  │
  ├─ ZCode 将 additionalContext 注入系统提示
  │
  └─ AI 模型看到 [loop-governance] 治理状态摘要
```

### 7.2 写入拦截流

```
AI 调用 Write/Edit 工具
  │
  ├─ PreToolUse 事件触发
  │
  ├─ gate_guard.py 执行
  │   ├─ 非治理项目? → exit 0（放行，快速路径）
  │   ├─ 写入 .ai/gates.yaml? → exit 0（决策记录豁免）
  │   ├─ 存在 pending gate? → exit 2（阻断）
  │   └─ 无 pending gate → exit 0（放行）
  │
  ├─ path_guard.py 执行
  │   ├─ 非治理项目? → exit 0（快速路径）
  │   ├─ 目标不在保护区? → exit 0（放行）
  │   ├─ deny 模式? → exit 2（阻断）
  │   └─ ask 模式 → JSON permissionDecision: ask
  │
  └─ ZCode 综合所有 hook 结果：
      ├─ 任一 exit 2 → 阻止工具调用
      ├─ ask → 弹出用户确认框
      └─ 全部 exit 0 → 执行工具调用
```

### 7.3 治理工作流

```
用户请求 "创建 T-XXXX"
  │
  ├─ loop-governance skill 加载
  │   ├─ 执行启动检查清单
  │   ├─ 运行 validate_state.py
  │   ├─ 发现 pending gate → 停止并向用户展示
  │   └─ 无 pending gate → 继续
  │
  ├─ AI 创建任务文件 .ai/tasks/T-XXXX.md
  ├─ AI 注册 gate 到 .ai/gates.yaml (gate_guard 豁免此路径)
  ├─ AI 更新 state.yaml / task_graph.yaml / HANDOFF.md
  │
  ├─ validate_state.py 显示 pending gate →
  │   gate_guard hook 阻断后续写入
  │
  ├─ 用户明确批准 gate →
  │   AI 更新 gates.yaml (豁免路径)
  │
  ├─ gate_guard 不再阻断 →
  │   AI 执行任务
  │
  └─ 任务完成 → AI 更新 state / task_graph / handoff
```

---

## 8. 部署架构

### 8.1 插件分发

```
loop-engine/                    # 插件源码仓库
├── .zcode-plugin/plugin.json   # ZCode 发现入口
│
├─ ZCode 注册方式：
│   1. Plugin Management → Discover → + → 选择目录
│   2. plugin-workspace/ 联结（开发模式）
│
└─ ZCode 加载：
    ├── skills/  → AI 可调用的技能
    ├── hooks/   → 事件拦截器
    ├── commands/ → 斜杠命令
    └── tools/   → MCP 服务器（独立进程）
```

### 8.2 目标项目安装

```
源（loop-engine 插件）           目标项目

skills/loop-governance/    →    .zcode/skills/loop-governance/
  config.yaml                         config.yaml
  chain.yaml                          chain.yaml

archive/lab-candidates/    →    .zcode/tools/
  scripts/*.py                       validate_state.py
                                     audit_handoff.py
                                     governor_lib.py
                                     ...

(模板生成)                  →    .ai/
                                     state.yaml
                                     gates.yaml
                                     task_graph.yaml
                                     HANDOFF.md
                                     PROJECT.md
```

安装命令：`python scripts/install.py --project-root <目标>`

### 8.3 运行时依赖

```
Python 3.10+
  ├── PyYAML >= 6.0（可选，缺失时退化为正则行扫描）
  └── 标准库（json, pathlib, subprocess, hashlib, re, sys）

ZCode
  ├── hook 协议（hooks.enabled + events schema）
  ├── MCP 协议（JSON-RPC 2.0 over stdio）
  └── skill 系统（SKILL.md 自动发现）
```

---

## 9. 技术选型决策

| 决策 | 选择 | 理由 |
|------|------|------|
| **Hook 执行方式** | `type: process` + args 数组 | 无 shell 拼接，Windows 下可靠 |
| **阻断方式** | exit 2（非 JSON deny） | 退出码最稳定，不受 JSON schema 严格校验影响 |
| **路径保护默认** | ask（非 deny） | 用户即信任锚，当场点击确认；deny 保留给高敏期 |
| **状态失败策略** | gate_guard fail-closed，其他 fail-open | 安全姿态 vs 可用性平衡 |
| **YAML 解析退化** | PyYAML → 正则行扫描 | 依赖缺失时保守降级，不瘫痪 hook |
| **配置注入方式** | 每个 hook 每次执行读取 config.yaml | 配置变更即时生效，无需重启 ZCode |
| **`__pycache__` 防止** | `sys.dont_write_bytecode = True` | 防止 hook 高频运行污染工作区（T-0032 事故） |
| **非治理项目** | 检测 `.ai/state.yaml` 不存在即跳过 | 零影响原则 |

---

## 10. 错误处理策略

| 场景 | 策略 | Hook 行为 |
|------|------|-----------|
| `.ai/state.yaml` 缺失 | 非治理项目，跳过 | exit 0（静默） |
| `config.yaml` 缺失 | 退化为 DEFAULT_CONFIG | 按默认值运行 |
| PyYAML 未安装 | 正则行扫描退化 | fail-closed（保守） |
| `gates.yaml` 损坏 | 按 fail_on_state_error | closed → exit 2；open → exit 0 + warn |
| hook 内部异常 | fail-open（gate_guard 除外） | exit 0 + stderr 警告 |
| MCP 工具异常 | 返回 JSON error | `{"error": "..."}` |
| validate_state.py 失败 | 区分 warning 和 error | warning 不阻塞，error exit 2 |

---

## 11. 演进路线

| 阶段 | 内容 | 状态 |
|------|------|------|
| **S0-init** | 项目合并、结构梳理 | ✅ 完成 |
| **S1-requirements** | 需求规格 | ✅ 完成 (T-0022) |
| **S2-architecture** | 架构设计（本文档） | 🔄 进行中 (T-0023) |
| **S3-interface** | 接口契约精确定义 | 待开始 |
| **S4-implementation** | 核心代码实现 | 待开始 |
| **S5-quality** | 测试套件 + 质量门禁 | 待开始 |
| **S6-delivery** | 打包、文档、发布 | 待开始 |
