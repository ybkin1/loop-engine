# T-0083 Fail-Closed Implementation Report (AC-06 / AC-07)

- Task: T-0083
- Gate: G-T-0083-REQUIREMENTS
- Role: security-engineer
- Session: zcode-sess-2c3d4e5f60718293
- Timestamp: 2026-07-31T19:10:00+08:00
- Scope: hooks/scripts/, agents/quality-engineer/scripts/, tests/, .ai/evidence/T-0083/

## Fix 1 — HardConstraints 异常 fail-open → fail-closed (AC-06)

- File: `hooks/scripts/loop_enforcement.py`, HardConstraints `except` block, now lines 1131-1138.
- Before: 任何 `_HardConstraints()` 异常 → 记录 warning 后回退到 legacy 逻辑（fail-open，不 return）。
  约束内核损坏时写入被静默放行 —— T-0082 的 governance-theater 失败点。
- After: `except Exception as exc:` → `should_fail_closed(root)`（读取 config
  `hooks.fail_closed_on_error`，默认 true）→ `return EXIT_BLOCK`（BLOCKED:
  HardConstraints 执行异常（fail-closed））。仅当显式配置
  `fail_closed_on_error: false`（DEBUG ONLY）时才 fail-open 放行。
  `should_fail_closed` 已从 hook_common 导入（原 import 在文件头，无需新增）。
- Verified (in-process smoke, BoomConstraints kernel raising RuntimeError):
  - fail_closed 默认 → EXIT 2（stderr 含 "BLOCKED: HardConstraints 执行异常（fail-closed）"）
  - fail_closed_on_error: false + legacy fixture + 合法任务 → EXIT 0（回退逻辑正常裁决）

## Fix 2 — diff-scope git 不可用 fail-open → NOT_VERIFIED 阻断 (AC-06)

- File: `hooks/scripts/loop_enforcement.py`, `check_diff_scope`, lines 216-287; call site lines 1205-1212.
- Before: 非 git 仓库 / git 不可用 / git 出错 → `(True, ...)` 放行（fail-open）。
- After（区分三种情形）:
  - 任务未声明 allowed_paths → 跳过（无可验证范围）。
  - 无 `.git` 目录 → 跳过（非 git 项目，无 diff 范围概念）。
  - git 可执行文件缺失（FileNotFoundError）/ 超时 → `(False, "变更范围无法验证
    （git 不可用）— NOT_VERIFIED")`。
  - `git diff` rc≠0（git 命令出错）→ `(False, "变更范围无法验证（git diff 失败）— NOT_VERIFIED")`。
  - 调用点 `if not diff_ok → EXIT_BLOCK`，因此配置了 allowed_paths 的 git 项目在
    git 无法验证时写入被阻断。
- Verified (smoke): 非 git skip → True；git 缺失 → False NOT_VERIFIED；rc=128 →
  False NOT_VERIFIED；clean → True。

## Fix 3 — content_guard ruff 缺失 fail-open → fail-closed (AC-06)

- File: `hooks/scripts/content_guard.py`, `_run_ruff_check`, lines 64-101.
- Before: `FileNotFoundError`/超时 → `return True, []`（放行）；rc≠0 + 空 stdout
  （如 "No module named ruff"）→ `return True, []`（放行）—— lint 门禁形同虚设。
- After:
  - `FileNotFoundError` → `(False, ["ruff 不可用：语法/质量检查无法执行（fail-closed）"])`
  - 超时 → `(False, ["ruff 检查超时：...（fail-closed）"])`
  - rc≠0 + 无输出（模块缺失/工具故障）→ `(False, ["ruff 检查执行失败（rc=..，无输出）：...（fail-closed）"])`
  - 其他执行异常 → `(False, [...（fail-closed）])`
  - 仅 rc==0 才 PASS；rc≠0 且有输出 → 原有违规明细（False + violations）。
- Verified (smoke): 伪造 sys.executable 缺失 → `(False, ['ruff 不可用：语法/质量检查无法执行（fail-closed）'])`。
- 注：本环境 ruff 0.15.14 已安装，真实路径下 lint 正常执行（见测试结果）。

## Fix 4 — S7-S11 证据判定显式 fail-closed (AC-06)

- File: `hooks/scripts/loop_enforcement.py`, `_check_phase_evidence_file`, lines 657-738.
- Before: 任一候选 overall=="PASS" 即整体通过；非 PASS 候选的失败消息模糊
  （"需要 PASS"），且文档声称"fail-open 于多候选场景"。
- After: 保持"任一候选通过即整体通过"，但已存在候选的任何非 PASS 判定
  （FAIL/BLOCKED/NOT_VERIFIED/NOT_RUN/SKIPPED 等）显式记为 gate failure
  （"overall=X 非 PASS（fail-closed）"）；全部候选缺失/无效/非 PASS → 阻断。
  docstring 同步更新。
- Verified (smoke): overall=NOT_VERIFIED → False 阻断；overall=PASS → True。
- 既有测试 test_s7_blocks_without_evidence / test_s7_allows_with_evidence /
  test_s11_blocks_without_evidence 全部通过。

## Fix 5 — NOGO 决策校验（修复 NOGO-passes-as-GO bug）(AC-06)

- File: `hooks/scripts/loop_enforcement.py`, `check_delivery_gate_evidence`, lines 500-593.
- Before: `release_decision.json` 中任意 truthy `decision` 即放行 —— NOGO、
  空值、非法值全部当作 GO 通过。
- After: decision 归一化为大写后精确校验：
  - `GO` → True
  - `CONDITIONAL_GO` / `CONDITIONAL-GO` → 要求 `owners` + `deadline` 均非空，
    否则 False（发布阻断）
  - `NOGO` → False（"交付经理决策：NOGO — 发布阻断"）
  - 其他/缺失 → False（"决策值非法或缺失: ..."）
  - 最新版本目录的决策文件即最终裁决（不再回退旧版本）；JSON 解析失败才跳过该版本。
  - certifications/state.yaml 兜底保留，但 delivery-manager state 归一化后必须
    恰好为 CERTIFIED 才放行（lines 563-573）。
- Verified (smoke): GO→True；NOGO→False；MAYBE→False；空→False；
  CONDITIONAL_GO 缺 owners/deadline→False；带 owners+deadline→True。

## Fix 6 — 工具链完整性门禁 (AC-07)

- File: `agents/quality-engineer/scripts/run_quality_gates.py`,
  `run_one_check` (lines 262-311), `collect_results` (lines 314-404),
  `generate_report` (lines 412-449).
- Before: 工具缺失 → `except Exception` 捕获为 FAIL（或 FileNotFoundError），
  stdout 为空 → `parse_lint_output` 解析成 0 错误 → **lint 检查 PASS**；
  `parse_test_output` 解析成 0/0 → **test 检查 PASS**。配置了但缺失的工具
  反而"通过"质量门（fail-open）。
- After: 工具缺失/无法执行 → status=BLOCKED + reason="tool missing
  (fail-closed)"（FileNotFoundError、"No module named"、"not recognized as
  an internal or external command"、"command not found"）；超时 →
  "check timeout (fail-closed)"；其他执行错误 → fail-closed。
  `collect_results` 对这些项不再做空输出→0 错误的阈值比较，直接标记 BLOCKED；
  `generate_report` 保留该 BLOCKED 状态（不做阈值比较），整体 overall=BLOCKED。
  未配置的命令（不在 config）不产生检查项（等同 NOT_VERIFIED，合法不阻断）。
- Verified (smoke, temp project config 指向不存在的工具):
  lint/typecheck/test 全部 BLOCKED "tool missing (fail-closed)"，
  overall=BLOCKED，quality_report.json 中状态正确；build/compile 未配置 → 报告缺省。

## Verification Results (real numbers)

- 目标套件（mission 指定）:
  `pytest tests/test_enforcement.py tests/test_runtime_delivery_gate.py tests/test_quality_gates.py tests/test_check_thresholds.py tests/test_content_guard_semantic.py -q --tb=short`
  → **89 passed, 0 failed** (23.83s)
- 扩展套件（+ tests/test_hook_guards.py，同走 content_guard）:
  → **100 passed, 0 failed** (21.24s)
- 顺带回归 tests/test_bash_readonly.py tests/test_cross_layer_safety.py
  tests/test_hook_integration.py: 149 passed, 3 failed —
  **3 个失败为基线已存在**（`git stash` 后在改动前代码上运行完全相同的 3 个
  test_bash_readonly 用例同样失败：test_git_log_passes_in_full_mode /
  test_git_status_passes_in_full_mode / test_readonly_bash_allowed_with_active_task，
  期望 rc=2 实际 rc=0），与本任务改动无关，未在任务范围内（该文件不在
  mission 指定测试集中，且按规则不应为无关基线失败改动测试）。

## Honest Remaining Fail-Open Paths (已知遗留)

1. `loop_enforcement.py` main() 顶层 `except Exception:` 仍依赖
   `should_fail_closed(root)`（默认 fail-closed，但 config
   `hooks.fail_closed_on_error: false` 可全局关闭）—— 保留为显式调试逃生门。
2. `_run_ruff_check` 之外的 content_guard 检查（secrets/injection/
   architecture/semantic）在异常时部分仍记录 warning 不阻断：
   - `_check_architecture_compliance` 读文档失败 → 放行；
   - 语义规则加载/执行异常 → `logger.debug` 非阻断（lines 299-300 区域）。
3. `check_quality_gate_evidence`（S5 质量证据）对旧格式报告（无
   execution_evidence）仅降级警告不阻断（向后兼容）；execution ledger 溯源
   校验仅 trace 不阻断。
4. `run_quality_gates.py`：未配置的检查项不出现在报告中（等同 NOT_VERIFIED，
   合法）；`parse_lint_output` 对"非 JSON 非空行"输出仍按行数计数——工具
   输出格式完全未知时可能低估错误数（保守方向未知，属解析器限制）。
5. `check_security_gate_evidence`：md 兜底路径只检查 "BLOCKED" 字样，其他
   否定判定（FAIL/NOGO/NOT_VERIFIED）不会阻断 md 报告。
6. test_bash_readonly 的 3 个基线失败（git status/log 在 active task + 无
   runtime projection 时放行）—— 由 git 本地操作豁免逻辑（`_git_commit_exempt`
   + `_GIT_ALL_LOCAL`）导致，属 T-0082 既有设计，不在本任务修复范围。
7. `check_diff_scope` 的 git 可用但 HEAD 不存在（初始提交、无 commit）场景
   现按 NOT_VERIFIED 阻断 —— 新仓库第一次提交前会被 diff 门阻断；这是
   fail-closed 的预期代价，需在 onboarding 流程中先完成首次提交。
