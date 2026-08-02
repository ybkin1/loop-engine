# D-04 B1 eval 最小实验设计 — 验证"开工前盲点自检"提示词效果（T-0103）

> 任务：T-0103（人机协作四象限方法论评估）
> 目的：为 D-03 设计-1（开工前盲点自检，D-02 P1-1）提供**落地前证据**：
> 单一变量对照实验，验证"任务启动时注入盲点自检提示词"是否提升任务产出质量。
> 依据：loop_core/evals.py（EvalCase/EvalRunner/EvalReport，T-0092 落地）、
> tools/tool_eval.py（CLI）、tests/test_evals.py（使用模式）、
> docs/designs/loop-v4-ai-agent-governance.md §1（B1 eval 栈设计，统计门禁 pass@k）。
> 本文件为实验设计（candidate-only），实验执行属后续正式任务（落地需 gate）。

---

## 1. 实验目标与单一变量

**研究问题**：在任务启动时向 AI 注入"开工前盲点自检"提示词（D-03 设计-1 §1.3.1 的盲点清单节文本），是否显著提升任务开工产出（盲点清单+执行前声明）的质量？

**单一变量（唯一自变量）**：
- **实验组（A）**：任务提示词 = 任务卡文本 + 盲点自检提示词（D-03 设计-1 候选文本："开工前列出≥3 条影响结果但任务未明说的变量，每条含'若不考虑会怎样'+是否需要用户确认"）。
- **对照组（B）**：任务提示词 = 任务卡文本（现状，无盲点自检提示词）。

两组除该注入文本外**完全一致**：同一任务卡文本、同一模型、同一温度、同一输出约束。任何其他差异（模型/温度/任务文本/评分方式）均为实验缺陷。

**控制变量**：
- 模型与驱动：固定同一模型（经 `loop_core.llm` 驱动解析，evals.py L556-582 build_llm_driver 同路径），temperature=0（可复现优先）。
- 任务卡文本：每个场景一份固定文本（见 §3），两组共用。
- 输出约束：两组都要求"输出开工产出（盲点清单+执行前声明）"，长度上限统一（参照 output_policy 的 agent_eval 预算，evals.py L76）。
- 评分：全部评分规则/人工评委对组别盲评（评分前隐藏 A/B 标签）。

---

## 2. 实验对象：复用现有 B1 eval 栈

| 组件 | 现有实现 | 复用方式 |
|---|---|---|
| EvalCase（schema+校验） | loop_core/evals.py L100-223 | 每个评分维度一个 case；input = 该轮产出文本；rule = text_matches/text_contains/json_equals（规则断言优先，L52-57） |
| EvalRunner | loop_core/evals.py L587-656 | 跑 case 集 → PASS/FAIL/SKIP + stats；异常隔离；LLM judge 可选且永不阻断（L514-553） |
| EvalReport | loop_core/evals.py L675-744 | ReportBinding 绑定（task_id/phase/git_commit/timestamp），写 JSON 报告 |
| CLI | tools/tool_eval.py | `--cases <yaml> --report <path> --json` 直接复用（L20-42）；可选 `--llm` 启用语义 judge |
| 用例样式 | tests/test_evals.py + evals.py 内置 guard 样例（L806-905） | 新 case 沿用 `{"case_id","title","input","rule","severity","version","tags"}` 结构；tags 标 `experiment:blindspot`、`group:A/B`、`scenario:S1` |

**关键事实（决定实验形态）**：EvalRunner 是**离线断言引擎**——它评估"给定的产出文本/证据"，本身不运行 LLM 任务（default_executor 对无 command 的 case 直接透传 input，evals.py L349-393）。因此实验分两步：**第一步用 LLM 驱动生成两组产出（跑任务）**，**第二步用 EvalRunner 对产出做断言评分**。第一步需要一个最小"任务运行 harness"（见 §6 步骤 3，candidate 脚本），第二步 100% 复用现有栈。

---

## 3. 任务样本选择（3-5 个典型治理任务场景）

每个场景 = 一份"简版任务卡"（目标/受众/边界/格式 4 要素 + 验收标准），**并在设计文档中预埋 5 个"种子盲点"（隐藏变量）作为评分 ground truth**——种子盲点不写入任务卡文本，是"用户没想到、AI 应替用户列出"的变量（与 D-02 Q3 定义一致）。

| 场景 | 任务卡形态 | 预埋种子盲点（ground truth，不写入任务卡） |
|---|---|---|
| S1 需求澄清 | 小型个人待办 Web 应用需求整理（参照 skills/loop-governance/examples/01 形态） | 1 目标设备（桌面/移动）；2 数据量级（几十条 vs 几十万条）；3 多用户并发；4 数据隐私（个人信息合规）；5 浏览器兼容范围 |
| S2 架构设计 | 小型应用系统架构（模块划分+数据模型） | 1 未来扩展规模；2 第三方服务依赖可用性；3 部署环境（内网/公网）；4 迁移成本（存量数据）；5 团队维护能力 |
| S4 实现任务 | 按契约实现一个函数模块（含单元测试） | 1 输入数据非法值边界；2 并发调用；3 性能上限（大数据量）；4 环境差异（编码/时区）；5 依赖版本锁定 |
| S5 安全审查 | 对给定代码做安全审查 | 1 依赖供应链；2 密钥管理路径；3 日志脱敏范围；4 第三方库授权合规；5 生产流量峰值 |
| S6 交付检查 | 发布前交付检查（清单核对） | 1 回滚路径真实可用；2 监控告警覆盖；3 数据备份验证；4 文档与实际配置漂移；5 验收环境与生产差异 |

选择理由（与 loop 治理任务形态对齐）：覆盖 S1/S2/S4/S5/S6 五个强制人工评审阶段（docs/07-phase-specification.md L163-177 人工评审汇总表），且都是"必填表单+清单化"任务——盲点自检最可能在这些场景产生差异（对照 D-02 P1-1 的理由：未知的未知事后返工成本最高）。

---

## 4. 每组运行次数与统计口径

- **主设计**：5 场景 × 2 组（A/B）× 5 次 = **50 次产出**（自动化路径 A，§6）。
- **最小可行**：若资源受限，≥3 场景 × 2 组 × 3 次 = **18 次产出**（自动化或手工路径 B 均可），但统计检验仅作探索性参考。
- 运行次数理由：EvalRunner 单次秒级；LLM 生成 50 次约 1-2 小时（temperature=0 下每次输出 ≤800 token）。50 次足够做维度级均值比较与非参数检验（Mann-Whitney U，n=25/组）。
- 统计口径：连续维度（盲点条数、命中种子数、漏检数、确认请求数）用 Mann-Whitney U + 均值±SD + 效应量（Cohen's d）；二元维度（格式合规、每维度断言 PASS 率）用 Fisher 精确检验。显著性阈值 α=0.05（探索性实验，双侧）。

---

## 5. 评分维度（4 维）与断言化方式

| 维度 | 定义 | 评分方式（规则优先） | 断言示例（EvalCase rule） |
|---|---|---|---|
| D1 盲点覆盖率 | 产出盲点清单条目数 ≥3 条；且命中预埋 5 个种子盲点中的 k 个 | 规则：text_matches 正则统计条目（如 `B\d` 行数）≥3；对每个种子盲点用关键词 text_contains 判定命中 | `{"type":"text_matches","pattern":"(?:B\\d|盲点[0-9]|\\d+\\.).*"} `；种子命中 case：`{"type":"text_contains","value":"移动端"}`（S1 种子 1） |
| D2 问题质量 | 每条盲点是否含"若不考虑会怎样"后果说明 | 规则：text_contains 后果标志词（"若不考虑"/"后果"/"影响"/"否则"）；语义质量可选 LLM judge（fail-safe SKIP） | `{"type":"text_contains","value":"若不考虑"}`；LLM 版：`{"type":"llm","prompt":"逐条判断后果是否具体可执行","expected_conclusion":"PASS"}` |
| D3 返工风险 | 漏检种子盲点数（5 - 命中数）——越低越好 | 规则：5 个种子各一个"命中断言"case，未命中=FAIL；漏检数 = 该轮 FAIL 数 | 每种子一个 case（tags 带 `dimension:D3`），EvalRunner 直接产出每轮漏检数 |
| D4 用户需确认次数 | 标记"需要用户确认"的盲点条数；验证 ≤3（R11 兼容：同轮提问≤3）且 ≥1（存在需要用户决策的盲点） | 规则：text_matches 统计"需要用户确认：是"行数 n，断言 1≤n≤3 | `{"type":"text_matches","pattern":"需要用户确认[：:](是|\\u2714)","flags":0}` + 计数 case 断言范围 |

**评分纪律**：
- 规则断言为主（rule-first，evals.py L12-13 语义）；LLM judge 仅用于 D2 语义质量，且永不阻断（无 driver/UNKNOWN → SKIP，L514-553）。
- 人工评分维度（D3 的"返工风险"若需专家判断而非关键词）采用盲评：两组合并打乱，评委不知组别，用统一评分表（§7）。
- 所有断言 case 先对 2 份校准样例（一份已知高质量、一份已知低质量）验证区分度，再正式评分（校准先行，避免规则失效）。

---

## 6. 实施步骤

### 步骤 1：构造场景任务卡 fixture（0.5 天）
每场景一份 `scenario-S{1,2,4,5,6}.json`：`{scenario_id, task_card_text, seed_blind_spots:[5 个 {id, keyword, consequence_expected}]}`。存放在 `.ai/evidence/T-0103/evals/blindspot-experiment/fixtures/`（该目录属 T-0103 证据范围，可写）。

### 步骤 2：固化提示词注入文本（0.5 小时）
实验组注入文本 = D-03 设计-1 §1.3.1 盲点清单节文本（含 4 条填写规则）；对照组无。两组提示词结构：`system: 你是治理任务的执行 AI… + user: [任务卡文本]`（对照组）/ `… + [盲点自检提示词] + [任务卡文本]`（实验组）。唯一差异必须只有注入文本。

### 步骤 3：最小任务运行 harness（candidate 脚本，0.5-1 天）
新脚本 `tools/blindspot_experiment.py`（candidate，落地需 gate）：
- 复用 `loop_core.llm` 驱动（build_llm_driver 同路径解析，或显式传 driver），temperature=0，输出预算 ≤800 token（对齐 output_policy agent_eval）。
- 对 (scenario, group, run) 生成产出文本 → 写入 `.ai/evidence/T-0103/evals/blindspot-experiment/outputs/{group}-{scenario}-{run}.md`。
- 若驱动不可用（无 key/无配置）：自动降级到步骤 6 手工协议（fail-safe，与 evals.py 的 SKIP 哲学一致）。

### 步骤 4：EvalRunner 评分（完全复用现有栈，0.5 天）
1. 用步骤 1 的种子盲点生成 case 文件：`.ai/evidence/T-0103/evals/blindspot-experiment/cases-blindspot.yaml`（含全部场景×维度 case，tags 标 `experiment:blindspot`）。
2. 跑分（每组产出分别作为 case 输入——**注意 EvalCase.input 即产出文本**，default_executor 透传模式，evals.py L393）：
   ```bash
   python tools/tool_eval.py --cases .ai/evidence/T-0103/evals/blindspot-experiment/cases-blindspot.yaml --report .ai/evidence/T-0103/evals/blindspot-experiment/eval-report.json
   ```
   （`--report` 指向实验目录，**不覆盖**既有 `.ai/evidence/observability/eval-report.json`——那是 T-0092 的正式报告，DEFAULT_EVAL_REPORT 只用于缺省路径。）
3. 可选：`--llm` 启用 D2 语义 judge（无 driver 自动 SKIP，不阻断）。
4. 按 `group:A/B` 标签聚合（case tags），统计 4 维度均值/命中率/漏检数。

### 步骤 5：显著性分析 + 报告（0.5 天）
- 维度级比较（Mann-Whitney U / Fisher）+ 效应量；写入实验报告 `.ai/evidence/T-0103/evals/blindspot-experiment/report.md`（含：各组 4 维度统计表、成功/失败信号判定、原始数据链接、模型/驱动/commit 记录）。

### 步骤 6：最小手工协议（路径 B，当自动化不可行时）
1. 在真实治理会话中跑 3 场景 × 2 组 × 3 次 = 18 次"任务启动"：对照组按现状流程开工；实验组在会话中人工注入盲点自检提示词（把 D-03 设计-1 §1.3.1 文本贴入任务提示）。
2. 收集每次的开工产出（盲点清单/提问/计划）→ 存同一 outputs/ 目录。
3. 用统一评分表（§7 表 1）人工盲评 4 维度；评分表转存 `scores.csv`。
4. 将人工评分固化为 EvalCase（如 `json_equals` 断言分数）→ 与步骤 4 相同的 EvalRunner 流程跑回归（人工结果变成可重跑的断言基线）。
5. 手工协议耗时约 2-3 人天（见 §9）。

---

## 7. 需要回收的数据与记录位置

| 数据 | 位置 | 说明 |
|---|---|---|
| 场景 fixture（任务卡+种子盲点） | `.ai/evidence/T-0103/evals/blindspot-experiment/fixtures/` | 5 个 JSON，ground truth |
| 提示词注入文本（A/B 两版） | 同上 `prompts/` | 唯一变量固化件，含版本号 |
| 全部产出原文 | `outputs/{group}-{scenario}-{run}.md` | 50（或 18）份原始产出 |
| 评分 case 集 | `cases-blindspot.yaml` | EvalCase 结构，可复跑 |
| 运行结果（逐 case verdict/reason） | `eval-report.json`（实验目录内） | EvalReport 格式，含 stats/by_severity |
| 逐轮 4 维度得分表 | `scores.csv` | 规则断言分 + 人工盲评分（维度 D3/D4） |
| 显著性分析 | `report.md` | 统计结果、效应量、判定 |
| 运行环境记录 | `report.md` 头部 | 模型名、驱动、temperature、git commit（EvalReport 自动含 git_commit，evals.py L661-672）、日期、LLM judge 是否启用及 SKIP 数 |
| 会话级副产物（手工协议） | `outputs/` 同目录 + 会话命令记录 | 提示词实际注入方式、用户交互（若有） |

**记录纪律**：产出原文与评分分离存储（原文只读归档，评分可迭代）；任何一次评分规则调整必须保留前一版 case 文件（版本后缀），保证结论可追溯——与 loop"证据只可 supersede 不可删除"（B-03）一致。

---

## 8. 成功信号与失败信号

### 成功信号（实验组显著优于对照组 → 支持设计-1 落地）
1. **D1 盲点覆盖率**：实验组命中种子盲点数均值 ≥ 对照组 + 1.5 条（或 ≥3/5 条），且组间差异显著（p<0.05）或效应量 d≥0.8（n 小时以效应量为主）。
2. **D2 问题质量**：实验组"含后果说明"条目占比 ≥80%，对照组 ≤50%。
3. **D3 返工风险**：实验组漏检种子数均值 ≤ 对照组的一半（如 1.2 vs 2.8），且无"致命漏检"（漏掉 S1 数据隐私类合规盲点）发生。
4. **D4 用户需确认次数**：实验组确认请求数落在 1≤n≤3 区间（R11 兼容），不因注入而超上限。
5. 综合判定：**4 维度中 ≥3 维度显著占优且无副作用** → 判定支持落地。

### 失败信号（→ 不落地或修改设计）
1. **无显著差异**：4 维度均 p≥0.05 且效应量 d<0.5（提示注入无效或对照组产出已隐含盲点——需检查现状是否已被 known_blind_spots/A-13 能力画像覆盖）。
2. **副作用**：实验组产出长度超预算 ≥30%（token 膨胀）、或确认请求数 >3（违反 R11，需与 P2-1"每轮≤3 可多轮"设计联动）、或出现"拒绝开工/空清单"（注入导致 fail-closed 过度）、或模板格式合规断言失败率升高。
3. **规则失效**：校准样例未通过（规则无法区分高低质量）→ 实验结论无效，需先修评分规则（不算作提示词失败，但实验需重跑）。

**判定流程**：统计结果 → 对照上表 → report.md 给出"支持落地 / 不支持 / 有条件支持（附修改建议）"三态结论（与 loop gate 三态语义一致）。

---

## 9. 时间与成本估算

| 路径 | 工作量 | 成本 |
|---|---|---|
| **路径 A（自动化，推荐）** | 场景 fixture 0.5 天 + harness 0.5-1 天 + 评分与 case 集 0.5 天 + 分析报告 0.5 天 ≈ **2-2.5 人天** | LLM API 50 次 × ~1.5K token ≈ 数百 token/次 → 总 <$1-3（或本地模型零成本）；运行时长 1-2 小时 |
| **路径 B（手工协议）** | 18 次真实会话 0.5-1 天（20-40 分钟/次）+ 盲评评分 0.5 天 + 固化回归与报告 0.5 天 ≈ **2-3 人天** | 无 API 成本；占用真实会话时间 |
| 可选 LLM judge 校准 | +0.5 天 | 与路径 A 合并时计入 |

**总预算**：约 **2-3 人天**（路径 A 为主，路径 B 为降级）；对比设计-1 落地的成本（低，纯文档）与潜在收益（避免 Q3 类返工/事故，loop 已有 gate 教训证明此类问题真实存在，D-02 表 3 P1-1 理由），ROI 合理。

---

## 10. 威胁有效性（限制与缓解）

| 威胁 | 缓解 |
|---|---|
| 单模型结论外推有限 | 报告注明模型+版本；后续可换模型复跑（case 集可复用） |
| temperature=0 仍有随机性 | n=5/组均值化；记录每次种子值 |
| 种子盲点设计者偏差（选了容易命中的词） | 种子盲点来自 D-02 教训类资产的真实模式（gate 教训/复盘主题）；校准样例先行 |
| 手工协议中评委知道实验意图 | 盲评：合并打乱、隐藏组别、统一评分表 |
| 产出格式差异导致断言失效 | 输出约束统一（步骤 3）；规则断言失败时检查输出再判定（区分"规则失效"与"产出不合格"，见失败信号 3） |
| 与真实 loop 治理流程的差异（本实验是简化任务而非完整 12 阶段） | 明确定位为"提示词效果先导实验"；落地后仍需真实任务观察（可复跑手工协议） |
