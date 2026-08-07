# loopx (rye567) 深读留档 — T-0154

> subagent 深读记录（只读研究，克隆于 /tmp/loopx-rye）
> 深读时点：2026-08-07（commit a8f3201，v0.1.0 首发）

## 关键发现（摘要）

- 17 阶段线性状态机（环境检查→需求→采访（人工确认门）→Spec→设计→
  测试设计→开发→质量审计→健康门→发布就绪→close）
- 推进只能走控制器：record-stage 6 态（PASS/CHANGES_REQUIRED/BLOCKED/
  SKIPPED/ACCEPTED_RISK/NEED_HUMAN）、can-write、fail-review
- 风险分级：risk.yml critical_triggers→FULL；score_rules 打分→
  LIGHT/STANDARD/FULL + ACCEPTED_RISK + SKIPPED 白名单（MODE_SKIPPABLE_STAGES）
- 写入保护：can-write --kind business 显式解锁
- 收口：gate → git-gate（git 状态摘要）→ compound → close（close-evidence
  矩阵 + ci_coverage: LOCAL_ONLY 显式声明）
- 非侵入：不写用户 AGENTS.md；双宿主（Codex $loopx / Claude Code /loopx）

## 对 loop-engine 的借鉴（详见 docs/designs/T-0154-loopx-comparison.md）

P0: 风险驱动执行分级；P1: git-gate + LOCAL_ONLY 收口声明 / 阶段快照；
P2: Provider 事件契约 / 双宿主发行 / health.yml 三态策略
