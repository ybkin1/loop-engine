# T-0128 命令记录

- 2026-08-07 登记与批准：G-T-0128-REQUIREMENTS 由用户批准（按顺序完成全量处理）；T-0128 推进 in_progress
- 2026-08-07 M1 确定性检出：
  - 新建 tests/seeded_defects/detector.py（6 个 AST/正则检出规则 + detect_all，纯函数可复算）
  - mutation_tester.py 新增 scan 子命令（--sample/--registry/--output）
  - 实测 M1 检出率 6/6（SD-001 f-string SQL / SD-002 缺校验 / SD-003 明文密码 / SD-004 除零无守卫 / SD-005 N+1 / SD-006 循环依赖）
  - 报告落盘 .ai/evidence/observability/mutation-report-m1.json
  - 测试 tests/test_mutation_scan.py（4 用例：6/6 检出/确定性/干净代码零误报/证据引用）
- 2026-08-07 M2 真实角色检出：
  - 派 security-engineer + quality-engineer 独立 subagent 审查 sample_code（只读、独立上下文）
  - findings 合并落盘 .ai/evidence/observability/reviewer-output-m2.json（7 findings，sd_ref 标注）
  - mutation_tester verify 子命令扩展 sd_ref 直配；实测 M2 检出率 6/6（100%）
  - 报告落盘 .ai/evidence/observability/mutation-report-m2.json
- 2026-08-07 release check 接线：scripts/release.py 新增 step_mutation_gate（PREFLIGHT 第 7 步，fail-closed：
  报告缺失即 FAIL；M1>=5/6 且 M2>=4/6）；tests/test_release.py idle 稳态测试同步 7/7
- 2026-08-07 KNOWN_ISSUES：seeded defects 未自动调用条目关闭（Recently Closed）
- 2026-08-07 bump 3.12.63（8 载体）
- 全量回归：后台运行中；独立审查 + 验收：待执行
