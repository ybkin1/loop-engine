# T-0111 独立审查报告（independent reviewer）

- 审查对象：T-0111 修复器治理 + 臃肿全景清理验证（排布收官）
- 审查基线：f3553aa（v3.12.47，T-0110 提交）→ 当前工作区
- 审查日期：2026-08-03/04
- 审查方法：全部结论亲自复验（git diff / 代码阅读 / 独立测试重跑 / 独立计算），不复述 developer 证据
- 审查范围：任务卡 8 项 AC + 硬约束；设计依据 design-common-weakness.md 3.2-3.4

---

## 一、裁决

# GO（附 2 项 closeout 条件，无 P1/P0 发现）

裁决依据：
- 硬约束三零全部实证成立（hooks/ 零改动、repair_continuity.py 零改动、零删除）；
- 治理内核判定零触碰（validate_state/close_session 仅旁路事件写入，diff 核对 + AC-03 测试双证）；
- 8 项 AC 中 AC-01~05 独立测试全绿；AC-06 全量回归 6 failed 全部落入"已登记/瞬态"类别（3 项登记基线项 + 1 项 bump 前版本同步 + 2 项 bump 瞬态未登记项，均非代码缺陷，closeout 自愈）；AC-07 版本载体一致（3.12.48），git HEAD 同步待提交；AC-08 成立。

closeout 条件（P2，见发现清单）：
1. 提交后必须执行 continuity 重同步（repair 全量模式或等价机制），否则 `test_t0108_fixes` 2 项保持红；
2. 主会话 closeout 生成 `.ai/evidence/T-0111/evidence-manifest.v1.yaml`（HANDOFF 引用自愈）。

---

## 二、改动范围 / 约束零弱化专项（最高优先）

### 2.1 diff 全量（f3553aa → 工作区）：24 文件，+963/-80

| 类别 | 文件 | 判定 |
|---|---|---|
| 产品代码 | loop_core/observability.py、governance_metrics.py、execution_ledger.py | 任务卡 allowed_paths ✓ |
| 治理工具 | .zcode/tools/validate_state.py、close_session.py（仅事件写入） | 任务卡 allowed_paths ✓ |
| 版本载体 | pyproject.toml、CHANGELOG.md、README.md、docs/06-delivery.md、loop_core/__init__.py、src/loop_engine/__init__.py、.zcode-plugin/plugin.json、.ai/version-manifest.yaml | AC-06/07 bump 3.12.48 必需载体（与 T-0110 惯例一致，全链路一致 = 3.12.48） |
| 状态/证据 | .ai/gates.yaml（新增 G-T-0111）、task_graph.yaml、state.yaml、HANDOFF.md、project_continuity.yaml（哈希同步）、guard-events.jsonl（+173 运行事件）、golden-before.json（+6 dir() 行） | .ai/ 允许路径 ✓ |
| 测试 | tests/test_repair_governance.py（新增 20 项）、test_execution_ledger.py（+7 项）、test_observability.py（+4 项）、test_t0109_f2_write_convergence.py（+1 行登记） | tests/ 允许路径 ✓ |

### 2.2 三零约束（独立验证）

- **hooks/ 零改动**：`git diff --name-only f3553aa | grep hooks/` 空（exit 1）✓
- **repair_continuity.py 零改动**：未出现在 diff 名单；测试只读调用其 `repair_continuity()` ✓
- **零删除**：`git diff --diff-filter=D` 与 `--diff-filter=RC` 均空 ✓（死工具复核为纯文档，无删除执行）

### 2.3 治理内核零触碰 / fail-closed 不变

- validate_state.py diff：仅新增 `_record_repair_event` 旁路写入（try/except 吞错），三个写入点均落在**既有分支结构内**（fixed>0→PASS / fixed=0→FAIL / 异常→FAIL），无任何判定/exit code/控制流变更；
- close_session.py diff：`result = repair_continuity(...)` 返回值仅用于事件字段（`result.get('fixed', 0)`，repair_continuity 恒返回含 fixed 的 dict，已读源码确认）；except TypeError/Exception 分支保留原 pass 语义；
- 非 repair 模式 SOURCE_DRIFT exit 2：`TestFallbackBoundaries::test_non_repair_mode_source_drift_still_exit_2` 独立重跑绿（exit 2 + 零 repair 事件 + 清单未被修复）✓

---

## 三、逐项真实性（审查重点 2-6）

### 3.1 修复器度量真实性（重点 2）— PASS

- **CHECK_REPAIR 事件**：observability.py 新增 `CHECK_REPAIR = "repair"` 常量 + 注释；validate_state/close_session 写入与 GuardCheckEvent 同 schema，loop_core 不可导入时降级为等价 JSONL 追加（fallback 路径字段集一致）；
- **向后兼容**：`load_guard_events` strict-parse 不校验 check_type 值（源码确认）；`guard_anomaly_rates` 按 check_type 计数（未知类型不报错）。独立重跑 `test_repair_events_loadable_by_existing_consumers` 绿 + 消费者集 150 passed；
- **判定零改动**：git diff 逐行核对，两工具仅加事件写入语句 ✓；
- **MetricsReport 零改动**：`build_report/render_markdown/to_dict` 无 diff；golden-before.json 仅 `dir_snapshots.governance_metrics` +6 行（CHECK_REPAIR/_REPAIR_FIXED_RE/classify_repair_event/re/repair_classification/repair_trigger_rate），其余逐字节一致——与 fixes/repair-metrics.md 声明完全吻合；golden 逐字节等价测试（test_t0110_batch_b1）独立重跑绿；
- **D4-6 读侧损坏行计数**：`_read_file` 逐行容错（计数 + warning + 跳过，保留前缀后缀），`summary()` 新增 `read_corrupt_lines` 键（加性，GuardEventRecorder.summary 的既有消费者仅 tests，无 schema 严格校验——grep 确认）；4 项测试独立重跑绿；当前真实文件 3827 行全部可解析（bad=0）。

### 3.2 归类报告真实性（重点 3）— PASS

- **规则与设计一致**：`classify_repair_event`：fixed>0→unstable_generation；result=FAIL 且 fixed=0→over_strict；其余→benign。与 design-common-weakness.md 3.3 逐条对应 ✓；
- **报告样本分布核对**：独立计算报告第 3 节 5 条样本 → `{"over_strict": 2, "unstable_generation": 1, "benign": 2, "over_strict_runs": 1}`，与报告声称的实测输出**逐字节一致** ✓；over_strict_runs 连续段逻辑（FAIL,FAIL,benign,FAIL → runs=1）测试绿；
- **报告制不自动阻断**：grep 全仓（含 .zcode/ hooks/ tools/ scripts/ agents/）——`classify_repair_event/repair_classification/repair_trigger_rate` 零生产代码消费者（仅定义处 + tests）→ 无任何 gate 判定路径接入 ✓；
- **基线数据真实性**：当前 guard-events 0 条 repair 事件（grep -c = 0）、trigger_rate=0.0 结论成立；报告"3719 总事件"为生成时点快照（现 3827 行），结论不受影响（见 P3-3）。

### 3.3 兜底边界（重点 4，AC-03）— PASS

`TestFallbackBoundaries` 5 项独立重跑全绿：
- dynamic_only 不重算 semantic_sha256 且不重算 source_sha256（哈希值不变可观测断言）；
- 全量模式对照组 source_sha256 变化（"不重算"为可区分行为）；
- 非 repair SOURCE_DRIFT exit 2 + 零 repair 事件 + 清单未被修复；
- dynamic_only 唯一写文件 = project_continuity.yaml（原子写语义保持）。

### 3.4 D3-3 / D4-6 真实性（重点 5）— PASS

- **归档保留 N 份**：`max_archives` 构造参数（默认 DEFAULT_MAX_ARCHIVES=3），checkpoint 后保留最近 N 份删除最旧（OSError 吞错）；`TestArchiveRetentionAndContinuity` 7 项独立重跑全绿（保留/prune/默认 3/链延续/篡改最旧/篡改最新/链空洞）；
- **跨归档链延续**：活动文件空时 `_last_chain_hash` 从最新归档尾续接；`verify_chain` 从归档尾起算；`verify_archive_chain` 全保留历史验证（最旧锚条前驱已清理的文档化边界 + `test_oldest_retained_anchor_link_is_bounded` 明确覆盖）；`test_auto_checkpoint_archives_and_resets` 既有用例保持绿；
- **排序 bug 修复核对**：`_archives()` 显式解析 (ts, seq) 排序键（字符串序 "-n" 文件 < 无后缀文件的颠倒缺陷已修），源码确认 ✓；
- **D4-6**：4 项独立重跑绿（主文件损坏计数/中段损坏后缀保留/归档内损坏计数/summary 上报）。

### 3.5 死工具复核（重点 6）— PASS

- **A 组抽查 2 项**（tool_quality_gates / tool_evidence_chain）：全仓 grep 实证 0 代码 importers——仅 server.py 注释（"原 ...run()"内联说明）、capability manifest 元数据、tests 冒烟 import、deep_probe_v35 字符串表、docs 目录；loop_enforcement_constants.py:33 与 loop_core/evidence_chain.py:472-474 均为注释非 import ✓；
- **run_\* 保留理由**：server.py:38 `_run_quality_gates` → 子进程目标 `agents/quality-engineer/scripts/run_quality_gates.py`（LIVE，quality_report.json 消费链）；server.py:58 `_run_security_scan` → `agents/security-engineer/scripts/run_security_scan.py`（LIVE，security_report/v1 契约）——均源码确认，保留结论成立 ✓；
- **零删除执行**：diff-filter=D 空 + B/C 组定性（tool_task_queue 死壳 / tool_eval 等独立 CLI 待用户确认 / scripts legacy 收敛建议）与删除建议汇总一致，全部交用户独立 gate，本任务未执行任何删除 ✓；
- **注册表终态**：`all_tool_names()` 36 = tools/*.py 36 双向零缺口（developer 实测 + test_t0109_f5 持续断言，消费者集重跑绿）。

---

## 四、测试 + 全量回归独立结果

### 4.1 独立重跑（C:/Python312/python.exe）

| 套件 | 独立结果 | developer 声称 | 一致 |
|---|---|---|---|
| tests/test_repair_governance.py | 20 passed | 20 passed | ✓ |
| tests/test_execution_ledger.py + test_observability.py | 59 passed | 79（含 governance_metrics 等） | ✓ |
| 消费者集（metrics/b1 golden/manifest/doc-link/guard_health/f5/batch3/self_audit/f2 收敛） | 150 passed, 2 failed | 139 passed, 3 failed（含 deployment） | ✓（差异=运行集不同） |
| 编译 | 8 个改动文件 py_compile COMPILE_OK | COMPILE_OK | ✓ |
| 归类样本独立计算 | over_strict=2/unstable=1/benign=2/runs=1 | 报告声称一致 | ✓ |

### 4.2 全量回归独立结果（`pytest tests/ -q`，4m20s）

**4168 passed / 6 failed / 64 skipped / 12 xfailed**（总数 4174，与 developer 的 4170+4 一致）

6 项失败逐项独立判定：

| 失败项 | 类别 | 判定 |
|---|---|---|
| test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed | 已登记基线（本机 localhost:3000/8080 服务可达） | 环境项，非缺陷 |
| test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real | 已登记瞬态（T-0111 evidence-manifest 未生成，closeout 自愈） | 非缺陷（但"基线即失败"表述不实，见 P3-1） |
| test_release.py::test_pyproject_version_matches_git_head | bump 前瞬态（pyproject=3.12.48 vs HEAD=3.12.47） | 提交后自愈（AC-07 语义） |
| test_t0108_fixes.py::test_validate_state_still_passes_on_repo / test_existing_verdicts_unchanged_on_repo | **未登记** bump 瞬态：`.ai/version-manifest.yaml` continuity 哈希陈旧（存储 54936535 vs 实际 E93E4F6E，独立计算确认） | 非代码缺陷；closeout 提交 + continuity 重同步后自愈（见 P2-1） |
| test_t0109_f5::test_hooks_only_whitelist_file_changed | 已登记状态断言（hooks/ vs HEAD 为 0 改动） | 非缺陷（"提交后恢复"预期不实，见 P3-2） |

验证说明：两个 t0108_fixes 失败根因为版本 bump 后 continuity 未同步（gates.yaml/task_graph.yaml 条目已同步、version-manifest.yaml 未同步）——与"version bump 前"登记类别同性质，非 T-0111 代码缺陷；validate_state 判定行为本身正确（输出为预期的 SOURCE_DRIFT 错误）。

---

## 五、发现清单

**P0/P1：无**

**P2（2 项，closeout 行动项，不阻断 GO）**
1. **t0108_fixes 2 项失败未登记 + 证据数字过期**：commands.md 全量回归记录"4170 passed / 4 failed"为 bump 前快照；当前工作区（bump 后）为 4168/6，其中 2 项 `test_t0108_fixes`（validate_state on-repo 判定）因 `.ai/version-manifest.yaml` continuity 哈希陈旧而红。closeout 必须执行 continuity 重同步（repair 全量模式或等价），否则提交后仍红。
2. **AC-07 待提交完成**：版本载体全链路 3.12.48 已一致，但 git HEAD 仍为 f3553aa（3.12.47）——`test_release` 版本同步测试在提交前保持红，属预期状态，提交后复验。

**P3（3 项，证据文档准确性）**
1. commands.md 遗留事项 #1 称 manifest 测试"git stash 验证基线即失败"——**不实**：基线 f3553aa 下 HANDOFF.md 引用 T-0110 evidence-manifest（存在），该测试通过；当前失败由 T-0111 进行中 HANDOFF 引用（T-0111 manifest 未创建）导致，属瞬态而非基线失败。
2. commands.md 遗留事项 #2 称 hooks 白名单断言"提交本任务后恢复"——**预期错误**：T-0111 不触碰 hooks/，提交后 `changed=[] != [loop_enforcement.py]` 仍红；该状态断言仅在"存在未提交的 loop_enforcement.py 改动"时成立（T-0112 若触碰则恢复）。
3. repair-classification-report 基线数字为快照：报告记"总事件 3719"，当前文件 3827 行（+108 运行事件）；报告日期 2026-08-03 与第 3719 行时间戳（2026-08-04T01:29Z）存在时差。核心结论（0 repair 事件 / rate 0.0 / 读侧损坏 0）对当前文件仍然成立（独立复验：grep 0 条 repair、3827 行全部可解析）。

---

## 六、总结论

T-0111 独立审查 **GO**。8 项 AC 全部达成（AC-07 提交后终验），硬约束三零 + 内核零触碰 + fail-closed 语义不变全部实证成立；修复器度量/归类/兜底边界/D3-3/D4-6/死工具复核均为真实实现且测试独立复验通过；全量回归 6 项失败全部落入已登记或瞬态类别，无一为代码缺陷。P2 两项为 closeout 行动项（continuity 重同步 + 版本提交终验），P3 为证据文档表述/快照准确性修订建议，均不阻塞验收。
