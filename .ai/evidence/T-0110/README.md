
## Golden 演进记录（T-0145/T-0146 2026-08-07）

golden-before.json 于 T-0145（metrics 生成器）与 T-0146（词表 BLOCK/REJECTED）
后重生成：governance_metrics 新增 build_mutation_metrics/build_gate_defense
两公开符号，MetricsReport.to_dict 新增 mutation_metrics/gate_defense 字段。
属功能演进（读侧计数替代手写快照），非拆分等价性回归；拆分等价语义
（加载器/度量/SLO/budget/DORA 结构）保持不变。

## Golden 演进记录（T-0149 2026-08-07 追加）

T-0149（P3 收尾包）后再次重生成：governance_metrics 新增
`_count_defense_drill_cases` 符号，render_markdown 新增 Mutation/Gate
Defense 区块渲染，build_gate_defense 的 defense_drill_pass_rate 改为
动态统计（缺失 → 0/0 fixture 值）。属功能演进，非拆分等价回归。
