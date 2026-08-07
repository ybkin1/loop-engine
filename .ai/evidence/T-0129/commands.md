# T-0129 命令记录

- 2026-08-07 登记与批准：G-T-0129-REQUIREMENTS 由用户批准（按顺序完成全量处理）；T-0129 推进 in_progress
- 2026-08-07 演练实现：tests/test_defense_drills.py（11 用例）
  - R1~R6 拒绝路径：治理写豁免判定（is_governance_write）/非豁免路径/拒绝收敛
    （validate rc==0）/拒绝后无 approved gate 阻断/登记矛盾检测/pending gate fail-closed
  - E1 状态漂移 L1 恢复；E2 连续性漂移 --auto-sync 自动修复
  - E3 YAML 损坏：L1 失败确认（--repair 不可修不可解析 YAML）→ L2 快照回滚 + RECOVERY.md
  - E4 rounds 悬空心跳检测：新增 .zcode/tools/rounds_heartbeat.py（最小落地，
    完整心跳随 T-0134）；悬空 rc=2 / 闭合 rc=0 实测
  - E5 回滚不无脑删：真实破坏动作 + 恢复后快照存在/evidence 完整/guard-events
    append-only/RECOVERY.md 存在
- 2026-08-07 指标语义修正：metrics-report gate_defense 字段（rejected_requests 0/4477
  实测 + defense_drill_pass_rate 11/11）+ metrics-semantics.md 口径文档
- 2026-08-07 bump 3.12.64 提交 559c65a；P1 修复（心跳工具 + E3/E4/E5 增强 + R3 增强）
  追加提交
- 独立审查 CONDITIONAL_GO → P1×2 修复 → 复核；全量回归 0 failed
