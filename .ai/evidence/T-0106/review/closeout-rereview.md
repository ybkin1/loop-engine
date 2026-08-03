# T-0106 收尾复验报告（closeout-rereview）

- 复验人：independent-reviewer（独立复验子代理，fresh context）
- 复验时间：2026-08-03
- 复验对象：T-0106（BH 融合总设计 + 全仓库漏洞排查，candidate-only）CONDITIONAL_GO 放行项修复闭环
- 原裁决：CONDITIONAL_GO（`review/independent-review.md`，基线 fb9d194）
- 复验基线：HEAD = `ee023cf`（v3.12.44）；修复提交链：`e083f7b`（T-0106 设计 + 放行项修复，CONDITIONAL_GO→GO）→ `dcb6353`/`f796615`（T-0107 实施与治理收尾）→ `ee023cf`（T-0112 撤销 + F0 改述）
- 复验方式：只读。三文档全文核对 + 版本间 git diff 核对（e083f7b/HEAD）+ 30 项 P3 归属全量计数 + 抽查 5 项编号在 audit 中定位 + state/gates/task_graph/KNOWN_ISSUES/HANDOFF 状态核对 + `git status --short`

---

## 一、裁决：GO

原 CONDITIONAL_GO 全部放行项（P2-1 归属总表、P2-2/F7 依赖、P3×3 文档精度）与用户后续决策（F0 改述为外部边界说明）均已落实并经本复验逐项确认。**无 P0/P1/P2 残余。** 4 项 P3 均为撤销/修复后的陈旧文本未同步（roadmap T-0112 候选节、KNOWN_ISSUES 指针、audit 头行、T-0112 卡片内字段），不影响 T-0106 AC 达成与后续排布执行，不构成放行条件。正式转 **GO**。

---

## 二、逐项复验表

| # | 复验项 | 判定 | 证据 |
|---|--------|------|------|
| 1 | F0 修正：design-bh-integration.md L10 起 F0 节 = 外部边界说明 | **PASS** | F0 节（L10-21）标题"会话证据边界说明（外部项，不属 LE 融合范围）——2026-08-03 修正"，含修正记录（原 F0 为错误 scope 表述、Qoder 不得作为 ZCode 证据、原 T-0112 候选已撤销）、问题编号 `session-source-disabled`（KNOWN_ISSUES 保留为记录，不立项）、修正后目标改为"ZCode 原生会话证据路径"候选设计、改动边界"不修改任何外部 Qoder/BH 项目"。"启用 Qoder source roots"字样仅出现在修正记录中作为被否定的旧 scope 引用（L12-13），F0 节本身无任何将其作为活动计划项的残留表述。git diff 确认 F0 节由 `ee023cf` 新增（e083f7b 版本无 F0 节，L10 直接是 F1） |
| 2 | P2-1 归属总表：plan-task-roadmap.md「P3 项归属总表」 | **PASS** | roadmap L172-209「P3 项归属总表」存在，30 行全量核对：D1-3/5/6/7/8（5）、D2-3~8（6）、D3-3~8（6）、D4-4~11（8）、D5-3~7（5）= 30 项，每项含归属任务 + 一行理由；归属统计（L209）T-0107×6（D3-4/5、D4-5/7/8、D5-5）/ T-0108×9（D1-3/7、D2-8、D4-4/10/11、D5-3/6/7）/ T-0110×12（D1-5/6/8、D2-3~7、D3-6/8、D4-9、D5-4）/ T-0111×2（D3-3、D4-6）/ 不实施×1（D3-7）= 30 全覆盖，与汇总表（L130-134，P3×6/9/12/2 + 不实施）一致。抽查 5 项编号在 audit-design-gaps.md 真实存在：D1-5（audit L58）、D2-6（L72）、D3-4（L83）、D4-10（L102）、D5-7（L118）✓；T-0107 范围（L24-30）与 T-0108 范围（L53-55）与归属表互指一致；audit §五（L175）与归属表逐字一致且明示"T-0109（BH 分层期）不承接 P3" |
| 3 | F7 依赖：design-bh-integration.md F7 对 D5-5 依赖与 roadmap 归属一致 | **PASS** | design F7 依赖（L81）改写为"T-0107（D5-5 contract_verifier fallback 收窄——P3 归属经 plan-task-roadmap.md『P3 项归属总表』明确：D5-5 由 T-0107 解析器收敛族同批承担，本引用与 T-0107 范围一致）"；四文档对齐：归属总表 D5-5→T-0107（L205）、T-0107 范围含 D5-5（L30，P3 追加第 6 项）、design 依赖图 T-0107 节点含 D5-5（L100）、audit §五 T-0107 含 D5-5（L175）。原矛盾（D5-5 为 P3 不在 T-0107 范围）已消除 |
| 4 | 文档一致性：audit 统计 42 = P1×1+P2×11+P3×30，域分布表各域之和 = 42，三文档编号交叉引用 | **PASS** | audit 维度表（L130-135）：D1 8（1/2/5）、D2 8（0/2/6）、D3 8（0/2/6）、D4 11（0/3/8）、D5 7（0/2/5），合计 42 = P1×1+P2×11+P3×30，各维度行内复算正确（原 P3-1 的"合计 36"瑕疵已修）。域分布表（L141-147）：loop_core 26 + tools 4 + scripts 4 + hooks/scripts 4 + agents 3 + .zcode/tools 1 = 42（原 loop_core 20→26 修正成立，按主文件域逐项复算 D1:6/D2:6/D3:5/D4:4/D5:5 = 26 ✓）。交叉引用抽查：D5-5（audit L116 ↔ roadmap L205 ↔ design F7 L81 ↔ design 依赖图 L100）、D3-4（audit L83 ↔ roadmap L190/T-0107 范围 L25 ↔ 依赖图 L100）、D4-8（audit L100 ↔ roadmap L199/T-0107 范围 L29）、D1-7（audit L60 ↔ roadmap L181/T-0108 范围 L55 ↔ design F7 L79）、D5-7（audit L118 ↔ roadmap L207/T-0108 范围 L54 ↔ design F4 L52）均无矛盾 |
| 5 | KNOWN_ISSUES：session-source-disabled 保留为记录（未立项）；12 条修复项在 Recently Closed（T-0107） | **PASS** | KNOWN_ISSUES.md Open 区 L5：`session-source-disabled` 保留为记录（未立项，未并入 T-0107）。Recently Closed 区（L10-25）："2026-08-03: T-0106 排查确认的 12 条修复项全部移入 Closed — T-0107 修复，v3.12.44"，12 条逐条列出（D1-1、D1-2、D1-4、D2-1、D2-2、D3-1、D3-2、D4-1、D4-2、D4-3、D5-1、D5-2），与 audit P1/P2 全集一一对应，编号引用 audit-design-gaps.md；T-0107 提交（dcb6353）消息确认 12 条清零 |
| 6 | gate/state 一致性：G-T-0112 撤销注记；state idle；task_graph T-0112 rejected | **PASS** | gates.yaml G-T-0112-REQUIREMENTS（L5589-5607）：notes 含完整撤销注记（"2026-08-03 撤销（用户决策 + HANDOFF Scope Correction）：Qoder 为外部会话宿主，其会话数据不能作为 ZCode 验收证据，原 scope 为错误框定。task_graph 标记 rejected，state 回 idle；.ai/evidence/T-0112/ 保留为外部诊断证据；KNOWN_ISSUES session-source-disabled 保留为记录。gate 记录保持 approved 为历史事实"）。state.yaml L4：`current_task_id: null`（idle，current_phase S6-delivery）。task_graph.yaml L1217-1228：T-0112 `status: rejected`，description 含撤销记录。T-0112 任务卡 Status 节 = `rejected`（ee023cf 修改）。四者一致 |
| 7 | git 状态：工作区无 T-0106 相关未提交遗留 | **PASS** | `git status --short` 输出为空（clean）。T-0106 全部交付物（三设计文档、review 报告、evidence-manifest 等）已随 e083f7b 提交；无未跟踪/未提交的 T-0106 文件 |

---

## 三、残余发现

**P0（阻断）：无。**
**P1（严重）：无。**
**P2（中等）：无。** 原 P2-1（P3 归属缺口）、P2-2/F7（依赖矛盾）均已消除。

**P3（4 项，均为撤销/修复后的陈旧文本未同步，文档卫生级，不阻塞）：**
- **P3-A**：plan-task-roadmap.md L140-168「新增前置机制项：session-source-disabled（T-0112 候选，独立于 T-0107）」整节仍将 T-0112 呈现为活跃候选任务，修复目标第 1 条（L148）为"恢复/启用 Qoder 工作区会话证据源，修复 source-root 配置……"——与 design F0 修正记录（T-0112 候选已撤销）、task_graph rejected、G-T-0112 撤销注记矛盾。该节系 dcb6353（T-0107 期间）加入，ee023cf 撤销时未同步更新。建议：在该节头部追加撤销注记或整体移入历史/归档段。
- **P3-B**：KNOWN_ISSUES.md L5 尾部指针"→ 独立会话源恢复任务（T-0112 候选；不得并入 T-0107 代码修复）"仍称"T-0112 候选"，与已撤销事实不符。建议改为"已撤销（2026-08-03），保留为记录"。
- **P3-C**：audit-design-gaps.md L6 头行"修复排布见 T-0107（正确性）与 T-0109（性能/预算）"为旧排布残留：修正后 §五（L175）明示 T-0109 不承接 P3，P3 全部分派至 T-0107/8/10/11。建议头行改为"修复排布见 plan-task-roadmap.md『P3 项归属总表』"。
- **P3-D**：T-0112 任务卡基本信息表 `status: pending_approval` 与同卡 Status 节 `rejected` 不一致（ee023cf 只更新了 Status 节）。建议基本信息表同步为 rejected。

---

## 四、总结论

T-0106 的 CONDITIONAL_GO 放行闭环已全部落实并复验通过：

1. **P2-1（排布缺口）→ 已修**：「P3 项归属总表」30/30 全覆盖（T-0107×6 / T-0108×9 / T-0110×12 / T-0111×2 / 不实施×1），编号与 audit 一一对应，抽查 5 项真实存在；汇总表与 T-0107/T-0108 范围互指一致。
2. **P2-2/F7（依赖矛盾）→ 已修**：D5-5 → T-0107 在 design/roadmap/audit/依赖图四文档完全一致。
3. **P3×3（统计/文件名/行号）→ 已修**：audit 维度与域分布两表复算均为 42；F3 目标文件为 gate.schema.json；行号精度问题未再出现于修改后的引用。
4. **F0 改述（用户决策）→ 已落实**：F0 节改为外部边界说明，Qoder 证据边界、T-0112 撤销、ZCode 原生证据路径候选三要素齐备；state/gates/task_graph/任务卡四处状态记录与之一致。
5. **回归面**：工作区干净，无 T-0106 相关未提交遗留；KNOWN_ISSUES 12 条修复项已由 T-0107（v3.12.44）关闭清零。

残余 4 项 P3 均为撤销后的陈旧文本同步问题，不涉及设计语义、执行排布或治理状态，**不构成放行条件**。

**正式裁决：GO（closeout 确认，原 CONDITIONAL_GO 条件全部满足）。**
