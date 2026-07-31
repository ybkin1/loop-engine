# U5 设计证据 — intent_router 路由升级（粘性 + 任务帧 + fail-safe 降级）

> **T-0088 工作包 U5 | 2026-07-31 | 承接：T-0086 staffdeck-benchmark.md U5**
> 对标来源：OpenBMB/StaffDeck `backend/app/core/router.py`（233 行，T-0086 子代理源码精读结论：纯 LLM 分类 9 决策类型；粘性规则（active 技能沿用）；非法目标降级 clarify；`task_frames` 表达复合意图）。

## 1. 借鉴映射（StaffDeck → loop-engine）

| StaffDeck router.py 机制 | loop-engine 现状（升级前） | U5 落地（升级后） | 落地位置 |
|---|---|---|---|
| 粘性规则：active 技能沿用，不重复问 | 每次 analyze() 独立判定，无任务延续概念；调用方（inbox/planner）对同一 active 任务反复路由 | `ActiveTaskSnapshot` + `RoutedIntent.sticky/sticky_basis/sticky_task_id`；active 任务存在时主帧延续该任务域（task_id 指向 active 任务） | `loop_core/intent_router.py`（U5 段） |
| 9 决策类型分类 | 领域识别 + 复杂度估算 + 轻量/完整 Loop 模式推荐（既有，保留不动） | 决策类型复用既有 ChangeType/领域/复杂度管线；新增"回合级"决策层（粘性 + 帧编排）叠加其上 | 同上 |
| `task_frames` 单轮多 SOP 顺序执行 | 无多意图概念，整段文本单意图处理 | `split_intents()` 保守切分 + `TaskFrame` 有序帧列表（主帧=第一意图，后续帧为新任务） | 同上 |
| 非法目标降级 clarify | 无降级路径（planner 内部 try/except 兜底但不返回结构化降级） | `route_upgrade()` 永不抛异常；内部错误 → `RoutedIntent(degraded=True)`"保持现状"（沿用 active 任务或默认轻量模式），不猜新意图 | 同上 |
| （无对应） | inbox.py 已 `from loop_core.intent_router import analyse_intent` 但该函数不存在（走 ImportError 兜底） | `analyse_intent()` 补齐（IntentBrief: domains + risk_level.name），失败返回 MEDIUM 空摘要，不抛 | 同上 |

## 2. 决策类型（路由输出三要素）

U5 路由输出 `RoutedIntent` 由三部分组成，均带可追溯依据：

1. **主分析**：`analysis`（IntentAnalysis）—— 沿用既有"领域识别 + 复杂度估算 + Loop 模式推荐 + change_type"，接口不变。
2. **粘性裁决**：`sticky`（bool）+ `sticky_basis`（依据字符串）+ `sticky_task_id`。
   - 默认规则：active 任务存在（`state.current_task_id` 非空 且 任务状态 active/in_progress）→ `sticky=True`，主帧 `task_id = active 任务 id`，不重复问"做什么"。
   - 显式失效条件（任一命中即切出）：
     - 新任务关键词（`INTENT_SWITCH_KEYWORDS`：new task/新任务/另一个任务/next task/切换任务…）；
     - 完成/关闭关键词（task done/任务完成/已完成/close/cancel/abort…）；
     - 输入引用**其他**任务 id（`T-\d{4}` ≠ active id，`_other_task_refs`）；
     - "mark `<active task id>` complete" 式闭合信号（active id + 完成动词邻近窗口，`_active_task_completion_signal`）；
     - active 任务状态已非 active（completed 等，`is_active` 判定）。
3. **帧编排**：`task_frames`（list[TaskFrame]）—— 多意图单轮顺序编排，主帧在前。

## 3. 粘性规则（正式定义）

```
输入: description, active_task(A)
判定:
  switched ← detect_intent_switch(description)              # 显式切换/完成关键词
  若 未 switched 且 A 存在:
    若 description 引用 ≠ A.id 的任务 id → switched ← True（引用其他任务）
    否则 若 A.id 与完成动词邻近共现 → switched ← True（闭合 active 任务）
  sticky ← (A 存在) ∧ A.is_active ∧ ¬switched
  主帧 task_id ← A.id 当 sticky，否则 None（新任务）
```

- 粘性**不是**模式（mode）覆盖：主帧 Loop 模式仍由 analyze 独立计算（高危及新工作照常升级，安全网"never downgrade"不变）；粘性只裁决"是否延续该任务域"。
- 粘性依据必填：`sticky_basis` 记录"为什么延续/为什么切出"，供审计与用户可见理由。

## 4. 任务帧结构

`TaskFrame` 字段（与任务文件/任务图兼容）：

| 字段 | 含义 | 任务图对应 |
|---|---|---|
| `frame_id` | 帧序号，0=主帧 | — |
| `intent` | 该帧意图原文 | `title`（to_task_dict） |
| `task_id` | 目标任务 id（粘性主帧=active 任务；其余=None=新任务） | `id` |
| `domain` | 领域（粘性主帧优先取 active 任务域） | `domains` |
| `complexity_score` | 复杂度估计 0-1 | `complexity_score` |
| `recommended_mode` | Loop 模式 | `loop_mode`（.name 大写，与 task_graph.yaml 一致） |
| `change_type` | 变更类型 → 入口阶段 | `phase`（CHANGE_TYPE_TO_ENTRY_PHASE） |
| `confidence` / `reasoning` | 置信度与依据 | — |
| `is_main` | 主帧标志（第一意图） | — |
| `suggested_phases` | 建议阶段 | — |

`to_task_dict()` 输出 `{id, title, status:"planned", phase, loop_mode, domains, complexity_score}`，可直接落为 task_graph.yaml 任务条目。

**多意图切分**（`split_intents`，保守启发式，仅显式标记，避免把单一意图切碎）：
- 分号 `；`/`;`
- 编号列表 `1. … 2. …`
- 英文顺序/并列连接词：then / after that / afterwards / next / finally / also / additionally / moreover / meanwhile
- 中文连接词**前置标点**限定（`，然后`、`。接下来`、`；之后`…）：然后/接下来/之后/接着/其次/再次/最后/同时/另外/此外/除此之外 —— 避免把"登录**之后**的重定向"这类单意图时间状语误切
- 句号 + 动作开头（`。新增`/`。修复`/`。写`…，零宽前瞻保留动词）
- 上限 `_MAX_TASK_FRAMES=5`；切分为空 → 整段作为单帧

## 5. 降级语义与 fail-closed 的边界

**fail-safe 降级（路由层，本升级新增）**：`route_upgrade()` / `route_user_input()` 内部任何异常（解析失败、非字符串输入、analyze 抛错、依赖缺失）→ 返回 `RoutedIntent(degraded=True, degraded_reason=…)`：
- 有 active 任务 → `sticky=True`，主任务沿用 active 任务，`route_result.mode = active 任务 loop_mode`；
- 无 active 任务 → 默认 `LIGHTWEIGHT`；
- **永不抛异常、永不猜测新意图**：`task_frames=[]`、`analysis=None`、`main_frame=None`，不会凭空生成新任务 id。

**与 fail-closed 的关系（边界明确）**：路由降级只影响**路由建议**（"保持现状"），路由输出不是权限/约束裁决：
- 约束裁决在 hook 层（C1-C11、path/scope/verdict 检查、loop_enforcement/gate_guard 等）保持不变，fail-closed 语义不受路由任何影响；
- 降级结果以 `degraded=True` 显式标记，且 status-quo RouteResult 的 reason 明示 "no new intent guessed"，可审计；
- 本升级未触碰任何 hook 脚本、enforcement 模块或约束常量（diff 审查可验证：仅新增 intent_router.py 的 U5 段 + 新测试 + 本证据）。

**向后兼容**：`analyze()`/`route()`/`IntentAnalysis`/`IntentAnalysis` 字段零改动；`RoutedIntent.analysis`/`route_result` 即主帧原有产物，既有调用方（planner.py、tool_route_intent.py）不受影响；`analyse_intent()` 补齐 inbox.py 早已导入的入口（成功返回 domains+risk_level，失败返回 MEDIUM 空摘要）。

## 6. 实现与测试位置

- 实现：`loop_core/intent_router.py` 文件尾新增 "U5 Routing Upgrade (T-0088)" 段（`route_upgrade` 方法 + `route_user_input`/`analyse_intent`/`split_intents`/`detect_intent_switch` + `ActiveTaskSnapshot`/`TaskFrame`/`RoutedIntent`/`IntentBrief`），既有代码零修改。
- 测试：`tests/test_intent_router_upgrade.py`（33 用例，覆盖 AC-04a 粘性 11 项、AC-04b 帧 11 项、AC-04c 降级 7 项、向后兼容 7 项——按类分组）。
- 验收对照：AC-04 三条（粘性行为测试 / 多意图编排测试 / 异常→保持现状不抛不猜）全部由上述测试类覆盖并通过。
