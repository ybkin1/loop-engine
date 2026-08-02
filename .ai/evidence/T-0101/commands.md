# T-0101 — 关键命令与输出摘要

任务：idle 稳态语义修复（NO_ACTIVE_TASK exit code 分流 + 消费端对齐）。
修复前后对照使用临时 worktree（`git worktree add` 于 T-0100 提交 ecac6a3，idle 态），
完成后已移除。

## 修复前（idle 稳态，旧工具，worktree 清洁后）

```text
$ python .zcode/tools/validate_state.py .
[loop-governance] project_root: ...\loop-engine-idle-wt
[loop-governance] phase: S6-delivery
[loop-governance] current_task_id: none
[error] NO_ACTIVE_TASK: state.current_task_id is null
$ echo $?    → 2        （与真实治理损坏共用 exit 2）
$ python .zcode/tools/audit_handoff.py .
[error] NO_ACTIVE_TASK: state.current_task_id is null
$ echo $?    → 2
```

## 修复后（idle 稳态，新工具，同一 worktree）

```text
$ python .zcode/tools/validate_state.py .
[loop-governance] project_root: ...\loop-engine-idle-wt
[loop-governance] phase: S6-delivery
[loop-governance] current_task_id: none
[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：state 无活动任务，等待任务发起；state 不可开工）
$ echo $?    → 3        （独立 exit code，无 [ok] state is usable，无 [error]）
$ python .zcode/tools/audit_handoff.py .
[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：等待任务发起；handoff 审计不含 usable 语义）
$ echo $?    → 3
```

## idle 稳态 release check（同一 worktree，修复后）→ 6/6 PASS

```text
$ python scripts/release.py check
[release] check 质量门前置（root=...\loop-engine-idle-wt，version=3.12.39）
[release]   [PASS] version_sync: pyproject=3.12.39 == git HEAD=3.12.39
[release]   [PASS] validate_state: validate_state.py 通过（rc=3：idle 合法阻塞态，
           current_task_id=null，无活动任务，等待任务发起；非治理损坏）: ... [info] NO_ACTIVE_TASK ...
[release]   [PASS] compile: compileall 通过（loop_core, src, scripts, hooks, tools）
[release]   [PASS] guard_health: guard 健康 PASS（5 个 guard 全部存活）
[release]   [PASS] slo_gate: SLO 门禁通过: error budget within limits — release allowed
[release]   [PASS] key_tests: 关键测试子集通过（test_version_consistency + test_loop_core）
[release] check 通过（质量门前置全部 PASS）   → exit 0
```

## 损坏态（fail-closed 保持，fixture 实测）

```text
$ python .zcode/tools/validate_state.py <root with semantic_sha256 篡改>
[error] ProjectContinuity invalid: Continuity semantic hash mismatch
[error] PROJECT_CONTINUITY_HASH_MISMATCH: Continuity semantic hash mismatch
$ echo $?    → 2        （真实损坏仍 exit 2，不被 idle 分流吞掉）
```

主树实测（AC-02 真实发生）：修改 `.ai/HANDOFF-NEXT.md`（文档同步）后，
主树 `validate_state` 如实拦截：`[error] ... Continuity source drift: .ai/HANDOFF-NEXT.md` → exit 2。
恢复路径已在 worktree 实证：`repair_continuity.py`（就地重算 manifest 哈希）+
`close_session.py`（重生成 HANDOFF.md 内嵌哈希）→ 回到干净 idle rc=3。

## 测试

```text
$ python -m pytest tests/test_idle_semantics.py tests/test_governance_consistency.py -q
22 passed          （主树激活态 + 合成 idle fixture）
$ python -m pytest tests/test_governance_consistency.py tests/test_idle_semantics.py -q   （idle worktree）
22 passed          （repo idle 场景 + idle fixture 场景）
$ python -m pytest tests/test_release.py -q
25 passed, 1 skipped, 1 failed   （唯一失败 = version==HEAD 瞬时项）
$ python -m pytest tests/test_release_bump.py -q
11 passed          （bump 连带维护：硬编码版本 3.12.39 → 3.12.40）
$ python -m pytest tests/test_version_consistency.py -q
7 passed           （bump 后 8 载体一致）
$ python -m pytest tests/ -q
3760 passed, 3 failed, 64 skipped, 12 xfailed
  失败明细（均已核实，非本次改动引入）：
  1. test_release.py::test_pyproject_version_matches_git_head —— F-03 "先 bump 再提交"
     约定瞬时项：pyproject=3.12.40 vs HEAD=3.12.39，提交 subject v3.12.40 后自愈；
  2. test_release_bump.py::test_bump_invalid_version_is_usage_error —— 测试硬编码
     版本 3.12.39 被本次 bump 失效，已更新为 3.12.40（复跑 11 passed，修复后不再失败）；
  3. test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real ——
     T-0101 激活态先验失败：HANDOFF 引用 .ai/evidence/T-0101/evidence-manifest.v1.yaml
     尚未生成（任务完成流程创建后自愈）；提交的 idle 态同样存在悬挂引用
     （.ai/evidence/none/...，旧渲染器产物），与本次改动无关。
```

## 版本 bump（F-03 机制）

```text
$ python scripts/release.py bump --to 3.12.40 --title "T-0101 ..."
[release] bump: 已更新 pyproject.toml / CHANGELOG.md / loop_core/__init__.py /
           src/loop_engine/__init__.py / README.md / docs/06-delivery.md /
           .zcode-plugin/plugin.json / .ai/version-manifest.yaml -> 3.12.40
```

## compile gate

```text
$ python .ai/checkers/compile_gate.py . --output .ai/evidence/T-0101/compile-evidence.json
→ pass（见 compile-evidence.json）
```
