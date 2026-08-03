# T-0105 独立审查报告（independent-review.md）

> 审查者：independent-reviewer 子代理（fresh context，全部结论亲自复验）
> 日期：2026-08-03
> 基线：da4fb18（v3.12.42）→ 当前工作区（bump 后 3.12.43，未提交）
> 方法：git diff 全量核对 + 代码路径逐条复验 + 测试亲自重跑（新增 82 项 + 全量 3867 项）+ eval 实验在临时目录完整复跑 + validate_state 亲自执行

---

## 一、裁决

**CONDITIONAL_GO**（条件达成后 GO）

四项批次修复的真实性、测试实质性与硬约束零弱化全部复验通过；但审查时点存在 **2 项 P1 收尾流程缺口**（均可用官方工具在收尾序列内修复，非代码/约束缺陷）：

1. **F-1**：`validate_state.py .` 亲自执行 → `exit 2`，`[error] Continuity source drift: .ai/version-manifest.yaml`（3.12.43 bump 于 11:20:49 写入后未重跑官方 `repair_continuity.py` + `close_session.py`；记录 hash EDA29293… vs 实际 E90C0B47…）。
2. **F-2**：T-0105 evidence-manifest 指纹陈旧——`fixes/batch4-sync-eval.md` 条目记录 size 8933 / sha256 0343DAA2…，实际 9698 / C0188951…（文件 11:17 定稿晚于 manifest 生成）；HANDOFF 的 unverified 列表已自行标记 `EVIDENCE_FINGERPRINT_MISMATCH`。

**放行条件（收尾序列必须执行）**：
- C1：bump 后重跑官方 `repair_continuity.py .` + `close_session.py .`，validate_state 恢复（预期仅剩 G-T-0106 pending gate 错误，exit 2 属该 gate 的预期语义，需用户决策后清零——批 4 已声明，非 T-0105 范围）。
- C2：按 B-4-3 自定约定重新生成 evidence-manifest（create-only）→ 刷新 HANDOFF 引用 → 重跑 `test_manifest_t0095`（该测试现通过，但只校验 T-0095 清单，不覆盖 T-0105 指纹——需用官方 `evidence_manifest` 校验模块确认 0 mismatch）。
- C3：验收提交（subject 含 3.12.43）后重跑 `test_release.py::test_pyproject_version_matches_git_head`（全量回归唯一失败项，先 bump 再提交约定下的预期瞬态）。

---

## 二、改动范围核对表

基线 da4fb18 → 工作区，全部变更文件（37 个 tracked + 4 组新增）：

| 文件 | 性质 | allowed_paths | 判定 |
|---|---|---|---|
| `.ai/`（CONTRACTS/HANDOFF/KNOWN_ISSUES/state/gates/task_graph/project_continuity/version-manifest/ledger/evidence/observability/tasks/T-0102,T-0104） | 文档/状态/证据 | `.ai/` ✓ | PASS |
| `skills/loop-governance/config.yaml`（仅注释）、`templates/gate-request.md`、`templates/task-card.md` | 模板/配置源 | `skills/loop-governance/` ✓ | PASS |
| `.zcode/skills/loop-governance/config.yaml`（合并同步 memory_injection） | 安装副本 | `.zcode/skills/loop-governance/` ✓ | PASS |
| `agents/main-thread/CONTRACT.yaml`、`agents/main-thread/SKILL.md`、`agents/product-manager/SKILL.md` | R11 微调 + Q2 提示词 | `agents/` ✓ | PASS |
| `loop_core/context_packager.py`、`role_orchestrator.py`、`inbox.py`、`planner.py`、`__init__.py`（版本号） | 批 2/批 3 代码 | `loop_core/` ✓ | PASS |
| `tools/tool_inbox.py`、`tool_planner.py` | MCP handler | `tools/` ✓ | PASS |
| `tests/test_t0105_batch2.py`、`test_t0105_batch3.py`（新增）、`test_t0104_templates.py`、`test_release_bump.py` | 测试 | `tests/` ✓ | PASS |
| `docs/06-delivery.md`（版本号） | bump 载体 | `docs/` ✓ | PASS |
| `pyproject.toml`、`CHANGELOG.md` | bump 载体 | 显式列出 ✓ | PASS |
| `.zcode-plugin/plugin.json`、`README.md`、`src/loop_engine/__init__.py` | bump 载体（release.py VERSION_CARRIERS 8 项中 3 项） | **未列入 allowed_paths** | **发现 F-3（P2）** |
| `.ai/evidence/S6/handoff-next-archived-2026-07-23.md`、`.ai/evidence/T-0103/evals/`、`.ai/tasks/T-0105.md`、`T-0106.md` | 新增（归档/eval 产物/任务卡） | `.ai/` ✓ | PASS |
| `hooks/` 全部 | — | 禁止改动 | **零改动（diff 空）** |
| `.zcode/tools/` | 只读兼容验证 | 只读 | 零改动（diff 空） |

越界判定：F-3 三文件仅含版本号字符串、由官方 `scripts/release.py bump`（任务卡明文授权"bump 3.12.43（8 载体原子写）"）写入，非人工越权改动；属任务卡 allowed_paths 声明与既定 bump 机制不一致的**范围声明缺口**（前序任务同模式，系统性问题）。

---

## 三、约束零弱化专项

### 3.1 硬约束 diff（全部亲自复验）

| 检查项 | 结果 |
|---|---|
| `git diff da4fb18 -- hooks/` | **空**（hooks.json/scripts 零改动，含 gate_guard.py） |
| `git diff da4fb18 -- loop_core/context_loader.py` | **空**（默认值不动） |
| 治理内核：`loop_core/enforcement.py`、`hard_constraints.py`、`guard_health.py`、`state_machine.py`、`hooks/scripts/gate_guard.py`、`.zcode/tools/validate_state.py` | **全部空 diff** |
| `.zcode/`（config.json / tools/） | 零改动 |
| `skills/loop-governance/chain.yaml` 与安装副本 | **零改动**且两副本逐字节一致（`diff` 空） |

### 3.2 R11 微调专项（判定：合规）

- `agents/main-thread/CONTRACT.yaml` L27：`R11_reduce_questions` 编号保留；文本由"同一阶段内向用户提问不超过 3 次"改为"**同一轮提问不超过 3 个、可多轮**（轮次不限，但每轮必须围绕已识别缺口、问题附'为什么问'）；非关键决策自行处理并标注"——**保留主体语义**（"非关键决策自行处理并标注"原样保留），仅放开轮次硬上限。仅文本改动，非 hook/内核。
- 同步引用一致性：`agents/main-thread/SKILL.md` L81（"每轮 ≤3 个、可多轮——P2-1 已落地…"）与 `skills/loop-governance/templates/task-card.md` 盲点清单规则 3（"R11'同一轮提问≤3 个、可多轮'"）均已同步；grep 全库确认旧措辞"同一阶段内…不超过 3 次"仅存于测试的否定断言中。
- 兼容测试：`tests/test_t0105_batch3.py::TestQ2PromptLayer::test_r11_new_semantics_in_contract` + `tests/test_t0104_templates.py` R11 断言更新（11 passed）。

### 3.3 fail-closed 语义（全部保持）

- inbox `ask_clarification` 空问题 → `raise InboxError`（测试覆盖）；`add_clarification_questions` 替换语义保留。
- memory_injection 配置：phases 非 list（字符串等）→ 整体回退 `{"enabled": False, "phases": [], "memory_limit": 5}`；memory_limit 非法 → 5；损坏 YAML → fail-closed（均有测试）。
- 配置缓存：读取/解析失败 → 清缓存条目并回退默认（损坏结果不驻留）。
- context_packager：空召回 no-op；store 损坏抛异常路径未触碰（既有测试保持）。
- planner `generate_prototype` 空描述 raise、非法形态 raise（工具层返回错误）。

**结论：约束零弱化确认。** 无任何 hook/内核改动，R11 属授权范围内的治理约定语义放开，fail-closed 语义不变。

---

## 四、批 1~4 逐批审查

### 批 1 文档漂移（真实性：全部复验通过）

- **A-1**：两 finding 文件 diff 确认仅状态行 `OPEN（…）` → `CLOSED` + 追加关闭记录行；版本引用 v3.12.40（T-0101）/v3.12.41（T-0102）与 CHANGELOG 一致。
- **A-2**：KNOWN_ISSUES 两项从 Open 移入 Recently Closed 并附关闭理由——**准确性复验**：`hooks/scripts/bash_content_guard.py` 存在于 hooks 注册表（hooks.json L50）且 guard-events.jsonl 有 health/death PASS 事件（T-0060 属实）；`project_continuity.yaml` source_manifest 443 条 **不含自身**（`contains self: False`，T-0049 拆弹属实）；Open 区保留 seeded defects / E2E lab fixture 两项，仍有效。
- **A-3**：HANDOFF-NEXT 归档——`git show da4fb18:.ai/HANDOFF-NEXT.md` 与归档文件 `diff` **逐字节一致**（10988 bytes）；全库 grep 无活动引用（残留仅历史 gate 记录/历史证据/归档文件本身/T-0105 描述文本）；`project_continuity.yaml` source_manifest 无 HANDOFF-NEXT 条目。
- **A-4**：`.ai/tasks/T-0102.md`、`T-0104.md` `## Status` = completed（diff 确认，仅该行）；T-0103 本就 completed 未动。
- **validate_state**：亲自执行——**0 条 legacy warn**（无 T-0102/T-0104 任务状态 mismatch），但见 F-1（version-manifest 漂移，bump 后产生，非批 1 遗留）。

### 批 2 P3 四项（真实性：复验通过）

- **B-4-1**：`context_packager.build_context` 新增 `memory_gate_id`/`memory_tag`，recall 透传 `task_id=task_id or None, gate_id, tag`（AND 组合，与 `memory_service.recall` 签名一致；context_loader 的 `_apply_memory_injection` 同语义）。task_id 管道复验：`build_dispatch_manifest` → `load_role_prompt_with_context(task_id=…)` → `build_role_context` → `build_context` → recall，透传链完整。
- **B-4-2**：`_validated_phases`（非 list → None → 整体回退 disabled，杜绝 "S4" 逐字符展开）与 `_validated_memory_limit`（bool/非数字/≤0 → 5，正浮点 int() 截断）逻辑与证据一致；`cfg.get("phases") or []` 缺失/空 → [] 合法。
- **B-4-3**：`.ai/CONTRACTS.md` 新增 `## Completion Flow Conventions` 节（manifest→HANDOFF→test_manifest_t0095 时序约定），内容与证据一致；测试断言 4 个关键短语。
- **B-4-4**：`_CONFIG_CACHE` 模块级缓存（path → (mtime_ns, cfg)），mtime 命中返回拷贝、变化重读、失败清缓存；两候选路径独立缓存。
- **测试**：`tests/test_t0105_batch2.py` 亲自运行 **21 passed**（B-4-1×7 / B-4-2×8 / B-4-3×1 / B-4-4×5），断言全部实质性（含同 mtime 命中、损坏清缓存、安装副本回退、task_id 派发透传）。

### 批 3 Q2/Q4（真实性：复验通过）

- **Q2 多轮澄清**：`Requirement.clarification_rounds`（to_dict/from_dict 缺省 0，旧 YAML 兼容有测试）；`ask_clarification` 追加轮次（跨轮累积、rounds 计数、NEW→CLARIFYING、空问题 raise）；`add_clarification_questions` 替换语义保留且 rounds 置 ≥1；`tools/tool_inbox.py` handler 校验 rid/questions。
- **product-manager SKILL 第 14 节**：三栏清单（用户已知/缺什么/缺口如何影响结果）+ 每轮≤3 + 每个问题附"为什么问" + 多轮闭环 + 缺口未清空 BLOCKED；工作流程步骤 1 引用已更新。
- **Q4 原型机制**：planner `TaskType`/`PrototypeForm` 枚举、`TaskDraft.task_type/prototype_form`（序列化缺省兼容、旧 plan 默认 standard 有测试）、`generate_prototype()`（S3-interface、LOW、AC 含低成本/可迭代/不追求完整/选择后反馈）；`tools/tool_planner.py` handler；gate-request"选择后反馈"节（理由不代编、默认一轮、不满意重新发起 Gate）；task-card"原型交付"节 + 三原则。
- **chain.yaml 零改动裁决合理性（亲自复验，判定成立）**：
  - `scripts/evidence_chain.py` L23-24 与 `tools/tool_evidence_chain.py` L54-56 均**优先读 `.zcode` 安装副本**——只改仓库副本会造成双副本漂移且线上验证读旧配置，裁决理由属实；
  - verifier 用 `node_file.exists()` 判存在（`scripts/evidence_chain.py`），**不支持 glob**——required+glob 在 strict 模式恒 MISSING→BLOCKED，理由属实；
  - grep 确认无任何 hook/gate 以 strict 模式调用证据链验证（`loop_core/evidence_chain.py` 的 verify_chain 为内部完整性自检，非门禁联动），"加了也无人消费"属实。
- **测试**：`tests/test_t0105_batch3.py` 亲自运行 **24 passed**（Q2 inbox×9、Q2 提示词×2、Q4 planner×10（含 3 形态 parametrize）、Q4 模板×3），断言实质性。

### 批 4 同步 + eval + ledger（真实性：复验通过）

- **C-1 config.yaml 合并**：`diff` 亲自对比——安装副本 = 源内容（含 memory_injection 节，**逐字节一致**）+ 3 个安装副本专有节（`compile_threshold: 0`、python 模板 `compile_command`、`runtime_delivery`），与证据描述完全一致；专有节消费方（`run_quality_gates.py`/`runtime_delivery_gate.py` 只读安装副本）核实存在。
- **模板保持精简决策**：`template_injector.py` 读取源目录（`Path("skills")/"loop-governance"/"templates"`），安装副本 2 个遗留模板无代码引用——决策合理；`diff -rq` 复验安装副本仅 config.yaml（含专有节）+ chain.yaml + 2 模板。
- **eval 实验方法学**：见第五节。
- **C-2 AiDecisionLedger**：`.ai/ledger/ai-decisions.jsonl` 含 1 条 `AD-7ce9f67bca96`（T-0105/S6-delivery/developer/BATCH4-C1-SYNC-DECISION）；亲自执行 `AiDecisionLedger('.')` → `verify_chain() = (True, "chain verified (1 entries)")`。备注：`verify_ai_decision_ledger_path.py` 每次运行会再 append 一条（非幂等），见 F-6。

---

## 五、eval 实验方法学审查

### 5.1 如实性（判定：如实）

- **降级路径声明属实**：`run_experiment.py` 构造 EvalRunner 时**不传 llm_driver**；`loop_core/evals.py` 的 LLM judge 是可选 fail-safe（无 driver → SKIP），本实验 0 LLM 调用。报告 §1.2 明确声明"规则式模拟/构造性评估，未触发任何 LLM 外部调用"。
- **构造性数据披露充分**：报告明确产出为"按 A/B 策略规范撰写"的构造样本、存在设计者偏差、n=5 仅探索性，未冒充真实模型采样。

### 5.2 可复跑性（亲自复跑：完全一致）

在临时副本完整重跑（`gen_cases.py` + `run_experiment.py`）：
- 96 case（96 unique ids）生成成功；
- 校准：high=5hits/D2=True/D4=3，low=0hits/D2=False/D4=0 → OK；
- **D1**：A=[4,4,3,4,4]（3.8±0.45）vs B=[0,0,0,0,0]，MWU p=0.0079，d=12.02；**D2**：5/5 vs 0/5，Fisher p=0.0079；**D3**：A=1.2 vs B=5.0，MWU p=0.0079，d=12.02；**D4**：A 全在 [1,3]，B 全 0；**副作用**：A 最大 541 字符 ≈270 token < 800。
- eval-report.json 统计 96 total / 42 PASS / 54 FAIL / 0 SKIP（FAIL 集中在 B 组与低校准负样本，属含负样本 case 集的正确语义）。
- CLI 等价路径 `tools/tool_eval.py --cases …` 亲自运行 → 同套 verdicts（Overall FAIL 为负样本集正确语义）。
- fixtures 5 场景 × 5 种子盲点核实存在。

### 5.3 结论恰如其分（判定：是）

"**有条件支持**"——报告将结论限定为"模拟一致 + 管线验证"层级，明确真实效应需路径 A/B 用同一 case 集复跑；三态判定框架（成功 4/4 无副作用、失败信号 1/2/3 均未触发）与 D-04 §8 一致。未夸大。

---

## 六、全量回归独立结果

亲自执行 `C:/Python312/python.exe -m pytest tests/ -q`（372s）：

**3867 passed / 64 skipped / 12 xfailed / 1 failed**

唯一失败：`tests/test_release.py::TestAC01VersionSync::test_pyproject_version_matches_git_head` —— pyproject=3.12.43 vs git HEAD=da4fb18（3.12.42）。这是项目"先 bump 再提交"约定（CHANGELOG 已记录）下的**预期瞬态**：bump 已在工作区完成、提交在验收后发生，验收提交（subject 含 3.12.43）后该测试自愈。非代码缺陷。

说明：批次证据中记录的另两个失败均已消除——`test_release_bump.py` 硬编码断言（src_version 动态化修复，12 passed）与 `test_manifest_t0095` 悬挂引用（T-0105 manifest 现已生成，测试通过；但注意该测试只校验 T-0095 清单，不覆盖 F-2 的 T-0105 指纹问题）。

新增测试独立重跑：`test_t0105_batch2.py`(21) + `test_t0105_batch3.py`(24) + `test_t0104_templates.py`(11) + `test_release_bump.py`(12) + `test_memory_injection.py`(14) = **82 passed**。

---

## 七、发现清单

### P0
无。

### P1（2 项，均为收尾流程缺口，非代码/约束缺陷）
- **F-1 连续性漂移（validate_state exit 2）**：bump 3.12.43（11:20:49 写入 `.ai/version-manifest.yaml`）后未重跑官方 `repair_continuity.py` + `close_session.py`。记录 hash EDA29293… vs 实际 E90C0B47…。亲自执行 `validate_state.py .` → `[error] Continuity source drift: .ai/version-manifest.yaml`，exit 2。与批 4 证据"0 连续性漂移"表述在审查时点不符（批 4 时点属实，bump 后回退）。阻断 AC-07（release check 6/6）直至修复。
- **F-2 evidence-manifest 指纹陈旧**：`fixes/batch4-sync-eval.md` 条目记录 8933B/0343DAA2…，实际 9698B/C0188951…（文件 11:17 定稿晚于 manifest 生成）。HANDOFF 的 unverified 列表已自标记 `EVIDENCE_FINGERPRINT_MISMATCH`（`evidence_manifest.py` 官方校验模块的语义）。阻断 AC-10（证据链完整）；按 B-4-3 自定约定需重生成 manifest → 刷新 HANDOFF 引用 → 官方校验 0 mismatch。

### P2（1 项）
- **F-3 allowed_paths 与 bump 载体不一致**：任务卡授权"bump 3.12.43（8 载体原子写）"，但 allowed_paths 未列入 `.zcode-plugin/plugin.json`、`src/loop_engine/__init__.py`、`README.md` 三个载体路径。改动仅版本号字符串、走官方 release.py bump，无越权实质；建议任务卡/未来 gate 显式声明 bump 载体例外（前序任务同模式，系统性）。

### P3（3 项）
- **F-4**：批 4 证据"phases 5 项"不准确——config.yaml 实际 6 项（S4,S5,S6,S8,S9,S10）。
- **F-5**：批 2 证据"B-4-2×9"不准确——`TestConfigValidationB42` 实际 8 个测试（总数 21 正确）。
- **F-6**：`fixes/verify_ai_decision_ledger_path.py` 非幂等——每次运行再 append 一条 AD 记录，重复运行会使账本膨胀（建议脚本加"已存在则跳过"）。

### 观察项（非缺陷）
- **O-1**：G-T-0106-REQUIREMENTS pending gate（父会话登记、用户暂缓）——修复 F-1 后 validate_state 将仅剩该错误（exit 2 为 pending gate 预期语义），需用户决策，非 T-0105 范围。
- **O-2**：`guard-events.jsonl` 追加为 hook 健康检查自动观测数据（.ai/ 内），非人工写入。

---

## 八、总结论

1. **约束零弱化：确认。** hooks/ 与治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine/validate_state/context_loader）diff 全空；fail-closed 语义（inbox 空问题 raise、配置非法回退 disabled、缓存失败清缓存回退、store 损坏抛异常）不变。
2. **R11 微调：合规。** 编号与主体语义保留，仅放开轮次上限；三处同步引用一致；兼容测试通过。
3. **四批落地真实性：全部复验通过**（含 chain.yaml 零改动裁决的两条理由——消费方读安装副本、verifier 无 glob——亲自核实属实）。
4. **eval 实验：如实、可复跑、结论恰如其分**（96 case 重跑统计完全一致；零 LLM 调用；"有条件支持"限定恰当）。
5. **全量回归：3867 passed / 1 failed（预期提交前瞬态）/ 64 skipped / 12 xfailed**。
6. **发现：P1×2（收尾流程缺口 F-1/F-2）、P2×1（F-3 范围声明）、P3×3（F-4/F-5/F-6）**。

**裁决：CONDITIONAL_GO**——按第一节 C1/C2/C3 完成收尾序列（repair_continuity + close_session、重生成 evidence-manifest 并刷新 HANDOFF、验收提交后重跑版本同步测试）并复验后转 GO。批 1~4 的代码与文档改动本身无需返工。
