# T-0137~T-0143 批量登记记录

## 登记时间

2026-08-07T18:00:00+08:00

## 背景

- T-0136 决策包：用户选择**选项 A**（全量三批落地）→ 登记 T-0137~T-0142
- 用户提出 `.ai/evidence/observability/legacy-issues-summary-2026-08-07.md`
  遗留问题 → 登记 T-0143 修复包

## 遗留问题核验结论

legacy-issues-summary 中各项经代码核验**全部仍存在**：

| 项 | 核验证据 |
|---|---|
| 1.1 security 证据时间戳漂移 | scripts/certification_runner.py + agents/security-engineer/scripts/run_security_scan.py 写 .ai/evidence/security/*（带当前时间戳） |
| 1.2 validate_state YAML 崩溃 | main() 顶层无 try 保护（governor_lib.py:473 抛 GovernanceError，validate_state.py 未捕获） |
| 3.2 gov_delegation approved_by 硬编码 | .zcode/tools/gov_delegation.py:61 "approved_by": "user" |
| 2.1 cli_entries 不在分发集 | loop_engine/cli_entries.py 顶层命名空间包 vs setuptools src 布局 |
| 3.1/3.3/3.4/4.1/4.2/4.4 | 对应代码文件存在且无修复痕迹 |

## 本次登记（7 任务 + 7 gate）

| 任务 | 标题 | 优先级 | Gate |
|---|---|---|---|
| T-0137 | 容量规划与压测模板落地 | P0 | G-T-0137-REQUIREMENTS pending |
| T-0138 | 稳定性设计模板落地 | P0 | G-T-0138-REQUIREMENTS pending |
| T-0139 | 数据迁移模板落地 | P0 | G-T-0139-REQUIREMENTS pending |
| T-0140 | 性能诊断模板落地 | P1 | G-T-0140-REQUIREMENTS pending |
| T-0141 | 一致性设计模板落地 | P1 | G-T-0141-REQUIREMENTS pending |
| T-0142 | 架构与方法决策指南落地 | P2 | G-T-0142-REQUIREMENTS pending |
| T-0143 | 遗留问题修复包 | P1+P2 | G-T-0143-REQUIREMENTS pending |

依赖链：T-0136 → {T-0137, T-0138, T-0139, T-0143}；T-0139 → T-0140 → T-0141 → T-0142

## 验证

- gates.yaml YAML 有效（97 gates），7 新 gate allowed_paths/forbidden_actions 完整
- task_graph 7 节点 + 8 边
- validate_state：唯一 error = 7 个 pending gate（预期，待用户批准）
- HANDOFF 已 auto-sync 重生成（USER_DECISION_REQUIRED）

## 待用户决策

批准/拒绝/请求修复 7 个 REQUIREMENTS gate（可分批：P0 批先行或全部批准）。
