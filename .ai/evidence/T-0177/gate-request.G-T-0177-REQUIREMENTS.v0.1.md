# Gate Request: G-T-0177-REQUIREMENTS

## 请求信息

| 字段 | 值 |
|------|-----|
| gate_id | G-T-0177-REQUIREMENTS |
| task_id | T-0177 |
| gate_type | user-approval（REQUIREMENTS） |
| status | pending |
| requested_at | 2026-08-11 |
| requested_by | ai（ZCode 主会话） |
| approval_required_from | user |

## 背景

外部五路并行深度评审（2026-08-11）对 loop-engine（zcode 分支，HEAD e5a048d
v3.12.67）产出 21 项发现。ZCode 侧已逐项只读验证：10/12 完全确认、2 项部分确认
（C3/H1 定位需修正）。用户指令（2026-08-11）："1、要做全量升级；2、但也要分析，
设计了这么久，为什么 loop agent 会有这么多的大漏洞，ai 的可信度在哪里"。

本 gate 请求批准 T-0177 全量修复任务（P0×2 / P1×4 / P2×4 / P3×9 + D-00 根因
分析交付物）。

## 提议范围

### 写入路径

- .ai/tasks/T-0177.md（已建）
- .ai/evidence/T-0177/
- .ai/state.yaml、.ai/task_graph.yaml、.ai/gates.yaml、.ai/HANDOFF.md
- .ai/PROGRESS.md、.ai/KNOWN_ISSUES.md、.ai/DECISIONS.md
- .ai/CONTRACTS.md、.ai/CODING_STANDARDS.md、.ai/CONVENTIONS.md
- hooks/scripts/gate_guard.py（C1 补 import json）
- hooks/scripts/loop_enforcement.py（C3 git 豁免收窄、H2 逃生开关加固）
- hooks/scripts/session_brief.py（M4 死代码清理）
- hooks/scripts/enforcement_degradation.py、hooks/scripts/hook_common.py（P2-1 接线）
- loop_core/state_machine.py（H3 边界匹配）
- src/loop_engine/quota_decision.py（H4 去 sys.path 污染）
- src/loop_engine/degradation.py、src/loop_engine/enforcement_degradation.py（P2-1）
- src/loop_engine/adapters/claude_adapter.py（M1 独立实现）
- agents/test-engineer/SKILL.md（P3-3 补全）
- tests/（新增/修改测试）
- docs/（P3-9 编号核查，仅补齐索引）
- 删除 hooks/scripts/loop_enforcement.py.bak（P3-5）

### 禁止动作

- 修改 AGENTS.md、.zcode/config.json、bundled-marketplace.json（T-0174 已处理）
- 安装/启用 skill、MCP、agent、automation、protocol、tool 行为
- 部署、回滚、改数据库、改权限、处理密钥、支付、生产数据、迁移
- 进入真实业务项目
- 重做 T-0174 的 hooks 修复（仅收口时提醒用户重启验证）

### high_risk_flags

deployment/rollback/database/permission/secret/payment/production_data/migration
均 false；runtime_behavior: true（hooks/ 与 src/loop_engine 修改，仅本仓库治理
路径，不涉外部系统）。

## 退出标准

- AC-D00 + P0~P3 全部 AC 达成（详见任务卡）
- 全量回归 0 新增失败（基线 25 failed 先与评审对齐确认性质）
- 独立审查 P0/P1 = 0
- 用户验收确认

## 说明

- 批准本 gate 只授权 T-0177 范围内的实现与文档修复。
- reviewer PASS / 测试通过仅为 evidence，不替代用户批准。
- 批准后按 P0 → P1 → P2 → P3 → 收口顺序执行，每批独立测试。
