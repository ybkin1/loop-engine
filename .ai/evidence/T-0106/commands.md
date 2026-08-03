# T-0106 批 2~4 执行记录（commands.md）

- 日期：2026-08-03
- 模式：candidate-only（只读排查 + 设计文档产出，零产品代码变更）

## 产出文件

| 产出文件 | 内容摘要 | 状态 |
|----------|----------|------|
| `.ai/evidence/T-0106/design/audit-design-gaps.md`（追加） | 批 2 补充 D5 启发式推断扫描：新增 7 项（D5-1~7，P2×2/P3×5）；更新汇总统计（D1-D5 共 42 项：P1×1/P2×11/P3×30）；更新建议排布 | 完成 |
| `.ai/evidence/T-0106/design/design-bh-integration.md`（新增） | BH 融合 8 特性模块级方案（F1 评估模型 / F2 单一数据源 / F3 gates 分层 / F4 文档路由 / F5 工具 capability 化 / F6 上下文打包 / F7 finding 契约 / F8 契约测试）；每特性含目标文件、改动方式、依赖、风险、验收、**必须保持**清单；依赖图 T-0107→T-0108→T-0109 | 完成 |
| `.ai/evidence/T-0106/design/design-common-weakness.md`（新增） | ①5 个巨文件拆分边界表 + 不拆主流程语义 + 行为等价验收；②魔法数字 M-1~17 清单与落点（constants/slo.yaml）；③修复器治理（guard-events 计数、缺陷归类、确定性兜底边界） | 完成 |
| `.ai/evidence/T-0106/design/plan-task-roadmap.md`（新增） | T-0107~T-0111 五任务：目标/范围/AC 草案/依赖/风险与缓解/验收门/变更文件清单；依赖图与汇总表；风险 LOW→MED 递增排布 | 完成 |
| `.ai/KNOWN_ISSUES.md`（修改） | Open 区登记 T-0106 已确认修复项 12 条（P1×1 + P2×11，编号引用 audit-design-gaps.md，注明 T-0107 修复）；既有 Open/Closed 项不动 | 完成 |

## 排查/验证操作摘要

- 只读扫描：`loop_core/` + `tools/` + `scripts/` + `hooks/scripts/` + `.zcode/tools/` 的 regex/startswith/split/位置推断模式 grep（D5 维度）
- 深读核实：context_controller（:355-538 naive YAML 解析 + 双解析器）、context_loader（:186-209/1255-1324）、intent_router（:626-738/1127-1183）、contract_verifier（:108-146）、memory_service（:52-70）、loop_enforcement（:158-159 EXIT 常量、:239-311 契约解析、:1600+ main/自愈链）、repair_continuity.py（全文）、validate_state（:360-404 REPAIR_MODE）、observability/governance_metrics（guard-events strict-parse）、state.yaml/gates.yaml/guard-events.jsonl 样本
- 行号真实性：全部发现均基于实际读取核实（非记忆推断）

## 硬约束执行

- 产品代码零变更：本次会话仅写 `.ai/evidence/T-0106/design/`（3 新 1 改）与 `.ai/KNOWN_ISSUES.md`；`loop_core/`/`tools/`/`scripts/`/`agents/`/`hooks/`/`.zcode/tools/` 全部只读
- hooks 强制层 0 改动、治理内核 0 触碰、fail-closed 语义不变（设计文档中"必须保持"清单逐特性标注）

---

## T-0106 独立审查放行项修复（P2-1 + P3×3，2026-08-03）

- **P2-1 P3 项任务归属补齐**：plan-task-roadmap.md 新增「P3 项归属总表」，30 项 P3 全覆盖——
  - T-0107 追加 6 项：D3-4/5（轮转族与 D3-1 同批）、D4-5/7/8（同文件同批最小 diff / 裸 except 正确性）、D5-5（解析器收敛族，F7 依赖项）
  - T-0108 追加 4 项：D1-7、D4-10/11（F7 agents 脚本输出收敛）、D5-7（F4 文档结构契约化）；D1-3/D2-8/D4-4 经 F6 显式化（既有）
  - T-0110 显式化 12 项：D1-5/6/8、D2-3/4/5/6/7（M-3/4/7/8/9/10/11 清单）、D3-6/8（timeout 落点）、D4-9、D5-4
  - T-0111 追加 2 项：D3-3（归档保留 + 跨归档链延续）、D4-6（读侧损坏行计数）
  - **不实施（记录留档）1 项**：D3-7（dev.py 日志轮转，audit 已分类"文档化即可"，dev 内部工具影响低）
- **F7 依赖对齐**：design-bh-integration.md F7 依赖声明明确 D5-5 归属 T-0107（引用 roadmap『P3 项归属总表』），消除"P3 不在 T-0107 范围"的文档间矛盾；F4 目标文件同步补充 docs/02-architecture.md front-matter designed_files:（消解 D5-7）
- **P3-1 统计表修正**：audit-design-gaps.md §三「按代码域」按主文件域逐项复算：loop_core 20→26、scripts 5→4、hooks/scripts 3→4（D2-6 跨 3 域计入主域）、tools/agents/.zcode/tools 不变，新增合计行 42 = 各维度和（D1:8/D2:8/D3:8/D4:11/D5:7）✓
- **P3-2 文件名修正**：design-bh-integration.md F3 与 plan-task-roadmap.md T-0109 变更文件 `gate.schema.yaml` → `gate.schema.json`（loop_core/schemas/ 实际文件名核实，无 yaml 版本）
- **P3-3 行号/表述修正**（audit-design-gaps.md）：D1-1 T-0105 长度 4365→4363、D2-6 tool_cost_tracker :18→:20、upgrade :247→:251、D3-4 append :489-492→:490-491、D3-6 scope_drift :14→:15、D4-2 对照区 ":1775 附近"→:1771-1777、D5-4 _INTENT_SPLIT_RE :1171-1183→:1171-1177、D4-8 表述（"本不会抛错"→冗余双重计算 + 双类型防御，root 为 str 时 Path 除法抛 TypeError）
  - 复验结论（review 声称 ±1 偏差但 audit 原值正确、未改）：D5-1 list_keys :473、D5-5 def :108 / warning :116、D5-6 _VERDICT_RE :63
- 行号修正均经 grep/sed 对实际代码逐条复验（upgrade.py:251、tool_cost_tracker.py:20、scope_drift_detector.py:15、runtime_controller.py:490-491、intent_router.py:1171-1177、loop_enforcement.py:1771-1777、context_controller.py:473、contract_verifier.py:108/116、memory_service.py:63、T-0105.md wc -m = 4363）
