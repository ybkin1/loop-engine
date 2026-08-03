# F7 finding 结构化契约（T-0108 线 3）— 证据

- 显式覆盖 P3：D1-7（run_security_scan raw `[:500]` 无 truncated 标志）、D4-10（analyze_dependencies:71 宽捕获静默返回 None）、D4-11（validate_contract:279,342 冗余宽捕获）、D5-6（memory_service 验收报告正则族静默丢失）
- 目标文件：`loop_core/schemas/finding.schema.json`（新增）、`loop_core/schemas/finding_contract.py`（新增）、`loop_core/design_reviewer.py`、`loop_core/security_scanner.py`、`loop_core/subagent_evidence_verifier.py`、`loop_core/memory_service.py`、`agents/security-engineer/scripts/run_security_scan.py`、`agents/system-architect/scripts/analyze_dependencies.py`、`agents/module-architect/scripts/validate_contract.py`

## 改动

1. **finding.schema.json（新增，对齐 BH harness-findings.input.json）**
   - 必填：finding_id/source/severity/title/message/expected_output/fix_boundary/verification_command/acceptance_checks
   - BH 映射（finding_contract.to_bh_finding 对照实现）：finding_id↔id、dimension_refs↔dimensionRefs、target{kind,package_route,owner_route}↔target{kind,packageRoute,ownerRoute}、ai_fix_prompt↔aiFixPrompt、expected_artifact↔expectedArtifact、expected_output(s)↔expectedOutput[]、severity 小写↔首字母大写
   - LE 独有（BH 无对应）：fix_boundary（allowed_paths/forbidden）、verification_command、acceptance_checks、truncated（D1-7 结构化截断标志）、schema_status（VALID/INVALID）
   - draft-07；`additionalProperties: true`（消费方兼容：加字段不删字段）

2. **finding_contract.py（新增校验器，fail-closed）**
   - `validate_finding`：永不抛出；schema 不可读/jsonschema 不可用 → 校验失败（不静默放行）
   - `mark_schema_status`：附加 schema_status/schema_errors（VALID/INVALID）
   - `to_bh_finding`：LE→BH 字段映射（AC-03 对照测试用）

3. **扫描器输出收敛（旧字段不动，加 findings_contract/schema 计数）**
   - design_reviewer：DesignFinding.to_finding()（severity error→high）；DesignReport.schema_valid/schema_invalid
   - security_scanner：SecFinding.to_finding()（truncated=len(snippet)>=100）；SecurityReport.schema_valid/schema_invalid；to_dict() 增 findings_contract
   - subagent_evidence_verifier：verify_review_evidence 结果增 findings（失败 check → EVID-* 契约 finding）；valid/reason/checks 语义保持（reason 取首个失败，与旧行为一致）

4. **agents 脚本输出收敛（独立 subprocess，自包含契约构造）**
   - run_security_scan：D1-7 RAW_OUTPUT_MAX_CHARS=500 + `_slice_raw` → raw_truncated/raw_length/raw_max 结构化标志；secret/injection/permission findings 增 finding_id/severity/truncated/snippet；`_finding_contract`/`_attach_contract` → 各 scan 输出 findings_contract（schema_status=VALID 由必填字段构造保证）
   - analyze_dependencies：D4-10 `run_madge` 返回 (graph, error_info)，失败原因区分 unavailable/timeout/error/non-zero-exit/invalid-json（含 reason + stderr/stdout_tail）；extract_dependency_graph 返回 source_info；报告增 dependency_source；`_extract_imports_from_file` 宽捕获收窄
   - validate_contract：D4-11 两处 `except (SyntaxError, Exception)` → (SyntaxError, UnicodeDecodeError, OSError)；_PARSE_ERRORS 记录失败文件；输出增 parse_errors

5. **D5-6 memory_service 报告 front-matter 契约化**
   - `_parse_acceptance_meta`：报告头部 `---\nacceptance_meta: {task_id,title,date,gate{id,decision},review_verdict,legacy_items}\n---` 结构化块；有块 → 优先读取（标题/日期/gate/裁决/遗留），无块 → 正则族旧行为
   - `_count_unmatched_meta_lines`：blockquote/加粗结构化外观行未命中任何正则 → 计数；`extract_from_acceptance_reports` 上报 `sources["unmatched_meta_lines"]` + logger.warning（模板措辞变化不再静默丢失）

## 测试

- `tests/test_t0108_fixes.py`：TestFindingContract（合法/非法/severity 枚举/schema_status 加性/BH 映射对照×2）、TestAgentsScripts（D1-7 截断标志、run_security_scan finding 契约过 schema、D4-10 madge 失败原因、D4-11 收窄+失败文件记录）、TestMemoryReportMeta（旧格式不变/meta 优先/未命中计数/report 上报）
- 回归：tests/test_knowledge_memory.py + test_memory_injection.py 87 passed

## 约束自查

- fail-closed：schema 校验失败 → INVALID + 告警（计数/上报），绝不静默丢弃；jsonschema 不可用 → INVALID（不静默放行）
- 防篡改：evidence_refs 只引用不修改；finding_contract 零写盘
- 审批闭环：finding 为建议性产物，不触发任何 gate 状态变更
- 兼容：全部扫描器旧字段原样保留（加字段不删字段），to_dict/report 结构兼容

## 遗留

- agents 脚本的 findings_contract 为自包含构造（schema_status 静态 VALID）；若需运行时对真实 schema 校验，可在脚本内按需加载 `loop_core/schemas/finding.schema.json`（独立 subprocess 场景不强制）
- D1-5（snippet `[:100]` 省略号）与 D2-6/D3-6/D4-9 等字面量族归 T-0110，不在本任务
