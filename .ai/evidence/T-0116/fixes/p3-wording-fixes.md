# T-0116 修复记录：p3-wording-fixes

## 范围

修正 T-0108/T-0110/T-0111/T-0113 独立审查遗留 P3 措辞/口径记录 + T-0104 P3×4
建议类登记留档 + 历史任务卡状态同步。纯 .ai/ 文档级，产品代码零改动。

## 修正明细

| 来源 | 项 | 修正 |
|------|-----|------|
| T-0108 P3-1 | design-bh-integration.md F2 验收"exit code 非 0" | → "仅告警，exit code 与既有判定一致"（.ai/evidence/T-0106/design/design-bh-integration.md:38 + plan-task-roadmap.md:62） |
| T-0108 P3-2 | 任务卡 allowed_paths 版本载体 | 说明记录（T-0108/commands.md：bump 统一原子写载体为 F-03 流程约定） |
| T-0108 P3-3 | agents schema_status 静态 VALID | 说明记录（F7 契约测试锁定双端一致） |
| T-0108 P3-4 | implementation_design_diff actual_but_undesigned | 说明记录（工具保守口径） |
| T-0110 P3-1 | golden C 场景数 51→48 | 修正 commands.md ×2 + fixes/batch-c-enforcement.md；测试 docstring 不在 allowed_paths，记录说明 |
| T-0110 P3-2 | test_t0108_fixes 失败登记 | 补登记（continuity 漂移 repair 自愈） |
| T-0110 P3-3 | loop_enforcement.py.bak 口径 15 vs 16 | 说明记录 |
| T-0110 P3-4 | guard-events +307 行 | 说明记录 |
| T-0111 P3-1 | commands.md"git stash 基线即失败" | 修正（基线 f3553aa 测试通过，实为 HANDOFF 引用瞬态） |
| T-0111 P3-2 | commands.md"提交后恢复"预期 | 修正（T-0111 不触碰 hooks/，提交后仍红属预期） |
| T-0111 P3-3 | repair-classification-report 3719 快照 | 报告头部注明快照时间点 + commands 记录 |
| T-0113 P3-1 | 证据区零改动措辞 | 说明记录（conformance 时间戳/guard-events 自动产物另计） |
| T-0113 P3-2 | 36→28 vs 36→30 | 修正 execution-evidence.json + 任务卡 + gate scope + task_graph 节点 |
| T-0113 P3-3 | AC-05 版本待提交 | 说明记录（F-03 提交后自愈约定） |
| T-0113 P3-4 | t0108 状态敏感 | 说明记录（repair 后自愈，非缺陷） |
| T-0113 P3-6 | server.py 行号 38/58 | 修正任务卡 + T-0111 acceptance → 41/61 |
| T-0104 P3×4 | 建议类（召回过滤/容错/schema 时序/配置重读） | KNOWN_ISSUES 登记留档（不实施） |
| 历史 | T-0113/T-0114 卡 ## Status in_progress | → completed（消解 legacy warn） |

## 验证

- grep 复核：51 场景/36→28/exit 非 0/38/58 无残留（审查报告原文引用除外，已注明修正）
- validate_state 应全绿；全量回归与基线一致

## T-0122 补充：T-0104 P3 重复登记说明

T-0116 将 T-0104 P3×4 登记为"建议类不实施"——**未对照 T-0105 证据目录**。
T-0105 批 2（B-4-1~4）已全部实施这 4 项（召回过滤/配置校验/时序约定/读盘
缓存，test_t0105_batch2.py 21 测试）。T-0122 核实关闭并修正登记
（KNOWN_ISSUES 条目已更新；本登记为重复登记，非缺口）。
