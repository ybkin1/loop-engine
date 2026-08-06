# D-02: 防伪造机制设计（硬约束 1）

> T-0132 设计文档 · 2026-08-07 · candidate-only（不落地）
> 关联：D-01 §6（eval 核心校验）/ D-03（防锁死）

## 1. 威胁模型

| 威胁 | 描述 | 现有防线 | 缺口 |
|---|---|---|---|
| T1 自编结果 | AI 直接编写"通过"报告，无实际执行 | 无（质量报告为 AI 自述） | 质量线程可伪造 PASS |
| T2 先射箭画靶 | 先定结论（如"检出 SQL 注入"），再凑/编造证据匹配结论 | 无 | agent 判定可事后合理化 |
| T3 倒填 | 校验结论写好后补写时间戳/哈希，使日志看似先于产出 | EvalReport 带 git_commit | 哈希登记时机无强制 |
| T4 双簧 | 执行线程与质量线程同主体（同 subagent 上下文），质量线程"同意"执行线程自述 | T-0062 developer≠reviewer | 未覆盖全组、未覆盖"结论注入" |
| T5 证据引用空洞 | verdict 声称"已验证"但引用的证据文件不存在/无关 | 部分（evidence_path_exists） | 无强制"无引用=无效" |

## 2. 五项机制详设

### M1 机器可复算（对治 T1/T2）

**规则**：任何进入校验报告的判定，必须能通过重跑命令**确定性复现**。

- 质量报告中的数字（测试通过数、lint error 数、覆盖率、exit code）必须携带
  `repro_command`（可复算命令）+ `repro_hash`（该命令输出的哈希）
- **repro_hash 输入边界（P2-3 修复，落地必定义）**：哈希输入 = "stdout + stderr
  + exit code 的规范化序列"；输出规范化：去除耗时、绝对路径、时间戳等
  非确定性片段（如 pytest 耗时列、机器名），规范化规则与哈希算法随
  repro_command 声明（`repro_norm: strip-timestamps`）
- 复算校验：`EvalRunner` 执行 `repro_command`，输出哈希一致 → 数字可信；
  不一致 → 该报告判定为 FAIL（伪造或失真），进入 ESCALATE
- **示例**：
  ```json
  {"finding": "lint_errors", "count": 3,
   "repro_command": "python -m ruff check loop_core/",
   "repro_norm": "strip-absolute-paths",
   "repro_hash": "sha256:9f86d0..."}
  ```
  复算器：执行命令 → 规范化 → 计算哈希 → 比对，不等即 FAIL

**为什么 eval 栈天然满足**：规则断言（json_equals/exit_code/text_contains）
本身就是"命令 + 期望"结构——重跑必同结果，是 M1 的现成实现载体。

### M2 检验者不见预期（对治 T4）

**规则**：质量线程的输入 = 产物文件本身 + 校验规范；**不得包含**执行线程的
自述结论、预期结果、自查报告。

- prompt 构造规范（落地于 manifest 生成器）：
  - ✅ 允许：产物路径、产物内容、校验规范（断言/阈值/规则集）
  - ❌ 禁止：执行线程的"我已完成/我认为/我的测试通过"类文本、
    developer 的提交说明、执行线程生成的测试报告
- 机器校验：`manifest.validate()` 增加"预期隔离检查"——质量 spec 的
  input_files 不得包含执行线程自述产物（如 `dev_self_report.md`）
- **示例**（质量 spec prompt 模板）：
  ```
  你的任务：校验以下产物是否符合规范。
  产物：src/loop_core/executor.py（只读）
  规范：assert QP-EXEC-001（exit_code 0）；assert QP-EXEC-002（含 except 处理）
  你不得接触任何执行者的总结性材料。输出 verdict + 证据引用。
  ```

### M3 产物哈希先行登记 + 时间戳链（对治 T3）

**规则**：校验对象的哈希在**校验开始前**登记，校验结论后附；链上任何
"结论时间 < 哈希登记时间"即视为倒填。

- 登记流程（轮次协议 CHECKING 起始动作）：
  1. 调度层对产物文件计算 sha256 → 写入 `.ai/evidence/<task>/rounds/<action_id>.jsonl`（含登记时间戳）
  2. 校验完成后，结论写入同文件（含校验时间戳）
  3. 校验器检查：校验时间戳 ≥ 登记时间戳，且结论引用的产物哈希 = 登记哈希
     （产物在校验期间被改 → 哈希不符 → 该轮无效，必须重开）
- 防倒填补充：登记行与结论行共用同一追加式日志（jsonl 物理顺序不可改写，
  与现有 guard-events.jsonl 同模式）；git_commit 作为链锚（EvalReport 已带）

### M4 抽查复算（对治 T1/T2 残留）

**规则**：机器对质量报告做**随机抽样复算**，抽中即独立重跑。

- guard_health 扩展新维度 `CHECK_RECOMPUTE`：
  - 比例 `recompute_rate`（建议 0.1，可配置）
  - 抽中报告 → 重新执行其全部 repro_command → 与报告数字比对
  - 任何不一致 → 该报告 FAIL + guard_health 事件记录（check_type=RECOMPUTE）
- 该维度为 **report 级还是 fail-closed 级**：设计为 **report 级 + 事件**
  （与 missing/drift 同级），但连续 N 次抽查失败（建议 3）→ 提升为
  fail-closed（该质量线程暂停，走 D-03 恢复路径）——防"质量线程系统性虚报"
  但不因单次抽查偶然失败而锁死
- **统计口径（P2-5 修复）**：连续失败计数按**任务粒度**（同任务内累计，跨
  任务清零）且带时间窗（如 24h 内），避免跨任务错误累计；CHECK_RECOMPUTE
  与 recovery 为新增 check_type 常量（落地时在 observability 事件常量表注册）

### M5 verdict 必须引用可核验证据（对治 T5）

**规则**：无证据引用 = 无效 verdict（机器拒绝）。

- EvalCase 结果强制携带 `evidence_ref`：产物路径 + 行号/段号 或
  repro 输出片段；校验器检查引用路径存在 + 内容相关（含关键 token）
- verdict 无 evidence_ref → 该 case 判 FAIL（不是 SKIP，不是忽略）
- **示例**：
  ```json
  {"case_id": "QP-SEC-001", "verdict": "FAIL",
   "evidence_ref": "src/loop_core/executor.py:128 (unhandled except: pass)"}
  ```

## 3. 机制与威胁覆盖矩阵

| 机制 | T1 自编 | T2 射箭画靶 | T3 倒填 | T4 双簧 | T5 空引用 |
|---|---|---|---|---|---|
| M1 机器可复算 | ✅ 直接 | ✅ 直接 | — | — | — |
| M2 不见预期 | — | ✅ 阻断预期注入 | — | ✅ 组隔离 | — |
| M3 哈希先行 | — | — | ✅ 直接 | — | — |
| M4 抽查复算 | ✅ 兜底 | ✅ 兜底 | — | — | — |
| M5 引用证据 | — | — | — | — | ✅ 直接 |

## 4. 失效场景与兜底

| 场景 | 失效点 | 兜底 |
|---|---|---|
| 质量 agent 与被检产物同源（同一 LLM 会话惯性） | M2 隔离被 prompt 绕过 | M4 抽查复算 + 复算器为纯机器（无 LLM），必然揭穿数字伪造 |
| 复算命令本身可被"优化"（如 pytest 缓存） | M1 复算非真执行 | repro_command 规范：禁用缓存参数（--no-cache 等）+ 随机顺序 |
| 哈希登记也被伪造（AI 同时写登记与结论） | M3 链被单主体破坏 | 登记由调度层（会话）执行而非质量线程；git 提交作为物理锚 |
| 全部机制被同一主体同时破坏 | 单点 | 无法用机制消除的主体同一性问题 → 由用户验收 + 决策包透明标注残余风险 |

## 5. 设计约束回顾（对应任务卡 AC-02）

| 任务卡要求 | 设计落点 |
|---|---|
| 机器可复算（数字可复跑重现） | M1（repro_command + repro_hash + 复算器） |
| 检验者不见预期 | M2（prompt 构造规范 + 预期隔离检查） |
| 防倒填 | M3（哈希先行 + jsonl 物理顺序 + git_commit 锚） |
| 抽查复算 | M4（CHECK_RECOMPUTE + 连续失败升级 fail-closed） |
| verdict 引用证据 | M5（evidence_ref 强制 + 无引用即 FAIL） |
