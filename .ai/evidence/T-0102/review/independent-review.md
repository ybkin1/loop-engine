# T-0102 独立审查报告 — handoff 生成器 idle 占位缺陷修复 + P3 观察项清零

- 审查人：independent-reviewer（独立子代理）
- 审查时间：2026-08-02
- 审查对象：T-0102（F-01 handoff idle 占位修复 + F-02 rollback rc=3 感知 + F-03 bump --title 透传 + F-04 版本 3.12.41）
- 方法：全部结论亲自复验（git worktree 隔离 idle 端到端 + 源码走读 + 边缘用例直测 + 定向/全量测试），不复述 developer 证据
- 基线：git HEAD `c737c3a`（v3.12.40）；主树含全部 T-0102 改动（未提交，T-0102 激活态）

## 裁决：GO

无 P1/P2 条件。2 项 P3 观察（developer 证据计数笔误；主会话完成流程事项清单），不阻断。

---

## 一、复验环境

- 主树（激活态 T-0102）：`validate_state.py .` → **exit 2**（`Continuity source drift: .ai/version-manifest.yaml` —— 版本载体已 bump 3.12.41 但 continuity source_manifest 未重算，fail-closed 如实拦截，属完成流程须重生成项，非缺陷）。
- 临时 idle worktree：`git worktree add ../loop-wt-review HEAD`（committed `current_task_id: null`，真 idle 态），复制修复后的 `continuity_producer.py` 入 worktree；验证完已 `git worktree remove --force`，主树状态文件零改动（worktree list 仅剩主树）。
- worktree 内 `repair_continuity.py` 修复 284 个漂移哈希（与 developer 记录一致）→ `validate_state.py` → **exit 3**（`[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态…）`）。

## 二、AC-01~AC-07 逐项

| AC | 结论 | 独立证据 |
|----|------|----------|
| AC-01 idle HANDOFF 无悬挂引用 + manifest 测试全绿 | **PASS** | idle worktree 端到端（repair_continuity → validate_state rc=3 → close_session）：HANDOFF L124 = `Evidence manifest: .ai/evidence/T-0101/evidence-manifest.v1.yaml.`（文件真实存在，mtime 序最新），`evidence/none` 出现 0 次；`.ai/evidence/none/` 目录不存在。`test_manifest_t0095` **4/4 passed**（含 F-01 核心断言 `test_manifest_exists_and_handoff_reference_is_real`，该断言在字节修复前即通过；另 2 项因 fresh checkout CRLF 化 + mtime 重置产生 3 个文件指纹偏差，按 manifest 记录值复原字节/mtime 后全绿 —— 纯检出环境噪声，与修复无关）。`_latest_manifest_path` 边缘直测：无 evidence 目录 → None；仅 `none` 目录含 manifest → 被排除返回 None；多任务取 mtime 最新；repair 文件优先语义保留 |
| AC-02 rollback rc=3 通过、rc=2 仍阻断 | **PASS** | 代码走读：`if result.returncode in (0, 3)` → 通过并标注"（idle 合法阻塞态 rc=3）"；else 分支原样（rc=2/1 阻断 + 输出诊断）；超时/异常分支未动。`pytest tests/test_operations.py -k "verify_state"` → **4 passed**（rc=0/3 → True；rc=2/1 → False，monkeypatch subprocess.run 断言真实）。rc=3 唯一性 grep：全库仅 `validate_state.py:450` 与 `audit_handoff.py:44` 两处 `return 3`（均为 T-0101 idle 白名单分支）—— 损坏（rc=2）不可能被误判为 rc=3 |
| AC-03 bump --title 透传 | **PASS** | `release.py bump --help` 含 `--title TITLE`。VERSION_CARRIERS 三元组仅 CHANGELOG 置 use_title=True，`_print_plan` 解包已同步；非 CHANGELOG 载体签名 `(content, version)` 不变。`test_bump_title_passthrough_to_changelog` 断言的是 **CHANGELOG 条目内容**（含"自定义标题"、不含缺省标题、旧条目保留），真实且通过（`test_release_bump.py` 共 **12 passed**）。CHANGELOG 头条目 = `## v3.12.41 (2026-08-02) — T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零` —— 与 bump 时 `--title` 传入值一致，F-03 闭环成立 |
| AC-04 全量回归 + compile | **PASS**（含 2 个已知瞬时失败，均在主树激活态） | 主树全量独立重跑：**3766 passed, 2 failed, 64 skipped, 12 xfailed（197.55s）**，与 developer 记录完全一致。2 失败逐一核因：① `test_pyproject_version_matches_git_head` —— pyproject=3.12.41 vs HEAD=3.12.40（F-04"先 bump 再提交"约定，提交后自愈）；② `test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real` —— 主树 HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 尚未生成（完成流程创建 manifest 后自愈；idle 稳态下由 F-01 渲染真实 manifest，worktree 已实证 4/4）。无意外失败。compile gate 独立重跑：**68 files, 0 failed, errors []** |
| AC-05 版本 3.12.41 与 HEAD 一致 | **PASS**（提交后成立） | 8 载体逐一实测 = **3.12.41**（pyproject.toml、CHANGELOG.md、loop_core/__init__.py、src/loop_engine/__init__.py、README.md、docs/06-delivery.md、.zcode-plugin/plugin.json、.ai/version-manifest.yaml）；`test_version_consistency` 7 passed。HEAD 尚为 3.12.40 —— 提交 subject 携带 v3.12.41 后 version_sync PASS（release.py check 当前仅 version_sync FAIL，输出与失败①同源） |
| AC-06 无约束被弱化 | **PASS** | 见第三节专项 |
| AC-07 无已知 OPEN-FINDING 悬挂 | **PASS**（修复已闭环，归档记录属完成流程） | handoff 占位 OPEN-FINDING → F-01 修复且独立实证（AC-01）；T-0101 遗留 P3 观察 #1（rollback idle 阻断）→ F-02、#2（bump --title）→ F-03，均有测试。idle 语义 finding 已由 T-0101 关闭（state notes 记录在案）。finding 文件的状态字段更新与 state.yaml 的 CLOSED 注记属任务完成流程收尾，审查时点修复已验证 |

## 三、约束零弱化专项（最高优先级）

1. **hooks/ 零改动**：`git diff --name-only HEAD` 全 21 个改动文件无任何 `hooks/` 路径（含 loop_enforcement hook、runtime_controller 均不在 diff）。
2. **validate_state / audit_handoff / governor_lib / continuity_auditor 零改动**：改动清单中不存在；rc=3 语义（T-0101 定义）原样未触碰。
3. **loop_core/ 零语义改动**：仅 `loop_core/__init__.py` 版本字符串 3.12.40→3.12.41（版本载体，见越界表）。
4. **rollback fail-closed 保持**：rc=2/1 仍阻断（测试实证 rc=2 → False）；放行集合严格为 {0, 3}，而 rc=3 全库唯一来源即 validate_state/audit_handoff 的 idle 白名单分支（grep 实证仅两处 `return 3`）—— 不存在"损坏被放行"路径；超时/异常分支原样（超时仍阻断，异常仍放行——后者为既有语义，非本次改动）。
5. **handoff 激活态逐字节不变**：改动仅新增 `active_task_id = action["current_task_id"]` 并在 Evidence 行用其替换原 `task_id`；激活态 `active_task_id` 非空 → 渲染 `f".ai/evidence/{active_task_id}/evidence-manifest.v1.yaml"`，与旧实现（`task_id` 为真实 id 时）逐字符相同。"Current Task" 展示行 `task_id = ... or "none"` 原样保留（格式不变）。
6. **idle 态永无 "none" 占位**：全库 grep `or "none"` 仅剩 2 处——continuity_producer.py:247（展示用，非路径）与 rollback.py:103（dry-run 展示串，非路径）；`evidence/none` 仅出现在 docstring。idle 渲染路径只有 `_latest_manifest_path(root)`（真实文件或 None）→ None 时渲染 `not available (no active task)` 文案，无悬挂引用。
7. **约束矩阵/C3/待决 gate 语义**：未触碰任何 gate 判定、forbidden_actions、fail-closed 门禁代码。

**结论：约束零弱化成立。**

## 四、越界核对表

改动文件共 21 modified + 2 untracked（.ai/tasks/T-0102.md、.ai/evidence/T-0102/），全部在范围内：

| 类别 | 文件 | 判定 |
|------|------|------|
| IN SCOPE 代码 | .zcode/tools/continuity_producer.py（`_latest_manifest_path` + render_handoff 拆 active_task_id）、scripts/rollback.py（`_verify_state` rc∈(0,3)）、scripts/release.py（VERSION_CARRIERS 三元组 + cmd_bump/_print_plan） | 合规（.zcode/、scripts/） |
| IN SCOPE 测试 | tests/test_operations.py（+4 verify_state 用例，monkeypatch 真实断言）、tests/test_release_bump.py（+title 透传用例 + 三元组连带维护） | 合规（tests/） |
| IN SCOPE 治理状态 | .ai/state.yaml、.ai/gates.yaml（G-T-0102-REQUIREMENTS 注册）、.ai/task_graph.yaml（T-0102 节点）、.ai/project_continuity.yaml（source_manifest 增量）、.ai/HANDOFF.md（激活态渲染）、.ai/tasks/T-0101.md（状态行）、.ai/evidence/observability/guard-events.jsonl（事件追加）、.ai/evidence/T-0087/conformance-report.json（仅时间戳）、.ai/version-manifest.yaml、.ai/evidence/T-0102/（新证据） | 合规（.ai/） |
| bump 载体 | pyproject.toml、CHANGELOG.md、docs/06-delivery.md（均 allowed_paths）；loop_core/__init__.py、src/loop_engine/__init__.py、README.md、.zcode-plugin/plugin.json | 合规（任务显式要求 bump 3.12.41；后 4 个不在字面 allowed_paths 列表，但为 test_version_consistency 强制校验的版本载体，纯版本字符串改动，且 T-0101（c737c3a）、T-0100 提交同模式先例成立——AC-05 版本同步的必然产物） |
| 零改动 | hooks/、agents/、.zcode/plans/、loop_core/runtime_controller.py、.zcode/tools/validate_state.py、.zcode/tools/audit_handoff.py、.zcode/tools/governor_lib.py、.zcode/tools/continuity_auditor.py、.zcode/tools/close_session.py、.zcode/tools/repair_continuity.py | 合规（diff 为空） |

**越界判定：无越界。**

## 五、修复真实性记录

1. **F-01（handoff idle 占位）**：根因链确认（L220 `or "none"` 展示占位 + L293 `if task_id` 保护被前置替换击穿 → idle 必然渲染 `none` 路径）。修复采用方案 A：idle 渲染**实际存在的最近真实 manifest**（mtime 序 + `none` 目录显式排除 + repair 文件优先），取不到渲染 `not available (no active task)`。worktree 端到端 + 边缘直测 + 主树回归三路实证（见 AC-01）。**真实修复，非表面处理。**
2. **F-02（rollback rc=3）**：修复前代码 `rc == 0` 才通过（T-0101 审查 P3 记录属实）；修复后 {0,3} 放行、标注 idle 合法态、rc=2/1 阻断；4 用例测试全绿。**真实。**
3. **F-03（bump --title）**：修复前 `lambda c, v: _update_changelog(c, v)` 丢 title（T-0101 审查 P3 记录属实）；修复后三元组透传，CHANGELOG 头条目标题 = `--title` 实传值（F-04 实机 bump 产物可核）。**真实。**

## 六、需主会话处理事项（完成流程清单，均非缺陷）

1. **连续性重算**：主树当前 validate_state **exit 2**（`Continuity source drift: .ai/version-manifest.yaml`——版本 bump 未折入 project_continuity source_manifest）。提交前须在主树跑 `repair_continuity.py` + `close_session.py`（worktree 已验证该流程；HEAD c737c3a 自带 284 个漂移哈希为 T-0101 已知遗留，一并修复）。
2. **T-0102 manifest 生成**：主树 HANDOFF 引用 `.ai/evidence/T-0102/evidence-manifest.v1.yaml` 未生成（完成流程创建后 test_manifest_t0095 自愈；idle 稳态已由 F-01 兜底全绿）。
3. **版本提交约定**：提交 subject 携带 v3.12.41（bump-before-commit），提交后 version_sync PASS、全量回归 0 failed 终态达成。
4. **归档**：OPEN-FINDING（handoff 占位）与 2 项 P3 在完成流程更新 finding 状态 + state notes（AC-07 归档记录）。

## 七、P3 观察（不阻断）

1. developer commands.md 记录 `test_release_bump.py` "13 passed"，实际收集 12 项（含新增 title 用例）全绿 —— 证据文档计数笔误，测试本身真实。
2. `.zcode-plugin/plugin.json` 等 4 个版本载体不在任务字面 allowed_paths 列表（先例 + AC-05 必需，详见越界表）—— 建议后续任务在 allowed_paths 中显式注明版本载体豁免，避免审查歧义。

## 八、关键结论

- 修复真实性：**全部亲自复验通过**（idle close_session 无 `none` 悬挂引用且引用真实文件、test_manifest_t0095 idle 稳态 4/4、rollback rc 0/3 放行 2/1 阻断、bump --title 透传至 CHANGELOG 内容、8 载体 3.12.41、compile 68/68、全量 3766 passed / 2 已知瞬时项）。
- 约束零弱化：**成立**（hooks/validate_state/audit_handoff/governor_lib/continuity_auditor/runtime_controller 零改动；rc=3 唯一性；激活态渲染逐字节不变；idle 全路径无 "none" 占位）。
- 越界：**无**。
- 裁决：**GO**。主会话按第六节完成流程清单收尾即可达成"0 failed + 无悬挂引用"终态。
