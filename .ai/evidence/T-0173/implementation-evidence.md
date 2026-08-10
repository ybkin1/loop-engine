# T-0173 实现证据 — 任务依赖图检查（validate_state）

## 实现

`.zcode/tools/validate_state.py` 新增 `check_task_dependencies(root, base)`：
- 依赖未满足（depends_on 指向非终态任务）→ `[warn]`（advisory，用户是唯一批准者）
- 依赖环（DFS）→ `[error]`（fail-closed）
- 未登记依赖 → `[warn]`（防幻影依赖）
- main() 3.5 步接入（在 pending gate 检查与 governance invariants 之间）

## 四场景单测（2026-08-10，全部通过）

1. 依赖未满足（T-002 pending）→ `[warn] 依赖未满足`，无 error
2. 依赖环（T-001→T-002→T-001）→ `[error] 依赖环: T-001 → T-002 → T-001`
3. 依赖已终态（T-002 completed）→ 无 warn
4. 未知依赖（T-999）→ `[warn] 依赖未登记`

## 真实项目验证（2026-08-10）

`validate_state.py .` 检出此前从未被提示的真实问题：
`[warn] task T-0154 依赖未满足: T-0153 — 等待其终态（completed/rejected）后再执行`

最终状态：`[ok] state is usable`（T-0154 依赖 warn 为预期功能输出）。

## mypy / 门禁

- validate_state.py 自身 mypy 0 错误（release.py mypy_gate 新增 5 错误均在
  并行会话未提交文件 execution_relay/output_quality(untracked)/pi_evidence_import，
  非本次引入）
- release.py check：validate_state/compile/guard_health/slo/key_tests/mutation 全 PASS
