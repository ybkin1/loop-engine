# T-0108 实施命令记录（BH 融合·收敛期）

- 任务：T-0108（F4/F6/F7/F8/F2-1 五线 + P3×9：D1-3/7、D2-8、D4-4/10/11、D5-3/6/7）
- 执行：developer 子代理（ZCode）
- 日期：2026-08-03
- 基线：git HEAD `3e766ec`（v3.12.44）；bump 由主会话执行（3.12.45）

## 线 1：F6 上下文打包升级（接续 T-0107）

| # | 动作 | 命令/依据 | 结果 |
|---|------|-----------|------|
| F6-1 | 新增 `loop_core/context_budget.py`（token 预算计算器：字符→token 估算 + 按节优先级分配，AC/验收节优先保留 + truncated 标记；D1-3 截断标记结构化） | Write 工具 | DONE |
| F6-2 | `loop_core/context_packager.py` 截断工具/预算逻辑外提为 context_budget 委托（常量 re-export，行为逐字节一致） | Edit（TASK_CARD_* 常量改 import + 别名） | DONE |
| F6-3 | P3 显式覆盖确认：D1-3（extra_files `[:2000]` 截断带 `…[truncated N chars]` 标记）、D2-8（git timeout 5/10/5 → GIT_TIMEOUT_* 命名常量）、D4-4（knowledge cases 损坏 → logger.warning，不静默丢弃） | T-0107 已落地，T-0108 回归确认 | DONE |
| F6-4 | 回归：`pytest tests/test_t0107_fixes.py tests/test_context_compression.py` | 79 passed | DONE |

## 线 2：F4 文档路由

| # | 动作 | 命令/依据 | 结果 |
|---|------|-----------|------|
| F4-1 | 新增 `.ai/README.md` Switchboard：Owns / Does Not Own / Read Next 三节 + 目录四态（active/generated/target/candidate/archived）+ 文档活/死归类表 + 机器可读 `section_routing` front-matter | Write 工具 | DONE |
| F4-2 | 死文档归档：`.ai/plans/PLAN-20260729-001.yaml`、`-002` → `.ai/archive/plans/`（git mv，非删除） | `git mv` ×2 | DONE |
| F4-3 | continuity 源清单同步（T-0105 先例）：移除 2 条 plans 条目 + 重算 source_sha256（`C0D2AF...` → `4FA31F...`，semantic_sha256 不变）+ `render_handoff` 重生成 HANDOFF.md | Python 脚本（governor_lib.canonical_json + continuity_producer.render_handoff） | DONE |
| F4-4 | `validate_state .` 全绿验证（归档后无 SOURCE_DRIFT） | `python .zcode/tools/validate_state.py .` → exit 0 `[ok] state is usable` | DONE |
| F4-5 | `loop_core/context_loader.py` `_select_relevant_sections` 改读 `.ai/README.md` section_routing（D5-3 消解）；路由表缺失 → 回退旧关键词启发式 + warning；`load_for_role` 透传 project_root；mtime+size 缓存 | Edit | DONE |
| F4-6 | golden 快照对比：routed == legacy 启发式（docs/02-architecture.md，developer 角色） | Python 断言 | DONE（节集一致） |
| F4-7 | `docs/02-architecture.md` front-matter 增加 `designed_files:` 显式声明区（D5-7 消解） | Edit | DONE |
| F4-8 | `scripts/role_checkers/implementation_design_diff.py` 改读显式声明区；正则推断仅作 `hint_regex_inferred` 提示，不参与 DRIFT 判定 | Write（重写） | DONE |
| F4-9 | 对照：修复前 checker 误报 designed_but_missing=[agents/, evidence_chain.py, hook_common.py, server.py, validate_state.py]（stash 实测）；修复后 declaration=front-matter designed_files、误报进 hint | `git stash` + 运行 + pop | DONE |

## 线 3：F7 finding 结构化契约

| # | 动作 | 命令/依据 | 结果 |
|---|------|-----------|------|
| F7-1 | 新增 `loop_core/schemas/finding.schema.json`（字段对齐 BH harness-findings.input.json：finding_id↔id、dimension_refs↔dimensionRefs、target{kind,package_route,owner_route}↔target{kind,packageRoute,ownerRoute}、ai_fix_prompt↔aiFixPrompt、expected_artifact↔expectedArtifact、expected_output(s)↔expectedOutput[]；LE 独有 fix_boundary/verification_command/acceptance_checks/truncated） | Write | DONE |
| F7-2 | 新增 `loop_core/schemas/finding_contract.py`：load/validate/mark_schema_status/to_bh_finding（fail-closed：校验失败 → INVALID + 告警；jsonschema 不可用 → INVALID） | Write | DONE |
| F7-3 | `loop_core/design_reviewer.py`：DesignFinding.to_finding()（severity 映射 error→high/warning/info）+ DesignReport.schema_valid/invalid 计数 | Edit | DONE |
| F7-4 | `loop_core/security_scanner.py`：SecFinding.to_finding() + SecurityReport.schema_valid/invalid + to_dict() 增加 findings_contract（旧字段不动） | Edit | DONE |
| F7-5 | `loop_core/subagent_evidence_verifier.py`：verify_review_evidence 结果增加 findings（失败 check → schema 化 fix 契约）；valid/reason/checks 语义保持 | Edit | DONE |
| F7-6 | `agents/security-engineer/scripts/run_security_scan.py`：D1-7 截断标志结构化（RAW_OUTPUT_MAX_CHARS=500 + raw_truncated/raw_length/raw_max + _slice_raw）；finding 字段（finding_id/severity/truncated/snippet）；_finding_contract + _attach_contract（findings_contract 视图） | Edit | DONE |
| F7-7 | `agents/system-architect/scripts/analyze_dependencies.py`：D4-10 madge 失败原因区分（unavailable/timeout/error/non-zero-exit/invalid-json + reason + stderr/stdout_tail）；extract_dependency_graph 返回 source_info；报告 dependency_source 字段；_extract_imports_from_file 宽捕获收窄 | Edit | DONE |
| F7-8 | `agents/module-architect/scripts/validate_contract.py`：D4-11 宽捕获收窄（`except (SyntaxError, Exception)` → SyntaxError/UnicodeDecodeError/OSError）+ 失败文件记录（_PARSE_ERRORS/parse_errors）+ 输出 parse_errors 字段 | Edit | DONE |
| F7-9 | D5-6 `loop_core/memory_service.py`：验收报告 front-matter 契约（acceptance_meta 结构化块优先于正则族）+ 未命中结构化行计数上报（unmatched_meta_lines + warning） | Edit | DONE |

## 线 4：F8 治理契约测试

| # | 动作 | 命令/依据 | 结果 |
|---|------|-----------|------|
| F8-1 | 新增 `tests/test_ai_doc_links.py`（8 用例）：README 三节/四态/归类表；全链接可解析（markdown 链接 + 反引号路径引用，白名单机制）；归档无悬挂引用；断链用例 FAIL（markdown + backtick 两个断链夹具） | Write | DONE |
| F8-2 | 新增 `tests/test_projection_freshness.py`（8 用例）：视图=state.yaml 派生一致性/确定性；mtime 新鲜度（伪造旧 mtime → stale）；validate_state 集成（`[warn] stale view` 仅告警，error 集合与 exit code 与无视图一致） | Write | DONE |
| F8-3 | 新增 `tests/test_t0108_fixes.py`（34 用例）：AC-01~AC-06 + F6/F7/D5-6/D5-7/F2-1 回归 | Write | DONE |

## 线 5：F2 阶段 1（只读）

| # | 动作 | 命令/依据 | 结果 |
|---|------|-----------|------|
| F2-1 | `loop_core/projection_engine.py`：generate_state_view（state.yaml 派生，task_status 取自 task_graph 权威源）+ write_state_view（显式落盘 `.ai/views/state-view.yaml`）+ is_state_view_stale（mtime 对比） | Edit | DONE |
| F2-2 | `.zcode/tools/validate_state.py`：新增 check_state_view_freshness（只读，仅追加 `[warn] stale view` 到 warn 流）；**diff 纯新增零删除**（`git diff | grep "^-"` 为空实证） | Edit | DONE |
| F2-3 | 既有判定回归：真实仓库 validate_state exit 0 + 伪造旧 mtime 视图 → 仅 warn、error 集合与 exit code 不变 | 测试 + 手工验证 | DONE |

## 验收（AC）

| AC | 验证 | 结果 |
|----|------|------|
| AC-01 | README Switchboard 三节存在 + doc-link 测试全绿（断链用例 FAIL 断言） | PASS |
| AC-02 | context_loader 节选择读路由表 golden 一致；缺失回退 + 告警 | PASS |
| AC-03 | finding 输出通过 schema 校验 + BH 字段映射对照 | PASS |
| AC-04 | validate_state 伪造旧 mtime 视图 → `[warn] stale view`（仅告警，既有判定不变） | PASS |
| AC-05 | 投影视图 = state.yaml 派生（一致性测试） | PASS |
| AC-06 | 死文档归档 + continuity 源清单同步（无悬挂引用）+ D5-7 显式声明区（有测试） | PASS |
| AC-07 | 全量回归（见命令输出）+ compile pass | 见下 |
| AC-08 | 版本 bump 3.12.45 由主会话执行 | 移交主会话 |
| AC-09 | 独立审查 GO：hooks/ 与治理内核零改动 diff 实证（见约束自查） | 移交审查 |

## 约束自查

| 约束 | 实证 |
|------|------|
| hooks/ 零改动 | `git diff HEAD --stat -- hooks/` 空 |
| 治理内核零触碰 | `git diff HEAD --stat -- loop_core/gate_guard.py loop_core/enforcement.py loop_core/hard_constraints.py loop_core/guard_health.py loop_core/state_machine.py` 空 |
| validate_state 仅新增只读告警 | `git diff HEAD -- .zcode/tools/validate_state.py` 纯新增（0 删除行）；测试证明 error 集合与 exit code 不变 |
| fail-closed 不变 | finding 校验失败 → INVALID+告警不静默；路由表缺失 → 回退+告警不静默空上下文；git diff 失败占位（T-0107 既有） |
| F2-1 仅告警不阻断 | `[warn] stale view` 走 warn 流，不改变 blocker 判定 |
| 不实施 T-0109+ | 无 gates 分层/写入收敛/证据七态/工具合并改动 |
| 写路径限 allowed_paths | 变更文件全部在任务卡 allowed_paths 内（见文件清单） |

## 变更文件清单（本次新增/修改）

- 新增：`.ai/README.md`、`.ai/archive/plans/PLAN-20260729-{001,002}.yaml`（git mv）、`loop_core/context_budget.py`、`loop_core/schemas/finding.schema.json`、`loop_core/schemas/finding_contract.py`、`tests/test_ai_doc_links.py`、`tests/test_projection_freshness.py`、`tests/test_t0108_fixes.py`
- 修改：`loop_core/context_packager.py`、`loop_core/context_loader.py`、`loop_core/design_reviewer.py`、`loop_core/security_scanner.py`、`loop_core/subagent_evidence_verifier.py`、`loop_core/memory_service.py`、`loop_core/projection_engine.py`、`.zcode/tools/validate_state.py`、`agents/security-engineer/scripts/run_security_scan.py`、`agents/system-architect/scripts/analyze_dependencies.py`、`agents/module-architect/scripts/validate_contract.py`、`scripts/role_checkers/implementation_design_diff.py`、`docs/02-architecture.md`、`.ai/project_continuity.yaml`（源清单同步）、`.ai/HANDOFF.md`（render_handoff 重生成，随清单）
- 删除（git mv 原位置）：`.ai/plans/PLAN-20260729-{001,002}.yaml`

## 遗留事项

- `.ai/views/state-view.yaml` 视图落盘由主会话/后续会话按需显式调用（`projection_engine.write_state_view`）；validate_state 在视图缺失时静默（默认路径零告警）
- `implementation_design_diff` 对 hooks/scripts 中非 v1.0 架构声明的 hook 文件（loop_enforcement/content_guard 等）仍报 actual_but_undesigned（DRIFT）——显式声明驱动的正确行为，系统架构师角色可在架构文档演进时扩充 designed_files
- AC-08 版本 bump 3.12.45 由主会话执行；T-0112 撤销记录不影响本任务
- **known transient（closeout 自愈，T-0107 先例）**：`test_manifest_t0095::test_manifest_exists_and_handoff_reference_is_real` 在 T-0108 ACTIVE 期失败——官方 `render_handoff` 重生成的 HANDOFF 引用当前任务（T-0108）的 evidence manifest 预期路径，该 manifest 为 closeout 产物（主会话 closeout 时经 validation_runner 创建后即存在）。主会话 closeout 时创建 `.ai/evidence/T-0108/evidence-manifest.v1.yaml` 并重跑 close_session 后该测试自愈。另 1 项 `test_deployment_quality_checker::test_runtime_report_is_simulated_and_fail_closed` 为 KNOWN_ISSUES 已登记的本机环境依赖失败（localhost:3000/8000 占用，baseline stash 实证预存在）
- **hook 交互实测发现**：docs/02-architecture.md front-matter `designed_files:` 必须用 YAML flow 风格（禁 `- ` bullet 行），否则 `hooks/scripts/content_guard.py` 架构合规检查会解析 bullet+反引号行并把声明项当架构模块、阻断范围外写入（实测 guard_health BROKEN）——hook 零改动约束下由文档侧规避，注释已写入 front-matter
