# T-0109 验收报告 — BH 融合·分层期（F2-2/F3/F1/F5）

- 任务：T-0109（G-T-0109-REQUIREMENTS，approved）— T-0106 排布第三项：
  F2-2 写入收敛 + F3 gates 分层 + F1 评估模型 + F5 工具 capability 化
- 角色：governance-controller（编排与验收）；developer（四线实现）；independent-reviewer（独立审查）
- 执行时间：2026-08-03（UTC+8）
- 基线：git HEAD `1f02409`（v3.12.45，T-0108）；版本 bump **3.12.46**
- 设计依据：`.ai/evidence/T-0106/design/design-bh-integration.md`（F1/F2/F3/F5）+ `plan-task-roadmap.md` T-0109 节

---

## 一、四线交付

| 线 | 内容 | 关键产出 |
|----|------|---------|
| F2-2 写入收敛 | 状态写入统一经 governor_lib 事务写 + projection 刷新 | `write_state_files()` 收敛入口（SCOPE_VIOLATION fail-closed）+ state_machine 刷新调用（判定零改动）+ validate_state 零改动 + 静态检查（四类白名单） |
| F3 gates 分层 | active/archive + forbidden 外提 + gate_type 枚举 | gates.yaml **66 active** + archive **36 条 verbatim**（union 102 无删无重）+ forbidden-actions.yaml（26 引用/40 内联 0 mismatch）+ gate_type 枚举 30 值 + **active 域等价测试** |
| F1 评估模型 | 证据七态 + 评分上限表 + 指标分离 | `evidence_state.py`（七态 + 59/74/84/94/100 上限表）+ GateLesson evidence 字段 + Repair/Loop 指标分离 + slo.yaml score_caps + **advisory-only 双证（AST + 全仓 grep 零符号）** |
| F5 工具 capability | 36 工具分组/薄壳/合并/audience | 注册表 **36/36 全覆盖** + 6 薄壳消除（逐字节等价）+ dashboard 四层合并 + 证据链收敛 + 白名单注释级同步（+6/-2）+ **死工具候选 10 项留档待独立 gate（零删除）** |

## 二、AC 对照

| AC | 验收标准 | 结果 |
|----|---------|------|
| AC-01 | gates 归档 active 域等价 + schema 校验 | **PASS**（独立复算 66+36=102；12 phase 内核 heuristic 完整集==active 域） |
| AC-02 | 写入收敛 + 双写告警清零 | **PASS**（AST 静态检查四类白名单 + 告警清零测试） |
| AC-03 | F1 分档边界 + 评分不进 gate 决策 | **PASS**（5 档 parametrize + advisory 静态断言双证） |
| AC-04 | F5 注册表 36 全覆盖 + 行为等价 | **PASS**（36/36 + 6 薄壳逐字节等价 + dashboard/证据链合并等价测试） |
| AC-05 | 白名单一致性 | **PASS**（36 工具全在白名单目录 + hooks/ 仅白名单一处断言） |
| AC-06 | 全量回归 0 failed + compile + release check 6/6 | **PASS**（放行项修复后 4048 passed；3 项为已登记瞬态；compile/release check 通过） |
| AC-07 | 版本 3.12.46 == git HEAD | **PASS**（提交后成立） |
| AC-08 | 独立审查 GO + hooks/ 仅白名单 + 内核零触碰 | **PASS**（CONDITIONAL_GO → P1 修复（DR-002 宿主路径注入化）→ GO；hooks 单文件注释级 diff 实证） |

## 三、独立审查摘要（independent-review.md）

- **裁决：CONDITIONAL_GO → GO**（P1×1：F5 证据链收敛引入宿主路径违反 DR-002 → 已修复（CHAIN_YAML_CANDIDATES 纯相对路径 + 注入式保持语义 + 4 项宿主无关回归防护）；P3×2 记录/修复）
- 四线逐线 PASS（F2-2 判定零改动、F3 独立复算等价、F1 advisory 双证、F5 逐字节等价）
- hooks 专项：仅 loop_enforcement.py 白名单注释级（+6/-2），判定逻辑零触碰
- 约束零弱化确认：治理内核 diff=0、validate_state 零改动、**零工具删除**、fail-closed 不变
- 全量回归独立复验：4042 passed / 5 failed → 放行项修复后 **4048 passed / 3 failed**（3 项均为已登记瞬态：环境依赖/closeout/bump 前）

## 四、裁决

**T-0109 验收通过（8/8 AC）。** BH 融合·分层期落地：状态写入收敛、gates 分层、
评估模型（advisory-only）、工具 capability 化；hooks/ 仅白名单注释级、治理内核零触碰、
零工具删除（死工具候选 10 项留档）。版本 3.12.46。

## 五、下一步

1. **F5 死工具删除**（候选 A 6 薄壳 / B 4 弱引用 / C 3 legacy）：用户未批准删除 → 保留清单
   （`design/tool-removal-candidates.md`），建议 T-0111 终态审计 gate 统一决策
2. T-0110（共同弱点·常量集中 + 5 巨文件拆分）待用户批准

## 六、遗留记录

- P3-2（dashboard_views 别名 import 风格）留档
- 安全扫描双实现收敛、scripts/evidence_chain.py legacy 壳化 → 后续任务
