# T-0177 执行证据（execution-evidence）

> G-T-0177-REQUIREMENTS 的 execution_evidence。日期：2026-08-11。

## 执行摘要

五路深度评审 21 项发现全量修复（P0~P3）+ D-00 根因分析。验证后 10/12 完全
确认、2 项定位修正（C3/H1），1 项不成立（L5：CONTRACTS.md 路径实际正确）。

## 修复项与证据

| 项 | 修复 | 测试证据 |
|----|------|---------|
| C1 | gate_guard.py 补 import json | test_gate_guard_lifecycle.py TestEmergencyBypassC1（2 用例，14 passed） |
| H3 | state_machine 段边界匹配 | test_state_machine_gate_matching.py（14 passed） |
| H4 | quota_decision 去 sys.path 污染 | test_quota_decision.py（14 passed 含劫持回归） |
| H2 | 逃生开关加固（TTL/审计/内容校验/fail-open） | test_hook_emergency.py（11 passed） |
| C3 | git 破坏性操作豁免收窄 | test_enforcement.py LoopEnforcementGitExemptNarrowing（9 用例，71 passed） |
| H1 | degradation 接线 + zcode 能力统一 STRONG + enforcement_degradation.py 删除 | test_degradation_wiring.py（8 passed） |
| M1 | 双适配器独立实现（_host_base 共享基座） | test_host_adapters.py（12 passed）+ test_dispatcher.py 回归 |
| M4 | session_brief 死代码清理 | test_t0121_session_check.py（12 passed）+ 实测输出 |
| M6/M7 | 评估留档（不修复，理由见评估文档） | .ai/evidence/T-0177/m6-m7-assessment.md |
| P3 | 文档同步 9 项 + L1/L2/L3/L4/L5/L6 | 见"P3 文档同步"节 |

## 全量回归

- 基线（评审实测 HEAD e5a048d）：4492 tests / 4391 passed / 25 failed / 64 skipped / 12 xfailed
- T-0177 实测：4535 tests / 4457 passed / **14 failed** / 64 skipped / 12 xfailed
  （新增 ~43 测试全过；失败净减 11）
- 剩余 14 失败分类：
  - 本任务引入 5 项：已修复 3（continuity drift 已 auto-sync / gate execution_evidence
    已补 / manifest 收口时创建）+ 2 项按约定更新（golden 基线重捕获、hooks 白名单
    扩展——T-0177 为 gate 授权行为变更，属预期基线演进）
  - 既有环境/基线漂移 4 项（与 T-0177 改动零交集，留档）：mypy 增量漂移
    （.zcode/tools/execution_relay 等 5 key）、security staging 假 key
    （.ai/staging/T-0167/debug_guard.py）、release check tmp 项目 mypy src 不可达、
    E2E 同源

## P3 文档同步

- PROGRESS.md 当前状态同步至 T-0177；角色数量 11→12（PROGRESS/01-requirements）
- test-engineer SKILL.md 空骨架 → 12 字段完整契约
- CONTRACTS.md enforcement level MEDIUM→STRONG（T-0174 证据，三处声明统一）
- CODING_STANDARDS/CONVENTIONS 补厚（含 T-0177 新约定）
- docs/04~05 编号缺口核查：从未创建（git 历史无删除），无悬挂引用，保持现状
- KNOWN_ISSUES 登记 T-0177 修复 + 观察项（M5/M6 身份验证 backlog）

## 收口后待办（用户动作）

**重启 ZCode 验证 hookCount > 0**（T-0174 插件登记生效确认）→ 关闭
KNOWN_ISSUES hooks-not-loaded 条目。
