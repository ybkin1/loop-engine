# T-0101 验收报告 — idle 稳态语义修复（NO_ACTIVE_TASK exit code 分流 + 消费端对齐）

- 任务：T-0101（G-T-0101-REQUIREMENTS，approved）— OPEN-FINDING 2026-08-02 修复：
  idle 稳态语义割裂（validate_state NO_ACTIVE_TASK 与真实治理损坏共用 exit 2，
  导致 release check 在 idle 稳态 6/6 不可达、consistency 测试 idle 失败、判定约定分裂）
- 角色：governance-controller（治理收尾：证据清单 + 验收记录；验收结论基于
  developer 修复记录与 independent-reviewer 独立审查）
- 执行时间：2026-08-02（UTC+8）
- 环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
- 基线：git HEAD `ecac6a3`（v3.12.39 T-0100，正式 GO）；工作树含全部 T-0101 改动（未提交，
  其中 main 会话完成流程须处理 HANDOFF-NEXT.md 编辑造成的连续性漂移——fail-closed 已如实拦截，
  恢复路径 repair_continuity + close_session 已在 worktree 实证）
- 任务文档：`.ai/tasks/T-0101.md`

---

## 一、任务概述

T-0100 提交后复验发现：任务关闭稳态（idle）下 validate_state 的 handoff 审计对
"无活动任务"硬阻断（exit 2，T-0078 起 fail-closed 设计），`release.py check` 在 idle
稳态必然 FAIL（6/6 不可达）→ 记录为 OPEN-FINDING 2026-08-02。根因：v2.0.0 计划要求的
exit code 分流从未实现——NO_ACTIVE_TASK 与真实治理损坏共用 exit 2 + `[error]` 级输出，
消费端（release check / loop_self_audit / consistency 测试）无法区分"合法 idle 阻塞"
与"治理损坏"。

T-0101 修复包（5 项修复 + 版本 bump 3.12.40）：
**F-01 validate_state / audit_handoff 分流**（idle → 独立 `[info]` 段 + exit 3，
不输出 `[ok] state is usable`；真实损坏/其他 blocker 保持 `[error]` + exit 2 fail-closed）
→ **F-02 release.py check 感知合法阻塞态**（step_validate_state rc=3 → PASS 标注
"idle 合法阻塞态"；rc 0/2 语义不变）→ **F-03 consistency 测试 idle 适配**（5 项
repo/idle 双场景参数化，消除 `None in str` TypeError；激活态断言原样保留）+
**F-04 loop_self_audit rc 判定 0/2 → 0/2/3 对齐**（含 HANDOFF-NEXT.md 文档同步）→
**F-05 版本 bump 3.12.40**（F-03 bump 机制闭环：8 载体原子更新 + 连带维护
test_release_bump 硬编码版本）→ 复验：idle 稳态 release check 6/6 PASS + 全量回归
无回归 → 达成 GO（待 git 提交 v3.12.40 后 idle 稳态最终复验由主会话执行）。

## 二、AC-01 ~ AC-07 逐项验收结果

| AC | 验收项 | 结果 | 证据引用 | 备注 |
|----|--------|------|----------|------|
| AC-01 | idle 稳态：validate_state / audit_handoff → NO_ACTIVE_TASK 独立段（非 `[error]` 级）+ exit 3；不输出 `[ok] state is usable` | **PASS** | `fixes/f-01-exit-code.md`；`review/independent-review.md` §AC-01；`commands.md` | idle worktree（ecac6a3）实测对照：旧工具 `[error] NO_ACTIVE_TASK…` → rc=2；新工具 `[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态…）` → **rc=3**，无 usable、无 error；audit_handoff 同 → rc=3。`tests/test_idle_semantics.py` 5 passed（主树 + idle worktree 双处） |
| AC-02 | 真实损坏仍 exit 2（fail-closed 保持，有测试） | **PASS** | `fixes/f-01-exit-code.md`；`review/independent-review.md` §AC-02 | worktree 实测三场景全部 exit 2：①连续性漂移（篡改 HANDOFF-NEXT.md → `[error] Continuity source drift`）；②idle + 待决 gate（`[error] Pending gate…` + `[error] NO_ACTIVE_TASK` 双行，fail-closed 不被分流吞掉）；③idle + gate + 漂移。fixture 测试：semantic_sha256 篡改 → exit 2。主树实测：HANDOFF-NEXT.md 文档同步造成漂移后 validate_state 如实拦截 exit 2；恢复路径（repair_continuity + close_session）worktree 实证回到干净 idle rc=3 |
| AC-03 | release.py check 在 idle 稳态 6/6 PASS（validate_state 步骤 rc=3 → 标注通过）；active 态行为不变（rc 0 → PASS、rc 2 → FAIL） | **PASS** | `fixes/f-02-release-check.md`；`review/independent-review.md` §AC-03；`commands.md` | idle worktree 端到端：`release.py check` → **6/6 PASS、exit 0**（version_sync/validate_state(rc=3 标注)/compile/guard_health/slo_gate/key_tests）；修复前同一 worktree rc=2 → 阻断。代码走读确认 rc=3 分支位于 rc≠0 分支**之前**，rc=0 PASS / rc=2 FAIL 语义原样；`tests/test_release.py -k "rc3 or validate_state or check_validate"` 7 passed（含既有 rc=2/超时/缺失阻断测试） |
| AC-04 | test_governance_consistency idle 稳态 0 失败（None 断言 idle 契约，无 TypeError）；激活态下原断言仍通过 | **PASS** | `fixes/f-03-consistency-tests.md`；`review/independent-review.md` §AC-04 | 5 项失败测试改造为 repo/idle 双场景参数化：None 先判分支（`current not in task_ids` 等，杜绝 `None in str`），HANDOFF null↔null 匹配显式规避；`test_current_gate_task_matches`/`is_approved` 增加 None 早退。主树（激活态）`test_governance_consistency + test_idle_semantics` **22 passed**；idle worktree 同 **22 passed**（repo-idle 分支 + fixture-idle 分支，0 failed、无 TypeError） |
| AC-05 | loop_self_audit rc 判定更新为 0/2/3（3=idle 合法态）；三处约定一致（有测试或文档证据） | **PASS** | `fixes/f-04-self-audit.md`；`review/independent-review.md` §AC-05 | `tools/loop_self_audit.py` L310-314：`(0, 2)` → `(0, 2, 3)` + 注释三态说明；idle worktree 实测 `loop_self_audit.py --quick` → overall PASS、failed=[]（rc=3 被接受）。HANDOFF-NEXT.md 2 处文档同步为 rc=3 语义；grep 确认 docs/ 无其他 NO_ACTIVE_TASK 描述。三处约定对齐：validate_state/audit_handoff 产 rc 0/2/3、release check 判 rc 0/3→PASS & rc 2→FAIL、self-audit 认 rc∈{0,2,3} 为工具按预期返回 |
| AC-06 | 全量回归 0 failed（idle 稳态下）+ compile pass + 版本 3.12.40 与 HEAD 一致 | **PASS**（2 个已知失败均为提交后自愈瞬时项） | `fixes/f-05-bump.md`；`review/independent-review.md` §AC-06；`compile-evidence.json`；`commands.md` | 主树全量 **3761 passed, 2 failed, 64 skipped, 12 xfailed**（independent-reviewer 独立复跑同值）。2 失败均已知：① `test_pyproject_version_matches_git_head`（F-03"先 bump 再提交"瞬时项：pyproject=3.12.40 vs HEAD=3.12.39，提交 subject v3.12.40 后自愈）；② `test_manifest_t0095`（HANDOFF 引用 `.ai/evidence/T-0101/evidence-manifest.v1.yaml` 未生成，本报告配套清单生成后自愈）。compile gate 独立重跑 pass 68/68；8 载体（pyproject/CHANGELOG/loop_core/src/README/docs/plugin.json/version-manifest）逐一 grep = 3.12.40，test_version_consistency 7 passed；test_release_bump 11 passed（连带维护真实：3.12.39→3.12.40 共 4 处） |
| AC-07 | 无约束被弱化（diff 审查：hook/RuntimeController/C3 语义零改动；rc=3 仅限 idle 合法态） | **PASS** | `review/independent-review.md` §三（约束零弱化专项）+ §四（越界核对） | ① fail-closed 保持：rc=3 条件为严格白名单（`task_id is None` 且去重后 blocker **恰好只有** `"NO_ACTIVE_TASK: state.current_task_id is null"` 一条），任何漂移/缺文件/待决 gate/哈希失配 → 必然 exit 2，无"因 idle 放行损坏"路径；缺 state.yaml 走 `load_yaml → {}` + Missing blocker → exit 2 无崩溃；② idle 安全意图：`return 3` 位于 `[ok] state is usable` 之前且永不打印该行，输出为 `[info]` 级、文案明确"合法阻塞态…state 不可开工"；③ rc=3 唯一性：全库唯一 return 3 点即 idle 分支（grep 确认），不存在把损坏误报为 3 的路径；④ hook/RuntimeController/C3 零改动（diff 为空；runtime_controller 内部枚举不消费 rc，hook 仅按目录白名单豁免 `.zcode/tools/` 不解析 rc）；⑤ 越界核对：23 modified + 4 untracked 全部在范围内，**无越界** |

**逐项汇总：AC-01~AC-07 全部 PASS**（AC-06 含 2 个"提交后自愈"预期瞬时项，不构成
阻断，见裁决节）。

## 三、独立审查裁决记录

- 审查人：independent-reviewer（独立子代理），2026-08-02
- 方法：全部结论亲自复验（git worktree 隔离 fixture + 源码走读 + 定向/全量测试），
  不复述 developer 证据；临时 worktree 验证完已移除，主树零改动

| 轮次 | 时间 | 裁决 | 结论 |
|------|------|------|------|
| 唯一一轮 | 2026-08-02 | **GO** | 无 P1/P2 条件；3 项 P3 观察（均为既有局限或提交后自愈项，不阻断）。修复真实性全部亲自复验通过（idle rc 2→3、损坏 rc=2、idle+blocker rc=2、release check idle 6/6、consistency idle 22 passed、self-audit 0/2/3、8 载体 3.12.40、compile pass、全量 3761 passed）；约束零弱化专项成立（5 点）；越界核对无越界；developer 报告与实测一致（唯一差异：复跑 3761 vs developer 3760 passed 源于 test_release_bump 已由其修复后复跑通过——修复真实） |

### P3 观察清单（不阻断，供主会话/后续任务）

1. **rollback idle 阻断**：`scripts/rollback.py:194-211` `_verify_state` 为
   `rc==0 → True`，其余 rc → False。T-0101 **未改此文件**（不在 diff 中）；idle 下
   rc=3 判失败 = 修复前 rc=2 判失败，行为前后一致、无回归。属性：既有保守局限
   （idle 稳态回滚会因"状态验证未通过"而阻断），可在后续任务顺带对齐 rc=3。
2. **bump `--title` 未透传**：`scripts/release.py:215` `VERSION_CARRIERS` 中 CHANGELOG
   更新器为 `lambda c, v: _update_changelog(c, v)`，`cmd_bump(title=...)` 的 title 被
   丢弃（`_update_changelog` 本身支持 title 参数但 lambda 不传）。该 lambda 属
   T-0100 F-03 引入、T-0101 diff 未触碰 → **F-03 既有缺陷，非本任务引入**；developer
   已手动完善 CHANGELOG v3.12.40 条目正文弥补。P3，建议后续任务修复。
3. **待决 gate 场景**：idle + 待决 gate → exit 2（`[error] NO_ACTIVE_TASK` 行保留，
   双行错误），fail-closed 不被分流吞掉——属设计内行为（T-0101 OUT OF SCOPE：本次
   只做 NO_ACTIVE_TASK 分流，pending_gate 独立 exit code 不实现）。P3 观察。

其他移交事项（独立审查第五节/第六节）：① committed ecac6a3 的 continuity manifest
已陈旧（283 个漂移哈希，T-0100 提交时遗留）——主会话完成流程须按 f-01 记录的路径
（repair_continuity + close_session）重生成主树 project_continuity.yaml + HANDOFF.md；
② 版本瞬时项按 F-03"先 bump 再提交"约定以 subject `v3.12.40` 提交后自愈，提交后由
主会话做 idle 稳态 6/6 最终复验。

## 四、测试汇总

| 项 | 结果 | 说明 |
|----|------|------|
| 定向 idle 语义 | **5 passed** | `tests/test_idle_semantics.py`（主树激活态 + idle worktree 双处；rc 0/2/3 输出与退出码断言） |
| consistency + idle 合跑 | **22 passed**（主树激活态）/ **22 passed**（idle worktree） | `test_governance_consistency.py + test_idle_semantics.py`；repo 分支 + fixture-idle 分支全覆盖，无 TypeError |
| release rc3 分支 | **7 passed** | `tests/test_release.py -k "rc3 or validate_state or check_validate"`（含既有 rc=2/超时/缺失阻断测试） |
| release check idle 端到端 | **6/6 PASS、exit 0** | idle worktree 实测（修复后）；修复前同一 worktree validate_state 步骤 FAIL 阻断 |
| release_bump 连带维护 | **11 passed** | `tests/test_release_bump.py`（硬编码版本 3.12.39→3.12.40 共 4 处，bump 后复跑） |
| version_consistency | **7 passed** | 8 载体（pyproject/CHANGELOG/loop_core/src/README/docs/plugin.json/version-manifest）全部 = 3.12.40 |
| 全量回归 | **3761 passed, 2 failed, 64 skipped, 12 xfailed** | 2 failed 均为**提交后自愈瞬时项**：① `test_pyproject_version_matches_git_head`（version==HEAD：3.12.40 vs HEAD 3.12.39，git 提交 v3.12.40 后自愈）；② `test_manifest_t0095`（T-0101 evidence-manifest 未生成，本任务清单生成后自愈）。相对 T-0100（3744 passed）新增 ~17 例全部通过，无意外失败 |
| 编译 | **68/68 PASS** | `compile-evidence.json`：status pass，failed_count 0 |
| 提交后复验（待办，主会话） | idle 稳态 release check 6/6 + 全量 0 failed | git 提交 v3.12.40 后：version_sync 自愈、manifest 引用自愈；idle 稳态最终复验（release check 6/6 + 全量 0 failed）由主会话在提交后执行 |

## 五、关键证据清单

- `fixes/f-01-exit-code.md` / `f-02-release-check.md` / `f-03-consistency-tests.md` /
  `f-04-self-audit.md` / `f-05-bump.md` — 5 项修复记录（根因、改动、测试、复验；
  f-01 含损坏态实测与恢复路径实证，f-05 含 bump 机制闭环与连带维护）
- `review/independent-review.md` — 独立审查报告（裁决 GO、逐项 AC 复验表、约束零弱化
  专项 5 点、越界核对表、遗留事项核实、P3 观察清单）
- `compile-evidence.json` — 编译 68/68 PASS（工具生成）
- `commands.md` — 修复前基线 → 修复后复验全程命令记录（idle worktree 对照、
  6/6 PASS 输出、损坏态 fail-closed 实测、测试与 bump 命令）
- `approval-evidence.json` / `execution-evidence.json` — Gate 批准与执行证据
- `evidence-manifest.v1.yaml` — 本任务证据清单（EvidenceManifest/v1）
- `acceptance/acceptance-report.md` — 本报告

## 六、裁决

**GO（正式）** — 待 git 提交 v3.12.40 后 idle 稳态复验（release check 6/6 + 全量
0 failed）完成收尾。

依据：
1. AC-01~AC-07 全部 PASS（证据见第二节），OPEN-FINDING 2026-08-02 的 idle 语义割裂
   修复真实落地：idle → exit 3 独立分流、真实损坏仍 exit 2（fail-closed 保持）、
   三处消费端约定（release check / self-audit / consistency 测试）统一 0/2/3 语义，
   并有测试钉住；
2. 独立审查唯一一轮 **GO**：无 P1/P2；3 项 P3 观察（rollback idle 阻断、bump --title
   透传、待决 gate 场景）均为既有局限或设计内行为，不阻断；
3. 全量测试 3761/3763 通过，2 个失败均为提交后自愈瞬时项（version==HEAD 随
   `v3.12.40` 提交自愈；manifest 引用已随本任务清单生成自愈），无意外回归；
4. 约束零弱化专项结论成立（5 点）+ 越界核对**无越界**：hook/RuntimeController/C3
   零改动、rc=3 仅限严格白名单的 idle 合法态、idle 安全意图（不输出 usable）保留。

提交 v3.12.40 后需执行的收尾复验：`git log -1`（subject `v3.12.40: T-0101 …`）→
idle 稳态 `python scripts/release.py check` 6/6 PASS → 全量 `pytest tests/ -q`
0 failed（含 test_manifest_t0095 自愈确认）。

---

## 七、idle 稳态复验记录（git 提交 c4426c6 后最终复验）

- 复验时间：2026-08-02；执行：复验子代理（主会话委托，提交后首次 idle 稳态完整复验）
- 环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
- 基线：git HEAD `c4426c6`（v3.12.40，T-0101 提交，subject 确认无误）；`.ai/state.yaml`
  `current_task_id: null`（idle 稳态）
- 工作树状态：HANDOFF.md 相对 HEAD 无改动；仅 2 个测试运行副产物漂移
  （`.ai/evidence/T-0087/contract-planes/conformance-report.json`、
  `.ai/evidence/observability/guard-events.jsonl`），非 T-0101 范围、不阻断

### 1. release check 6/6 端到端（idle 稳态）

命令：`C:/Python312/python.exe scripts/release.py check` → **exit 0**

| 步骤 | 结果 | 输出要点 |
|------|------|----------|
| version_sync | **PASS** | `pyproject=3.12.40 == git HEAD=3.12.40`（提交后自愈确认） |
| validate_state | **PASS** | `rc=3：idle 合法阻塞态，current_task_id=null，无活动任务，等待任务发起；非治理损坏`（修复前该步必然 FAIL 阻断） |
| compile | **PASS** | compileall（loop_core, src, scripts, hooks, tools） |
| guard_health | **PASS** | 5 个 guard 全部存活 |
| slo_gate | **PASS** | error budget 内（consumed 5.0 / 100.0，remaining 95.0） |
| key_tests | **PASS** | test_version_consistency + test_loop_core 子集 |

最终输出 `[release] check 通过（质量门前置全部 PASS）`，**exit 0** —— 修复前 idle 稳态
1/6 FAIL（validate_state 阻断）场景闭环，**6/6 达成**。

### 2. validate_state 直接验证

命令：`C:/Python312/python.exe .zcode/tools/validate_state.py .` → **exit 3**

输出：`[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：state 无活动
任务，等待任务发起；state 不可开工）`；确认**无 `[error]` 行、不输出 `[ok] state is
usable`** —— 与 AC-01 修复目标逐字一致。

### 3. 全量回归

`C:/Python312/python.exe -m pytest tests/ -q`（198.83s）→
**3762 passed, 1 failed, 64 skipped, 12 xfailed**

- 自愈项① `test_pyproject_version_matches_git_head`：**已自愈**（随 v3.12.40 提交生效，
  含入 3762 passed）✓
- 自愈项② `test_manifest_t0095`：**未自愈**（1 failed）—— 根因见第 5 节，**非 T-0101
  引入、非回归**；提交前"清单生成后自愈"的归因经复核有误
- 相对 T-0100（3744 passed）新增 ~18 例全部通过；consistency + idle 全套
  （test_governance_consistency / test_idle_semantics）通过，无 TypeError

### 4. 定向子集确认

`-k "manifest or consistency or idle"` → **212 passed, 1 failed, 3626 deselected**
（唯一失败即第 5 节悬挂引用项；consistency/idle/version_consistency 相关全部通过，
与全量结果一致，并入全量结论）。

### 5. 唯一失败项根因分析（test_manifest_t0095 —— 既有缺陷，非本任务回归）

- 失败断言：`test_manifest_exists_and_handoff_reference_is_real` ——
  `.ai/HANDOFF.md:124` 含悬挂引用 `Evidence manifest: .ai/evidence/none/evidence-manifest.v1.yaml.`
  （`.ai/evidence/none/` 目录不存在）。同文件其余 3 个断言（schema/指纹/官方校验器）
  全部 PASS，T-0101 清单本身无问题。
- 引入时间：`git log -S "evidence/none"` → **bc6680f（v3.12.36，T-0097）**，idle/无
  任务态 handoff 生成流程以 task_id=None 写 "none" 占位路径所致；c4426c6 提交的
  HANDOFF.md 仍含此行（工作树零改动）。
- 归因复核：提交前报告将该项归为"T-0101 evidence-manifest 未生成，清单生成后自愈"
  **不成立**——HANDOFF.md 从未引用 `.ai/evidence/T-0101/evidence-manifest.v1.yaml`
  （该清单已生成且通过全部校验），生成 T-0101 清单不可能自愈该项。该项自 T-0097 起为
  **持续性失败**（T-0098/T-0099/T-0100 的"瞬时项/提交后自愈"归因建议一并复核），
  但从未阻断 release check（key_tests 不含该项目）。
- 修复建议（P3，后续任务）：handoff 生成器在 idle/无任务态不应写 "none" 占位 manifest
  路径（应省略该行或写真实路径）；或由主会话按官方流程（repair_continuity +
  close_session）重生成 HANDOFF.md 后复跑该项确认全量 0 failed。

### 6. 结论

**idle 稳态 6/6 达成，OPEN-FINDING 2026-08-02（idle 语义割裂）闭环。**

- T-0101 核心目标全部实测达成：① release check idle 稳态 **6/6 PASS、exit 0**
  （修复前 1/6 FAIL 场景）；② validate_state **exit 3** + `[info] NO_ACTIVE_TASK` +
  不输出 usable（修复目标逐字一致）；③ consistency/idle 全套测试通过、无 TypeError；
  ④ fail-closed 语义未被破坏（validate_state 仍只对严格白名单 idle 态放行 rc=3）。
- "全量 0 failed"收尾条件**未完全满足**：唯一失败为 **bc6680f（T-0097）引入的既有
  悬挂引用**（HANDOFF.md `evidence/none` 占位路径），非 T-0101 引入、非回归、不阻断
  release check——不作为本任务 OPEN-FINDING 未闭环的依据，但建议单独立项修复
  handoff 生成器 idle 占位路径后复跑确认（P3）。
