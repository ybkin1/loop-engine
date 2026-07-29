---
description: 运行 Loop 工程状态校验——检查 state.yaml、gates.yaml、任务一致性
argument-hint: "[--run-checks]"
allowed-tools: [Bash, Read]
---

运行 Loop 工程治理状态校验。

## 用法

```
/loop-validate           # 基础校验（state、gates、任务一致性）
/loop-validate --run-checks  # 同时运行 gate register checker
```

## 执行

调用 `codex_loop/governance/validate_state.py`（使用 `python` 执行）：
- exit 0 → 状态可用
- exit 2 → 存在 pending gate 或其他阻塞

输出格式：
```
[loop-governance] project_root: <路径>
[loop-governance] phase: <current_phase>
[loop-governance] current_task_id: <任务ID>
[ok] state is usable
```
