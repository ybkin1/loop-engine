# T-0042 Completion Evidence

## 交付日期

2026-07-23 (代码实现) / 2026-07-24 (证据记录)

## 实际交付内容

T-0042 的代码实现在 v3.1.0 中已完成，本次（T-0048）补充正式证据记录。

### 1. 变更迭代支持

| 功能 | 位置 | 状态 |
|------|------|------|
| `REENTRY_TRANSITIONS` (5 change types) | `loop_core/state_machine.py:70-76` | ✅ |
| `ProjectStatus` (draft/released/maintenance) | `loop_core/state_machine.py:29-33` | ✅ |
| `validate_reentry()` | `loop_core/state_machine.py:162-210` | ✅ |

### 2. Hook 拆分

| 模块 | 状态 |
|------|------|
| `_hook_bash.py` (155行) — Bash tokenizer + command detection | ✅ T-0042 完成 |
| `_hook_state.py` (130行) — 状态读取 | ✅ T-0048 补齐 |
| `_hook_path.py` (120行) — 路径处理 | ✅ T-0048 补齐 |
| `_hook_config.py` (90行) — 配置加载 | ✅ T-0048 补齐 |
| `_hook_sync.py` (80行) — 缓存同步 | ✅ T-0048 补齐 |

### 3. Bash 增强

- Shell tokenizer: quote/escape-aware command extraction
- 新增检测: curl, wget, tar, pip, npm, rsync, scp, openssl

### 4. Deep QA 探针

- 75 个新探针测试覆盖 enforcement 边缘情况
- 5 个问题发现并修复

### 5. 缺陷修复（5项）

1. Shell tokenizer `\binstall\b` 误判 — 修改正则模式
2. 嵌套引号中的 tokenizer 分割 — 增加 quote 栈跟踪
3. 中文关键词匹配中的 change_type 检测漏洞 — 扩展关键词表
4. Shell 命令否定检测 — 增加 `!` / `not` 前缀处理
5. 角色能力状态在 profile 重载后丢失 — 修复持久化逻辑

## 验证

```
loop_core/state_machine.py:
  REENTRY_TRANSITIONS = {'bug_fix', 'feature_add', 'refactor', 'requirement_change', 'quality_fix'}
  ProjectStatus = {DRAFT, RELEASED, MAINTENANCE}
  validate_reentry() — functional, tested

hooks/scripts/_hook_bash.py: 155 lines, 7 detection functions
hooks/scripts/hook_common.py: ~689 lines (down from 998, plus re-exports)
```

## 备注

任务标题中的"3缺陷修复"为简化描述；实际修复了 5 个问题（详见 CHANGELOG.md v3.1.0）。
