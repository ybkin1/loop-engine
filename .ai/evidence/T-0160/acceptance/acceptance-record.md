# T-0160 验收记录

验收结论：AC 全部 PASS

## 逐项验收

- **[AC-01] mini-loop schema v2 数据面**：tasks.json v2 + gates.json + state.json +
  events.jsonl + handoff.md 五件套（运行时 `~/.pi/agent/loop/<project>/`），实测生成 ✓
- **[AC-02] 迁移器**：pi-test-lab 旧 tasks.json（T-001/T-010/T-011）→ v2 保留，
  备份 `tasks.json.bak-2026-08-08-01-01-20-535-`，补 gate/state，
  events.jsonl 含 state.migrated，executor/delegation 字段保留，evidence 锚定
  （EM-T-010-21f1d87a 3 files / EM-T-011-6b8bfb59 2 files）✓
- **[AC-03] validate 校验链**：迁移后合法状态 [ok] state is usable；
  人为 pending gate → [error] PENDING_GATE（fail-closed）✓（govern.test.ts 用例）
- **[AC-04] gate 范围拦截**：allowed_paths 越界 write 拦截 + forbidden_actions
  命中 bash 拦截（isPathAllowed/matchesForbidden 判定测试通过）✓
- **[AC-05] 反幻觉补漏**：PASS+0 工具 → FAIL；FAIL+0 工具 → 闸门文本追加留痕 ✓
- **[AC-06] 证据锚定**：评审记录自哈希 + 任务 evidence 锚定；篡改 process/*.json →
  validate 报 EVIDENCE_ANCHOR_MISMATCH（测试实证）✓
- **[AC-07] 事件溯源**：状态变更追加事件 + stateSha256 锚定；手改状态文件 →
  replay-check 漂移检测（测试实证）✓
- **[AC-08] 升级协议**：评审 3 轮上限 → escalation.required 事件升级用户 ✓
- **[AC-09] 测试全绿**：govern.test.ts 17/17 passed（node --test）+ tsc 无错误 ✓
- **[AC-10] 部署与提交**：运行时部署 + pi-test-lab 实测 + pi-agent-extensions
  提交 ad56377 + 本仓库收口 ✓

## 附加发现与处理

- 运行时 `~/.pi/agent/extensions/mini-loop/` 存在用户 2026-08-08 02:32-02:36 开发的
  v2 雏形（delegate/quota/spawn/events/state/artifacts，执行委派 P0-A 试点），
  不在源码仓库——已整合（保留全部雏形功能 + 叠加治理机制），并同步回源码仓库
- hooks/ 零改动、loop_core 零触碰；未安装/启用新 skill/MCP/agent
