# 03 — 接口契约

> Loop Engine v1.0 接口契约 | 状态: draft | 对应架构: docs/02-architecture.md

---

## 1. 概述

本文档精确定义 Loop Engine 四层架构中所有模块间的接口契约。每个接口包含：
- **输入/输出 Schema**（JSON Schema 或字段定义表）
- **错误语义**（退出码、异常策略）
- **依赖约束**（前置条件、环境变量）

---

## 2. Hook 层接口

### 2.1 公共协议

所有 hook 脚本通过以下方式与 ZCode 交互：

**stdin**（ZCode → hook）：
```json
{
  "cwd": "<当前工作目录>",
  "tool_input": {
    "file_path": "<被操作的文件路径>",
    "path": "<备用路径字段>",
    "notebook_path": "<notebook 路径>"
  }
}
```

**环境变量**：
| 变量 | 说明 |
|------|------|
| `ZCODE_PROJECT_DIR` | 项目根目录 |
| `CLAUDE_PROJECT_DIR` | 兼容旧版项目根 |
| `ZCODE_PLUGIN_ROOT` | 插件根目录（hooks.json 中 `${ZCODE_PLUGIN_ROOT}`） |

**退出码**：
| 退出码 | 语义 |
|--------|------|
| 0 | 通过/放行 |
| 2 | 阻断（PreToolUse 的 deny） |
| 其他非 0 | hook 错误（非阻断） |

---

### 2.2 H-01: session_brief（SessionStart）

**触发事件**: `SessionStart`，matcher: `startup|resume`

**stdin**: 不使用（仅读取环境变量获取项目根）

**输出 Schema**（stdout JSON）：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<治理状态摘要文本>"
  }
}
```

**additionalContext 内容模板**：
```text
[loop-governance] 治理状态摘要（SessionStart hook 自动注入）
phase: <S0-init | S1-requirements | S2-architecture | ...>
current_task_id: <T-XXXX | none>
current_gate_id: <G-XXXX | none>
PENDING GATES（...）:          ← 仅当有 pending gate
  - G-XXXX
  - ...
HANDOFF next step:             ← 仅当 HANDOFF.md 存在该节
<next step 文本>
提醒：reviewer PASS / validator / 测试通过均为 evidence，不等于用户批准。
```

**异常策略**: fail-open。任何异常 → exit 0，stderr 输出警告，不阻断会话。

**前置条件**: `.ai/state.yaml` 不存在 → exit 0（非治理项目，静默跳过）。

---

### 2.3 H-02: gate_guard（PreToolUse）

**触发事件**: `PreToolUse`，matcher: `Write|Edit`

**stdin**: 使用 `tool_input.file_path`（或 `path`、`notebook_path`）

**输出**: 无 stdout JSON（仅通过退出码通信）

**阻断条件**（满足任一即阻断）：
1. `gates.yaml` 中存在 `status: pending` 的 gate
2. `state.yaml` 的 `current_gate_id` 为非空且未在 gates.yaml 中找到匹配的 pending gate

**豁免路径**: `.ai/gates.yaml`（精确匹配，`decision_recording_exempt` 配置项）

**异常策略**（fail_on_state_error）：
| 值 | 行为 |
|----|------|
| `closed`（默认） | 状态不可读 → exit 2，stderr 输出阻塞原因 |
| `open` | 状态不可读 → exit 0，stderr 输出警告 |

**前置条件**: `.ai/state.yaml` 不存在 → exit 0（非治理项目）。

---

### 2.4 H-03: path_guard（PreToolUse）

**触发事件**: `PreToolUse`，matcher: `Write|Edit`

**stdin**: 使用 `tool_input.file_path`

**保护区列表**（`config.yaml` 可配）：
```
AGENTS.md          精确文件匹配
stable/            目录前缀匹配（含所有子文件）
registry/          目录前缀匹配
.zcode/config.json 精确文件匹配
.zcode/tools/      目录前缀匹配
```

**输出 Schema**（ask 模式，stdout JSON）：
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "[path_guard] 目标 <rel_path> 命中保护区规则 <rule>。该路径属于治理权威事实或执行层，写入需要你当场确认。"
  }
}
```

**deny 模式**: 无 JSON 输出，直接 exit 2 + stderr 消息。

**异常策略**: fail-open。内部异常 → exit 0 + stderr 警告。

---

## 3. MCP 工具层接口

### 3.1 公共协议

**传输**: JSON-RPC 2.0 over stdin/stdout

**服务器**: `tools/server.py`

**请求格式**：
```json
{"jsonrpc": "2.0", "id": <req_id>, "method": "tools/list | tools/call", "params": {...}}
```

**响应格式**：
```json
{"jsonrpc": "2.0", "id": <req_id>, "result": {"content": [{"type": "text", "text": "<json>"}]}}
```

**tools/list 返回**：
```json
{
  "tools": [
    {"name": "<tool_name>", "description": "...", "inputSchema": {...}},
    ...
  ]
}
```

---

### 3.2 T-01: quality_gates_run

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string", "description": "项目根目录路径"},
    "output_dir": {"type": "string", "description": "报告输出目录（默认 .ai/evidence/quality/）"}
  },
  "required": ["project_root"]
}
```

**output**:
```json
{
  "overall": "PASS | FAIL | BLOCKED | UNKNOWN | NOT_APPLICABLE",
  "lint": {"status": "...", "issues": 0},
  "typecheck": {"status": "...", "issues": 0},
  "test": {"status": "...", "passed": 0, "failed": 0},
  "coverage": {"status": "...", "percent": 0.0},
  "audit": {"status": "...", "high": 0, "critical": 0},
  "build": {"status": "...", "exit_code": 0}
}
```

---

### 3.3 T-02: security_scan_run

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"},
    "output_dir": {"type": "string"}
  },
  "required": ["project_root"]
}
```

**output**:
```json
{
  "overall": "PASS | FAIL | BLOCKED | UNKNOWN",
  "cve_count": {"high": 0, "critical": 0},
  "secret_leaks": 0,
  "injection_surfaces": [],
  "permission_issues": []
}
```

---

### 3.4 T-03: dependency_analysis

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"},
    "rules_file": {"type": "string", "description": "边界规则 JSON 文件路径"}
  },
  "required": ["project_root"]
}
```

**output**:
```json
{
  "overall": "PASS | BLOCKED",
  "graph": {"nodes": [], "edges": []},
  "cycles": [["mod_a", "mod_b", "mod_a"]],
  "boundary_violations": [{"from": "...", "to": "...", "rule": "..."}],
  "stderr": "..."
}
```

---

### 3.5 T-04: contract_validate

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"},
    "contract_file": {"type": "string", "description": "interface-contract.json 路径"},
    "check_actual": {"type": "boolean", "description": "是否对比代码实际导出"}
  },
  "required": ["project_root", "contract_file"]
}
```

**output**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

---

### 3.6 T-05: evidence_verify

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"},
    "strict": {"type": "boolean", "description": "严格模式：required 节点缺失即 BLOCKED"}
  },
  "required": ["project_root"]
}
```

**output**:
```json
{
  "overall": "PASS | BLOCKED",
  "nodes": [
    {"name": "requirements", "status": "PASS | HASH_MISMATCH | MISSING", "stale_reason": null}
  ],
  "issues": ["<问题描述>"]
}
```

---

### 3.7 T-06: evidence_freeze

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"},
    "file": {"type": "string", "description": "要冻结的文件路径（相对 project_root）"}
  },
  "required": ["project_root", "file"]
}
```

**output**:
```json
{
  "success": true,
  "message": "<冻结确认或错误信息>"
}
```

---

### 3.8 T-07: cost_report

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "project_root": {"type": "string"}
  },
  "required": ["project_root"]
}
```

**output**:
```json
{
  "summary": {"total_tokens": 0},
  "by_role": {"product-manager": 0, "developer": 0, "..."},
  "by_phase": {"S0-init": 0, "S1-requirements": 0, "..."},
  "rework_estimate": 0
}
```

---

## 4. Skill 层协议

### 4.1 SKILL.md 元数据契约

```yaml
---
name: loop-governance
description: >
  治理启动器——当项目级治理任务触发时加载。
when_to_use: >
  项目根存在 .ai/state.yaml 且请求非简单问答
  或用户明确要求"走 loop / 启动治理"。
---
```

### 4.2 启动检查清单（Skill 输出协议）

Skill 加载后 AI 必须按序执行：

```
1. 读取用户最新请求
2. 确认项目根（.ai/state.yaml 存在）
3. 读取 .ai/state.yaml + HANDOFF.md + 当前任务文件 + gates.yaml + task_graph.yaml
4. 运行 validate_state.py
5. 存在 pending gate → 停止，展示 gate 内容
6. 只在批准的任务和 gate 范围内继续
```

### 4.3 输出格式契约

启动检查后必须输出：
```text
[loop-governance] project_root: <路径>
[loop-governance] phase: <current_phase>
[loop-governance] current_task_id: <任务ID 或 none>
[loop-governance] current_gate_id: <gateID 或 none>
[ok] state is usable
```

被阻塞时输出：
```text
[error] Pending gate(s) require user decision: <gateID 列表>
```

### 4.4 config.yaml Schema

```yaml
version: 1

gate_guard:
  enabled: boolean
  fail_on_state_error: "closed" | "open"
  decision_recording_exempt: [string]   # 相对路径列表

path_guard:
  enabled: boolean
  decision: "ask" | "deny"
  protected_paths: [string]             # 文件或目录前缀（/ 结尾）

session_brief:
  enabled: boolean
  max_pending_listed: integer

quality_gates:
  project_type: "auto" | "python" | "javascript" | "default"
  lint_threshold: integer
  typecheck_threshold: integer
  test_threshold: integer
  coverage_threshold: integer
  audit_threshold: { HIGH: integer, CRITICAL: integer }
  build_threshold: integer
  templates: { <lang>: { lint_command, typecheck_command, ... } }

certification:
  enabled: boolean
  strict_mode: boolean
  revalidate_interval_days: integer
  max_consecutive_failures: integer
  grace_period_days: integer
  max_consecutive_challenge_attempts: integer
  cooling_period_days: integer
  record_retention: { max_records_per_role, archive_dir, overrides_dir }

degradation:
  rules:
    - id: string
      description: string
      condition: { type, ... }
      target_state: string
      automatic: boolean
      requires_human_approval: boolean
```

### 4.5 chain.yaml Schema

```yaml
chain:
  - name: string
    file: string
    upstream: [string]
    required: boolean
    type?: "directory"

verify:
  strict_mode: boolean
  max_stale_hours: integer
```

---

## 5. 命令层接口

### 5.1 命令元数据契约

```yaml
---
description: "<命令描述>"
argument-hint: "[可选参数]"
allowed-tools: [Bash, Read, ...]
---
```

### 5.2 `/loop-validate`

| 属性 | 值 |
|------|-----|
| 参数 | `[--run-checks]` |
| 工具 | Bash, Read |
| 调用 | `python .zcode/tools/validate_state.py` |
| 输出 | `[ok] state is usable` 或 `[error] ...` |

### 5.3 `/loop-verify-chain`

| 属性 | 值 |
|------|-----|
| 参数 | `[--phase NN] [--strict]` |
| 工具 | Bash, Read |
| 调用 | `python .zcode/tools/evidence_chain.py` |
| 输出 | `PASS` / `BLOCKED` + 问题列表 |

### 5.4 `/loop-cost`

| 属性 | 值 |
|------|-----|
| 参数 | `[--by-role] [--by-phase]` |
| 工具 | Bash, Read |
| 数据源 | `.ai/evidence/costs/cost_log.jsonl` |
| 输出 | 总 Token / 按角色 / 按阶段 / 返工估算 |

---

## 6. 治理数据 Schema

### 6.1 state.yaml

```yaml
schema_version: 1
project_name: string
current_phase: "S0-init" | "S1-requirements" | "S2-architecture" | "S3-interface" | "S4-implementation" | "S5-quality" | "S6-delivery"
current_task_id: string | null   # "T-XXXX"
current_gate_id: string | null   # "G-XXXX"
last_handoff_at: string          # ISO 8601
notes: [string]
```

### 6.2 gates.yaml

```yaml
schema_version: 1
gates:
  - id: string                   # "G-T-XXXX-..."
    task_id: string              # "T-XXXX"
    gate_type: string            # user-design | user-approval | user-installation | ...
    status: "pending" | "approved" | "rejected" | "blocked"
    decision: "pending" | "approved" | "rejected"
    requested_at: string         # ISO 8601（pending 时必填）
    requested_by: "ai" | "user"
    approval_required_from: "user"
    approval_actor?: "user"      # 批准后必填
    approval_source?: "explicit_user_message"
    approval_text?: string
    recorded_at?: string         # 批准后必填
    scope: string
    allowed_actions: [string]
    forbidden_actions: [string]
    notes: [string]
    # 可选字段（视 gate_type 而定）
    artifact_id?: string
    evidence?: string
    execution_status?: string
```

### 6.3 task_graph.yaml

```yaml
schema_version: 1
tasks:
  - id: string                   # "T-XXXX"
    title: string
    status: "pending" | "active" | "in_progress" | "completed" | "blocked" | "rejected"
    created_at: string           # ISO 8601
    updated_at?: string
    note?: string
edges:
  - from: string                 # "T-XXXX"
    to: string                   # "T-YYYY"
    type?: "depends_on" | "blocks"
```

### 6.4 HANDOFF.md

```markdown
# Handoff

## Current Phase
<S0-init | S1-requirements | ...>

## Current Task
<描述，含任务 ID>

## Current Status
<简述，含 validate_state.py 结果、pending gates>

## Next Session First Step
<下一步的具体步骤>
```

---

## 7. 安装/卸载接口

### 7.1 install.py

```
用法: python scripts/install.py --project-root <目标> [--project-name <名称>]

输入: 目标项目根目录（必须存在）
输出:
  创建 .ai/state.yaml, gates.yaml, task_graph.yaml, HANDOFF.md, PROJECT.md
  创建 .ai/tasks/, .ai/evidence/
  复制 config.yaml, chain.yaml → .zcode/skills/loop-governance/
  复制 validate_state.py, audit_handoff.py → .zcode/tools/
前置条件: Python 3.10+, PyYAML
幂等性: 已存在文件不覆盖
```

### 7.2 uninstall.py

```
用法: python scripts/uninstall.py --project-root <目标>

行为:
  备份 .ai/ → .ai.backup-<timestamp>/
  删除 .zcode/skills/loop-governance/
保留: .ai/tasks/, .ai/evidence/ 通过备份保留
```

---

## 8. 跨层依赖矩阵

| 调用方 ↓ / 被调用方 → | hook_common | config.yaml | state.yaml | gates.yaml | HANDOFF.md | MCP server |
|------------------------|-------------|-------------|------------|------------|------------|------------|
| session_brief.py | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| gate_guard.py | ✅ | ✅ | ✅ | ✅ | — | — |
| path_guard.py | ✅ | ✅ | — | — | — | — |
| loop-governance Skill | — | — | ✅ | ✅ | ✅ | — |
| validate_state.py | — | — | ✅ | ✅ | ✅ | — |
| MCP tools | ✅ | — | — | — | — | ✅(server) |
| Slash commands | — | — | — | — | — | — |

---

## 9. 版本兼容性

| 接口 | 版本 | 向后兼容策略 |
|------|------|-------------|
| Hook JSON schema | v1 | 仅增加可选字段，不删除已有字段 |
| MCP inputSchema | v1 | required 列表不增；新字段均为 optional |
| config.yaml | v1 | 新增键 + 默认值覆盖，旧路径保持不变 |
| state.yaml | v1 | 仅扩展 notes，不重命名字段 |
| gates.yaml | v1 | 新 gate_type 值可加，已有类型不变 |
