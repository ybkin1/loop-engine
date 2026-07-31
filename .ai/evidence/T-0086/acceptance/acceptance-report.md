# T-0086 验收报告（acceptance-report）

> **T-0086: 治理清障 + StaffDeck 对标落地 + 任务计划编排 | 2026-08-01**
> Gate: G-T-0086-REQUIREMENTS（user 批准，approval_actor=user）
> 独立审查：CONDITIONAL_GO（1 项 P1 条件）→ P1 已修复并复验 → 转 GO

## AC 验收矩阵

| AC | 标准 | 结果 | 证据 |
|---|---|---|---|
| AC-01 | validate_state 通过，state/HANDOFF/task_graph/PROGRESS 四者一致 | ✅ PASS | `[ok] state is usable`；四文件一致（T-0086 active / S6-delivery / G-T-0086-REQUIREMENTS approved） |
| AC-02 | PROGRESS.md 已同步 | ✅ PASS | 头部同步 T-0086 ACTIVE + 存档说明；T-0020 旧内容标注历史 |
| AC-03 | 只读工具项目外放行；写入仍拦截 | ✅ PASS | tests/test_path_guard.py 119 项通过（含只读放行/写入拦截/回归）；真实 subprocess 验证矩阵 |
| AC-04 | staffdeck-benchmark.md 落盘 | ✅ PASS | .ai/evidence/T-0086/staffdeck-benchmark.md（D1-D10/U1-U9/领先项/映射/事实-推断分级） |
| AC-05 | task-plan.md 落盘 | ✅ PASS | .ai/evidence/T-0086/task-plan.md（T-0087~T-0090 编排） |
| AC-06 | 全量测试无回归 | ✅ PASS | 2821 passed / 63 skipped / 12 xfailed / 0 failed（基线 2791 → +30 = 新增测试） |
| AC-07 | 无约束被弱化 | ✅ PASS（含 P1 修复） | 独立审查发现 P1（sh/bash/./ 执行形态误判只读）→ 已修复（_hook_bash.py 重写 is_readonly_command + path_guard 执行形态拦截 + 26 新测试）；复验 470 passed；写入拦截实测仍 BLOCK |

## P1 缺陷修复记录（CONDITIONAL_GO 条件）

| 条件 | 修复 | 验证 |
|---|---|---|
| is_readonly_command 误判 sh/dash/bash <file>/./script/php -r/ruby -e 为只读 | _hook_bash.py：引号感知分段扫描重写；解释器执行形态判写能力；xargs/awk 执行形态检测；帮助标记整词匹配；hook_common re-export；path_guard 执行形态+外部引用 → BLOCK | tests/test_bash_readonly.py +24 单元；test_bypass_matrix 3 xfail 转正；test_path_guard +2 回归（sh/bash/./ → exit 2） |
| 补拦截回归测试 | tests/test_path_guard.py 新增 sh/bash/.//php/ruby 形态拦截断言 | 119 passed |
| 复跑全量测试 | pytest tests/ | 2821 passed / 0 failed |

## 交付物清单

1. `.ai/tasks/T-0086.md`（含 allowed_paths 契约字段）
2. `hooks/scripts/path_guard.py`（只读豁免 + 执行形态拦截）
3. `hooks/scripts/loop_enforcement.py`（EXTERNAL_READ 只读外部引用放行）
4. `hooks/scripts/_hook_bash.py`（is_readonly_command 安全重写）
5. `hooks/scripts/hook_common.py`（re-export）
6. `tests/test_path_guard.py`（新增，119 项含 P1 回归）
7. `tests/test_bash_readonly.py`（+24 单元测试）
8. `tests/test_bypass_matrix.py` / `tests/test_deep_qa_probe.py`（断言更新）
9. `.ai/evidence/T-0086/`：approval-evidence / execution-evidence / compile-evidence（42/42）/ commands / staffdeck-benchmark / task-plan / acceptance
10. `.ai/evidence/quality/runtime_quality_report.json`（overall=PASS，schema 严格校验）
11. `.ai/evidence/security/security_audit.json`（verdict=PASS，真实扫描+复核）
12. 治理同步：state.yaml / gates.yaml / task_graph.yaml（T-0086 登记 + T-0083/T-0001 状态清理）/ HANDOFF.md / PROGRESS.md / project_continuity.yaml

## 治理记录

- 任务登记：task_graph T-0086 + edge T-0085→T-0086；gates G-T-0086-REQUIREMENTS（pending→approved）；state current_task_id=T-0086
- 启动证据：approval/execution/compile/continuity/HANDOFF 全部就位，validate_state `[ok] state is usable`
- 派发记录：developer 子代理 2 次（实现 + P1 修复）、independent-reviewer 1 次（CONDITIONAL_GO）
- 全程零越界写入（git diff 范围审查：.ai/、hooks/、tests/ 内）
- 全程零约束弱化：写入拦截语义保持并加强（执行形态回归拦截）

## 最终裁决

**GO**（独立审查 CONDITIONAL_GO 的 P1 条件已修复并复验；AC-01~AC-07 全部 PASS）
> 裁决为验收证据，gate 最终批准权在用户。

## 已知遗留（超范围，记录）

- Bash 写入目标含 Windows 反斜杠路径时 shlex.split POSIX 模式路径损坏（既有行为，loop_enforcement DISPATCH 门兜底）
- 主会话 active task 下非治理读写需 runtime projection（既有设计）
- 只读豁免在 path_guard（无条件）与 loop_enforcement（需外部引用）口径不一致（P2，建议 T-0089 可观测性任务中统一）
