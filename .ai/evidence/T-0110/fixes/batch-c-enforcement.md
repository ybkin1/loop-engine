# T-0110 批 C — hooks/scripts/loop_enforcement.py 行为等价拆分验收（最高风险项）

日期：2026-08-03
执行：developer 子代理（批 C，T-0110 批序最后）
基线：工作树 = HEAD v3.12.46 + 批 A（常量表）+ 批 B-1/B-2（loop_core 拆分）+ 本批
拆分前：loop_enforcement.py **2115 行**（任务卡标注 2059，T-0107/T-0083 后增长）
验收方法：**golden 快照先行**（拆分前捕获 → 拆分后重放 → 逐字节对比）+ 自愈
re-exec 实测 + hook 全套件拆分前后基线对比

---

## 一、拆分边界表（按 design-common-weakness.md §1.1 + 任务卡批 C）

| 外提内容 | 原位置（拆分前行号） | 目标新模块 | 实现 |
|---|---|---|---|
| 契约解析：`_SHARED_FRONT_MATTER_PARSER`/`_front_matter_parser`/`_parse_task_front_matter_legacy`/`load_task_contract`/`_task_mcp_allowed_tools` + `_read_task_max_files`（任务卡 max_files 字段） | :263-362, :729-753 | `loop_contract_parser.py`（155 行，仅依赖 Path + 可选 loop_core.front_matter） | 逐字迁移；T-0107 产物为 `loop_core/front_matter.py`（任务卡所称"T-0107 已存在"的共享解析器），本模块为 hooks 侧接线封装（共享优先 + 本地同逻辑副本兜底），以 loop_enforcement 既有行为为准 |
| 命令/路径判定 + 子进程执行：`_PYTHON_INTERPRETER_RE`/`_SIDE_EFFECT_CAPABLE`/`_is_python_interpreter`/`_msys_to_windows`/`_script_in_governance_dirs`/`_split_command_segments`/`_is_governance_tool_segment`/`_is_safe_cd_segment`/`_is_safe_display_segment`/`_command_references_outside` + `is_in_task_scope`/`check_diff_scope` | :425-630, :633-724, :1627-1653 | `loop_command_utils.py`（339 行，依赖 hook_common + 常量表 + _hook_bash） | 逐字迁移；`check_diff_scope` 的 git diff `timeout=30` 接线 `COMMAND_TIMEOUT_SECONDS`（批 A M-3 唯一消费者）、`max_diff_files` kwdefault 接线 `MAX_DIFF_FILES`（值 15 不变）；`is_in_task_scope` 随迁避免循环导入（check_diff_scope 依赖）——任务卡"子进程执行辅助类（subprocess timeout 等，接入批 A 常量）" |
| 常量表：`EXIT_PASS`/`EXIT_BLOCK`（M-1）、`_REEXEC_MAX`、`GOVERNANCE_EXEMPT`/`MINIMAL_METADATA_READ`/`MAIN_THREAD_ALLOWED` | :172-173, :80, :181-224 | `loop_enforcement_constants.py`（批 A 已建） | 壳改引常量表（`REEXEC_MAX as _REEXEC_MAX` 别名保持 dir() 名）；`GOVERNANCE_TOOL_DIRS` 例外：**壳保留 tuple 字面量双登记**（T-0109 AC-05 门禁 AST 断言要求源文件字面量，一致性测试锁定壳值 == 常量表值） |
| gate 证据检查：`check_quality_gate_evidence`/`_self_review_block_enabled`/`trace_review_evidence_isolation`（T-0067 接线）/`check_delivery_gate_evidence`/`check_runtime_quality_gate`/`_import_loop_core_gate`/`check_slo_gate_evidence`/`check_second_failure_gate_evidence`/`_PHASE_EVIDENCE_FILES`/`_check_phase_evidence_file`/`check_security_gate_evidence`/`check_phase_gate_enforcement` | :798-1624 | `gate_evidence_checks.py`（709 行，依赖 hook_common + 可选 loop_core） | 逐字迁移（纯函数返回 (bool, str)；T-0078 P0 真实性校验、T-0093 SLO fail-closed、T-0097 second-failure、B6 自审阻断语义全保持） |
| **保留在壳（不拆的主流程语义）** | — | `loop_enforcement.py`（2115 → 1052 行壳） | main() 入口控制流 + 自愈 SHA+重执行机制（`_snapshot_hook_file_shas`/`_read_hook_input`/`_hook_files_changed_since_load`/`_reexec_with_fresh_code` + main 内 :1602-1613 调用链）+ fail-closed 裁决链（runtime projection 三态/MCP 白名单/DISPATCH/IDENTITY/GOVERNANCE_CONTROLLER_ONLY/HardConstraints 整合/阶段门禁/task scope/diff 范围）+ 治理写读判定 `is_governance_write`/`is_minimal_metadata_read`/`is_governance_tool_command` + B7 context builders（`build_hard_constraints_context` 等 4 函数）+ C11 计数（3 函数）+ `is_loop_mode_enforced`/`is_legacy_synthetic_hook_fixture` |

**自愈扫描集扩展说明**（对"机制绝对不动"的解释）：`_snapshot_hook_file_shas`
的文件清单追加 4 个拆分模块名——机制逻辑（sha 快照 → 磁盘变更检测 → 环境变量
计数防循环 → os.execv 重执行一次）逐字未动；拆分后判定逻辑分布到新模块，扫描集
不扩展则"改 gate_evidence_checks.py 本地文件不触发 re-exec"（自愈保证回退）。
扩展仅是文件集接线，AC-03 实测 re-exec 恰一次、判定与新代码一致（
tests/test_t0110_batch_c.py::TestSelfHealReexec 固化）。

**logger 名前缀说明**：随函数迁移，`logging.getLogger(__name__)` 派生名变化
（脚本态 `__main__` → `gate_evidence_checks` 等）。golden stderr 归一化规则把
hook 自家 logger 前缀统一为 `[HOOK_LOGGER]`（消息文本仍逐字节断言；
`loop_core.*` 等外部 logger 名保持原样参与断言）。

## 二、新模块清单与壳规模

| 文件 | 角色 | 行数 |
|---|---|---|
| hooks/scripts/loop_contract_parser.py | 新增（契约解析，依赖图叶子方向） | 155 |
| hooks/scripts/loop_command_utils.py | 新增（命令/路径判定 + git diff 子进程执行，批 A 常量接线） | 339 |
| hooks/scripts/gate_evidence_checks.py | 新增（gate 证据检查 + B6/T-0067 证据校验） | 709 |
| hooks/scripts/loop_enforcement.py | 瘦身壳（2115 → 1052，re-export + 主流程保留） | 1052 |
| hooks/scripts/loop_enforcement_constants.py | 批 A 已建（本批接线 + GOVERNANCE_TOOL_DIRS 双登记） | 110 |
| tests/t0110_c_golden.py | 新增（golden 捕获助手，非测试收集） | ~600 |
| tests/test_t0110_batch_c.py | 新增（验收测试 14 项） | 340 |
| .ai/evidence/T-0110/golden/generate_golden_c.py | 新增（golden 生成器） | 44 |
| .ai/evidence/T-0110/golden/golden-c-before.json | 拆分前基线快照 | 49,858 B |
| .ai/evidence/T-0110/golden/golden-c-after.json | 拆分后重放快照 | 49,858 B |

依赖 DAG（无环）：`loop_enforcement_constants`（叶）← `loop_contract_parser`（叶，
可选 loop_core.front_matter）；`loop_command_utils`（依赖 hook_common/常量表/
_hook_bash）；`gate_evidence_checks`（依赖 hook_common）；壳 import 四模块。
静态断言：tests/test_t0110_batch_c.py `test_leaf_modules_never_import_shell` +
`test_new_modules_importable_standalone`。

## 三、golden 等价证据（硬门槛 1，比批 B 更严：语料最全）

**对比方法**：同一确定性捕获器（tests/t0110_c_golden.py）在拆分前后各运行一次，
产物为同一 dump_json 文本（sort_keys + ensure_ascii=False），`sha256` 逐字节对比。
捕获器运行两次自证确定性（byte-identical）；pytest 环境（PYTEST_CURRENT_TEST
已设置）下再跑一次仍 byte-identical。

- 捕获范围（hook 入口判定矩阵，**48 场景子进程实跑**（T-0116 措辞修正：golden-c-before.json 实际 48 个矩阵条目），stdin JSON +
  ZCODE_PROJECT_DIR，rc+stdout+stderr 全量）：
  - PASS 放行：非治理项目、LIGHTWEIGHT、治理写入 ×5、任务范围内写入
    （S4 基线）、git 提交/本地操作、编排（Agent 无 target）、只读治理引用、
    治理工具调用（validate_state + 主会话复合形态 `cd <root> && python … | tail`）、
    只读外部引用 EXTERNAL_READ、legacy synthetic fixture、S5/S7/S8 证据齐、
    S6 SLO 关闭、MCP 白名单命中+身份、GOVERNANCE_RECOVERY+controller、
    C11 首次写入
  - BLOCK：外部路径写入、任务范围外、STANDARD/FULL 无任务、S4 无门禁
    （C1/C2/C6 消息）、S4 无独立审查（C6）、S5 无安全证据/SECURITY BLOCKED、
    S6 SLO 数据不足 fail-closed、S7/S11 无证据、自审（B6）、runtime projection
    三态（SETUP_INCOMPLETE/IDENTITY_REQUIRED/GOVERNANCE_CONTROLLER_ONLY）、
    MCP 无任务/不在白名单、治理工具复合写段、python -c、只读项目探索、
    Read 业务文件、C11 第二次写入（max_files=1）
- 捕获范围（关键函数直接调用，**204 项**）：常量值、is_loop_mode_enforced ×5
  （含损坏 state fail-closed）、is_legacy_synthetic_hook_fixture ×2、
  is_governance_write ×9 / is_minimal_metadata_read ×8 / is_in_task_scope ×5、
  load_task_contract ×4（内联/表格/普通/缺失）、_task_mcp_allowed_tools ×4、
  legacy 解析 ×4 形态、front_matter_parser 选择、_read_task_max_files ×4、
  C11 计数三函数、_split_command_segments ×10、_msys_to_windows ×4、
  _is_python_interpreter ×8、_script_in_governance_dirs ×11、
  _is_safe_cd_segment ×9、_is_safe_display_segment ×8、is_governance_tool_command
  ×33（含 cd 复合/绝对路径/root 缺失）、_command_references_outside ×6、
  check_diff_scope ×8（patch subprocess：越界/无变更/git 失败/缺失/超时/
  治理豁免/跳过 ×2）、gate 证据 ×38（quality 5 / delivery 7 / runtime 3 /
  security 5 / phase_gate 9 / _check_phase_evidence_file 6）、B6 自审 ×8、
  context builders ×6、SLO/second-failure 直调 ×3、_import_loop_core_gate ×1
- 两模块 dir() 全量快照（104 名）+ import * 公开面（55 名）同步入基线

**结果**：
```
golden-c-before.json sha256 = 47e105ce5d23bbf3eaa56e130f13ba64134fa68f2653e64dc4c457e87270ca61
golden-c-after.json  sha256 = 47e105ce5d23bbf3eaa56e130f13ba64134fa68f2653e64dc4c457e87270ca61
byte-identical: True（49,858 bytes）
```
（golden-after 在拆分后、ruff --fix 后各跑一次，两次均 byte-identical。）

## 四、re-export 完整性断言（硬门槛 4）

- `sorted(dir(壳)) == 拆分前 dir 基线`（**104 名零缺失零新增**，含私有名——
  覆盖测试直连导入路径：`_parse_task_front_matter_legacy`（test_t0107_fixes）、
  `_task_mcp_allowed_tools`/`load_task_contract`（test_mcp_capability）、
  `_HOOK_SHA_WARNED`/`_snapshot_hook_file_shas`（test_t0107_fixes）等）；
- `from loop_enforcement import *` 公开面 == 基线公开名（55 名）；
- 对象同一性 12 项：壳绑定即新模块定义对象（`LE.load_task_contract is
  LCP.load_task_contract`、`LE.check_diff_scope is LCU.check_diff_scope`、
  `LE.check_phase_gate_enforcement is GEC.check_phase_gate_enforcement`、
  `LE.trace_review_evidence_isolation is GEC.trace_review_evidence_isolation` 等）；
- 常量接线：`LE.EXIT_PASS is HKC.EXIT_PASS == 0`、`LE.GOVERNANCE_EXEMPT is
  HKC.GOVERNANCE_EXEMPT`、`LE._REEXEC_MAX == HKC.REEXEC_MAX == 1`；
- GOVERNANCE_TOOL_DIRS 双登记一致性（壳字面量 == 常量表）+ 壳源 AST tuple
  字面量断言（T-0109 AC-05 兼容）；
- 壳 import 面逐名保留：`importlib`/`subprocess` 等以 `# noqa: F401` 保留绑定
  （dir() 104 名保持）；pyproject.toml per-file-ignores 登记壳 F401（批 B 同模式）。

## 五、自愈 re-exec 实测（AC-03）

**场景构造**（tests/test_t0110_batch_c.py::TestSelfHealReexec，2 项）：
- 插件缓存侧：`base/cache/hooks/scripts/` 完整 hook 副本（旧代码）；
- 项目侧：受治理 fixture（FULL/T-0001/S4 + gates approved + review evidence）
  且 `root/hooks/scripts/` 为**本地新代码**（`loop_enforcement_constants.py`
  的 GOVERNANCE_EXEMPT 追加 `"extra/"`——仅改 fixture 副本，仓库零改动）；
- hook 从缓存副本运行（`Path(__file__)` 指向缓存），stdin 注入写入目标。

**实测结果**（手动取证与 pytest 固化一致）：
| 调用 | 目标 | rc | re-exec 次数 | 说明 |
|---|---|---|---|---|
| call-1 | extra/x.txt | **0** | **1** | 旧代码对 extra/ 无豁免 → 本应 SETUP_INCOMPLETE rc=2；re-exec 后新代码判定 rc=0（"本次仍按旧代码拦截"竞态消除）；同步后缓存 == 本地 |
| call-2 | docs/y.txt | 2 | 0 | 文件无变化不触发；范围外写入 fail-closed 保持 |
| call-3 | extra/z.txt | 0 | 0 | 新代码已加载，豁免路径直接放行 |
| 对照（无本地修改） | extra/x.txt | 2 | 0 | 本地 == 缓存 → 不触发，按旧代码判定（fail-closed 保持） |

**判定一致**：call-1 的最终 rc == 新代码直接判定（call-3 rc=0）；
call-2 的 rc == 旧/新代码一致判定（docs/ 范围外）——re-exec 前后判定一致。

## 六、hook 套件基线对比（拆分前后）

| 套件 | 拆分前基线 | 拆分后 | 说明 |
|---|---|---|---|
| hook 全套件（enforcement/hooks/role_isolation/enforcement_hub/hook_guards/hook_integration/path_guard/mcp_capability/bash_readonly/t0107_fixes/slo_gate/runtime_delivery_gate/cross_layer_safety/learning_loop/t0109_f2/t0109_f5/batch_a/guard_health/gate_guard_lifecycle/content_guard_semantic/ledger_guard/roles ×5） | **1229 passed, 60 skipped, 1 failed**（唯一失败 = T-0109 AC-08 陈旧期望 test_hooks_only_whitelist_file_changed：断言 hooks diff 恰为 loop_enforcement.py，T-0110 hooks 零触碰下为空） | **1273 passed, 60 skipped, 0 failed** | +44 = 批 C 14 项 + test_import_checker 等；AC-08 因本批恰改 loop_enforcement.py 一处（git diff HEAD -- hooks/ == [loop_enforcement.py]）恢复绿色（断言与本批改动巧合一致，非放水——git 实证） |
| 全量回归 `pytest tests/` | （批 B-2 记录 4126 passed + 1 deselected 环境依赖项 + 2 项工作树型失败） | **4141 passed, 64 skipped, 12 xfailed, 2 failed** | 2 failed 均为既有登记项：① test_manifest_t0095（HANDOFF 引用的 T-0110 evidence-manifest 于 closeout 生成，批 A/B 同款预存）；② test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed（批 B-1 已登记环境依赖项，批 B-2 以 deselect 处理，本批全量直跑复现） |
| 编译 compileall（触及文件 + hooks/scripts 全目录） | — | 0 错误 | — |
| lint ruff（我的 6 个文件） | — | All checks passed | test_hook_integration.py 余 4 项 N806（HC/Sev）为 git HEAD 预存，未触碰 |
| 循环导入 | — | 4 拆分模块零反向引用壳（静态断言 + 独立导入） | 叶子先拆模式 |

## 七、约束自查（任务卡硬约束）

| 约束 | 自查 |
|---|---|
| hooks/ 仅批 C 5 文件；其余 hook 文件零改动 | ✓ `git diff HEAD -- hooks/` 仅 `loop_enforcement.py`（其余 15 个 hook 文件零改动；4 个新增文件为 untracked 增量） |
| 治理内核判定零触碰（gate_guard/enforcement 判定语义/hard_constraints/guard_health/state_machine） | ✓ 未触碰任何治理内核文件；golden 判定语义逐字节一致（C1/C2/C6/SLO fail-closed 消息原样） |
| 不改变任何行为 | ✓ golden byte-identical（sha256 相同）；自愈机制与 fail-closed 裁决链逐字保留；自愈 re-exec 一次且判定一致；仅三处"接线"：常量引用（值逐一相同）、check_diff_scope timeout/max_diff_files 常量（值相同）、自愈扫描集扩展（机制语义不变） |
| 零删除 | ✓ dir() 104/104 全量保留（含私有名）；无任何符号消失 |
| 写路径仅限 hooks/scripts 指定文件 + tests/ + .ai/evidence/T-0110/ + pyproject.toml | ✓ 新增 3 模块 + 2 测试文件 + golden 3 文件 + 壳重写 + pyproject per-file-ignores 1 条；test_hook_integration.py 仅复制集改造（T-0110 批 C 夹具同步） |
| 版本文件不改 | ✓ 未触碰 |
| 循环导入规避 | ✓ 叶子先拆（constants → contract_parser/command_utils/gate_evidence_checks → 壳）；静态防线测试 + 独立导入 |

## 八、遗留事项

1. 全量回归 2 项失败（evidence-manifest closeout 引用、deployment_quality_checker
   环境依赖）为批 A/B 已登记项，非本批引入——留给主会话处置。
2. `GOVERNANCE_TOOL_DIRS` 双登记（壳字面量 + 常量表）为 T-0109 AC-05 AST 门禁
   的刻意例外：若未来该门禁改为读取常量表，可消解双登记（一致性测试
   test_governance_tool_dirs_dual_registration_consistent 守护）。
3. test_hook_integration.py 的 4 项 N806（HC/Sev 局部变量）为 git HEAD 预存
   测试风格债，未触碰（避免无关 diff）。
4. 本批未触碰的既有 hook 文件 lint 债（_hook_bash.py E701/E702/I001/F401 等）
   维持现状（hooks 零改动约束）。
