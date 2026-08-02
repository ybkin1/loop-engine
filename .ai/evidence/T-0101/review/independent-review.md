# T-0101 独立审查报告 — idle 稳态语义修复

- 审查人：independent-reviewer（独立子代理）
- 审查时间：2026-08-02
- 审查对象：T-0101（NO_ACTIVE_TASK exit code 分流 + 消费端对齐），developer 5 项修复
- 方法：全部结论亲自复验（git worktree 隔离 fixture + 源码走读 + 定向/全量测试），不复述 developer 证据

## 裁决：GO

无 P1/P2 条件。3 项 P3 观察（均为既有局限或提交后自愈项，不阻断）。

---

## 一、复验环境

- 主树（激活态 T-0101，current_task_id=T-0101，`validate_state.py .` → rc=0 `[ok] state is usable`）
- 临时 idle worktree：`git worktree add ../loop-wt-idle ecac6a3`（T-0100 提交，committed state 为 `current_task_id: null`，真 idle 态；验证完已 `git worktree remove`，主树零改动）
- 注意：committed ecac6a3 本身带 1 处连续性漂移（.ai/ACCEPTANCE.md，`--repair` 重算 283 个哈希后恢复干净 idle），说明 T-0100 提交时的 continuity manifest 已陈旧 —— 主会话完成流程需重生成（见 f-01 遗留），非本任务缺陷。

## 二、AC-01~AC-07 逐项

| AC | 结论 | 独立证据 |
|----|------|----------|
| AC-01 idle → exit 3 + [info] + 无 usable | **PASS** | idle worktree 实测：新 validate_state → `[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态…）` + **exit 3**，无 `[ok] state is usable`、无 `[error]`；audit_handoff 同 → exit 3。修复前对照（同 worktree 旧工具）：`[error] NO_ACTIVE_TASK…` + exit 2。tests/test_idle_semantics.py 5 passed（主树 + idle worktree） |
| AC-02 真实损坏仍 exit 2 | **PASS** | worktree 实测三场景：①篡改 .ai/HANDOFF-NEXT.md → `[error] Continuity source drift` + exit 2；②idle + 待决 gate（continuity 干净）→ `[error] Pending gate…` + `[error] NO_ACTIVE_TASK` 双行 + exit 2；③idle + gate + 漂移 → exit 2（漂移错误在列）。fixture 测试：semantic_sha256 篡改 → exit 2 |
| AC-03 release check idle 6/6 PASS、active 不变 | **PASS** | idle worktree 端到端：`release.py check` → 6/6 PASS、exit 0，validate_state 步骤标注"rc=3：idle 合法阻塞态"；主树激活态：step_validate_state 直调 → OK（rc=0 路径），`release.py check` 仅 version_sync FAIL（F-03 约定瞬时项：pyproject=3.12.40 vs HEAD=3.12.39，提交后自愈）。代码确认 rc=3 分支位于 rc≠0 分支**之前**，rc=0 PASS / rc=2 FAIL 语义原样；tests/test_release.py `-k "rc3 or validate_state or check_validate"` 7 passed |
| AC-04 consistency idle 0 失败、激活断言保留 | **PASS** | 走读改后测试：5 项参数化 repo/idle 双场景，None 先判分支（`current not in task_ids` 等，杜绝 `None in str` TypeError），激活态断言原样保留；`test_current_gate_task_matches`/`is_approved` 增加 None 早退。主树（激活）22 passed；idle worktree 22 passed（repo-idle 分支 + fixture-idle 分支） |
| AC-05 self-audit 0/2/3 三处对齐 | **PASS** | 代码确认 `(0, 2)` → `(0, 2, 3)` + 注释三态说明；idle worktree 实测 `loop_self_audit.py --quick` → overall PASS、failed=[]（rc=3 被接受）。HANDOFF-NEXT.md 两处文档同步为 rc=3 语义（grep 确认 docs/ 无其他 NO_ACTIVE_TASK 描述） |
| AC-06 全量回归 + compile + 3.12.40 | **PASS**（含 2 个已知失败） | 主树全量：**3761 passed, 2 failed, 64 skipped, 12 xfailed**。2 失败均为已知：①version_sync HEAD 瞬时项（提交后自愈）；②test_manifest_t0095 悬挂引用（T-0101 manifest 未生成，完成流程创建后自愈）。compile gate 独立重跑：pass 68/68。8 载体逐一 grep = 3.12.40；test_version_consistency 7 passed。test_release_bump 11 passed（developer 连带维护真实）。idle worktree 全量：3758 passed + 5 failed，5 项全部归因（见第四节），无 T-0101 相关失败 |
| AC-07 无约束弱化 | **PASS** | 见第三节专项 |

## 三、约束零弱化专项（最高优先级）

1. **fail-closed 保持（真实损坏仍 exit 2）**：rc=3 分支条件为 `task_id is None and len(unique_blockers)==1 and unique_blockers[0]=="NO_ACTIVE_TASK: state.current_task_id is null"` —— 严格白名单判定。任何连续性漂移/缺文件/待决 gate/哈希失配都会使 blocker 数 >1 或内容不同 → 必然 exit 2。**"idle + 其他 blocker 并存"实测 exit 2**（见 AC-02 三场景），不存在"因 idle 放行损坏"的路径。缺 state.yaml 时 `load_yaml` 返回 `{}`（governor_lib.py:446-448）+ "Missing .ai/state.yaml" blocker → exit 2，无崩溃路径。
2. **idle 安全意图**：idle 分支 `return 3` 位于 `[ok] state is usable` 之前且永不打印该行；输出段为 `[info]` 级（非 error），文案明确"合法阻塞态…state 不可开工"。
3. **rc=3 唯一性**：全代码库唯一 return 3 点即 validate_state / audit_handoff 的 idle 分支（grep 确认）；release.py 将 rc=3 映射 PASS 仅此一处。不存在把损坏误报为 3 的路径。
4. **hook/RuntimeController/C3 零改动**：`git diff hooks/ loop_core/ agents/ .zcode/plans/` 为空（loop_core 仅 `__init__.py` 版本字符串）。runtime_controller.py 中 NO_ACTIVE_TASK 为内部枚举（L26/L139/…），不消费 validate_state rc；hook（L1729 DISPATCH 门 / L1822-1900 idle 豁免通道）只按目录白名单豁免 `.zcode/tools/`，不解析 rc → rc=3 不改变 hook 行为。
5. 边缘语义：idle + `[warn]` 级错误 → rc=3（warn 非 blocker，激活态下同样不阻断，语义一致，非弱化）。

## 四、越界核对表

改动文件共 23 modified + 4 untracked，全部在范围内：

| 类别 | 文件 | 判定 |
|------|------|------|
| IN SCOPE 代码 | .zcode/tools/validate_state.py、.zcode/tools/audit_handoff.py（continuity_auditor.py / governor_lib.py 零改动）、scripts/release.py、tools/loop_self_audit.py | 合规 |
| IN SCOPE 测试 | tests/test_governance_consistency.py、tests/test_release.py、tests/test_release_bump.py、tests/test_idle_semantics.py（新增） | 合规 |
| IN SCOPE 文档/状态 | .ai/HANDOFF-NEXT.md（rc=3 语义同步，2 处）、.ai/HANDOFF.md（激活态渲染）、.ai/state.yaml、.ai/gates.yaml（G-T-0101 注册）、.ai/task_graph.yaml、.ai/project_continuity.yaml（连续性重算）、.ai/version-manifest.yaml、.ai/evidence/T-0087/conformance-report.json（仅时间戳）、.ai/evidence/observability/guard-events.jsonl（事件追加）、CHANGELOG.md、docs/06-delivery.md、.ai/evidence/T-0101/（新证据） | 合规（.ai/、docs/、CHANGELOG.md 均为 allowed_paths） |
| bump 载体 | pyproject.toml、loop_core/__init__.py、src/loop_engine/__init__.py、README.md、.zcode-plugin/plugin.json | 合规（任务显式要求 bump 3.12.40 并验证 F-03 机制；diff 均为纯版本字符串 3.12.39→3.12.40，无语义改动；F-03 唯一 bump 机制即写这 8 载体） |
| 零改动 | hooks/、agents/、loop_core/runtime_controller.py、.zcode/plans/、.zcode/tools/continuity_auditor.py、.zcode/tools/governor_lib.py | 合规（diff 为空） |

**越界判定：无越界。**

## 五、遗留事项核实

1. **rollback.py `_verify_state`（scripts/rollback.py:194-211）**：`rc==0 → True`，其余 rc → False。T-0101 **未改此文件**（不在 diff 中）。idle 下 rc=3 判失败 = 修复前 rc=2 判失败，行为前后一致、无回归。属性：既有保守局限（idle 稳态回滚会因"状态验证未通过"而阻断），P3 观察，可在后续任务顺带对齐。
2. **bump `--title` 未透传**：`VERSION_CARRIERS` 中 CHANGELOG 更新器为 `lambda c, v: _update_changelog(c, v)`（scripts/release.py:215），`cmd_bump(title=...)` 的 title 被丢弃（`_update_changelog` 本身支持 title 参数但 lambda 不传）。该 lambda 属 T-0100 F-03 引入、T-0101 diff 未触碰 → **确认 F-03 既有缺陷，非本任务引入**。developer 已手动完善 CHANGELOG 条目正文（v3.12.40 条目完整）。P3，建议后续任务修复。

## 六、P3 观察清单（不阻断，供主会话/后续任务）

1. 提交后 idle 稳态复验时注意 test_manifest_t0095：T-0100 完成流程在 idle 下渲染 HANDOFF 曾产出 `.ai/evidence/none/evidence-manifest.v1.yaml` 悬挂引用（ecac6a3 committed HANDOFF 实测存在）。T-0101 完成流程若以激活态生成 manifest 引用则可自愈；提交后请复跑该测试确认。
2. committed ecac6a3 的 continuity manifest 已陈旧（283 个漂移哈希）—— 主会话完成流程须按 f-01 记录的路径（repair_continuity + close_session）重生成主树 project_continuity.yaml + HANDOFF.md（主树当前因 HANDOFF-NEXT.md 文档编辑存在连续性漂移，fail-closed 已如实拦截，属预期工作流，非缺陷）。
3. 版本瞬时项：主树 `release.py check` 当前仅 version_sync FAIL（3.12.40 vs HEAD 3.12.39），按 F-03"先 bump 再提交"约定以 subject `v3.12.40` 提交后自愈；提交后由主会话做 idle 稳态 6/6 最终复验。
4. rollback.py `_verify_state` 与 bump `--title`（见第五节）。

## 七、关键结论

- 修复真实性：**全部亲自复验通过**（idle rc 2→3、损坏 rc=2、idle+blocker rc=2、release check idle 6/6、consistency idle 22 passed、self-audit 0/2/3、8 载体 3.12.40、compile pass、全量 3761 passed）。
- 约束零弱化：**成立**（fail-closed 保持、rc=3 唯一性、idle 安全意图、hook/RuntimeController/C3 零改动）。
- 越界：**无**。
- developer 报告与实测一致；唯一差异（我复跑 3761 vs developer 3760 passed / 2 vs 3 failed）源于 test_release_bump 已由其修复后复跑通过 —— 修复真实。
