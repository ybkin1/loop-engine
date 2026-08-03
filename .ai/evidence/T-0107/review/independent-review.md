# T-0107 独立审查报告（independent-reviewer）

- 审查对象：T-0107 设计漏洞修复（P1 context_packager 专项 9 处 + P2 全量 11 项 + P3 首批 6 项 + hook 门禁）
- 基线：e083f7b（v3.12.43）→ 当前工作区
- 审查日期：2026-08-03
- 审查方式：fresh context，全部结论亲自复验（读代码 / 跑测试 / git diff / baseline worktree 对照），不依赖 developer 记录
- 结论：**CONDITIONAL_GO**（无 P0/P1 发现；3 项附条件均非 T-0107 代码引入，见第十节）

---

## 一、裁决

**CONDITIONAL_GO**

修复真实性全部复验通过：P1 专项 9/9、P2 11/11、P3 6/6 均为真实行为改变（非注释/摆设），方向全部为强化或等价，无任何约束弱化。hooks/ 仅 `loop_enforcement.py` 一个文件、恰好 3 处功能变更（D4-2、D4-7、D5-2 接线），其余 hook 文件零改动；治理内核零触碰。

附条件（全部为 closeout/环境性事项，不要求 developer 改动代码）：
1. 版本同步：pyproject 等载体已 bump 3.12.44，git HEAD 仍为 3.12.43（提交后消除，AC-06 瞬态）。
2. closeout 生成 `.ai/evidence/T-0107/evidence-manifest.v1.yaml`（test_manifest_t0095 瞬态）。
3. 环境相关预存在失败 `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed`（本机 localhost:3000/8000 被无关进程占用导致 `service.startup=PASS`；在 baseline worktree 复现，与 T-0107 无关）——建议登记为 KNOWN_ISSUE（环境依赖测试），但不阻塞本任务。

---

## 二、改动范围核对表 + 约束零弱化专项

### 全量改动文件（git diff e083f7b --stat，28 文件 + 3 新增）

| 文件 | 行数变化 | 归属 |
|------|---------|------|
| hooks/scripts/loop_enforcement.py | +94/− | D4-2/D4-7/D5-2（见专项） |
| loop_core/context_packager.py | +336 | P1 专项 9 处 |
| loop_core/context_controller.py | +188 | D5-1/D5-2（仅 I/O 与解析层） |
| loop_core/audit_ledger.py | +142 | D3-1/D4-5 |
| loop_core/async_jobs.py | +41 | D3-5 |
| loop_core/runtime_controller.py | +34 | D3-4 |
| loop_core/contract_verifier.py | +33 | D5-5 |
| loop_core/intent_router.py | +7 | D2-2 |
| tools/tool_constraint_check.py | +16 | D4-3（偏差文件，见第三节） |
| .zcode/tools/transaction_registry.py | +9 | D4-8（偏差文件，见第三节） |
| loop_core/front_matter.py（新增） | 新模块 | D5-2 共享契约解析 |
| tests/test_t0107_fixes.py（新增） | 44 测试 | 回归 |
| 版本载体 | pyproject/__init__×2/version-manifest/plugin.json/README/docs-06/CHANGELOG | bump 3.12.44 |
| .ai/ 治理簿记 | gates.yaml/HANDOFF/state/continuity/task_graph/KNOWN_ISSUES/guard-events/T-0106.md | 主会话 gate 与簿记，allowed |
| .zcode-plugin/plugin.json | 版本 | bump |

未改动核对（治理内核零触碰实证）：`gate_guard.py`、`hard_constraints.py`、`guard_health.py`、`state_machine.py`、`validate_state.py`、`context_loader.py`、`execution_ledger.py`（D3-3 属 T-0111，正确未动）、`observability.py`（D4-6 属 T-0111，正确未动）——以上均无 diff。

### hooks/ 专项（逐行 diff 核对）

`git diff e083f7b -- hooks/scripts/loop_enforcement.py` 全量 3 个功能 hunk，无其他改动：

1. **D4-7**（`_snapshot_hook_file_shas`，约 :83-100）：OSError 分支由静默 `continue` 改为首次告警 `HASH_SCAN_SKIPPED` + 进程内 `_HOOK_SHA_WARNED` 集合去重。返回的 shas 内容与逻辑不变，纯可见性增强。方向：等价/强化。
2. **D4-2**（`is_loop_mode_enforced`，约 :225-241）：state 读取异常 `return False`（fail-open）→ `return True`（fail-closed）+ `STATE_UNREADABLE` warning。FULL/STANDARD→True、LIGHTWEIGHT/缺失→False 正常路径逐字未动。方向：**强化**（符合门禁要求，未反向）。
3. **D5-2**（`load_task_contract` 重构，约 :263-349）：抽共享模块 `loop_core.front_matter.parse_task_front_matter`，退化环境回退本地同逻辑副本 `_parse_task_front_matter_legacy`。逐行比对：legacy 副本与原 e083f7b 版本解析逻辑**逐字节一致**（含 `line.strip()`、表格 `| mcp_allowed_tools` 形态、内联 `[a,b]` 形态），enforcement 语义零变化；front_matter.py 与 legacy 副本逐行一致（已逐行比对）。context_controller 侧为增量收敛（新增 mcp_allowed_tools 字段解析，消除分歧点）。方向：等价/收敛。

任务卡 allowed_paths 文案「hooks/ 仅 D4-2 + D4-7 两处」与 P2 范围 D5-2「enforcement 与 context_controller 统一调用」存在表面张力；但任务卡 P2 清单、AC-02（契约测试双路径一致）均明确要求 D5-2 接线，且 D5-2 在 P2 范围而不在「禁止动作」之列，故判定**在范围内**（记 P3 观察，见第九节）。

### fail-closed 语义核查

- D4-2 fail-open → fail-closed：强化 ✓
- D5-5 contract_verifier：PyYAML 语法错误不再 pattern 降级（返回空结构 + 告警）：fail-closed ✓
- D5-1 naive 降级：从静默降级改为告警 + schema 校验：可见性强化 ✓
- 无任何方向为弱化的改动 ✓

---

## 三、路径偏差文件专项审查

### 1. `tools/tool_constraint_check.py`（D4-3，P2）

- **范围判定**：D4-3 是任务卡 P2 全量 11 项之一（audit 编号明确），且为 KNOWN_ISSUES 登记项（T-0106 清单 [D4-3 P2]）。任务卡允许路径虽未单列该文件，但 P2 范围与 AC-02（P2 11 项全部修复）明确覆盖 → **判定在任务范围内**。
- **最小 diff**：+16/−，仅将两处 `except ValueError: pass` 改为 `phase_problems` 收集 + 返回新增 `phase_problems`/`phase_problem_count` 两个字段。原有返回键全部保留（兼容）。
- **gate 声明**：`.ai/gates.yaml` G-T-0107-REQUIREMENTS allowed_paths 已补 `tools/tool_constraint_check.py` ✓
- **行为验证**：测试 TestD43 两项通过；代码读核 confirm。

### 2. `.zcode/tools/transaction_registry.py`（D4-8，P3）

- **范围判定**：D4-8 是任务卡 P3 首批 6 项之一（audit 编号明确 + KNOWN_ISSUES 登记项 [D4-8 P3]）→ **判定在任务范围内**。
- **最小 diff**：+9/−，删除裸 `except:` 双重计算，统一 `Path(root) / ".ai/transaction_registry.yaml"`。`Path` 已导入（第 4 行），str 与 Path root 均正确。
- **gate 声明**：G-T-0107-REQUIREMENTS allowed_paths 已补 `.zcode/tools/transaction_registry.py` ✓
- **行为验证**：测试 TestD48 两项通过；`grep -c "except:"` = 0（无裸 except 残留实证）。

---

## 四、P1 context_packager 专项真实性（9 处逐项）

代码复读 `loop_core/context_packager.py` 全文件（379 行）+ 独立行为脚本复验：

| 编号 | audit 描述 | 复验结论（读代码/独立运行） |
|------|-----------|---------------------------|
| D1-1 | `[:1000]` 静默截断 → token 预算 + AC 节优先 | **真实**。`_format_task_card()`：按 `## ` 节解析（`_split_task_sections`），`TASK_CARD_TOKEN_BUDGET=1500`×4 字符 ≈6000 字符预算；`TASK_CARD_AC_HEADING_MARKERS`（可验证验收标准/验收标准）命中的节无条件完整保留（`test_ac_section_huge_never_cut` 实证：AC 超预算仍不切）；丢弃/截断追加 `…[task card truncated: N section(s) dropped, ...]` 标记。独立运行确认 AC-01 内容保留 |
| D1-2 | 角色文件截断无标记 | **真实**。`_slice_with_marker()` 追加 `\n…[truncated N chars]`；独立运行 product-manager 4000 字符文件确认标记出现 |
| D1-3 | extra_files `[:2000]` 无标记 | **真实**。`EXTRA_FILE_MAX_CHARS` 常量 + 同一标记函数；`test_extra_file_truncation_marked` 通过 |
| D1-4 | knowledge cases 中段截断 → 无效 JSON | **真实**。`_format_knowledge_cases()` 按 case 边界截断（尾部 case 丢弃），输出前缀可 `json.loads`；独立运行确认 3→2 case、前缀有效、`…[truncated 1 cases]` 标记 |
| D2-1 | 1000/2000/3000/5/3 字面量 | **真实**。全部集中为 5 个命名常量（TASK_CARD_TOKEN_BUDGET/EXTRA_FILE_MAX_CHARS/KNOWLEDGE_CASES_MAX_CHARS/MAX_EXTRA_FILES/MAX_KNOWLEDGE_CASES），代码无残留字面量切片 |
| D2-8 | git timeout 5/10/5 散落 | **真实**。4 个命名常量（GIT_TIMEOUT_DIFF_STAT/CODE/NAME/REV_PARSE），调用点全部引用常量 |
| D3-2 | MAX=15000 死护栏 | **真实**。`_add()` 内 `total` 真实累计；超限截断带标记；monkeypatch 预算=400 独立运行确认 `…[context truncated: total budget exceeded]` 出现且 footer 保留 |
| D4-1 | git diff `except: pass` 吞错 | **真实**。每命令独立捕获 → warning + `## Git Diff Status\n(diff unavailable: ...)` 占位节；非 git 目录独立运行确认占位节输出 + warning 日志 |
| D4-4 | (a) knowledge 损坏静默丢弃 (b) diff 无缓存 | **真实**。(a) JSONDecodeError → warning（测试 caplog 实证）；(b) `_DIFF_CACHE` 进程内缓存 key=(root, head, kind)，成功才入缓存、上限 64 条目清空重置；测试用双提交真实 git 仓库 + subprocess 计数实证第二次不重跑 |

备注：`_estimate_tokens()` 函数在模块内未被调用（预算以常量乘积实现），仅被外部 parity 测试引用——记 P3 观察（第九节）。

---

## 五、P2/P3 真实性（抽查表）

| 编号 | 严重度 | 验证方式 | 结论 |
|------|--------|---------|------|
| D2-2 intent_router 阈值 | P2 | 读代码：类常量 `MEDIUM_RISK_ESCALATION_MIN=3`，静态方法内 `IntentRouter.MEDIUM_RISK_ESCALATION_MIN` 引用；测试 3 因素升级/2 因素不升级 | 真实 |
| D3-1 audit_ledger 轮转 | P2 | 读代码：`_rotate_if_needed`（行/字节阈值 + N 档归档 .1~.N）；`_load` 按归档旧→新 + 主文件读入，链哈希跨文件延续；测试 12 条轮转后 reload verify valid、归档数有界 | 真实 |
| D4-2 hook fail-closed | P2 | 读代码 + 3 测试（缺失/损坏 state → True+告警；三态不变） | 真实（强化） |
| D4-3 phase_problems | P2 | 读代码 + 2 测试（非法 2 个 → count=2；合法 → 0） | 真实 |
| D5-1 naive 告警+schema | P2 | 读代码 `_yaml_load_checked`（YAMLError/ImportError 显式告警 + `_validate_naive_parse_result` 复用 state/gate schema + jsonschema 逐条校验）；5 测试全过（含"无 gate 不告警"、"主路径零告警"） | 真实 |
| D5-2 共享解析模块 | P2 | 读 front_matter.py 全文 + 与原 enforcement 解析器逐行比对 + 双路径契约测试 4 项通过 | 真实 |
| D3-4 journal 轮转 | P3 | 读代码 `_rotate_journal_if_needed`（5MB/3 档）+ 测试 monkeypatch 100B 后 .1 归档存在 | 真实 |
| D3-5 persist 轮转 | P3 | 读代码 `_rotate_persist_if_needed`（构造可配置）+ 测试 200B 轮转 + 归档有界 | 真实 |
| D4-5 corrupt_line_count | P3 | 读代码（逐行计数 + AuditIntegrity.corrupt_lines 字段）；尾部损坏行链有效+计数 1、中段损坏链断裂 2 测试 | 真实 |
| D4-7 HASH_SCAN_SKIPPED | P3 | 读代码 + 测试（告警一次 + 去重） | 真实 |
| D4-8 裸 except 删除 | P3 | 读代码 + 2 测试 + grep 实证 | 真实 |
| D5-5 fallback 收窄 | P3 | 读代码（仅 ImportError 降级 + `_parsed_by` 标注；语法错误 → 空结构 fail-closed）；3 测试 | 真实 |

---

## 六、测试真实性 + hook 套件复验

### tests/test_t0107_fixes.py（44 项）

独立重跑：**44 passed**（3.46s）。抽查 ≥10 项断言实质性（非空断言）：
- `test_ac_section_not_cut_when_beyond_old_1000_limit`：断言 AC 内容在且无截断标记（复现场景）
- `test_ac_section_huge_never_cut`：700 行 AC 超预算仍完整 + 非 AC 节被丢
- `test_knowledge_cases_truncated_to_valid_json`：`json.loads` 前缀（语法完整性断言）
- `test_diff_cache_reuses_same_head`：真实 git 仓库 + subprocess 调用计数（first>0 且第二次相等）
- `test_total_budget_enforced`：monkeypatch 预算 + 超限标记 + footer 保留
- `test_rotation_preserves_chain_integrity`：12 条目轮转 → reload → verify valid
- `test_corrupt_middle_line_breaks_chain`：篡改行 → valid=False
- `test_state_unreadable_fails_closed`：缺失 state → True + STATE_UNREADABLE
- `test_dual_path_enforcement_vs_controller`：同一任务卡两路径解析相等
- `test_yaml_syntax_error_warns`：PyYAML 语法错误 → 显式告警
- `test_import_error_uses_pattern_fallback`：_parsed_by 标注 + 结构重建断言
- `test_no_bare_except_remains`：源码级断言（"except:" 不在文件内）

以上均为行为级断言，无空断言。

### hook 套件独立重跑（D4-2/D4-7 改动后必全绿）

`test_enforcement.py + test_hooks.py + test_role_isolation.py + test_enforcement_hub.py + test_hook_guards.py + test_hook_integration.py`：**177 passed**（24.81s），与 developer 声明一致。

### 编译

11 个改动/新增 Python 文件 `py_compile` 全部通过。

---

## 七、全量回归独立结果

`C:/Python312/python.exe -m pytest tests/ -q`（含全部子目录，未排除）：

**3909 passed, 64 skipped, 12 xfailed, 3 failed**（175.54s）

三个失败逐一独立判定：

1. `test_release.py::test_pyproject_version_matches_git_head` — **closeout 瞬态**：pyproject 3.12.44 vs git HEAD 3.12.43，提交后消除（AC-06 预期）。
2. `test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real` — **closeout 瞬态**：HANDOFF.md 引用 `.ai/evidence/T-0107/evidence-manifest.v1.yaml`，该文件由 closeout 生成，当前不存在。
3. `test_deployment_quality_checker.py::test_runtime_report_is_simulated_and_fail_closed` — **预存在环境依赖失败，与 T-0107 无关**：
   - 失败断言：`all(c["status"] != "PASS" or c["id"] == "artifact.manifest")`；实际 `service.startup → PASS`。
   - 根因：`scripts/runtime_delivery_gate.check_service_startup` 探测 localhost:3000/3001/8080/8000 任一可达即 PASS；本机 3000（PID 22796）与 8000（PID 42732）被无关进程占用（netstat 实证）。
   - **基线对照实证**：`git worktree add` 到 e083f7b（零 T-0107 改动）重跑同一测试 → **同样失败**（1 failed, 3 passed）。测试与脚本两个文件在 T-0107 中均零 diff。
   - developer「0 failed」声明在其运行时刻（端口未被占用）成立，非虚假报告。
   - 建议：登记为 KNOWN_ISSUE（环境依赖测试），与本任务解耦。

结论：**无任何 T-0107 引入的回归**。

---

## 八、KNOWN_ISSUES 核对

- **12 条移入 Recently Closed**：D1-1(P1) + D1-2/D1-4/D2-1/D2-2/D3-1/D3-2/D4-1/D4-2/D4-3/D5-1/D5-2（P2×11）共 12 条，全部在 Recently Closed 区块，注明「T-0107 修复，v3.12.44」，编号与 audit 权威编号一一对应，无缺项无多余。
- **Open 区保留项合理**：`session-source-disabled`（主会话新登记，T-0112 候选，任务卡明确要求不并入本任务）+ 两条既有项（seeded_defects 手动验证、E2E lab fixture skip）——保留合理。

---

## 九、发现清单

**P0**：无。

**P1**：无。

**P2**：
1. `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed` 在本机环境失败（localhost:3000/8000 被占用 → `service.startup=PASS`）；已实证为 e083f7b 预存在、环境依赖、与 T-0107 无关。AC-05「0 failed」在当前环境字面不成立，需登记为独立 KNOWN_ISSUE 或文档化排除。
2. AC-06（版本==HEAD）与 test_manifest_t0095 依赖 closeout 动作（提交 + 生成 manifest），提交前为已知瞬态。

**P3**：
1. `context_packager._estimate_tokens()` 模块内未被调用（token 预算以常量乘积实现，函数仅被 tests/test_context_compression.py 的 parity 测试引用）——轻微死助手，建议下轮清理或删除。
2. `AuditLedger.corrupt_lines` property docstring 写「仅主文件内行号」，实现实际收集所有文件（含归档）的行号且不标识来源文件；日志按文件警告故可观测性保留——文档与实现轻微漂移。
3. 任务卡 allowed_paths 中 hooks 条目文案「仅 D4-2 + D4-7 两处」未提 D5-2 同文件接线，与 P2 范围存在表面张力（已判在范围内）；建议后续任务卡文案与 P2 清单对齐。
4. hooks 对 `loop_core.front_matter` 的导入用 `except Exception`（宽捕获）——有本地同逻辑副本兜底 + 告警，属刻意韧性设计，可接受。

**环境观察（非本任务产物）**：untracked `.qoder/better-harness/` 目录（Better Harness canvas 运行产物，非代码）。

---

## 十、总结论

- 裁决：**CONDITIONAL_GO**
- P1 专项 9 处：全部真实（代码行为复验 + 独立脚本 + 测试）
- P2 11 项：全部真实；P3 6 项：全部真实
- hook 专项：`loop_enforcement.py` 单文件、恰好 3 处功能变更（D4-2 fail-closed 强化 / D4-7 哈希跳过告警 / D5-2 共享解析接线），其余 hook 文件零改动；D4-2 为纯强化方向
- 治理内核零触碰实证成立；2 个写路径偏差文件均在任务卡 P2/P3 范围 + KNOWN_ISSUES 登记项，最小 diff，gate 已补路径声明
- 测试：44 新测试通过、hook 套件 177 通过、全量 3909 通过 / 3 失败（2 个 closeout 瞬态 + 1 个预存在环境依赖，均非本任务引入）
- 附条件：提交完成版本同步（3.12.44==HEAD）、closeout 生成 evidence-manifest、将环境依赖测试失败登记为 KNOWN_ISSUE（不阻塞）
