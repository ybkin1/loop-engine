# D-01: 三层质量线程模型详设

> T-0132 设计文档 · 2026-08-07 · candidate-only（不落地）
> 关联：D-02 防伪造机制 / D-03 防锁死机制 / decision-packet.md

## 1. 设计目标

将 loop 工程从"两层架构（ZCode 会话 + 平级角色）+ 阶段终点质量门禁"升级为
**三层质量线程架构**：质量类 agent 作为独立线程，对任意动作产出、阶段产出、
过程数据做多轮机器可验校验。核心原则：

- **执行线程与质量线程结构性分离**（打破自证循环）
- **质量校验判定层复用 eval 栈**（机器可复算，agent 的话不是最终证据）
- **校验密度与动作重量匹配**（成本可控的分层伴飞）

## 2. 架构总览

```
┌─ 决策层 ─────────────────────────────────────────────┐
│ 用户：目标 / 验收 / 否决（唯一需要用户的时刻）          │
└──────────────────────────────────────────────────────┘
              ▲ 结论包（成果+证据路径）│ 目标（自然语言）
┌─ 调度层 ─────────────────────────────────────────────┐
│ ZCode 会话（唯一有 Agent 工具）：按 manifest 调度       │
│ · 拉起执行线程组 / 质量线程组                          │
│ · 轮次协议状态机驱动（D-01 §5）                        │
│ · 委托链上下文（loop_mode=DELEGATED 时）               │
└──────────────────────────────────────────────────────┘
   ┌──────── 执行线程组 ────────┐   ┌──── 质量线程组 ────────┐
   │ main-thread（军师，每阶段）│   │ quality-engineer      │
   │ developer                │   │ test-engineer          │
   │ system/module-architect  │   │ security-engineer      │
   │ product/project-manager  │   │ independent-reviewer   │
   └──────────────────────────┘   └───────────────────────┘
        │ 动作产出（文件/证据）          │ 校验判定（EvalCase 断言化）
        ▼                               ▼
   ┌────────────────────────────────────────────────────┐
   │ 校验执行器 = EvalRunner 扩展                        │
   │ · 规则断言（json_equals/exit_code/text_contains）    │
   │ · agent 判定桥接（verdict → EvalCase，可选 LLM）     │
   │ · EvalReport 落盘（git_commit+时间戳，机器可复算）    │
   └────────────────────────────────────────────────────┘
        │
        ▼
   guard_health 兜底：death（fail-closed）/ missing / drift
   + 新维度 CHECK_RECOMPUTE（抽样复算，见 D-02 M4）
```

## 3. 角色分组契约（Grouping Contract）

### 3.1 分组定义

| 组 | 角色 | 职责边界 |
|---|---|---|
| 执行线程组 | main-thread、developer、system-architect、module-architect、product-manager、project-manager、delivery-manager、release-engineer | 产出（设计/代码/文档/证据） |
| 质量线程组 | quality-engineer、test-engineer、security-engineer、independent-reviewer | 只读校验（检测、评分、审查）；**永不修改执行产物**（quality-engineer 契约已有"绝不修改源代码"） |

### 3.2 隔离规则（T-0062 扩展）

1. **subagent_id 强制不同**：同一任务内，执行组与质量组必须使用不同 subagent_id
   （现有"developer ≠ reviewer"扩展为全组隔离，机器校验）
2. **上下文隔离**：质量线程的 prompt 只含产物文件路径与校验规范，
   **不含执行线程的自述结论**（防"检验者见预期"，详见 D-02 M2）
3. **只读执行**：质量线程不得修改任何文件，其产出仅为校验报告/EvalReport

### 3.3 质量线程触发规则

| 触发时机 | 触发者 | 校验对象 |
|---|---|---|
| 重量动作完成后 | 调度层（按 quality_pair） | 该动作的全部产出 |
| 阶段产出后 | 调度层（阶段收口） | 阶段产出 + 过程数据（evidence 链） |
| 用户要求 | 用户 | 指定对象 |

## 4. SubagentManifest quality_pair schema

在现有 `loop_core/subagent_manifest.py` 基础上扩展（candidate 设计，落地时改）：

```yaml
# SubagentSpec 新增字段（可选）
quality_pair:
  enabled: true                    # 无 quality_pair 的重量动作 = 编排无效（机器可判）
  quality_role: quality-engineer   # 或 test-engineer / security-engineer / independent-reviewer
  check_scope:                     # 校验对象
    - path: src/loop_core/executor.py
      hash_registered: true        # 产物哈希先行登记（D-02 M3）
  eval_cases:                      # 质量校验断言（eval 栈复用，字段对齐 EvalCase schema）
    - case_id: QP-EXEC-001
      title: executor 测试套件通过         # EvalCase 必填（evals.py validate 强制）
      input: { command: "python -m pytest tests/test_executor.py -q" }
      rule: { type: exit_code, params: { command: "python -m pytest tests/test_executor.py -q", expected: 0 } }
      severity: critical
  round_limit: 3                   # 轮次上限（默认 3）
  on_escalate: default_no          # 超限默认不通过（fail-safe）

# SubagentManifest 新增字段
quality_policy:
  phase_gate: true                 # 阶段收口必须质量线程 PASS
  recompute_rate: 0.1              # 抽查复算比例（D-02 M4）
```

**机器可判的编排有效性**：`manifest.validate()` 增加规则——
重量动作（按文件数/跨模块判定，见 §4.1）必须携带 quality_pair，缺失即
`(False, ["weighted action X requires quality_pair"])`。

### 4.1 轻量/重量动作分级

| 级别 | 判定条件（机器可算） | 校验方式 |
|---|---|---|
| 轻量 | 单文件修改 / 文档 / 纯注释；改动行 ≤ 阈值（建议 100） | hook 机器检查（现有 7 个 guard 已覆盖），不上 agent 线程 |
| 重量 | 跨模块 / 契约变更 / 新增文件 / 改动行 > 阈值 / 涉及 hooks/loop_core/agents | 质量 agent 线程 + eval 断言（quality_pair 强制） |

分级阈值由配置承载（如 `config.yaml: quality_pair.weight_action_min_lines`），
变更需走 gate（与现有"修改门槛是决策"语义一致）。

## 5. 多轮校验轮次协议（Round Protocol）

### 5.1 状态机

```
              ┌──────────────────────────────────────┐
              ▼                                      │
[动作产出] → CHECKING → FOUND → FIXING → RE-CHECK ───┤
              │(PASS)     │          │(PASS)         │
              ▼           │          ▼               │
           NEXT ◄─────────┴──────── PASS（下一动作/阶段）
              ▲
              │ round ≥ round_limit(3)
           ESCALATE → 默认不通过（fail-safe）：
              ① 缩小范围 + KNOWN_ISSUES 登记（继续其余部分）
              ② 回滚该动作重做（走 D-03 回滚路径）
              · 不转嫁用户；用户介入仅当产物涉及价值取舍
```

### 5.2 状态机实现要点（candidate）

- 状态存于任务 evidence 目录：`.ai/evidence/<task>/rounds/<action_id>.jsonl`
  （追加式，每行一个状态迁移：时间戳 + 动作 + 状态 + 校验者 + 证据引用）
- 每轮 RE-CHECK 必须重跑 eval 断言（不得复用上一轮结果——机器可复算保证）
- CHECKING 的校验者与 FIXING 的修复者必须分属不同线程组（§3.2）

### 5.3 过程数据校验（阶段收口）

阶段收口时质量线程额外核验：
- evidence 链完整性（evidence-manifest 存在 + 哈希一致）
- guard-events 事件可追溯（时间戳链无倒填，见 D-02 M3）
- 本阶段所有动作的 rounds 日志闭合（无悬空 CHECKING）

## 6. eval 栈作为核心校验机制（用户确认方向）

### 6.1 分层判定模型

```
校验判定 = EvalRunner（规则断言，机器可复算）   ← 最终证据层
         + Agent 判定（可选增强，fail-safe）   ← 建议层
```

| 层 | 判定者 | 语义 | 可信度 |
|---|---|---|---|
| L1 规则断言 | EvalRunner（json_equals/exit_code/text_contains） | 数字/结构/行为的事实校验 | 机器级（重跑必同结果） |
| L2 agent 判定 | 质量线程 subagent（可读码/可跑命令） | 语义判断（设计合理性、缺陷检出） | 建议级（必须桥接为 EvalCase 后才算证据） |
| L3 LLM judge | evals.py 可选 judge（ProtocolDriver） | 复杂语义评分 | 建议级（不可用 → SKIPPED 不阻断） |

**关键规则：任何 L2/L3 判定进入报告前必须"断言化"**——agent 的 verdict
（如 "detected: SQL injection"）必须转换为可复算断言（如对产物执行 bandit
B608 规则检查并断言 exit 0/输出含预期 finding），转换后由 EvalRunner 复算
确认。**agent 的话永远不是最终证据，eval 复算才是**（与 D-02 M1 一致）。

### 6.2 EvalReport 落盘契约（对齐真实接口 + 显式扩展）

复用现有 `EvalReport`（`loop_core/evals.py`，ReportBinding 风格，真实字段
`type: "eval_report"` / 顶层 `verdict` / `binding` 含 git_commit + timestamp /
`cases[]` 每项为 `EvalCaseResult.to_dict()`：`case_id/title/severity/result/
duration_ms/rule_type/version/reason`）。每轮校验产出
`.ai/evidence/<task>/evals/<round>.json`：

```json
{
  "type": "eval_report",
  "schema_version": "1",
  "binding": {"task_id": "T-XXXX", "phase": "S6-delivery", "gate_id": "...",
              "execution_id": "...", "git_commit": "<sha>", "timestamp": "..."},
  "suite": {"suite_id": "...", "suite_version": "..."},
  "stats": {"total": 2, "passed": 2, "failed": 0, "skipped": 0},
  "by_severity": {},
  "verdict": "PASS",
  "started_at": "...",
  "duration_ms": 12.5,
  "cases": [
    {"case_id": "QP-EXEC-001", "title": "...", "severity": "critical",
     "result": "PASS", "duration_ms": 3.2, "rule_type": "exit_code",
     "version": "1", "reason": null}
  ]
}
```

**显式扩展（candidate，落地时改 `loop_core/evals.py`）**：
- `EvalCaseResult` 增加 `evidence_ref: str | None` 字段（M5 强制引用，
  与 D-02 §2 M5 联动：无引用 = 该 case FAIL）；`to_dict()` 同步输出
- 若落地时选择不改 EvalCaseResult，则新增 wrapper 报告类型
  `quality_report`（字段：eval_report 全量 + 每 case evidence_ref +
  recompute 摘要），二选一在落地任务中确定，本设计默认前者（改动最小）

**关键语义**：`verdict` 顶层值 = `EvalVerdict`（PASS/FAIL/SKIP）；
SKIP 不阻断（LLM judge 不可用时 fail-safe），任何 FAIL 即整轮 FAIL。

### 6.3 现有资产复用清单

| 资产 | 位置 | 复用方式 |
|---|---|---|
| EvalCase/EvalRunner/EvalReport | loop_core/evals.py | 直接作为校验执行器 |
| 内置 guard 样例 | loop_core/evals_builtin.py | 质量校验用例基线的种子 |
| 规则断言类型 | evals.py（text_contains/text_matches/json_equals/exit_code） | 校验断言全集 |
| guard_health 三类检查 | loop_core/guard_health.py | 兜底 + 新增 CHECK_RECOMPUTE |
| SubagentManifest/SubagentSpec | loop_core/subagent_manifest.py | 增加 quality_pair 字段 |
| 调度器 | loop_core/dispatcher.py | 按 manifest 调度质量线程 |

## 7. 落地影响面（candidate 清单，供决策包）

| 文件 | 改动类型 | 说明 |
|---|---|---|
| loop_core/subagent_manifest.py | 扩展 | SubagentSpec.quality_pair + validate() 强制规则 |
| loop_core/evals.py | 扩展 | agent 判定桥接（verdict→EvalCase 转换器） |
| loop_core/guard_health.py | 扩展 | CHECK_RECOMPUTE 维度（D-02 M4） |
| loop_core/router.py | 扩展 | `LoopMode` 枚举新增 `DELEGATED` / `MANUAL`（现仅 LIGHTWEIGHT/STANDARD/FULL，router.py:13-16）；**回退语义 fail-closed**：未知值不得回退 LIGHTWEIGHT（会关闭 enforcement，loop_enforcement 白名单仅认 FULL/STANDARD），必须回退 FULL 或拒绝启动；state_machine.py:715 的默认值同步 |
| agents/main-thread/SKILL.md | 修改 | 编排协议：质量配对规范 |
| agents/quality-engineer|test-engineer|security-engineer|independent-reviewer SKILL.md | 修改 | when_to_use 前置（动作完成即触发）+ 只读校验规范 |
| hooks/scripts/loop_enforcement.py | 扩展 | 委托链上下文（后续任务，本次仅设计） |
| docs/ | 新增 | 三层模型架构文档 |

**本次 T-0132 零落地**：以上仅为设计影响面，实施另立任务。
