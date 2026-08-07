# 遗留问题汇总（除 T-0136 外）— 2026-08-07

> 供并行会话统一处理。来源：T-0127~T-0135 各任务独立审查的 P2/P3 遗留观察、
> 验收报告登记项、KNOWN_ISSUES Open 区、反复出现的工程性问题。
> 每项含：来源 / 问题 / 影响 / 建议处理。

---

## 一、反复出现的工程性问题（优先级最高）

### 1.1 测试套件非密封：security 证据时间戳漂移
- **来源**：T-0129/T-0133/T-0135 三次全量回归均复现；多次审查确认（pre-existing）
- **问题**：运行测试套件会重写 `.ai/evidence/security/security_summary.md` 与
  `security_report.json`（带当前时间戳）→ 已登记哈希漂移 → `validate_state` 报
  `CONTINUITY_SOURCE_DRIFT` → release check validate_state 步骤 FAIL
- **影响**：每次全量回归后必须 `--auto-sync` 收敛；t0108 两项 on_repo 测试
  隔离重跑必失败；CI 若跑全量+check 会假红
- **建议**：定位重写者（security scanner 测试路径）→ 固定时间戳或输出到临时目录；
  或将 security 证据从 continuity 源集排除（需评估证据语义）

### 1.2 validate_state 对不可解析 YAML 崩溃式 fail（exit 1 而非 exit 2）
- **来源**：T-0129 审查观察（E3 演练确认）
- **问题**：`validate_state.py` 对 state.yaml 的 `load_yaml` 无 try 保护，
  YAML 损坏时抛未捕获 traceback exit 1（非干净的 exit 2 fail-closed 语义）
- **影响**：损坏态的退出码语义不统一；外部消费者（release check/脚本）依赖
  rc 语义时可能误判
- **建议**：`main()` 顶层捕获 YAML_INVALID → 打印干净错误 + exit 2；
  补损坏态测试（正反例）

---

## 二、T-0135 遗留（审计收尾任务）

### 2.1 安装态打包：cli_entries 不在分发集
- **来源**：T-0135 审查 P2-1（接受范围内遗留，验收报告登记）
- **问题**：`loop_engine/cli_entries.py` 位于顶层 `loop_engine/`（命名空间包），
  而 `[tool.setuptools]` 是 src 布局（packages 仅 `src/loop_engine` + `loop_core`）
  → wheel 安装后 6 个 console scripts（loop-validate 等）ModuleNotFoundError
- **影响**：CLI 入口仅在仓库内可用；pip 安装态不可用
- **建议**：迁入 `src/loop_engine/cli_entries.py` 或显式文档化"仅仓库内使用"；
  改后需重新验证 6 入口（tests/test_cli_entries.py 12 用例）

---

## 三、T-0134 遗留（委托模式）

### 3.1 router.route() order 表不含 DELEGATED/MANUAL
- **来源**：T-0134 审查 P2
- **问题**：`loop_core/router.py` 的 route() order 表（约 L87）未登记
  DELEGATED/MANUAL——若 `user_forced_mode` 设为二者之一 → KeyError 崩溃
- **影响**：潜伏边缘（当前产品代码无调用方，但 DELEGATED 是正式枚举值）
- **建议**：order 表补两值，或显式拒绝（fail-closed）

### 3.2 gov_delegation approved_by 无验证机制
- **来源**：T-0134 审查 P2
- **问题**：`gov_delegation.py` register 硬编码 `"approved_by": "user"`，
  无任何用户交互验证；gates.yaml 在 GOVERNANCE_EXEMPT 内，register 不被 hook
  拦截 → AI 可自授委托而无需用户动作
- **影响**：委托链授权的可信度依赖流程自觉（当前 C-001 有真实用户批准背书）
- **建议**：register 要求关联已批准 gate 记录（如 --gate G-T-XXXX 且该 gate
  approved 才允许），或要求 approval 证据文件存在

### 3.3 gov_delegation._save_gates 整体重写 gates.yaml
- **来源**：T-0134 审查 P2
- **问题**：`_save_gates` 用 yaml.dump 全文件重写 → 丢头部注释 + 5000 行 churn
- **影响**：git diff 噪声大；注释丢失
- **建议**：仅 patch delegations 键（文本级或读取-修改-写回保持其余原样）

### 3.4 is_loop_mode_enforced 白名单变更无直接单测
- **来源**：T-0134 审查 P2
- **问题**：DELEGATED 加入白名单（MANUAL 不加）无专项测试
  （test_t0107_fixes 仅覆盖 FULL/STANDARD/LIGHTWEIGHT/缺失）
- **建议**：补 is_loop_mode_enforced(DELEGATED)=True / (MANUAL)=False 单测

### 3.5 委托链端到端免 gate 裁决待真实任务验证
- **来源**：T-0134 AC-02 显式范围声明（非缺陷，验证闭环）
- **问题**：链内新任务免 gate 自治执行的端到端裁决未实战（当前链内任务 gate
  均已批准）；需用户发起真实新任务验证
- **建议**：用户发起下一个任务时以委托链方式执行（C-001 或新链），验证
  登记→链内→结论包全链路

---

## 四、T-0133 遗留（三层质量线程）

### 4.1 不可复算报告可逃过复算（缺 repro_command 静默跳过）
- **来源**：T-0133 审查遗留观察
- **问题**：`run_sampled_recompute` 对缺 repro_command 的报告静默跳过
  （不写 FAIL 事件）→ 不可复算报告逃过复算
- **建议**：缺 repro_command → 写 FAIL 事件（fail-closed 语义）

### 4.2 单次复算 FAIL 无 GuardCheckEvent 侧信道事件
- **来源**：T-0133 审查遗留观察
- **问题**：仅 BROKEN 升级（连续 3 次）时观测 GuardCheckEvent；
  单次 FAIL 只落 recompute-events.jsonl，guard-events 侧信道静默
- **建议**：单次 FAIL 也追加 GuardCheckEvent（check_type=recompute）

### 4.3 repro_norm（D-02 M1 规范化规则）未实现
- **来源**：T-0133 审查遗留观察 / T-0132 D-02 设计承诺
- **问题**：复算执行器用原始 stdout+stderr 哈希约定，D-02 M1 的
  输出规范化（去耗时/绝对路径/时间戳）未实现——需与报告生产方约定一致
- **建议**：实现 repro_norm 字段消费（strip-timestamps/strip-absolute-paths），
  或文档化"原始哈希约定"并统一生产方

### 4.4 manifest.validate() 无 quality_pair 一致性规则
- **来源**：T-0133 审查 P2-4
- **问题**：quality_pair 强制在 SubagentSpec.__post_init__（构造期）；
  SubagentManifest.validate() 无对应规则——未来 JSON 反序列化路径可绕过
- **建议**：validate() 补一致性检查（is_weighted=True 且 quality_pair=None →
  error）

### 4.5 QualityPair 字段集偏离未文档化
- **来源**：T-0133 审查 P2-3
- **问题**：缺 D-01 设计的 `enabled` 字段（由 is_weighted 表达）；
  check_scope 结构简化（list[str] vs list[dict]）
- **建议**：任务卡/设计文档补偏离说明（低优先）

---

## 五、T-0129 遗留（防御演练）

### 5.1 E5 guard-events 断言为属性钉（无真实删除动作）
- **来源**：T-0129 审查遗留观察（定位合理，可选增强）
- **问题**：演练流程本身不触碰 guard-events，断言只是"约束钉"
- **建议**：可选——演练中加"模拟删除 guard-events → 断言恢复/留痕"

---

## 六、KNOWN_ISSUES Open 区（既有，非本批次引入）

### 6.1 E2E integration test skipped（lab fixture 依赖）
- **来源**：KNOWN_ISSUES.md Open 区
- **问题**：`test_E2E_CURRENT_001` 因 lab fixture 依赖被 skip
- **建议**：如需 E2E 能力，立项修复 fixture 或降级为契约测试

### 6.2 session-source-disabled（保留项）
- **来源**：KNOWN_ISSUES.md Open 区（记录保留，不立项——T-0112 边界）
- **状态**：无需处理

---

## 七、指标/观测面（低优先）

### 7.1 metrics-report 的 mutation/gate_defense 字段为手写合并
- **来源**：T-0128/T-0129 实现方式
- **问题**：`metrics-report.json` 的 mutation_metrics/gate_defense 由脚本一次性
  写入，无生成器自动刷新（读侧计数 vs 快照）
- **建议**：观测面演进时接入生成器（与 T-0136 无关，独立小任务）

### 7.2 observability 词表无 BLOCK 值（rejected_requests 恒 0）
- **来源**：T-0129 metrics-semantics 如实标注
- **问题**：guard-events 结果词表仅 PASS/FAIL/REPORT；rejected_requests 为
  口径定义值（恒 0），无自动计数
- **建议**：词表扩展（BLOCK/REJECTED）+ 拦截事件自动计数（观测面演进）

---

## 处理优先级建议

| 优先级 | 项 | 理由 |
|---|---|---|
| P1 | 1.1 测试套件非密封 | 每次全量回归后 release check 假红，最反复 |
| P1 | 1.2 YAML 崩溃 exit 1 | fail-closed 语义不统一 |
| P1 | 3.2 委托链 approved_by 无验证 | 授权可信度（治理核心） |
| P2 | 2.1 / 3.1 / 3.3 / 3.4 / 4.1 / 4.2 / 4.4 | 各自功能缺陷/边界 |
| P2 | 3.5 委托链端到端验证 | 随用户真实任务闭环 |
| P3 | 4.3 / 4.5 / 5.1 / 6.1 / 7.1 / 7.2 | 低影响/观测面/可选增强 |
