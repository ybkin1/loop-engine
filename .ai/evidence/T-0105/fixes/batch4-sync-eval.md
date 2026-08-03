# T-0105 批 4：C-1 安装副本同步 + B-3 eval 最小实验 + C-2 AiDecisionLedger 真实路径验证

> 执行者：developer 子代理（批 4）
> 日期：2026-08-03

---

## 一、C-1 安装副本同步

### 1.1 同步前差异清单（`diff -rq skills/loop-governance/ .zcode/skills/loop-governance/`）

| 差异项 | 源（skills/loop-governance/） | 安装副本（.zcode/skills/loop-governance/） |
|---|---|---|
| config.yaml | 有 `memory_injection` 节（T-0104 设计-5）；无 `compile_threshold`/`compile_command`/`runtime_delivery` | **无** `memory_injection`；有 `compile_threshold: 0`、python 模板 `compile_command`、`runtime_delivery` 节（T-0078 部署专有） |
| SKILL.md | 有（含第 7 步盲点简报等） | **无** |
| examples/ | 4 个文件 | **无** |
| references/ | 3 个文件（governance-lifecycle/decision-rules/hook-protocol） | **无** |
| templates/ | 全套：INDEX.md、README.md、task-card.md、gate-request.md、human-review-packet.md、phase-delivery-index.md、architecture/coding/deployment/design/requirements/review/security/testing 子目录 | 仅 gate-decision-summary.md、phase-acceptance-summary.md（无其他） |
| chain.yaml | 与安装副本一致（diff 未列出，无差异） | 不变 |

### 1.2 消费方证据（决定同步方向的事实）

| 资产 | 消费方 | 读取目录 | 结论 |
|---|---|---|---|
| config.yaml | `loop_core/slo_gate.py`、`loop_core/second_failure.py`、`agents/quality-engineer/scripts/run_quality_gates.py`、`tools/loop_onboard.py`（作为新项目模板） | **只读 `.zcode` 安装副本**（GATE_CONFIG_REL = `.zcode/skills/loop-governance/config.yaml`） | **必须同步** |
| config.yaml | `loop_core/role_orchestrator.py`（memory_injection 消费方） | 先读源 `skills/...`，后 `.zcode` 回退 | 同步后回退路径也正确 |
| templates/*.md | `hooks/scripts/template_injector.py`（SessionStart 注入） | **只读源** `skills/loop-governance/templates`（TEMPLATES_DIR = `Path("skills")/"loop-governance"/"templates"`） | 模板消费方在源侧 |
| templates/*.md | 会话 AI（经 SKILL.md 资源索引） | 源 | 源侧 |
| SKILL.md / references/ / examples/ | 会话 AI / 文档引用；无代码消费方 | 源 | 源侧 |
| chain.yaml | `scripts/evidence_chain.py`、`tools/tool_evidence_chain.py` | `.zcode` 优先，源回退 | 已一致，零改动 |
| 安装副本 2 个专有模板 | 无代码引用（D-02/D-03 设计文档提及 B-07/B-14 背景）；T-0078 部署快照遗留 | — | 保留 |

### 1.3 同步决策（含理由）

1. **config.yaml → 合并同步到安装副本**（已执行）：
   - 把源最新内容（含 `memory_injection` 节）同步到 `.zcode/skills/loop-governance/config.yaml`；
   - **合并保留**安装副本专有节：`quality_gates.compile_threshold: 0`、python 模板 `compile_command`、`runtime_delivery` 节——这三个节分别被 `run_quality_gates.py`（只读安装副本）与 `scripts/runtime_delivery_gate.py`（T-0078）消费，删除会导致 S5 质量门/运行时交付门读默认值；
   - 同步后验证：YAML 解析通过；`memory_injection` 与源完全一致；`role_orchestrator._load_memory_injection_config` 加载正常（enabled=True/phases 5 项/limit 5）；`slo_gate` 加载安装副本配置正常。
2. **templates/ → 安装副本保持精简（不复制全套模板）**：
   - 唯一代码消费方 template_injector 读**源目录**；安装副本 2 个模板无任何代码/会话引用；
   - D-03 §1.3.3 已记录同一决策："安装副本 templates/ 目前只有 gate-decision-summary.md/phase-acceptance-summary.md（无 task-card），若后续同步机制要求则走 loop-update"；
   - 全套模板（含 task-card.md 盲点清单/信息完整度/原型交付 3 新节、human-review-packet.md 理解确认节）已在源侧生效。
3. **SKILL.md / references/ / examples/ → 安装副本保持精简**：无安装副本消费方；技能内容经源目录加载与引用（AGENTS.md 指引 + template_injector 源侧读取）；批 3 已确立"消费方读哪边就同步哪边"的先例（chain.yaml）。
4. **chain.yaml**：无差异，零改动。

### 1.4 同步后复验（`diff -rq`）

保留差异清单（全部为有意保留）：

| 保留差异 | 理由 |
|---|---|
| config.yaml 仍 differ | 安装副本 = 源内容 + memory_injection + **3 个部署专有节**（compile_threshold/compile_command/runtime_delivery），属有意超集 |
| SKILL.md、examples/、references/ 仅源有 | 安装副本保持精简（无消费方） |
| templates/ 全套仅源有；gate-decision-summary.md/phase-acceptance-summary.md 仅安装副本有 | 消费方在源侧；安装副本 2 个遗留模板保留不动 |
| chain.yaml | 一致，无差异 |

### 1.5 相关测试

`tests/test_t0105_batch2.py` + `tests/test_memory_injection.py` + `tests/test_t0104_templates.py` + `tests/test_evals.py` + `tests/test_ai_decision_ledger.py` + `tests/test_ledger_guard.py` = **116 passed**（config 加载、memory_injection 双路径、模板、eval、ledger 无回归）。

**全量回归**（tests/ 全量）：3866 passed / 64 skipped / 12 xfailed，2 failed 均为**既有问题**（非本批引入）：
1. `test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real` —— HANDOFF 引用 `.ai/evidence/T-0105/evidence-manifest.v1.yaml`，该 manifest 按批 2 B-4-3 约定在任务**完成时**创建；T-0105 未完成故暂缺（批 3 已记录同一失败，git stash 验证与本批无关）。
2. `test_release_bump.py::test_bump_invalid_version_is_usage_error` —— 测试硬编码版本 "3.12.41"，仓库在 T-0104 落地时已升至 3.12.42（`.ai/version-manifest.yaml` 无工作区改动），测试预期自 T-0104（commit da4fb18）起过期；应随 T-0105 收尾 bump 3.12.43 流程一并修正。

---

## 二、B-3 eval 最小实验（D-04 设计）摘要

- **完整报告**：`design/eval-experiment-report.md`
- **路径**：降级路径（D-04 §6 步骤 6 变体——**规则式模拟/构造性评估**）；评分 100% 复用 EvalRunner 自动化（EvalCase/EvalRunner/EvalReport/CLI 全链路真实运行）。未触发任何 LLM 外部调用（硬约束）。
- **结果**：5 场景（S1/S2/S4/S5/S6）× 2 组 = 10 份产出 + 2 份校准样例；96 个 EvalCase；校准通过（规则可区分高低质量）；**4/4 维度信号**：
  - D1 盲点覆盖率：A 命中 3.8/5（SD 0.45）vs B 0/5，MWU p=0.0079，d=12.0
  - D2 问题质量：A 5/5 含后果说明 vs B 0/5，Fisher p=0.0079
  - D3 返工风险：A 漏检 1.2 vs B 5.0，MWU p=0.0079，d=12.0
  - D4 用户确认次数：A 全部落在 [1,3]（R11 兼容）vs B 0（违反 ≥1）
  - 副作用检查：A 最大 541 字符 ≈ 270 token < 800 预算（无 token 膨胀）；无"拒绝开工/空清单"；无格式合规失败
- **信号判定**：≥3 维度显著占优且无副作用 → **成功信号成立**；但**结论限定为"模拟一致 + 管线验证"**（构造性数据，非真实模型效应测量；真实效应需路径 A/B 用本 case 集复跑）。
- **产物**：`.ai/evidence/T-0103/evals/blindspot-experiment/`（fixtures 5 份 JSON、prompts/、outputs/ 12 份、cases/cases-blindspot.yaml 96 case、eval-report.json、scores.csv、gen_cases.py、run_experiment.py 可复跑）

---

## 三、C-2 AiDecisionLedger 真实 S4 路径验证

- 通过 `loop_core.approval_ledger.AiDecisionLedger` **自身 API**（`AiDecisionRecord.create()` + `ledger.append()`，append 语义 + chain_hash 计算）真实追加 1 条决策记录到 `.ai/ledger/ai-decisions.jsonl`（**未手写文件**）：
  - `AD-7ce9f67bca96`，task_id=T-0105，phase=S6-delivery，role_id=developer，reason_ref=BATCH4-C1-SYNC-DECISION
  - 内容：C-1 安装副本同步采用"源最新内容合并同步"而非全量覆盖的决策记录
- **链校验**：`ledger.verify_chain()` → `(True, "chain verified (1 entries)")`（root seed 链从空账本起算）
- **ledger_guard 验证**：以 ZCode hook 调用方式子进程运行 `hooks/scripts/ledger_guard.py`（Write 到 .ai/ledger/ai-decisions.jsonl）→ **exit 0**（append-only + chain 连续校验通过）
- 验证脚本：`fixes/verify_ai_decision_ledger_path.py`（可复跑）

---

## 四、validate_state 结果

- 0 legacy warn（未新增）；0 连续性漂移（本批修复了父会话 task_graph.yaml 编辑导致的 2 项 hash 漂移，走官方 `repair_continuity.py` + `close_session.py`）
- **唯一 error：`G-T-0106-REQUIREMENTS` pending gate**（父会话 2026-08-03T11:20+08:00 创建 T-0106 任务时挂起，**非本批产生、不在本批范围**；按治理语义须由用户决策，AI 不得代批）。validate_state exit=2 为 pending gate 的预期行为。
- 需父会话向用户呈现该 gate 以恢复 `[ok] state is usable`。

## 五、硬约束自查

| 检查项 | 结果 |
|--------|------|
| hooks/ | 零改动（git diff --stat 空） |
| 治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine/validate_state/context_loader） | 零触碰（本批仅运行官方修复脚本重算 hash） |
| `.zcode/tools/`、`.zcode/config.json` | 零改动（仅运行 validate_state/repair_continuity/close_session） |
| fail-closed | 不变；未触碰任何 hook 与 gate 语义 |
| `.zcode/skills/loop-governance/` | 仅 config.yaml 合并同步（T-0105 授权范围内） |
| LLM 外部调用 | 零（eval 用规则式/构造性路径） |
| AiDecisionLedger | 走自身 API append + chain_hash，未手写 |
| 本批写出目录 | .ai/、.zcode/skills/loop-governance/、.ai/ledger/（API 追加） |
