# 设计：Runtime Controller（统一授权入口）

版本：v0.1 | 状态：candidate | 日期：2026-07-23

## 1. 问题

当前敏感操作入口分散，无统一授权：

| 操作 | 当前方式 | 问题 |
|------|---------|------|
| Write/Edit | gate_guard hook | 仅检查 pending gate |
| Bash | loop_enforcement hook | 检查任务范围 |
| MCP tools/call | 无 | 完全未拦截 |
| CLI command | 无 | 完全未拦截 |
| executor role launch | executor 内部 | fixture_mode 检查 |
| evidence/state/gate 写入 | 无 | 无授权 |
| install/upgrade/rollback | 无 | 完全未拦截 |

## 2. 设计

### 2.1 核心数据类型

```python
class Action(str, Enum):
    WRITE_FILE = "write_file"
    APPLY_PATCH = "apply_patch"
    EXEC_BASH = "exec_bash"
    MCP_TOOL_CALL = "mcp_tool_call"
    CLI_COMMAND = "cli_command"
    LAUNCH_ROLE = "launch_role"
    SUBMIT_EVIDENCE = "submit_evidence"
    STATE_TRANSITION = "state_transition"
    GATE_TRANSITION = "gate_transition"
    INSTALL = "install"
    UPGRADE = "upgrade"
    ROLLBACK = "rollback"

class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"

@dataclass
class AuthContext:
    action: Action
    target_path: str | None
    actor_id: str | None
    session_id: str | None
    task_id: str | None
    role_id: str | None

@dataclass
class AuthResult:
    decision: Decision
    reason: str
    required_gate_id: str | None
```

### 2.2 决策链（优先级从高到低）

```
1. 高风险操作（install/deploy/rollback）→ 无对应 gate → DENY
2. 保护区路径（AGENTS.md 等）→ ASK_USER
3. 治理文件（.ai/）→ 有 pending gate 时检查 allowed_paths → ALLOW/DENY
4. 任务范围 → 匹配 allowed_paths → ALLOW
5. 默认 → DENY（fail-closed）
```

### 2.3 关键改进：pending gate 期间按 allowed_paths 放行

旧行为（gate_guard bug）：看到 pending gate → 阻断所有写入。

新行为：pending gate 期间，写入目标在 allowed_paths 内 → ALLOW。

### 2.4 集成计划

| 阶段 | 文件 | 改动 |
|------|------|------|
| Phase 1 | loop_core/runtime_controller.py | 新增 |
| Phase 2 | hooks/scripts/gate_guard.py | 导入 Controller |
| Phase 3 | hooks/scripts/loop_enforcement.py | 导入 Controller |
| Phase 4 | loop_core/executor.py | execute_role 前授权 |
| Phase 5 | evidence/state 写入路径 | 统一授权 |

## 3. 测试策略

- 每种 Action × Decision 组合的单元测试
- Controller + gate_guard 联合集成测试
- 不破坏现有 132 条测试的回归验证
