# T-0102 验收报告 — handoff 生成器 idle 占位缺陷修复 + P3 观察项清零

- 任务：T-0102（G-T-0102-REQUIREMENTS，approved）— OPEN-FINDING 2026-08-02 修复：
  handoff 生成器 idle 态渲染 `.ai/evidence/none/` 悬挂路径（T-0097/bc6680f 引入），
  致 test_manifest_t0095 持续性失败；同时清零 T-0101 独立审查遗留的 2 项 P3 观察
  （rollback idle 阻断、bump --title 透传），达成"全量 0 failed + 无已知悬挂引用"
- 角色：governance-controller（治理收尾：证据清单 + 验收记录；验收结论基于
  developer 修复记录与 independent-reviewer 独立审查）
- 执行时间：2026-08-02（UTC+8）
- 环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
- 基线：git HEAD `c737c3a`（v3.12.40，T-0101，正式 GO）；工作树含全部 T-0102 改动
  （未提交，T-0102 激活态；临时 idle worktree 验证完已移除，主树状态文件零改动）
- 任务文档：`.ai/tasks/T-0102.md`

---

## 一、任务概述

T-0101 提交后 idle 稳态复验发现：HANDOFF.md L124 存在悬挂引用
`.ai/evidence/none/evidence-manifest.v1.yaml`（目录不存在），根因是
`.zcode/tools/continuity_producer.py` render_handoff L220 的展示占位
`task_id = action["current_task_id"] or "none"` 把 None 提前替换为 truthy 的
`"none"`，击穿 L293 的 `if task_id` 保护 → idle 态 close_session 必然渲染
`none` 占位路径。该行自 T-0097（bc6680f，v3.12.36）首次进入提交的 HANDOFF，T-0101
起 idle 态 close_session 成为常态路径后持续暴露 → 记录为 OPEN-FINDING 2026-08-02。

T-0102 修复包（4 项修复 + 版本 bump 3.12.41）：
**F-01 handoff 生成器 idle 占位修复**（新增 `_latest_manifest_path`：mtime 序取最近
真实 manifest、显式排除 `none` 目录、取不到渲染 `not available (no active task)`；
`render_handoff` 拆出 `active_task_id`，激活态渲染逐字节不变）→
**F-02 rollback.py `_verify_state` rc 判定 0 → (0, 3)**（rc=3 idle 合法态放行并标注，
rc=2/1 损坏与非 0 仍阻断 fail-closed；对应 T-0101 审查 P3 观察 #1）→
**F-03 release.py bump `--title` 透传**（VERSION_CARRIERS 二元组 → 三元组
`use_title` 标志，仅 CHANGELOG 透传；对应 T-0101 审查 P3 观察 #2）→
**F-04 版本 bump 3.12.41**（8 载体原子同步 + test_release_bump 硬编码版本连带维护
3.12.40→3.12.41，CHANGELOG 头条目实机验证 `--title` 生效）→ 复验：idle worktree
端到端无 `none` 悬挂引用 + test_manifest_t0095 4/4 全绿 + 全量回归无意外失败 →
达成 GO（待 git 提交 v3.12.41 后 idle 稳态终验：release check 6/6 + 全量 0 failed）。

## 二、AC-01 ~ AC-07 逐项验收结果

| AC | 验收项 | 结果 | 证据引用 | 备注 |
|----|--------|------|----------|------|
| AC-01 | idle 态 close_session 生成的 HANDOFF 无 `.ai/evidence/none/` 悬挂引用（渲染实际 manifest 或省略字段）；test_manifest_t0095 全绿（idle 态 HANDOFF 提交场景） | **PASS** | `fixes/f-01-handoff-placeholder.md`；`review/independent-review.md` §AC-01；`commands.md` §1-3 | idle worktree 端到端（repair_continuity → validate_state rc=3 → close_session）：HANDOFF L124 = `Evidence manifest: .ai/evidence/T-0101/evidence-manifest.v1.yaml.`（真实存在、mtime 序最新），`evidence/none` 出现 0 次、目录不存在；`test_manifest_t0095` **4/4 passed**（fresh checkout CRLF/mtime 噪声按 manifest 记录值复原后全绿，属检出环境噪声）。`_latest_manifest_path` 边缘直测：无 evidence 目录 → None；仅 `none` 目录 → 排除返回 None；多任务取 mtime 最新；repair 优先语义保留。激活态渲染逐字节不变（`active_task_id` 非空 → 与旧实现字符相同） |
| AC-02 | rollback.py `_verify_state`：rc=3 → 通过（idle 合法态标注）；rc=2 → 仍阻断（有测试） | **PASS** | `fixes/f-02-rollback-idle.md`；`review/independent-review.md` §AC-02 | `if result.returncode in (0, 3)` → 通过并标注"（idle 合法阻塞态 rc=3）"；else 分支原样（rc=2/1 阻断 + 输出诊断）；超时/异常分支未动。`tests/test_operations.py -k "verify_state"` → **4 passed**（monkeypatch subprocess.run 真实断言：rc=0/3 → True、rc=2/1 → False）。rc=3 唯一性：全库仅 validate_state.py:450 与 audit_handoff.py:44 两处 `return 3`（均 T-0101 idle 白名单分支）——损坏不可能被误判为 rc=3 |
| AC-03 | bump `--title` 透传：`bump --to x --title "..."` 的 CHANGELOG 条目使用该 title（有测试） | **PASS** | `fixes/f-03-bump-title.md`；`review/independent-review.md` §AC-03；`commands.md` §5 | VERSION_CARRIERS 三元组仅 CHANGELOG 置 use_title=True，非 CHANGELOG 载体签名 `(content, version)` 不变；`_print_plan` 解包同步。`test_bump_title_passthrough_to_changelog` 断言 CHANGELOG 条目内容（含"自定义标题"、不含缺省标题、旧条目保留）真实通过（test_release_bump.py 共 **12 passed**，developer 记录 13 为计数笔误——P3 观察 #1）。F-04 实机 bump 产物核：CHANGELOG 头条目 = `## v3.12.41 (2026-08-02) — T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零`，与 `--title` 实传值一致，F-03 闭环成立 |
| AC-04 | 全量回归 0 failed（idle 稳态下）+ compile pass | **PASS**（2 个已知失败均为提交后自愈瞬时项） | `fixes/f-04-bump.md`；`review/independent-review.md` §AC-04；`compile-evidence.json`；`commands.md` §6-7 | 主树全量 **3766 passed, 2 failed, 64 skipped, 12 xfailed**（independent-reviewer 独立重跑 197.55s 同值）。2 失败均已知、均提交后自愈：① `test_pyproject_version_matches_git_head`（F-04"先 bump 再提交"瞬时项：pyproject=3.12.41 vs HEAD=3.12.40，提交 subject v3.12.41 后自愈）；② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`（主树 HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 尚未生成，本任务配套清单生成后自愈；idle 稳态由 F-01 兜底，worktree 已实证 4/4）。compile gate 独立重跑 68/68 pass、failed_count 0 |
| AC-05 | 版本 3.12.41 与 git HEAD 一致（version_sync PASS） | **PASS**（提交后成立） | `fixes/f-04-bump.md`；`review/independent-review.md` §AC-05；`commands.md` §8 | 8 载体（pyproject.toml/CHANGELOG.md/loop_core/__init__.py/src/loop_engine/__init__.py/README.md/docs/06-delivery.md/.zcode-plugin/plugin.json/.ai/version-manifest.yaml）逐一实测 = **3.12.41**；`test_version_consistency` 7 passed。HEAD 尚为 3.12.40 —— 按"先 bump 再提交"约定以 subject `v3.12.41` 提交后 version_sync PASS（当前 release check 仅 version_sync FAIL，与瞬时失败①同源，提交后自愈） |
| AC-06 | 无约束被弱化（diff 审查：fail-closed 语义保持；rc=2 损坏阻断不变） | **PASS** | `review/independent-review.md` §三（约束零弱化专项 7 点）+ §四（越界核对） | ① hooks/ 零改动（21 modified + 2 untracked 无任何 hooks/ 路径，含 loop_enforcement hook、runtime_controller）；② validate_state/audit_handoff/governor_lib/continuity_auditor 零改动，rc=3 语义（T-0101 定义）原样；③ loop_core/ 仅版本字符串 3.12.40→3.12.41；④ rollback fail-closed 保持：放行集合严格 {0, 3}，rc=3 全库唯一来源即 idle 白名单分支（grep 仅两处 `return 3`），不存在"损坏被放行"路径，超时仍阻断；⑤ handoff 激活态逐字节不变；⑥ idle 态全路径无 "none" 占位（`or "none"` 仅剩展示串 2 处，非路径；`evidence/none` 仅 docstring）；⑦ 约束矩阵/C3/待决 gate 语义零触碰。越界核对：21 modified + 2 untracked 全部在范围内，**无越界**（4 个版本载体不在字面 allowed_paths，属 AC-05 版本同步必然产物 + T-0101/T-0100 同模式先例——P3 观察 #2 建议后续显式注明豁免） |
| AC-07 | 无已知 OPEN-FINDING 悬挂（idle 语义 + handoff 占位均闭环；P3 观察项清零或明确记录） | **PASS**（修复已闭环；归档记录属完成流程） | `review/independent-review.md` §AC-07 + §五（修复真实性）+ §六（完成流程清单） | handoff 占位 OPEN-FINDING → F-01 修复且独立实证（AC-01 三路：worktree 端到端 + 边缘直测 + 主树回归）；T-0101 遗留 P3 观察 #1（rollback idle 阻断）→ F-02、#2（bump --title）→ F-03，均有测试钉住；idle 语义 finding 已由 T-0101 关闭。finding 状态字段更新与 state notes 归档属主会话完成流程收尾（审查时点修复已验证，见裁决节待办） |

**逐项汇总：AC-01~AC-07 全部 PASS**（AC-04 含 2 个"提交后自愈"预期瞬时项、AC-05 提交后
成立，均不构成阻断，见裁决节）。

## 三、独立审查裁决记录

- 审查人：independent-reviewer（独立子代理），2026-08-02
- 方法：全部结论亲自复验（git worktree 隔离 idle 端到端 + 源码走读 + 边缘用例直测 +
  定向/全量测试），不复述 developer 证据；临时 worktree 验证完已移除，主树零改动

| 轮次 | 时间 | 裁决 | 结论 |
|------|------|------|------|
| 唯一一轮 | 2026-08-02 | **GO** | 无 P1/P2 条件；2 项 P3 观察（developer 证据计数笔误；版本载体 allowed_paths 豁免建议），不阻断。修复真实性全部亲自复验通过（idle close_session 无 `none` 悬挂引用且引用真实文件、test_manifest_t0095 idle 稳态 4/4、rollback rc 0/3 放行 2/1 阻断、bump --title 透传至 CHANGELOG 内容、8 载体 3.12.41、compile 68/68、全量 3766 passed/2 已知瞬时项）；约束零弱化专项成立（7 点）；越界核对无越界；developer 报告与实测一致（唯一差异：commands.md 记录 test_release_bump "13 passed"，实际收集 12 项——计数笔误，测试本身真实） |

### P3 观察清单（不阻断，供主会话/后续任务）

1. **证据文档计数笔误**：developer commands.md 记录 `test_release_bump.py` "13 passed"，
   实际收集 12 项（含新增 title 用例）全绿——测试本身真实，仅文档计数笔误。
2. **版本载体 allowed_paths 豁免建议**：`.zcode-plugin/plugin.json` 等 4 个版本载体
   不在任务字面 allowed_paths 列表（先例 + AC-05 必需，详见独立审查越界表）——
   建议后续任务在 allowed_paths 中显式注明版本载体豁免，避免审查歧义。

其他移交事项（独立审查第六节，完成流程清单，均非缺陷）：① 主树 validate_state 当前
exit 2（`Continuity source drift: .ai/version-manifest.yaml`——版本 bump 未折入
project_continuity source_manifest），提交前须在主树跑 repair_continuity.py +
close_session.py（worktree 已验证该流程；HEAD c737c3a 自带 284 个漂移哈希为 T-0101
已知遗留，一并修复）；② T-0102 manifest 生成（本报告配套完成，见第五节清单）；③ 版本
提交约定 subject `v3.12.41`，提交后 version_sync PASS + 全量回归 0 failed 终态达成；
④ OPEN-FINDING 与 2 项 P3 的状态字段更新 + state notes 归档。

## 四、测试汇总

| 项 | 结果 | 说明 |
|----|------|------|
| manifest 全套（idle worktree） | **4/4 passed** | `tests/test_manifest_t0095.py`（F-01 核心断言 `test_manifest_exists_and_handoff_reference_is_real` 字节修复前即通过；另 2 项 fresh checkout CRLF/mtime 噪声按 manifest 记录值复原后全绿） |
| rollback verify_state | **4 passed** | `tests/test_operations.py -k "verify_state"`（rc=0/3 → True、rc=2/1 → False，monkeypatch 真实断言） |
| release_bump 全套 | **12 passed** | `tests/test_release_bump.py`（含新增 title 透传用例 + 三元组连带维护用例；developer 记录 13 为计数笔误） |
| version_consistency | **7 passed** | 8 载体（pyproject/CHANGELOG/loop_core/src/README/docs/plugin.json/version-manifest）全部 = 3.12.41 |
| 全量回归 | **3766 passed, 2 failed, 64 skipped, 12 xfailed** | 2 failed 均为**提交后自愈瞬时项**：① `test_pyproject_version_matches_git_head`（version==HEAD：3.12.41 vs HEAD 3.12.40，git 提交 v3.12.41 后自愈）；② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`（主树 HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 尚未生成，本任务清单生成后自愈）。independent-reviewer 独立重跑同值，无意外失败 |
| 编译 | **68/68 PASS** | `compile-evidence.json`：status pass，failed_count 0，errors [] |
| 提交后终验（待办，主会话） | idle 稳态 release check 6/6 + 全量 0 failed | git 提交 v3.12.41 后：version_sync 自愈、manifest 引用随本清单生成自愈；idle 稳态最终复验（release check 6/6 + 全量 0 failed）由主会话在提交后执行 |

## 五、关键证据清单

- `fixes/f-01-handoff-placeholder.md` / `f-02-rollback-idle.md` / `f-03-bump-title.md` /
  `f-04-bump.md` — 4 项修复记录（根因、改动、测试、复验；f-01 含根因链定位与
  idle worktree 端到端实证，f-02/f-03 含 T-0101 P3 观察归因，f-04 含 bump 机制
  闭环与连带维护）
- `review/independent-review.md` — 独立审查报告（裁决 GO、逐项 AC 复验表、约束零弱化
  专项 7 点、越界核对表、修复真实性三路记录、完成流程清单、P3 观察清单）
- `compile-evidence.json` — 编译 68/68 PASS（工具生成）
- `commands.md` — 根因定位 → 修复前对照 → 修复后复验全程命令记录（git blame 归因、
  idle worktree 对照、rollback/bump 定向测试、全量与 compile 命令）
- `approval-evidence.json` / `execution-evidence.json` — Gate 批准与执行证据
- `evidence-manifest.v1.yaml` — 本任务证据清单（EvidenceManifest/v1，immutable
  create-only 生成）
- `acceptance/acceptance-report.md` — 本报告

## 六、裁决

**GO（正式）** — 待 git 提交 v3.12.41 后 idle 稳态终验（release check 6/6 + 全量
0 failed）完成收尾。

依据：
1. AC-01~AC-07 全部 PASS（证据见第二节），OPEN-FINDING 2026-08-02 的 handoff idle
   占位缺陷修复真实落地：idle 态渲染实际存在的最近真实 manifest（无 `.ai/evidence/none/`
   悬挂引用、取不到渲染 `not available (no active task)`），并有 test_manifest_t0095
   全绿 + 边缘用例直测钉住；激活态行为逐字节不变；
2. 独立审查唯一一轮 **GO**：无 P1/P2；2 项 P3 观察（commands.md 计数笔误、版本载体
   allowed_paths 豁免建议）均为文档级/建议级事项，不阻断；修复真实性全部亲自复验通过；
3. 全量测试 3766/3768 通过，2 个失败均为提交后自愈瞬时项（version==HEAD 随
   `v3.12.41` 提交自愈；manifest 引用已随本任务清单生成自愈），无意外回归；
4. 约束零弱化专项结论成立（7 点）+ 越界核对**无越界**：hooks/、validate_state/
   audit_handoff/governor_lib/continuity_auditor/runtime_controller 零改动、
   rollback 放行集合严格 {0, 3} 且 rc=3 唯一来源为 idle 白名单分支、
   fail-closed（rc=2 损坏阻断）语义保持。

提交 v3.12.41 后需执行的收尾终验：`git log -1`（subject `v3.12.41: T-0102 …`）→
idle 稳态 `python scripts/release.py check` 6/6 PASS → 全量 `pytest tests/ -q`
0 failed（含 test_manifest_t0095 自愈确认）。

---

## 八、v3.12.41 提交后 idle 稳态终验（git HEAD 57f96d5，工程全绿可推送）

- 终验时间：2026-08-02；执行：终验子代理（主会话委托，交付前最后一道闸——
  "工程完全没问题"最终验证；全部步骤真实执行，未复述任何历史记录）
- 环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10，pytest 9.0.3）
- 基线：git HEAD `57f96d5`（subject `v3.12.41: T-0102 — handoff 生成器 idle 占位修复
  + rollback rc3 + bump --title（7/7 AC，独立审查 GO）`，确认无误）；
  `.ai/state.yaml` `current_task_id: null`、`current_gate_id: null`（**idle 稳态**，
  S6-delivery）；工作树相对 HEAD 仅 2 个测试运行副产物漂移（见本节约 8.6）
- 本节编号按终验指令"第八节"字面；本报告正文为一~六（T-0101 先例中提交后复验为
  第七节，如需编号连续可将本节改"七"，不影响内容）

### 1. release check 6/6（idle 稳态，逐步骤实况）

命令：`C:/Python312/python.exe scripts/release.py check` → **exit 0**

| 步骤 | 结果 | 输出要点 |
|------|------|----------|
| version_sync | **PASS** | `pyproject=3.12.41 == git HEAD=3.12.41`（提交后自愈确认） |
| validate_state | **PASS** | `validate_state.py 通过（rc=3：idle 合法阻塞态，current_task_id=null，无活动任务，等待任务发起；非治理损坏）`，内嵌 `[info] NO_ACTIVE_TASK` 输出 |
| compile | **PASS** | `compileall 通过（loop_core, src, scripts, hooks, tools）` |
| guard_health | **PASS** | `guard 健康 PASS（5 个 guard 全部存活）` |
| slo_gate | **PASS** | `error budget within limits — release allowed (consumed 5.0 / 100.0 units, remaining 95.0)` |
| key_tests | **PASS** | `关键测试子集通过（test_version_consistency + test_loop_core）` |

最终输出 `[release] check 通过（质量门前置全部 PASS）`，**exit 0** —— **6/6 全 PASS**，
修复前 idle 稳态 1/6 FAIL（validate_state 阻断）场景最终闭环。

### 2. validate_state 直接验证

命令：`C:/Python312/python.exe .zcode/tools/validate_state.py .` → **exit 3**

- 输出：`[loop-governance] project_root: C:\Users\Administrator\ZCodeProject\loop-engine`、
  `[loop-governance] phase: S6-delivery`、`[loop-governance] current_task_id: none`、
  `[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：state 无活动任务，
  等待任务发起；state 不可开工）`
- **无 `[ok] state is usable`、无 `[error]` 行** —— idle 合法阻塞态语义正确（T-0101
  定义未变：真实损坏仍 exit 2 fail-closed）

### 3. 全量回归

命令：`C:/Python312/python.exe -m pytest tests/ -q` → **3768 passed, 0 failed,
64 skipped, 12 xfailed**（204.55s，**exit 0**）

- 提交前 2 个"提交后自愈瞬时项"全部确认自愈：①
  `test_pyproject_version_matches_git_head`（pyproject 3.12.41 == HEAD 3.12.41）；
  ② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real`
  （主树 HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 已生成，
  idle 稳态由 F-01 生成真实路径）
- 3766 passed（提交前）+ 2 自愈 = **3768 passed**；日志 FAILED/ERROR 计数均为 0，
  无任何意外失败

### 4. test_manifest_t0095 专项 + manifest 引用实况

- `tests/test_manifest_t0095.py` 专项运行：**4/4 passed**（0.15s）——四个用例
  （`test_manifest_exists_and_handoff_reference_is_real` /
  `test_manifest_schema_and_entries` /
  `test_every_listed_file_exists_and_matches_fingerprint` /
  `test_manifest_passes_official_verifier`）全绿；全量回归中同 4 项亦全绿
- HANDOFF.md L124：`Evidence manifest: .ai/evidence/T-0102/evidence-manifest.v1.yaml.`
  → 引用路径**真实存在**（2616 bytes，manifest_id `EM-T-0102-EBC8C127`，
  files 10 条），**非 `.ai/evidence/none/`**
- `.ai/evidence/none/` 目录不存在；HANDOFF.md 中 "none" 仅 3 处展示值
  （L96/L102/L103：状态显示、`pending_gate_status`、`active_gate`），
  **零路径引用** —— F-01 idle 占位修复在提交后稳态 HANDOFF 上实证闭环

### 5. compile gate

命令：`C:/Python312/python.exe .ai/checkers/compile_gate.py .` → **pass**
（exit 0；compiled_files 68/68，failed_count 0，errors []）

### 6. 工作树状态（诚实记录）

- `git status` 仅 2 个测试运行副产物漂移：
  `.ai/evidence/T-0087/contract-planes/conformance-report.json`、
  `.ai/evidence/observability/guard-events.jsonl` —— 与 T-0101 提交后复验时完全
  相同的两个文件（测试自生成物），非 T-0102 范围、不阻断
- 本报告追加（本节）为唯一主动改动；T-0102 evidence-manifest 指纹为 create-only
  快照（同 T-0101 先例：提交后复验节追加不折入清单，官方校验器不受影响）

### 7. 结论

**工程全绿，可推送。** idle 稳态下 release check **6/6 全 PASS**（exit 0）、
validate_state 直接运行 **exit 3**（`[info] NO_ACTIVE_TASK`，无 `[ok]`/`[error]`）、
全量回归 **3768 passed / 0 failed**（提交前 2 个瞬时项全部自愈）、
test_manifest_t0095 **4/4**（HANDOFF 引用真实 manifest，无 `.ai/evidence/none/`
悬挂）、compile **68/68**。T-0102 裁决"待 git 提交 v3.12.41 后 idle 稳态终验"
的收尾条件全部达成：无未决项、无已知悬挂引用、无约束弱化，可推送发布。
