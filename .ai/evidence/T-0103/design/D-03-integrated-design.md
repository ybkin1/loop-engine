# D-03 整合设计（candidate-only）— 四象限增强点集成方案（T-0103）

> 任务：T-0103（人机协作四象限方法论评估）
> 依据：D-01 资产盘点（A-xx/B-xx/C-xx/D-xx/E-xx/F-xx/G-xx 条目引用）、D-02 差距分析（P1-1/P1-2/P1-3 + P2-3 + P3）
> 范围：5 项增强点的**整合设计候选**（设计-1 ~ 设计-5）。全部为 candidate-only：
> **本文件不修改任何生产文件；所有模板/字段/步骤文本均为"可直接采用"的候选文本，
> 待用户 gate 批准后方可落地。** 落地时需转正式任务并走既有治理流程。
> 硬约束遵守：不触碰 hook 强制层（C-01~C-13 全部零改动）、不触碰治理内核（D-18 系零改动）、
> 与 loop 哲学兼容（Gate 是用户决策、evidence≠approval、fail-closed、必填表单、契约 Schema）。
> 行号引用基于 2026-08-02 实际读取。

---

## 0. 设计总览

| 设计编号 | 名称 | D-02 来源 | 优先级 | 主要落点 | 成本 |
|---|---|---|---|---|---|
| 设计-1 | 开工前盲点自检 | P1-1（Q3 空白象限补全） | P1 | task-card.md + loop-governance SKILL.md | 低 |
| 设计-2 | 任务卡 Q1-Q4 定位声明区 | 表 1 横向（象限切换判据）+ P3 | P1+P3 | task-card.md + main-thread SKILL.md | 低 |
| 设计-3 | 执行中偏离日志统一化 | P1-2 | P1 | developer SKILL + main-thread SKILL + approval_ledger 记录类型 + gate 呈现 | 中低 |
| 设计-4 | 执行后反向考察 | P1-3 | P1 | human-review-packet.md + 验收记录字段 | 低 |
| 设计-5 | 执行前简报 4 要素补全 | P2-3 | P2 | task-card.md + context_loader/role_orchestrator 调用点 | 低 |

设计-1 ~ 设计-5 相互独立、可分批落地；设计-2 是设计-1 的"上游判据"（先判定信息完整度，缺失才触发盲点自检/提问/方案），建议与设计-1 同一批落地。设计-3 的记录层与设计-4 的字段都落在既有记录载体上（gates.yaml approval 子块 / 验收报告），无新增强制机制。

---

## 1. 设计-1：开工前盲点自检（D-02 P1-1，Q3 补白）

### 1.1 目标

在任务开工前（执行前简报阶段），强制 AI 产出"影响结果但用户没想到的变量"清单（Q3 未知的未知），并与用户核对；将 loop 目前"事后才发现盲点"（事故/教训/复盘）改为"事前列举+用户确认"，把 Q3 转化为可处理的 Q1/Q2 输入。纯提示词+模板改动，零新代码。

### 1.2 现状（D-01/D-02 引用）

- **核心缺口**：无任何提示词/模板要求 AI 开工前列出"用户没想到但影响结果的变量"（D-02 表 1 Q3 行、D-02 表 3 结论"Q3 是空白象限"）。
- 现有机制只有 AI **自身**盲点声明：各角色 CONTRACT `known_blind_spots`（A-02 L12-17 等 12 角色）、role-capability-profiles `known_failure_modes/abstention_conditions`（A-13）——这些是"AI 不知道自己会什么"，不是"项目里用户没想到的变量"。
- 事后机制存在但缺事前：gate 教训（D-11）、复盘（D-13）、DEGR-009/011 事故封锁（B-11）、自审计（E-01）。
- 现有"必填表单"哲学（B-05，INDEX.md L3-7"缺任何必填项=打回重做"）是天然载体：新增节即成为必填项，由 main-thread 验收（A-01 §4 逐角色验证标准）强制执行，无需 hook 改动。

### 1.3 设计内容

#### 1.3.1 任务卡模板新增"盲点清单"必填节（候选文本，直接可复制）

注入位置：`skills/loop-governance/templates/task-card.md`，"范围与边界"节（L30-42）与"验收标准"节（L46）之间的分隔线处（L43-45，L44 为 `---`）新增以下整节：

```markdown
---

## 盲点清单（必填，≥3 条）

> 开工前必须完成：列出"可能影响本任务结果、但当前任务描述中没有明说"的变量。
> 这是 Q3 盲点自检——不是采访用户缺什么知识（那是 Q2），而是替用户列出**没被想到**的变量。
> 每条盲点必须同时回答三问：影响什么结果？不理会会怎样？要不要用户确认？
> 缺任何一条 = 任务卡不完整，主控验收打回。

| # | 盲点变量 | 若不考虑会怎样（后果） | 需要用户确认？ | 确认方式 |
|---|---|---|---|---|
| B1 | （例：目标用户的设备类型——移动端还是桌面端） | （例：只做桌面布局，移动用户不可用，验收阶段才发现=返工） | 是 | （例：随执行前简报一次确认，不单独提问） |
| B2 | （例：数据量级——几十条还是几十万条） | （例：内存方案在数据量级大时不可用，架构阶段要改方案） | 是 | ... |
| B3 | （例：并发/多人同时使用） | （例：单用户假设下不做锁，多人使用数据互相覆盖） | 是 | ... |
| B4 | （例：隐私/合规——数据是否含个人信息） | （例：本地存储个人数据违反合规，上线前才发现） | 是 | ... |

**填写规则**：
1. 至少 3 条；每条必须来自任务描述之外的推断（若所有变量任务里已明说，则声明"无新增盲点"并给出理由——不允许空表）。
2. "需要用户确认"默认为"是"；仅当该变量可由 AI 在既有批准范围内自行兜底（如错误处理策略）时才填"否"并写明兜底方式。
3. 盲点清单在任务执行前随执行前简报一次性呈现给用户核对（与 main-thread CONTRACT R11"同阶段提问≤3 次"合并为同一次提问，不额外增加轮次）。
4. 用户确认/补充的盲点，执行后写入 `.ai/evidence/knowledge/knowledge-store.yaml`（经 memory_service 幂等去重，D-10），跨任务复用——把 Q3 变成 Q1（已确认事实）。
```

#### 1.3.2 loop-governance SKILL 启动检查清单新增"盲点简报"步骤（候选文本）

注入位置：`skills/loop-governance/SKILL.md` 启动检查清单（L26-35），在第 6 步（L35"6. 只在已批准的任务与 gate 范围内继续。"）之后新增第 7 步：

```markdown
7. **盲点简报（开工前，Q3）**：若当前任务的任务卡含"盲点清单"节且尚未向用户核对过，
   按任务卡盲点清单逐条向用户简报（每条一句话后果 + 是否需要确认），得到用户确认或补充后
   才开始执行。盲点确认结果写入任务卡"盲点清单"节（标注"已核对 + 日期 + 用户补充项"）。
   若任务卡缺失盲点清单节，视为任务卡不完整，回退到模板补全，不猜测直接开工。
```

配套（可选，同批）：`skills/loop-governance/examples/01-new-task-creation.md` 增加第四步"盲点简报"教学示例（在第三步"项目分级"之后，L54-60 附近），延续该文件既有的 Q2 教学风格（B-13）。

#### 1.3.3 注入点与影响文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `skills/loop-governance/templates/task-card.md` | 新增节（L44 处插入） | 盲点清单必填节 |
| `skills/loop-governance/SKILL.md` | 新增步骤（L35 后） | 启动检查第 7 步"盲点简报" |
| `skills/loop-governance/examples/01-new-task-creation.md` | 新增示例步骤（可选） | 教学示例第四步 |
| `agents/main-thread/SKILL.md` | 验收标准补充（可选，见 1.4） | §4 增加"任务卡盲点清单 ≥3 条"检查项 |
| `.zcode/skills/loop-governance/` 安装副本 | 同步（如适用） | 安装副本 templates/ 目前只有 gate-decision-summary.md/phase-acceptance-summary.md（无 task-card），若后续同步机制要求则走 loop-update |

#### 1.3.4 兼容性（不破坏现有必填表单校验）

- **任务卡无机器 schema 校验**：`.ai/schemas/` 8 个 schema（G-06）中无 task-card schema；`validate_state.py` 只校验任务文件存在（L351-355）与 task_graph 一致性；`task_contract.py`（.zcode/tools/）只解析任务文件 YAML 代码块中的 `developer_agent_id/reviewer_agent_id/phase` 三个字段（L43-77）。新增 markdown 节不影响任何解析器。
- **必填表单强制**由模板哲学（B-05 INDEX.md）承担，实际执行者是 main-thread 验收（A-01 §4）。若落地时要求"盲点清单缺失=打回重做"，需同步在 `agents/main-thread/SKILL.md` §4 角色验证标准表中加一行检查项（对应用户目标/任务卡维度），此为提示词层改动，不触碰 hook。
- **R11 提问上限兼容**：盲点核对并入执行前简报同一次呈现（1.3.1 规则 3），不增加提问轮次。

### 1.4 风险与回退

| 风险 | 等级 | 缓解 |
|---|---|---|
| 盲点节流于形式（AI 填 3 条套话） | 中 | 规则 1 要求"每条来自任务描述之外的推断 + 无新增时须给出理由"；main-thread 验收核对"与任务描述的差异度" |
| 核对动作增加用户负担（每任务一次简报） | 低 | 并入执行前简报/plan-approval gate 同一次呈现；"需要用户确认=否"项不打扰用户 |
| 模板改动影响存量任务卡 | 低 | 只新增节；存量任务卡不回溯（新任务创建时生效） |
| 回退 | — | 删除新增节/步骤即完全回退（纯文档，无状态迁移） |

### 1.5 实现成本评估：**低**（2 个模板/提示词文件加节 + 1 个教学示例，约 1-2 小时编辑；无代码）

### 1.6 验收方式

1. 新建任务卡样例（T-XXXX 草稿）按新模板填写，盲点节 ≥3 条且每条含三要素，validate_state.py 通过、task_contract 解析不受影响。
2. main-thread 按新验收项检查：盲点节缺失/不足 3 条 → 打回重做。
3. loop-governance 启动检查第 7 步在真实会话中触发一次盲点简报并获用户确认。
4. 回归：`python .zcode/tools/validate_state.py` 零新增报错；现有任务卡（如 T-0103 自身）不受影响。

---

## 2. 设计-2：任务卡 Q1-Q4 定位声明区（D-02 表 1 横向 + P3）

### 2.1 目标

补上"象限切换判据"：AI 在开工前显式声明本任务的"信息完整度"（目标/受众/边界/格式 4 项），并据声明映射到行为模式（Q1 直行 / Q2 提问 / Q3 自检 / Q4 方案）。让"已知的已知是否成立"成为显式判定步骤，而不是靠 BLOCKED 兜底（D-02 表 1 Q1 行差距 1）。

### 2.2 现状（D-01/D-02 引用）

- 意图路由只做"模式分级"（FULL/STANDARD/LIGHTWEIGHT，D-08），不做"知识象限"分级（D-02 表 1 横向差距）。
- main-thread SKILL（A-01）有 11 角色验证标准（L89-185）与输出格式（L187-239），无"信息状态→行为模式"映射规则。
- 任务卡现有"用户可见目标 / 范围与边界 / 验收标准"（task-card.md L22-53）已隐含 4 要素但无显式 ✓/✗ 声明。
- R11"同阶段提问≤3 次"（A-02 CONTRACT L27）是 Q2 行为的上限约束，设计-2 的映射表需与其兼容（每轮≤3、可多轮属 P2-1 范畴，本设计不触碰）。

### 2.3 设计内容

#### 2.3.1 任务卡新增"信息完整度声明 + 象限判定"节（候选文本）

注入位置：`skills/loop-governance/templates/task-card.md`，"基本信息"节（L9-19）之后、"用户可见目标"节（L22）之前（即原 L21 空行处）：

```markdown
---

## 信息完整度声明 + 象限判定（必填）

> 开工前由 AI 逐项判定本任务的信息状态。**四项全 ✓ = Q1 直行，不提问、不猜测、直接执行；
> 任一 ✗ = 按映射表降级处理。** 此声明是任务卡必填项，缺 = 任务卡不完整。

| 维度 | 状态 | 判定说明（一句话） |
|---|---|---|
| 目标（用户要什么结果） | ✓ / ✗ | （如：✓ 任务描述已明确；✗ 只有方向没有结果标准） |
| 受众（谁用/谁看产出） | ✓ / ✗ | （如：✗ 未说明是内部还是外部用户） |
| 边界（做什么/不做什么） | ✓ / ✗ | （如：✓ 范围与边界节已列明非目标） |
| 格式（产出形态/格式） | ✓ / ✗ | （如：✗ 未说明交付物是文档还是可运行代码） |

**象限判定**（按上表自动映射，写入此处）：
- 四项全 ✓ → **Q1 直行**：不提问、不猜测，按任务卡直接执行；声明"假设为零"。
- 目标/受众/边界任一 ✗ → **Q2 提问**：围绕缺口向用户提问（每轮 ≤3 个，问题附"为什么问"），补齐后回到本表更新声明。
- 存在"影响结果但任务卡未明说的变量"（见盲点清单节）→ **Q3 自检**：按盲点清单节核对。
- 用户说不清但看到能判断（如界面风格、取舍偏好）→ **Q4 方案**：出 2-3 个可选方案随 gate-request 呈现，不自行拍板。
```

#### 2.3.2 main-thread SKILL"象限判定→行为选择"小节（候选文本）

注入位置：`agents/main-thread/SKILL.md` §2.2 速查（L60-67）之后新增 §2.3（或在 §3 执行流程"1. 接收阶段定义"前作为第 0 步）：

```markdown
## 2.3 象限判定 → 行为选择（开工前必做）

接收阶段定义后、冻结输入前，先读任务卡"信息完整度声明 + 象限判定"节：

| 信息状态 | 象限 | 行为模式 |
|---|---|---|
| 目标/受众/边界/格式 四项全明确 | Q1 已知的已知 | 直接执行不猜测：不提问、声明假设为零；产出与任务卡逐项对照 |
| 至少一项缺失但用户知道自己缺 | Q2 已知的未知 | 围绕缺口提问（每轮 ≤3 个，附"为什么问"）；补齐后回填声明节再开工 |
| 存在任务卡未明说但影响结果的变量 | Q3 未知的未知 | 按任务卡盲点清单节向用户简报核对（与 R11 合并为一次呈现） |
| 用户说不清但看到能判断 | Q4 未知的已知 | 出 2-3 个可选方案（方案/效果/风险）随 gate-request 呈现，AI 给推荐+理由，不自行拍板 |

约束：
- Q2 提问遵守 R10（先给 [AI判断] 再问）与 R11（每轮 ≤3 次，多轮属后续 P2-1 设计，本小节不放开上限）。
- 象限判定结果写入 SubagentManifest 的 aggregation_prompt（A-01 L198），让汇总阶段知道本阶段行为模式。
- 判定为 Q1 时，若执行中仍出现未声明变量 → 立即转入偏离记录（见设计-3），不得静默继续。
```

#### 2.3.3 注入点与影响文件清单

| 文件 | 改动类型 |
|---|---|
| `skills/loop-governance/templates/task-card.md` | 新增节（L21 处插入） |
| `agents/main-thread/SKILL.md` | 新增 §2.3（L67 后） |
| `agents/main-thread/CONTRACT.yaml` | 可选：fixed_stance 增加"象限判定先行"一句（L19-27 区）——不触碰 R10/R11 文本 |
| `USER-PROMPTS.md` | 可选：向用户解释"AI 会先声明信息完整度再决定是否提问"（F-05） |

### 2.4 风险与回退

| 风险 | 等级 | 缓解 |
|---|---|---|
| 象限判定流于自说自话（声明全 ✓ 但实际不全） | 中 | 任务卡四要素判定由创建者填写、main-thread 复核；执行中一旦出现未声明变量即触发偏离记录（与设计-3 联动） |
| 与 R11 冲突（Q2 连续提问被压制） | 低 | 本设计明确"每轮 ≤3、不放开上限"，放开属 P2-1 独立设计 |
| 声明节增加任务卡填写成本 | 低 | 每项一句话即可；缺省判定规则明确 |

回退：删除新增节/小节即完全回退。

### 2.5 实现成本评估：**低**（2 个文档加节 + 2 个可选同步点）

### 2.6 验收方式

1. 用 4 种信息状态（全 ✓ / 目标缺 / 盲点存在 / 说不清）各构造一个任务卡样例，main-thread 按 §2.3 映射输出对应行为（Q1 直行不提问 / Q2 提问 ≤3 / Q3 简报 / Q4 方案）。
2. 回归：R10/R11 原文零改动（git diff 验证 CONTRACT 仅 fixed_stance 可选加句或不动）。
3. SubagentManifest aggregation_prompt 含象限判定字段。

---

## 3. 设计-3：执行中偏离日志统一化（D-02 P1-2）

### 3.1 目标

把分散的偏离记录（developer known_deviations、project-manager 进度预警、R10 [AI判断] 标注）统一为结构化 deviation-log 三要素（新情况/改方案原因/替用户做的关键决定），并保证：(a) 角色产出 JSON 可携带；(b) [AI判断] 决策有落盘位（不可只说不记）；(c) 阶段 gate 呈现时用户一次性知情。不新增 hook、不改账本链机制。

### 3.2 现状（D-01/D-02 引用）

- developer 输出已含 `known_deviations`（偏离描述+adr_ref）、`unimplemented`（原因+decision_by）、`clarification_requests`（歧义）（A-09，developer/SKILL.md L63-82）——只覆盖"契约偏离"，无"新情况/改方案/替用户决策"三类通用记录。
- R10 `[AI判断]` 标注（A-02 CONTRACT L26）要求标注但**无结构化落盘**；账本（D-17 execution/audit/approval 三账本）记录工具调用与批准，不记录 AI 替用户做的决定。
- approval_ledger（D-17）现有 `ApprovalRecord` 是**用户**批准记录（human_actor 恒为 "user"，approval_ledger.py L63/L70），写入 gates.yaml 的 gate `approval` 子块（L169-227）——AI 决策记录不能混入该结构（语义冲突），需新增记录类型。
- audit_ledger（D-17）是链式 hash 追加 JSONL（`.ai/audit_ledger.jsonl`），事件类型枚举为 gate_advance/role_activate/veto/handoff（audit_ledger.py L27）——可扩展新事件类型，append-only 语义天然兼容。
- ledger_guard（C-09）只保护 `.ai/ledger/` 目录（LEDGER_DIR，ledger_guard.py L45），对目录内所有文件做追加+链校验（L74-87、L149-182）——新增 `.ai/ledger/ai-decisions.jsonl` 需遵循与 executions.jsonl 相同的 chain_hash JSONL 契约（execution_ledger.py L157-182），这是**兼容性要求而非障碍**（格式已有先例）。
- 阶段 gate 呈现（A-01 main-thread SKILL §5.2 L213-230）只有 verdict/roles/gate_presentation 三块，无偏离摘要。

### 3.3 设计内容

#### 3.3.1 deviation-log 结构化字段（通用，候选）

```json
{
  "deviations": [
    {
      "deviation_id": "DEV-S4-001",
      "phase": "S4-implementation",
      "task_id": "T-XXXX",
      "new_situation": ["执行中出现的新情况列表（任务卡/契约/计划中未声明的事实）"],
      "plan_change": "相对原计划/契约的改变（如：改为分两批实现、调整了实现顺序）",
      "reason": "改方案的原因（对照：原方案为什么不行/新情况为什么迫使改变）",
      "ai_decisions_made_for_user": [
        {
          "decision": "替用户做的关键决定（[AI判断] 内容）",
          "why_not_ask": "为什么没有问用户（R10 判断：低风险/可自行兜底/时间敏感）",
          "impact_if_wrong": "若此决定是错的，影响什么、如何回滚",
          "needs_user_review": true
        }
      ]
    }
  ]
}
```

字段规则（提示词层强制）：
- `new_situation` 与 `plan_change` 可为空数组，但 `reason` 必填（"改了什么、为什么改"）；缺任一字段 = 无效输出打回。
- 任何 `ai_decisions_made_for_user` 条目必须同时填 `why_not_ask` 与 `impact_if_wrong`（与 B-06 gate-request"风险代价"同哲学：用户需要知道代价与回滚路径）。
- `needs_user_review: true` 的条目必须进入本阶段 gate 呈现的偏离摘要（3.3.3），不得只写在产出里。

#### 3.3.2 developer 产出 JSON 扩展（对齐现有结构，候选）

注入位置：`agents/developer/SKILL.md` §5.1 implementation_summary.md JSON Schema（L50-87）。在 `known_deviations`（L76-82）之后新增：

```json
  "deviations": [
    {
      "deviation_id": "DEV-S4-001",
      "new_situation": ["实现中发现的、契约未声明的新事实"],
      "plan_change": "实现的调整（如：按契约实现但发现依赖缺失，改为先实现无依赖部分）",
      "reason": "调整原因",
      "ai_decisions_made_for_user": [
        {
          "decision": "[AI判断] 选择了 X 而不是 Y",
          "why_not_ask": "低风险且可在既有批准范围内兜底",
          "impact_if_wrong": "错误则影响性能而非正确性，可在 S5 质量门发现",
          "needs_user_review": true
        }
      ]
    }
  ]
```

兼容性说明：`deviations` 为**新增可选数组**（缺省 `[]`），现有 `known_deviations/unimplemented/clarification_requests` 字段及其语义**原样保留**（A-09 对齐，不破坏任何消费 known_deviations 的既有逻辑）；main-thread §4 开发工程师检查表（A-01 L129-137）同步加一项"deviations 数组格式合规"（提示词层）。

#### 3.3.3 阶段 gate 呈现强制附"偏离摘要"节（候选文本）

注入位置：`agents/main-thread/SKILL.md` §5.2 Gate 呈现包（L213-230）。gate_presentation 中文段落内强制包含以下小节（模板文本）：

```markdown
### 本阶段偏离摘要

- 新情况：N 条（列出每条一句话；空则写"无"）
- 方案调整：M 条（每条：原方案 → 现方案，一句话原因）
- 替您做的决定：K 条（每条：[AI判断] 内容 + 若判断错误的影响 + 是否建议您复核）
```

自检规则（§5.3，L232-239）增加：角色产出中 `needs_user_review: true` 的条目数 = gate 呈现偏离摘要中"替您做的决定"列出条数（不匹配 = 打回）。

#### 3.3.4 approval_ledger 新增"AI 决策记录"类型（候选）

落点设计（与现有格式兼容的三层方案）：

**第一层（记录载体）**：新增 `.ai/ledger/ai-decisions.jsonl`，格式与 executions.jsonl 完全一致（每行 JSON + `chain_hash`，chain_hash = SHA256(prev_hash || row)，见 execution_ledger.py L157-182）。ledger_guard 对 `.ai/ledger/` 全目录的追加+链校验（ledger_guard.py L54-87）自动覆盖该新文件——**落地前必须验证 verify_ledger_chain 对"空文件起步的新链"行为与 executions.jsonl 一致**（当前实现：空链返回 True，L87），验证通过则零 hook 改动。

**第二层（代码）**：`loop_core/approval_ledger.py` 新增 `AiDecisionRecord` dataclass 与 `AiDecisionLedger`（或最小化：仅新增 dataclass + append/read 方法，复用 `_sha256`/`_short_uuid` 既有工具，L40-47）。候选字段：

```python
@dataclass
class AiDecisionRecord:
    decision_id: str        # "AD-{uuid12}"（与 ApprovalRecord approval_id 同风格，L68）
    task_id: str            # T-XXXX
    phase: str              # S4-implementation
    role_id: str            # 做出决策的角色（developer/main-thread）
    decision: str           # [AI判断] 内容
    why_not_ask: str        # R10 判断依据
    impact_if_wrong: str    # 错误影响与回滚路径
    reason_ref: str | None  # 关联 deviation_id（3.3.1）或 gate_id
    recorded_at: str        # ISO-8601 UTC
```

**第三层（写入点）**：由 developer/main-thread 的偏离节产出经会话调度（loop_execute_phase.py 或会话自身）调用写入；写入动作需符合 loop "写入必须走受管工具"（C-08）与 ledger append 语义（C-09）。此层属落地实现细节，本设计只约定"记录类型+格式+写路径"。

不采用"复用 ApprovalRecord 塞 AI 决策"的原因：`human_actor` 语义为"Always user"（approval_ledger.py L63），混入 AI 决策会破坏 approval 记录的不可混淆性（用户批准 vs AI 自决是 D-02 的核心关切"evidence≠approval"）。

#### 3.3.5 注入点与影响文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `agents/developer/SKILL.md` | 扩展 JSON Schema（L82 后） | 新增 deviations 数组（可选，缺省 []） |
| `agents/main-thread/SKILL.md` | §5.2/§5.3 扩展（L213-239） | gate 呈现强制偏离摘要节 + 自检规则 |
| `loop_core/approval_ledger.py` | 新增记录类型（候选代码） | AiDecisionRecord + AiDecisionLedger |
| `.ai/ledger/ai-decisions.jsonl` | 新数据文件 | 链式 JSONL，格式同 executions.jsonl |
| `hooks/scripts/ledger_guard.py` | **零改动**（仅验证） | 落地前验证 verify_ledger_chain 对新文件兼容 |
| `agents/references/role-conflict-protocol.md` | 可选（A-16） | 升级呈现可引用偏离记录 |

### 3.4 风险与回退

| 风险 | 等级 | 缓解 |
|---|---|---|
| ledger_guard 对新 JSONL 链校验不兼容（若 verify_ledger_chain 隐含 executions.jsonl 特定字段） | 中 | 落地前先跑只读验证（对 .ai/ledger/ 下新文件的 append+verify 干跑）；不兼容则回退为"AI 决策记录写入 audit_ledger 新事件类型 ai_decision"（audit_ledger.py L27 事件枚举扩展，同样零 hook 改动） |
| 角色敷衍填偏离（全都空） | 中 | reason 必填 + main-thread 自检规则 3.3.3（呈现条数=needs_user_review 条数） |
| 偏离摘要增加 gate 呈现长度 | 低 | 每条一句话；空节写"无" |
| 用户被"替您做的决定"淹没 | 低 | 只有 needs_user_review:true 才进呈现；false 项只落盘不进呈现 |

回退：deviations 数组为可选字段，删除即回退；ai-decisions.jsonl 为新增文件，删除即回退（chain 链随文件删除重置，与 ledger 恢复协议一致，ledger_guard.py L48-49）。

### 3.5 实现成本评估：**中低**（2 个提示词文件扩展 + 1 个 dataclass/记录类型 + 1 个新数据文件；无 hook 改动）

### 3.6 验收方式

1. developer 产出含 deviations 数组且格式合规（main-thread 验收通过）；缺 reason / ai_decisions 缺 why_not_ask → 打回。
2. 一次真实 S4 执行：至少 1 条 [AI判断] 决策写入 `.ai/ledger/ai-decisions.jsonl`，`ledger_guard` 的 append+chain 校验通过（验证零 hook 改动成立）。
3. gate 呈现含偏离摘要节，呈现条数与 needs_user_review 条数一致。
4. 回归：现有消费 known_deviations 的逻辑（若有）零影响；`.ai/ledger/executions.jsonl` 链完整性不受影响（cross_validate 通过）。

---

## 4. 设计-4：执行后反向考察（D-02 P1-3）

### 4.1 目标

把"用户说接受"升级为"用户答明白才算验收"：Human Review Packet 新增"理解确认"节，AI 解释后用通俗语言问 2-3 个理解性问题，用户回答正确才标记 `USER_ACCEPTED`（并记录 `user_comprehension_confirmed`）。纯模板+记录字段，不触碰 gate 强制层。

### 4.2 现状（D-01/D-02 引用）

- Human Review Packet 模板（B-07，human-review-packet.md）已有"用户需要做的决策/需要您说的一句话"（L79-84），是单向解释，无反向考察（D-02 表 2 执行后行差距 1）。
- `USER_ACCEPTED` 是 PASS 语义分层的一层（B-03，governance-lifecycle.md L36-38），**纯语义标签、无机器校验**（经 grep 确认 loop_core/tools/hooks/.zcode/tools 均无 USER_ACCEPTED 处理逻辑）——加字段不触碰任何强制层。
- 验收报告（acceptance-report）有固定头部格式，memory_service 以确定性正则解析（memory_service.py L28-40 `_ACCEPTANCE_HEADING_RE/_TITLE_LINE_RE/_GATE_LINE_RE`）——新字段若放在验收报告头部，必须保持现有正则可解析（向后兼容要点）。
- 考题素材源存在：gate 教训（D-11 gate_feedback，rejected/repair_requested → lesson）、knowledge_store pitfalls（D-09）、Human Review Packet"已知但未处理的问题"（B-07 §四）。

### 4.3 设计内容

#### 4.3.1 Human Review Packet 新增"理解确认"节（候选文本）

注入位置：`skills/loop-governance/templates/human-review-packet.md`，"六、下一步"（L79-84）之前新增：

```markdown
## 六、理解确认（用户答对才算验收）

> 请您回答下面 2-3 个问题，确认您真的理解了本阶段做了什么。
> 答对全部问题，本阶段才标记为"用户已接受"；答错或不确定，AI 会重新解释后再次提问。

| # | 理解性问题（AI 提问） | 参考答案要点（AI 内部，不展示） | 用户回答 | 判定 |
|---|---|---|---|---|
| 1 | （例：这个版本为您完成了哪三件事？） | （例：注册/登录/退出，不含找回密码） | （用户原话） | ✓ / ✗ |
| 2 | （例：我们明确没有做哪件事？为什么？） | （例：没做多设备同步——您选择了本地存储） | （用户原话） | ✓ / ✗ |
| 3 | （例：如果 X 出问题了，会发生什么、怎么处理？） | （例：数据只在本机，删除浏览器数据即丢失；回滚=恢复上次备份） | （用户原话） | ✓ / ✗ |

**规则**：
1. 问题必须来自本阶段实际内容，通俗语言、无术语；优先覆盖"最容易误解的点"（见 4.3.3）。
2. 用户回答与参考答案要点实质相符 → ✓；全部 ✓ → 本阶段验收记录标记
   `user_comprehension_confirmed: true`，之后才允许标记 USER_ACCEPTED。
3. 任一 ✗ → 不标记 USER_ACCEPTED；AI 重新解释该问题对应内容后重问（可重试，无次数上限但每次重新解释须换一种说法）。
4. 用户明确拒绝回答（如"不想做测验"）→ 记录 `user_comprehension_confirmed: false` 与原因，
   验收标记降级为"用户已接受（未做理解确认）"，呈现在下一阶段 Human Review Packet 中供用户知情。
```

#### 4.3.2 `user_comprehension_confirmed` 字段定义与落点（向后兼容）

| 落点 | 字段形态 | 向后兼容性 |
|---|---|---|
| 验收记录文件 `.ai/evidence/T-XXXX/acceptance/acceptance-report.md` | 头部新增一行 `> 理解确认：✅ 2/3（或 ⚠️ 未做/❌ 1/3）` | memory_service 解析正则（L28-40）只匹配 `# T-XXXX 验收报告` 标题、`> **T-XXXX: ...**` 标题行与 `> Gate:` 行——新增 `> 理解确认：` 行不匹配任何现有正则，**零影响**（已逐行核对正则模式） |
| gates.yaml 的 gate `approval` 子块（approval_ledger.py L190-206） | `ApprovalRecord` 新增可选字段 `user_comprehension_confirmed: bool \| None = None` | 可选字段 + `get_approval` 用 `.get()` 读取（L261 区同风格），存量记录无此键 → None（未采集），不破坏 `record_approval` 的键写入逻辑（L201-206 可选键追加风格相同） |
| `.ai/ledger/ai-decisions.jsonl`（设计-3 新文件） | 可选：`user_comprehension_confirmed` 事件（记录"用户答对/答错/拒绝"） | 新文件无历史兼容问题 |

#### 4.3.3 考题素材来源建议

1. **gate 教训**：`gate_feedback.py`（D-11）rejected/repair_requested 决策生成的 lesson——"用户上次没懂导致拒绝的点"是本阶段最高优先考题。
2. **本阶段"已知但未处理的问题"**（human-review-packet.md §四）：用户需要知道"哪些事没做、为什么不现在做"。
3. **最容易误解的点**（与模板 §二/§三对照）：阶段概览与质量门结果中最易被误读的项（如"测试通过≠产品完成"，B-03 语义分层）。
4. **非目标/边界**（task-card.md L38-42"不做什么"）：用户常误以为包含的功能。
5. knowledge_store pitfall 类条目（D-09）中与本阶段相关的历史坑。

#### 4.3.4 注入点与影响文件清单

| 文件 | 改动类型 |
|---|---|
| `skills/loop-governance/templates/human-review-packet.md` | 新增"六、理解确认"节（L79 前），原"六、下一步"顺延为"七" |
| `loop_core/approval_ledger.py` | `ApprovalRecord` 新增可选字段 + `record_approval`/`get_approval` 键读写（候选代码） |
| `.ai/evidence/T-XXXX/acceptance/acceptance-report.md` | 格式约定（新增 `> 理解确认：` 行），非文件改动 |
| `skills/loop-governance/references/governance-lifecycle.md` | 可选：PASS 分层说明补充"USER_ACCEPTED 前须 user_comprehension_confirmed"（L36-38） |
| `agents/main-thread/SKILL.md` | 可选：§4 验证标准补充"Human Review Packet 含理解确认节" |

**不触碰**：gate_guard.py / loop_enforcement.py（USER_ACCEPTED 无机器校验，保持零改动）；gate 状态机（approved 语义不变，理解确认是"标记 USER_ACCEPTED"的前置条件而非 gate 前置条件——避免触碰 gate_guard 的 pending 阻断逻辑）。

### 4.4 风险与回退

| 风险 | 等级 | 缓解 |
|---|---|---|
| 用户反感"被考" | 中 | 规则 4 提供"拒绝回答"路径且不阻塞交付（降级标记+知情呈现）；问题用通俗语言、与用户利益相关（"数据丢了怎么办"） |
| 与 memory_service 正则解析冲突 | 低 | 4.3.2 已逐行核对：新头部行不匹配现有任一正则 |
| 理解性问题流于形式（AI 问废话） | 中 | 考题素材规则（4.3.3）强制来自 gate 教训/未处理问题/非目标 |
| 重问循环拖长验收 | 低 | 每次重新解释换一种说法；用户可随时选择"拒绝回答"降级路径 |

回退：删除"理解确认"节与可选字段即完全回退；字段 None 缺省保证存量数据零迁移。

### 4.5 实现成本评估：**低**（1 个模板加节 + 1 个可选字段 + 文档说明）

### 4.6 验收方式

1. 模板渲染样例：Human Review Packet 含理解确认节（2-3 问 + 判定列 + 4 条规则）。
2. 构造一次"用户答错 → 重新解释 → 答对"的模拟流程，验收报告标记 `> 理解确认：✅ 3/3`，approval 子块含 `user_comprehension_confirmed: true`。
3. 回归：memory_service 对新增头部行解析结果与改动前一致（确定性提取不受影响）。
4. 存量验收报告（如 T-0092 的 acceptance-report.md）在无该字段时一切正常（None 路径）。

---

## 5. 设计-5：执行前简报 4 要素补全（D-02 P2-3，低风险高收益）

### 5.1 目标

补全执行前简报缺失的 2 个要素："相关经验"与"不熟悉处"（D-02 表 2 执行前行差距 1），并让既有的记忆注入基础设施（D-01 D3）真正生效（当前默认关闭=形同虚设）。

### 5.2 现状（D-01/D-02 引用）

- 任务卡（B-05）有目标/范围/验收/禁止动作，无"相关经验/不熟悉处"字段。
- 记忆基础设施完备但默认关闭：context_loader `include_memories` 默认 False（D-01 L23-30；context_loader.py L806/L1122 `include_memories: bool = False`），memory_service recall（D-10）与 knowledge_store（D-09）均已就绪，context_packager 已注入 knowledge 前 3 条（D-02 L57-65）。
- 起点要素已有（session_brief 自动注入，C-02）；执行计划要素已有（planner 草稿+plan-approval Gate，D-07）。

### 5.3 设计内容

#### 5.3.1 任务卡新增"相关经验 / 不熟悉处"字段（候选文本）

注入位置：`skills/loop-governance/templates/task-card.md`，"用户可见目标"节（L22-26）之后、"范围与边界"节（L30）之前：

```markdown
---

## 相关经验与不熟悉处（必填）

| 字段 | 内容 | 填写来源 |
|---|---|---|
| **相关经验** | （例：T-0088 做过同款上下文压缩；knowledge-store 命中 2 条 lesson） | 从 `.ai/evidence/knowledge/knowledge-store.yaml` 按任务标签/关键词 recall（memory_service，上限 5 条）；无命中填"无" |
| **不熟悉处** | （例：本任务首次涉及前端移动端适配，此前只做过桌面端） | AI 对照相关经验与角色能力画像（A-13 known_failure_modes）如实声明；无则填"无" |

**规则**：
1. "不熟悉处"不得为空而不说明——无则不填"无"，有则必须写"我们没做过的部分"。
2. 有"不熟悉处"的任务：执行策略默认选择"更小步 + 更早展示中间产物"（与 Q4 原型思想一致，但本设计不引入原型机制，属 P2-2 范围）。
3. 不熟悉处若同时属于"影响结果的未明说变量"→ 并入盲点清单节（设计-1）请用户确认。
```

#### 5.3.2 context_loader 记忆注入默认开启（S4+）——调用点方案（候选）

**推荐方案（调用点开启，不修改默认值）**：

- 改动点 1：`loop_core/role_orchestrator.py`（D-04，PHASE_ROLES 表 L13-26）——在生成 SubagentManifest / dispatch 指令时，对 S4 及之后阶段（S4-implementation 及以后）的角色上下文加载显式传 `include_memories=True, memory_limit=5`。
- 改动点 2：`loop_core/context_packager.py`（D-02）——对 S4+ 阶段打包角色上下文时同样显式传 `include_memories=True`（若其内部调用 load_role_context_with_context 等入口，L66-67 执行模式声明处附近）。
- **不修改** context_loader.py L806/L1122 的默认值（保持 False）：改默认值影响全部调用者（含测试与轻量模式），违背"fail-closed 最小改动"；显式传参使 S4+ 开启成为可审计的显式行为，且可通过配置文件一键回退。

**回退方案**：
- 开关化：`skills/loop-governance/config.yaml` 新增 `memory_injection: {enabled: true, phases: ["S4","S5","S6","S8","S9","S10"], memory_limit: 5}`（配置节，非 hook 配置）；role_orchestrator 读取该开关，`enabled: false` 即完全回退到现状。
- 若 S4+ 阶段记忆注入造成 token 膨胀或行为漂移：先降 `memory_limit`（5→3→0），再整体关闭开关；记忆注入为纯附加节（context_loader.py L945-980：空召回即 no-op，L959-960），无状态迁移。

#### 5.3.3 注入点与影响文件清单

| 文件 | 改动类型 |
|---|---|
| `skills/loop-governance/templates/task-card.md` | 新增节（L28 处插入） |
| `loop_core/role_orchestrator.py` | S4+ 阶段显式传 include_memories=True（候选代码，落地需 gate） |
| `loop_core/context_packager.py` | 可选：S4+ 打包时传 include_memories=True |
| `skills/loop-governance/config.yaml` | 新增 memory_injection 配置节（非 hook 配置） |
| `agents/main-thread/SKILL.md` | 可选：§2.3 象限判定表 Q1 行引用"相关经验"字段 |

**不触碰**：context_loader.py 默认参数（保持 False，向后兼容全部现有调用与测试）；hook 层零改动。

### 5.4 风险与回退

| 风险 | 等级 | 缓解 |
|---|---|---|
| 记忆注入 token 膨胀（FULL ~2600 → +N×200） | 低 | memory_limit=5 上限既有（D-01 L117-123）；S4+ 才开；压缩器兜底（U3） |
| 召回条目不相关反而误导 | 低 | recall 按任务/gate/标签检索（D-10），上限 5；"相关经验"字段让 AI 显式判断相关性 |
| knowledge store 损坏 | 低 | include_memories=True 时 store 损坏 fail-closed（context_loader.py L957），回退开关即关闭 |
| 存量调用（测试/轻量模式）受影响 | 无 | 默认值不动，显式传参只影响 S4+ 调度路径 |

### 5.5 实现成本评估：**低**（1 个模板节 + 2 个调用点参数 + 1 个配置节）

### 5.6 验收方式

1. 任务卡样例含"相关经验/不熟悉处"节；知识库有命中时如实填入。
2. S4 阶段派发 developer 时上下文含"相关经验（Related Memories）"节（context_loader.py L26-27 既有渲染格式）；S1-S3 阶段不注入（对照组验证）。
3. `memory_injection.enabled: false` 时 S4+ 行为与现状逐字节一致（回归基线）。
4. 全量测试无回归（context_loader 相关测试 test_context_loader.py 默认值路径不受影响）。

---

## 6. 总影响文件清单表

> 路径均为项目根相对路径。改动类型：A=新增节/字段，M=修改现有内容，N=新增文件。
> "触碰 hook 强制层/治理内核"列：全部为 **否**（hook 仅一处"验证兼容"而非改动，见设计-3）。

| 路径 | 改动类型 | 设计-编号 | 触碰 hook 强制层/治理内核 |
|---|---|---|---|
| `skills/loop-governance/templates/task-card.md` | A（3 处新节：盲点清单 / 信息完整度声明 / 相关经验与不熟悉处） | 1、2、5 | 否（模板，必填哲学由 main-thread 验收承担） |
| `skills/loop-governance/SKILL.md` | M（启动检查新增第 7 步） | 1 | 否（技能提示词） |
| `skills/loop-governance/examples/01-new-task-creation.md` | A（第四步盲点简报示例，可选） | 1 | 否 |
| `skills/loop-governance/templates/human-review-packet.md` | A（理解确认节）+ M（节序顺延） | 4 | 否 |
| `skills/loop-governance/references/governance-lifecycle.md` | M（USER_ACCEPTED 前置说明，可选） | 4 | 否（决策材料） |
| `skills/loop-governance/config.yaml` | A（memory_injection 配置节） | 5 | 否（配置，非 hook 配置） |
| `agents/main-thread/SKILL.md` | A（§2.3 象限判定 + §5.2/5.3 偏离摘要 + §4 检查项补充） | 2、3 | 否（角色提示词） |
| `agents/main-thread/CONTRACT.yaml` | M（fixed_stance 可选加句；R10/R11 原文不动） | 2 | 否（角色合同） |
| `agents/developer/SKILL.md` | A（deviations 数组，可选缺省 []） | 3 | 否（角色提示词） |
| `loop_core/approval_ledger.py` | A（AiDecisionRecord + user_comprehension_confirmed 可选字段） | 3、4 | 否（记忆服务层，非内核；落地需 gate） |
| `.ai/ledger/ai-decisions.jsonl` | N（链式 JSONL 数据文件） | 3 | 否（数据文件；ledger_guard 兼容验证而非改动） |
| `loop_core/role_orchestrator.py` | M（S4+ 显式传 include_memories=True） | 5 | 否（上下文工程层，非内核） |
| `loop_core/context_packager.py` | M（可选：S4+ 传 include_memories） | 5 | 否 |
| `loop_core/context_loader.py` | **零改动**（默认值保持 False） | 5 | 否（刻意不动） |
| `hooks/scripts/ledger_guard.py` | **零改动**（仅落地前兼容性验证） | 3 | 否（hook 强制层零触碰） |
| `hooks/*` 其余全部、`loop_core` 治理内核（D-18 系）、`.ai/schemas/` | 零改动 | — | 否 |
| `.ai/evidence/T-XXXX/acceptance/acceptance-report.md` | M（格式约定：`> 理解确认：` 行） | 4 | 否（记录格式约定，向后兼容已验证） |
| `USER-PROMPTS.md` | A（可选：向用户解释新机制） | 2 | 否（用户侧提示词） |

**摘要**：设计-1~5 合计涉及 **14 个现有文件（均加节/加字段/加配置，无删除、无语义替换）+ 1 个新数据文件**；其中 10 个为提示词/模板/文档/配置，3 个为 loop_core 服务层（approval_ledger/role_orchestrator/context_packager，落地需独立 gate），**0 个 hook 文件改动、0 个治理内核（gate_guard/enforcement/hard_constraints/guard_health/state_machine 等）触碰**。唯一与 hook 的交互是设计-3 落地前对 ledger_guard 的**只读兼容性验证**（不改动）。

---

## 7. 落地顺序建议（candidate，转正式任务时参考）

1. **第一批（低风险纯文档）**：设计-1 + 设计-2 + 设计-4（三个模板/提示词加节，零代码）——同步改 task-card.md 的 3 个新节（一次编辑三节同批落地，避免反复动模板）。
2. **第二批（记录层）**：设计-3（developer SKILL 扩展 → main-thread gate 呈现 → approval_ledger 记录类型 + ai-decisions.jsonl，落地前跑 ledger_guard 兼容验证）。
3. **第三批（开关+调用点）**：设计-5（先加配置节与 task-card 字段，再改 role_orchestrator 调用点；`enabled: false` 先灰度）。
4. 每批独立 gate：由用户批准；D-04 eval 实验可在第一批落地前先跑（对照组基线）与第一批落地后复跑（实验组），以支撑"是否值得落地"的证据。
