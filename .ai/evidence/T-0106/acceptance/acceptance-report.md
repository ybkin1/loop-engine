# T-0106 验收报告 — BH 融合总设计 + 全仓库漏洞排查（candidate-only）

- 任务：T-0106（G-T-0106-REQUIREMENTS，approved）— Better Harness 融合与 LE 去臃肿升级总设计：
  批 1 全仓库设计漏洞排查 + 批 2 BH 融合 8 特性方案 + 批 3 共同弱点方案 + 批 4 整合任务排布 T-0107~T-0111
- 角色：governance-controller（编排与验收）；designer/audit（批 1~4）；independent-reviewer（独立审查）
- 执行时间：2026-08-03（UTC+8）
- 基线：git HEAD `fb9d194`（v3.12.43，T-0105）；**版本保持 3.12.43**（candidate-only，无代码变更）
- 任务文档：`.ai/tasks/T-0106.md`；审查报告：`.ai/evidence/T-0106/review/independent-review.md`

---

## 一、交付内容

| 批次 | 产出 | 规模 |
|------|------|------|
| 批 1 漏洞排查 | `design/audit-design-gaps.md`：D1-D5 五维度 × 4 代码域，**42 项发现**（P1×1/P2×11/P3×30），含 context_packager P1 专项（1000 字符截断无标记，实测 T-0105.md AC 节被切）与 D5 启发式推断补充（双解析器分歧等 7 项） | 22/22 抽查准确 |
| 批 2 BH 融合方案 | `design/design-bh-integration.md`：8 特性模块级方案（评估模型七态/单一数据源/gates 分层/文档路由/工具 capability 化/上下文打包/finding 契约化/契约测试），每特性含"必须保持"清单 | 8 特性 |
| 批 3 共同弱点方案 | `design/design-common-weakness.md`：5 巨文件拆分边界（行为等价验收）+ 魔法数字 M-1~17 集中化（4 落点）+ 修复器治理度量（guard-events check_type="repair"） | 3 项 |
| 批 4 任务排布 | `design/plan-task-roadmap.md`：T-0107~T-0111 排布（风险低→高，hook/内核全程不动），含 P3 项归属总表（30 项全覆盖） | 5 任务 |
| 登记 | KNOWN_ISSUES.md 新增 **12 条**（P1+P2 全集，编号引用 audit，注明 T-0107 修复） | 12 条 |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | 排查报告覆盖审计维度 × 代码域，文件:行号证据 + 分类；context_packager 专项 ≥5 处 | **PASS**（D1-D5 × 4 域，42 项全部文件:行号；专项 9 处；独立抽查 22/22 准确） |
| AC-02 | BH 融合方案覆盖 8 特性 + 必须保持清单 | **PASS**（8 特性逐项含"必须保持"（防篡改/fail-closed/审批闭环）；目标文件引用抽查真实） |
| AC-03 | 共同弱点 3 项（巨模块拆分边界/魔法数字清单/修复器治理） | **PASS**（5 巨文件外提表 + 行为等价验收；M-1~17 落点；度量方案可落地） |
| AC-04 | 任务排布 T-0107~T-0111 每任务 AC/依赖/风险/验收门/文件清单 | **PASS**（结构要素齐备；P2 放行项修复后 P3 归属全覆盖；依赖链低→高） |
| AC-05 | 已确认修复项 KNOWN_ISSUES 登记 | **PASS**（12 条 = P1+P2 全集，编号引用一致） |
| AC-06 | 仅 .ai/ 变更 + 设计文档与任务卡同步 | **PASS**（git diff 实证：产品代码零改动、版本载体未动） |
| AC-07 | 独立审查 GO | **PASS**（CONDITIONAL_GO → 放行项修复（P2×1 P3×3）→ GO 达成；约束零弱化确认） |

## 三、独立审查摘要（independent-review.md）

- **裁决：CONDITIONAL_GO → GO**（抽查 22/22 准确率 100%，行号精确率 ~86% 修正后核对）
- 约束零弱化：**确认**（仅 .ai/ 变更；hooks/、loop_core/、tools/、scripts/、agents/、.zcode/、tests/ 零改动；版本 3.12.43 未动；forbidden_actions 未改）
- P2 放行项：~18 项 P3 无任务归属 + F7 依赖矛盾 → 已修复（30 项 P3 归属总表 + F7 显式指向）
- P3 文档瑕疵：统计表 42 核对、gate.schema.json 文件名、行号 ±1~4 → 已修正（复验中 6 条 audit 原值正确未误改）
- 回归：全量 3867 passed / 1 failed（test_deployment_quality_checker 预存问题，worktree 基线复现确认非本任务引入）/ 64 skipped / 12 xfailed

## 四、裁决

**T-0106 验收通过（7/7 AC）。** BH 融合总设计 + 全仓库漏洞排查完成：
42 项设计漏洞（含 P1 截断）已定位并排布修复任务、8 特性融合方案就绪、共同弱点优化方案成型、
T-0107~T-0111 实施排布可执行。hook 强制层 0 改动、治理内核 0 触碰、版本保持 3.12.43。

## 五、下一步

T-0107~T-0111 按排布顺序待用户逐任务批准（T-0107 漏洞修复为下一候选，含 context_packager P1 清零）。
