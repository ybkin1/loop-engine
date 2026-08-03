# T-0110 批 A — 魔法数字集中化（M-1~17）落地表 + P3 消解 + 测试/约束自查

依据：T-0106 design-common-weakness.md §2（M-1~17 清单与落点）、
audit-design-gaps.md（D2-3~7/D1-5/6/8/D3-6/8/D4-9）、T-0110 任务卡批 A 范围。

## 一、M-1~17 落地表

| M# | 常量名（新登记） | 落点 | 原散落位置（现状） | 等价验证 |
|----|------------------|------|--------------------|----------|
| M-1 | `EXIT_PASS=0` / `EXIT_BLOCK=2` | hooks/scripts/loop_enforcement_constants.py（批 C 接线） | loop_enforcement.py:172-173（已命名）、gate_guard.py:330、path_guard.py:200、content_guard.py:406（各自定义同值） | 与 loop_enforcement.py 现值脚本比对 ALL MATCH；hook 文件零改动（硬约束 1） |
| M-2 | `EXIT_OK=0` / `EXIT_VALIDATION_FAILED=2` / `EXIT_IDLE_BLOCKED=3` | loop_core/constants.py（tool 共享常量登记；validate_state/close_session 不在 allowed_paths，保留原字面量为显式豁免） | validate_state.py（2=校验失败、3=idle 合法阻塞态）、close_session.py（2=未稳定）；loop_self_audit.py:317,321 已接线 | loop_self_audit rc 判定改引常量后行为等价（test_self_audit_llm 全绿）；M-2 值 0/2/3 由 test_exit_code_family_m2 锁定 |
| M-3 | `COMMAND_TIMEOUT_SECONDS=30` | hooks/scripts/loop_enforcement_constants.py（6 文件 7 处同值登记；消费方接线受限，批 C 接 loop_enforcement） | content_guard.py:71,76、loop_enforcement.py:686、rollback.py:207、tool_evidence_chain.py:21,41、tool_cost_tracker.py:20、upgrade.py:251 | 值 30 由 test_timeout_family_m3_m4 锁定；消费方字面量保留为显式豁免（allowed_paths/批 C） |
| M-4 | `GUARD_HEALTH_PROBE_TIMEOUT_SECONDS=20` | hooks/scripts/loop_enforcement_constants.py（共享登记） | guard_health.py:247,258（治理内核零触碰，保留字面量） | 值 20 由 test_timeout_family_m3_m4 锁定；零触碰豁免 |
| M-5 | （T-0107 已落地，不迁移） | context_packager.GIT_TIMEOUT_DIFF_STAT/DIFF_CODE/DIFF_NAME/REV_PARSE | context_packager.py:41-44 | 既有具名常量，集中化模板 |
| M-6 | （T-0107 已落地，不迁移） | IntentRouter.MEDIUM_RISK_ESCALATION_MIN=3 | intent_router.py:340（类级具名） | 既有具名常量，集中化模板 |
| M-7 | `CONFIDENCE_CONFLICT_MIN_DOMAINS=4` / `CONFIDENCE_CONFLICT_MAX_RISK_FACTORS=2` | loop_core/constants.py | intent_router.py:617（原 :612）置信度惩罚 `>= 4 且 <= 2` | 边界行为测试（4 域+2 风险→触发；3 域→不触发；4 域+3 风险→不触发）全过 |
| M-8 | `KEYWORD_BOUNDARY_MAX_LEN=3` | loop_core/constants.py | intent_router.py:642,795 `len(kw) > 3`（两处） | 边界行为测试（len=3 词边界不命中 "apicall"；len=4 子串命中 "crest"→"rest"）全过 |
| M-9 | `USER_GATE_MIN_DISTINCT_ROLES=3` | loop_core/constants.py | veto_escalation.py:245 `len(distinct_roles) >= 3` | 边界测试（2 同域角色→CROSS_ROLE 不触发；3/4 角色→USER_GATE）全过 |
| M-10 | `SNIPPET_MAX_CHARS=100` / `FAILED_STDERR_MAX_CHARS=500` + `TRUNCATION_ELLIPSIS`/`truncate_with_marker` | loop_core/constants.py | security_scanner.py 4 处 `[:100]`、design_reviewer.py 2 处 `[:100]`、executor.py:813 `[:500]`；context_packager 侧 T-0107 已集中 | 长行→99+`…` 总长 100、短行零变化（测试锁定）；`truncated` 标志与截断一致；executor caplog 断言 500 |
| M-11 | `AUDIT_STDOUT_TAIL_CHARS=4000`/`AUDIT_STDERR_TAIL_CHARS=2000`/`AUDIT_SUMMARY_STDOUT_TAIL_CHARS=800`/`AUDIT_SUMMARY_STDERR_TAIL_CHARS=400` + `tail_with_marker` | loop_core/constants.py | loop_self_audit.py:81,138-139（原 :88-92） | 长输出→`…`+尾部（总长=常量）、短输出零变化（测试锁定） |
| M-12 | （T-0107 已落地，不迁移） | context_packager.MAX_TOTAL_CHARS=15000（死护栏修复） | context_packager.py:38 | 既有具名常量 |
| M-13 | （T-0107 已落地，不迁移） | context_packager.ROLE_CONTEXT 角色上限表（2000-8000） | context_packager.py:52-64 | 既有具名常量表 |
| M-14 | （先例模板，不迁移） | observability.DEFAULT_MAX_LINES/BYTES/ARCHIVES | observability.py | 已有集中先例 |
| M-15 | （先例模板，不迁移） | validate_state.MAX_CONTRACT_AGE_DAYS=90 | validate_state.py:43 | 已有集中先例 |
| M-16 | （T-0109 已落地，本批核对一致） | .ai/slo.yaml score_caps（59/74/84/94/100）| BH 上限表显式化 | 与 evidence_state.DEFAULT_SCORE_CAPS 逐项一致（test_slo_yaml_matches_default_score_caps 锁定） |
| M-17 | （先例模板，不迁移） | evals.MAX_CAPTURE_CHARS=64KB | evals.py:65 | 已有集中先例 |

**汇总**：批 A 新增登记常量 26 个（loop_core/constants.py 22 + hook 常量表 4 组），
4 个落点（loop_core/constants.py、hooks/scripts/loop_enforcement_constants.py、
tool 共享登记（loop_core/constants.py 承载）、.ai/slo.yaml 核对）；
M-5/6/12/13/14/15/17 为 T-0107 前序已落地或既有先例，仅登记不迁移。

## 二、P3 消解表

| P3 | 文件 | 修复 | 行为 |
|----|------|------|------|
| D2-3（M-7） | intent_router.py:617 | `>= CONFIDENCE_CONFLICT_MIN_DOMAINS and <= CONFIDENCE_CONFLICT_MAX_RISK_FACTORS` | 纯字面量→常量，判定零变化 |
| D2-4（M-8） | intent_router.py:642,795 | `len(kw) > KEYWORD_BOUNDARY_MAX_LEN`（两处） | 纯字面量→常量，词边界策略零变化 |
| D2-5（M-9） | veto_escalation.py:245 | `>= USER_GATE_MIN_DISTINCT_ROLES` | 纯字面量→常量，升级规则零变化 |
| D2-6（M-3/M-4） | 6 文件 7 处 timeout=30 + guard_health 2 处 timeout=20 | 常量表登记（COMMAND_TIMEOUT_SECONDS/GUARD_HEALTH_PROBE_TIMEOUT_SECONDS）；消费方接线受限 | 显式豁免表（下）；loop_enforcement 接线批 C |
| D2-7（M-11） | loop_self_audit.py:81,138-139 | 4 个尾部常量 + tail_with_marker 标记 | 长输出首部 `…` 标记；数值零变化 |
| D1-5（M-10） | security_scanner.py ×4、design_reviewer.py ×2 | `truncate_with_marker(..., SNIPPET_MAX_CHARS)` 统一 `…` 标记 | 仅 >100 字符行 snippet 尾部追加 `…`（显示层）；truncated 标志一致 |
| D1-6（M-10） | executor.py:813 | `truncate_with_marker(stderr, FAILED_STDERR_MAX_CHARS)` | 仅 >500 字符 stderr 日志尾部追加 `…` |
| D1-8（M-11） | loop_self_audit.py | 尾部常量 + 标记（同 D2-7） | 同上 |
| D3-6 | scope_drift_detector.py:15、review_coverage_checker.py:8 | `timeout=GIT_DIFF_NAME_ONLY_TIMEOUT_SECONDS` + `except (OSError, subprocess.TimeoutExpired)` 兜底（error dict / status=ERROR） | git 缺失/挂起不再 crash；正常路径输出零变化 |
| D3-8 | loop_self_audit.py:88-92 | git_commit 补 `timeout=GIT_SHORT_SHA_TIMEOUT_SECONDS` + `except (OSError, subprocess.SubprocessError)` 返回 ""（对齐 evals.py:664 同款） | git 缺失/挂起返回 ""（不再 crash）；正常路径零变化 |
| D4-9 | scope_drift_detector.py:8、review_coverage_checker.py:13 | 裸 `except:` 收窄（ImportError / (ValueError, OSError)）+ `logger.warning` 记原因；yaml 错误信息含导入失败详情 | 异常路径从"静默降级"变为"收窄+可观测"；正常路径零变化 |

## 三、grep 零新散落断言（AC-01）

`grep -rn "timeout=[0-9]" loop_core/ hooks/ tools/ scripts/`：

- **批 A touched 文件**（executor/security_scanner/design_reviewer/intent_router/
  veto_escalation/loop_self_audit/role_checkers×2）：仅 executor.py:435,774
  两处既有 `timeout=120`（审计 D2-6 未列、不在 M-1~17 清单 → 显式豁免）；
  其余零匹配（tests/test_t0110_batch_a.py::TestGrepZeroScatter 双断言锁定）。
- **常量表文件**：仅注释提及（非代码散落）。
- **显式豁免表（批 A 启动前既有、不可写/零触碰/批 C 接线）**：
  - M-3 族（批 C 接线 / allowed_paths 外）：content_guard.py:71,76、
    loop_enforcement.py:686、rollback.py:207、upgrade.py:251、
    tool_evidence_chain.py:21,41、tool_cost_tracker.py:20
  - M-4（治理内核零触碰）：guard_health.py:247,258
  - 其余非 M 清单既有值（2/5/10/15/60/180/300 等，D2-6 未列入）：
    evals.py:666、dashboard_views.py:77、mcp_client.py:257,263,269、
    governance_metrics.py:1337、tool_dependency_analysis.py:21、
    tool_contract_validate.py:23、server.py:45,65,85,111,131、
    tool_quality_gates.py:27、tool_security_scan.py:27、dev.py:169、
    perf_runner.py:49、deployment_quality_checker.py:117、regression_runner.py:37,74,99,118、
    runtime_delivery_gate.py:330,545,599,704,756
- 截断字面量：touched 文件仅 security_scanner.py:114 `[:16]`（SHA-256 摘要前缀，
  非显示截断阈值，豁免）；其余 `[:N]` 全部接入常量/辅助函数。

## 四、测试结果

| 套件 | 结果 |
|------|------|
| tests/test_t0110_batch_a.py（新增 41 项：常量表单测 ×2 表、截断辅助、D2-3/4/5 边界、D1-5/6/8 标记、D3-6/8 兜底、D4-9 收窄、grep 零散落、M-16 一致性） | **41 passed** |
| 相关既有套件（executor/intent_router×2/veto/self_audit_llm/verdicts/code_quality/t0108_fixes/security×2/evals/governance_metrics/enforcement/hooks/import_checker） | **493 passed** |
| 全量回归 `pytest tests/` | **4090 passed, 64 skipped, 12 xfailed, 2 failed**（2 failed 为批 A 启动前预存：test_manifest_t0095 HANDOFF 引用 T-0110 清单（closeout 产出，T-0109 同款预存记录）；test_t0109_f5 hooks diff 硬编码 T-0109 工作树态（提交后干净树必红，批 C 后自然恢复）——均与批 A 改动无关） |
| compileall（loop_core/ + 全部改动文件 + tests） | 0 错误 |

## 五、约束自查

| 约束 | 状态 |
|------|------|
| hooks/ 仅新建 loop_enforcement_constants.py；其他 hook 文件零改动 | ✓（git diff HEAD -- hooks/ 为空；新文件为唯一 hooks 增量） |
| 治理内核判定零触碰（gate_guard/enforcement 判定语义/hard_constraints/guard_health/state_machine） | ✓（均未修改；guard_health 字面量保留并登记共享引用） |
| 行为等价：常量替换只改字面量为命名常量引用，数值/逻辑零变化 | ✓（golden：相关既有套件 493 passed；边界/标记/兜底行为均有测试锁定；截断标记为 P3 消解本意） |
| 零删除 | ✓（无任何删除操作） |
| 写路径仅限任务卡 allowed_paths | ✓（.ai/evidence/T-0110/、loop_core/、hooks/scripts/loop_enforcement_constants.py、tools/loop_self_audit.py、scripts/role_checkers/、tests/） |
| 版本文件不改 | ✓（bump 3.12.47 由主会话执行） |
