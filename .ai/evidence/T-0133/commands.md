# T-0133 命令记录

- 2026-08-07 登记与批准：G-T-0133-REQUIREMENTS 由用户批准（按顺序完成全量处理）；T-0133 推进 in_progress
- 2026-08-07 实现：
  - loop_core/subagent_manifest.py：QualityPair dataclass + SubagentSpec.is_weighted/quality_pair +
    __post_init__ 强制（重量动作无配对 = ValueError，fail-fast）
  - loop_core/evals.py：EvalCaseResult.evidence_ref 字段 + finding_to_eval_case 断言化桥接 +
    finding_evidence_ref + EvalRunner 对 quality-pair case 强制"无引用=FAIL"（D-02 M5）
  - loop_core/guard_health.py：recompute_detection（任务粒度 + 24h 窗口 + 连续3失败 fail-closed）+
    run_sampled_recompute 抽样执行器（rate 0.1 配置化）
  - loop_core/observability.py：CHECK_RECOMPUTE 常量
  - loop_core/dispatcher.py：重试透传 is_weighted/quality_pair（P2-1）
  - agents 5 角色契约：quality-engineer/test-engineer/security-engineer/independent-reviewer
    when_to_use 前置（动作产出即触发）+ 只读校验规范；main-thread 质量配对规则
  - tests/test_quality_pair.py（17 用例）
- 2026-08-07 验证：153 相关测试 passed；全量 4274 passed 0 failed；release check 7/7；bump 3.12.65
- 2026-08-07 审查：CONDITIONAL_GO → P1×2（evidence_ref 强制 + 抽样执行器）修复 → 复核 GO
- 2026-08-07 收口：task_graph/gates/任务卡 completed；验收 7/7 AC PASS
