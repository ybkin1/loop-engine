# T-0104 独立审查报告（independent-reviewer）

> 审查人：independent-reviewer 子代理（fresh context，未接触 developer 执行过程）
> 审查时间：2026-08-02
> 审查对象：T-0104（D-03 全部 5 项设计落地）工作区全部未提交改动
> 审查依据：`.ai/evidence/T-0103/design/D-03-integrated-design.md`（候选文本基线）、
> `git status --short` + `git diff` 全量、`.ai/tasks/T-0104.md`、developer 记录
> （commands.md / fixes/batch1-doc.md / batch2-ledger.md / batch3-memory.md）

## 审查方法（亲自复验了什么）

1. **git 全量 diff 逐文件阅读**：20 个修改文件 + 7 个新增文件全部亲自读 diff/源码，
   未依赖 developer 记录中的任何结论。
2. **约束零弱化**：独立执行 `git diff --stat -- hooks/`、`loop_core/context_loader.py`、
   治理内核五文件、`git diff agents/main-thread/CONTRACT.yaml` 逐字核对 R10/R11；
   `.ai/schemas/` 状态核对。
3. **候选文本一致性**：编写脚本从 D-03 提取 35 个关键候选文本串（含引号归一化
   处理）逐一断言在落地文件中的存在性，全部通过。
4. **独立运行时验证**（Python 子进程隔离）：
   - AiDecisionLedger 对真实 `.ai/ledger/ai-decisions.jsonl`（空链）verify_chain；
   - 以 ZCode hook 调用方式子进程运行 `hooks/scripts/ledger_guard.py`：
     合法追加 exit 0、篡改 exit 2（零 hook 改动实证）；
   - `_memory_injection_for` 对真实 config.yaml：S4/S10 → (True,5)，S3 → (False,5)；
   - **默认行为逐字节对比**：将 HEAD 版本 context_packager/role_loader 装入影子目录，
     与当前版本在相同输入下（8 角色 × 5 调用 = 40 项输出）逐一字节比较 → 完全一致。
5. **全量回归**：独立运行 `C:/Python312/python.exe -m pytest tests/ -q`
   （排除 deep_probe_v35.py/lab/vertical_slice，与 developer 相同口径），172.59s。
6. **编译/状态/版本**：`compileall` 通过；`validate_state.py .` → state usable；
   `pyproject.toml` version=3.12.41 未被改动。

---

## 一、裁决

# **GO**

无 P1/P2 条件。发现 0 P0 / 0 P1 / 0 P2 / 4 P3（均为建议性记录，不阻塞交付）。

依据：
- 全部 5 项设计落地内容与 D-03 候选文本一致（35/35 抽查通过）；
- 约束零弱化专项全部实证通过（hooks/ 零改动、context_loader 默认值零改动、
  治理内核零触碰、R10/R11 原文逐字未动、fail-closed 语义不变）；
- 超清单改动 role_loader.py 经专项审查判定为合理必要的管道转发，默认行为
  40 项输出逐字节一致，无风险；
- 独立全量回归 3636 passed / 64 skipped / 12 xfailed / 0 failed；
- 版本载体未被改动（bump 留待主会话，符合分工）。

---

## 二、改动范围核对表

### D-03 §6 清单内文件（14 现有 + 1 新数据文件）

| 文件 | 类别 | D-03 对照 | 判定 |
|---|---|---|---|
| `skills/loop-governance/templates/task-card.md` | M（3 处新节） | §6 设计-1/2/5 | ✅ 三节均按候选文本原样落地，节序：基本信息→信息完整度→用户可见目标→相关经验→范围与边界→盲点清单→验收标准 |
| `skills/loop-governance/SKILL.md` | M（第 7 步） | §6 设计-1 | ✅ 候选文本 §1.3.2 原样 |
| `skills/loop-governance/examples/01-new-task-creation.md` | A（可选） | §6 设计-1 | ⏭ 未改（D-03 标"可选"，允许） |
| `skills/loop-governance/templates/human-review-packet.md` | A+M（节顺延） | §6 设计-4 | ✅ 理解确认节原样 + "六、下一步"顺延为"七" |
| `skills/loop-governance/references/governance-lifecycle.md` | M（可选） | §6 设计-4 | ✅ USER_ACCEPTED 前置说明 |
| `skills/loop-governance/config.yaml` | A（配置节） | §6 设计-5 | ✅ memory_injection 节与 D-03 §5.3.2 回退方案原文一致 |
| `agents/main-thread/SKILL.md` | A（§2.3/§5.2/§5.3/§4） | §6 设计-2/3 | ✅ 均按候选文本落地 |
| `agents/main-thread/CONTRACT.yaml` | M（+1 行） | §6 设计-2 可选 | ✅ 仅 fixed_stance 追加"象限判定先行"一句；R10/R11 逐字未动 |
| `agents/developer/SKILL.md` | A（deviations 数组） | §6 设计-3 | ✅ 候选文本原样，known_deviations 等既有字段原样保留 |
| `loop_core/approval_ledger.py` | A（记录类型+字段） | §6 设计-3/4 | ✅ AiDecisionRecord/AiDecisionLedger + user_comprehension_confirmed 可选字段 |
| `.ai/ledger/ai-decisions.jsonl` | N（链式 JSONL） | §6 设计-3 | ✅ 空链起步（0 字节），链契约与 executions.jsonl 完全一致 |
| `loop_core/role_orchestrator.py` | M（S4+ 显式传参） | §6 设计-5 | ✅ 开关读取 + 阶段前缀匹配 + 显式传参 |
| `loop_core/context_packager.py` | M（可选） | §6 设计-5 | ✅ 新增关键字参数默认 False，开启时注入记忆节 |
| `loop_core/context_loader.py` | **零改动** | §6 刻意不动 | ✅ `git diff` 为空（L806/L1122 `include_memories: bool = False` 原样） |
| `hooks/scripts/ledger_guard.py` | **零改动** | §6 刻意不动 | ✅ `git diff` 为空，仅只读兼容验证 |
| `USER-PROMPTS.md` | A（可选） | §6 设计-2 | ✅ 用户侧说明节 |

### 实际 diff 中的其他文件（清单外）

| 文件 | 类别 | 审查判断 | 判定 |
|---|---|---|---|
| `loop_core/role_loader.py` | M（管道转发） | 超清单改动，专项审查见第五节 | ✅ 可接受 |
| `.ai/gates.yaml` | M（+73 行） | G-T-0104-REQUIREMENTS 门记录：status=approved、approval_actor=user、approval_source=explicit_user_message、forbidden_actions 含 hooks/内核/部署等全部禁止项；allowed_paths 覆盖改动文件 | ✅ 任务正常产物 |
| `.ai/state.yaml` | M | current_task=T-0104、current_gate=G-T-0104-REQUIREMENTS | ✅ 正常推进 |
| `.ai/task_graph.yaml` | M（+13 行） | T-0104 节点挂 G-T-0104-REQUIREMENTS、depends_on T-0103 | ✅ 正常 |
| `.ai/project_continuity.yaml` | M | source_manifest 哈希随 gates.yaml/task_graph.yaml 变更而更新 | ✅ 正常 |
| `.ai/HANDOFF.md` | M | 引用 T-0104 manifest（该文件现已存在）、checkpoint 状态推进 | ✅ 正常 |
| `.ai/evidence/observability/guard-events.jsonl` | M（+80 行） | 全部为 hook 遥测 health/death 检查 PASS 记录（自动追加） | ✅ 正常 |
| `.ai/tasks/T-0104.md` / `.ai/evidence/T-0104/` | ?? | 任务卡 + 证据目录（commands/fixes/evidence 文件） | ✅ 正常 |
| `tests/test_approval_ledger.py` | M（+4） | 预期测试更新 | ✅ |
| 4 个新测试文件 | ?? | 预期测试新增 | ✅ |

**结论**：无清单外生产代码改动（role_loader.py 除外，专项通过）；无删除、无语义替换；全部为加节/加字段/加配置。

---

## 三、约束零弱化专项（逐项实证）

| 约束 | 实证方法 | 结果 |
|---|---|---|
| `hooks/` 零改动 | `git diff --stat -- hooks/` 输出为空；`git status --short -- hooks/` 无未跟踪文件 | ✅ 零改动 |
| `loop_core/context_loader.py` 默认参数零改动 | `git diff --stat -- loop_core/context_loader.py` 为空；L806/L1122 `include_memories: bool = False` 确认 | ✅ 零改动 |
| 治理内核零改动 | `git diff --stat` 对 gate_guard/enforcement/hard_constraints/guard_health/state_machine 均为空（目录级 diff 亦无 loop_core 其他内核文件） | ✅ 零改动 |
| R10/R11 原文零改动 | `git diff agents/main-thread/CONTRACT.yaml` 全文仅 +1 行（"象限判定先行"）；R10/R11 两行为上下文行（前缀空格，未改）；HEAD 与工作区逐字一致（grep 比对） | ✅ 零改动 |
| `.ai/schemas/` 零改动 | `git status --short -- .ai/schemas/` 为空 | ✅ |
| fail-closed 语义不变 | ① 配置缺失/损坏 → `_memory_injection_for` 返回 (False,5)，与现状一致（测试 + 独立复验）② store 损坏 → `build_context(include_memories=True)` 抛 KnowledgeStoreError（不静默猜记忆）③ ai-decisions.jsonl 空链合法（verify 返回 True，与 ledger_guard 空链语义一致）④ ledger_guard 对新文件追加 exit 0 / 篡改 exit 2（子进程独立复验） | ✅ 不变 |
| 版本文件不改 | `git diff --stat -- pyproject.toml CHANGELOG.md` 为空；pyproject version=3.12.41（未 bump，符合"bump 由主会话执行"） | ✅ 未改 |

---

## 四、设计-1~5 落地抽查表（与候选文本一致性）

抽查方法：从 D-03 提取候选文本串（含 35 处关键串），对落地文件逐一断言；对因中英文引号（“” vs ""）产生的 6 处假阴性做了引号归一化复验，归一化后 35/35 全部通过。

| 设计 | 抽查点 | 与候选文本一致性 | 判定 |
|---|---|---|---|
| 设计-1 | task-card 盲点清单节：标题、三问、"缺任何一条=任务卡不完整"、B1-B4 示例表、4 条填写规则 | 逐字一致（含规则 3 与 R11 合并表述） | ✅ |
| 设计-1 | loop-governance SKILL 启动检查第 7 步"盲点简报（开工前，Q3）"全文（含"不猜测直接开工"） | 逐字一致（D-03 §1.3.2 原样） | ✅ |
| 设计-1 | main-thread §4 主控自检表新增"任务卡盲点清单 ≥3 条" | 落地（§4 主控检查项 +2 行） | ✅ |
| 设计-2 | task-card"信息完整度声明 + 象限判定"节：4 维表、Q1-Q4 判定规则 | 逐字一致（含"假设为零"） | ✅ |
| 设计-2 | main-thread §2.3"象限判定 → 行为选择"：映射表 4 行 + 3 条约束（R10/R11 上限不放开、aggregation_prompt、Q1 偏离联动） | 逐字一致（D-03 §2.3.2 原样） | ✅ |
| 设计-2 | CONTRACT fixed_stance"象限判定先行"一句（D-03 §2.3.3 可选） | 一致（内容为候选文本描述的实现） | ✅ |
| 设计-3 | developer SKILL deviations 数组（D-03 §3.3.2 原样，known_deviations 原样保留） | 逐字一致；既有字段保留（测试断言 + diff 实证） | ✅ |
| 设计-3 | main-thread §5.2"本阶段偏离摘要"模板（新情况/方案调整/替您做的决定三行）+ §5.3 自检第 7 条（条数匹配=打回） | 逐字一致 | ✅ |
| 设计-3 | approval_ledger AiDecisionRecord：9 字段（decision_id="AD-{uuid12}"…reason_ref/recorded_at），**无 human_actor**（evidence≠approval 语义隔离） | 与 D-03 §3.3.4 候选一致；测试断言无 human_actor | ✅ |
| 设计-3 | ai-decisions.jsonl 链契约：root seed `LOOP_ENGINE_EXECUTION_LEDGER_V1_ROOT` 与 execution_ledger/ledger_guard 完全相同；SHA256(prev‖row) 算法逐行一致；ledger_guard 子进程 exit 0/2 | 独立复验通过 | ✅ |
| 设计-4 | human-review-packet"六、理解确认（用户答对才算验收）"：3 问表 + 4 条规则；原"六、下一步"顺延"七" | 逐字一致（D-03 §4.3.1 原样） | ✅ |
| 设计-4 | ApprovalRecord `user_comprehension_confirmed: bool \| None = None`：create 增参、record_approval 非 None 才写键、get_approval `.get()` 读取（存量无键→None） | 与 D-03 §4.3.2 一致；+4 测试覆盖两种 round-trip + legacy None + 不写键 | ✅ |
| 设计-4 | governance-lifecycle PASS 分层前置说明（可选） | 一致 | ✅ |
| 设计-5 | task-card"相关经验与不熟悉处"节（2 字段 + 3 规则，含"更小步+更早展示"） | 逐字一致（D-03 §5.3.1 原样） | ✅ |
| 设计-5 | config.yaml `memory_injection: {enabled: true, phases: [S4,S5,S6,S8,S9,S10], memory_limit: 5}`（非 hook 配置） | 与 D-03 §5.3.2 回退方案原文一致 | ✅ |
| 设计-5 | role_orchestrator S4+ 显式传 include_memories=True；context_packager 关键字参数默认 False；context_loader 默认值不动 | 独立复验：真实配置 S4→(True,5)、S3→(False,5)；默认路径 40 项输出逐字节一致 | ✅ |
| 设计-5 | fail-closed：配置缺失/损坏→disabled；store 损坏→异常 | 独立复验 + 测试 | ✅ |

---

## 五、role_loader.py 超清单改动专项审查

**改动内容**（`loop_core/role_loader.py`，+21/-0，仅两处）：
- `build_role_context(role_id, project_root=".", task_id="", extra_files=None, *, include_memories=False, memory_limit=5)` — 关键字专用新参数，透传 `context_packager.build_context`；
- `load_role_prompt_with_context(...)` — 同签名扩展，透传 `build_role_context`。

**逐项审查结论**：

1. **是否如其声明"默认 False 转发参数、默认行为逐字节不变"**：✅ 独立验证成立。
   - 新参数均为关键字专用（`*` 后），不改变既有位置参数调用；
   - 默认 False 时 `build_context` 跳过记忆注入块（`if include_memories:` 短路），
     函数其余代码零改动；
   - **隔离子进程字节对比**：HEAD 版本与当前版本在 8 角色 × 5 调用（build_context /
     build_role_context / load_role_prompt_with_context，含 task_id 与 extra_files
     组合）= 40 项输出，逐字节完全一致。
2. **是否合理必要**：✅ 必要。D-03 设计-5 §5.3.2 要求"调用点显式传参"
   （role_orchestrator → 角色上下文），而 role_orchestrator 唯一加载角色上下文的入口
   就是 `load_role_prompt_with_context`（`loop_core/role_loader.py:140` 是
   role_orchestrator.py:103 的调用目标）；不加转发参数则显式传参无法到达
   context_packager，设计-5 落地必须走此管道。改动是 D-03 §6 清单文件
   （role_orchestrator/context_packager）之间缺失的最小接线，无替代路径。
3. **是否引入风险**：✅ 无。
   - 全项目仅 role_orchestrator 一处调用 `load_role_prompt_with_context`（grep 实证），
     无第三方/测试之外的隐式调用者；关键字专用参数不影响既有调用；
   - 未开启时行为逐字节不变（上述 40 项对比）；
   - 开启时记忆注入的失败路径全部 fail-closed（空召回 no-op、store 损坏抛异常）。
4. **唯一非阻塞备注（P3）**：该文件不在 D-03 §6 清单内，属 developer 主动扩展；
   已在 commands.md 遗留事项 #2 与 batch3-memory.md 中如实披露（"非 D-03 §6 清单文件，
   属最小管道"），披露充分、无隐瞒。

**专项结论**：role_loader.py 改动与其声明一致（默认 False、默认行为逐字节不变），
合理必要（设计-5 调用点机制的必经管道），不引入风险。**可接受**。

---

## 六、测试真实性抽查

| 测试文件 | 数量 | 断言真实性判断 |
|---|---|---|
| `tests/test_ai_decision_ledger.py` | 14（新） | ✅ 真实。覆盖：AD-{uuid12} 生成（长度/字符集断言）、JSON round-trip（`restored == rec`）、**无 human_actor 字段断言**、链校验多条目、"空链=合法"、篡改检测（替换字段后 verify False）、插入伪造行检测、find_by_task；**两条 ledger_guard 子进程测试**（合法追加 exit 0 / 篡改 exit 2）——非空断言，直接检验 D-03 §3.3.4 的"零 hook 改动"主张 |
| `tests/test_memory_injection.py` | 14（新） | ✅ 真实。配置读取三态（enabled true/false/缺失/损坏→fail-closed）、阶段前缀匹配（S4↔"S4-implementation"）、**monkeypatch 捕获 dispatch 实际 kwargs**（S4→(True,5)、S3→(False,5)、disabled→(False,5)）、context_packager 注入节存在性、**memory_limit=2 时逐行数断言（恰好 2 条 bullet）**、空 store no-op、store 损坏 `pytest.raises(KnowledgeStoreError)` |
| `tests/test_t0104_deviations.py` | 12（新） | ✅ 真实。从 SKILL.md 实际解析 JSON Schema（非字符串包含断言）、既有字段保留断言、格式校验器复刻 D-03 §3.3.1 规则（缺 reason/why_not_ask/impact_if_wrong→无效、空数组合法）、§5.2/§5.3 规则存在性 |
| `tests/test_t0104_templates.py` | 11（新） | ✅ 真实。三节存在 + **节顺序断言**（positions==sorted）、第 7 步、理解确认节 + 无残留"六、下一步"、**R10/R11 原文逐字断言**（与 HEAD 文本一致）、lifecycle/USER-PROMPTS 内容 |
| `tests/test_approval_ledger.py` | 58（54 存量 + 4 新） | ✅ 真实。comprehension True/False round-trip（写临时 gates.yaml 再读回）、**存量记录无键→None**（构造 legacy approval 块）、**None 不写键**（读回 YAML 断言键不存在） |

抽查结论：51 个新测试 + 4 个更新测试全部为实质性断言（值/存在性/顺序/子进程退出码），
无空断言、无"测试恒真"模式；独立运行 109 项全通过。

---

## 七、全量回归独立结果

命令：`C:/Python312/python.exe -m pytest tests/ -q`（排除 tests/deep_probe_v35.py、
tests/lab、tests/vertical_slice，与 developer 相同口径；tests/mcp_mock_server.py
为辅助模块，按默认收集不产生独立用例）。

**独立结果：3636 passed, 64 skipped, 12 xfailed, 0 failed（172.59s，exit 0）**

- 与 developer 报告（3635 passed + 1 failed = 3636 total）总数一致；
  developer 报告的唯一失败
  `test_manifest_t0095.py::test_manifest_exists_and_handoff_reference_is_real`
  在本次独立运行中**已通过**——`.ai/evidence/T-0104/evidence-manifest.v1.yaml`
  现已存在（HANDOFF 引用可解析），该失败是主会话 evidence 管线"先引用后生成"的
  时序问题，与本批代码改动无关，且已自愈。
- 编译检查：`compileall` 68/68 通过（与 compile-evidence.json 一致）。
- `validate_state.py .`：state usable（T-0102 的 legacy 状态 mismatch 为历史遗留，
  与本次改动无关）。
- 测试计数：4 个新测试文件 51 项 + test_approval_ledger +4 = 55 项新增，全部通过。

---

## 八、发现清单

**P0（阻断）：0**

**P1（高）：0**

**P2（中）：0**

**P3（低，建议性，不阻塞）：4**

1. **context_packager 记忆召回无任务/门过滤**（`loop_core/context_packager.py:78`）：
   `recall(root, limit=memory_limit)` 未传 task_id/gate_id/tag 过滤，为全局最新 N 条
   （newest-first），而 D-03 §5.4 与 context_loader（L940 传过滤参数）均为
   "按任务/gate/标签检索"。可能注入跨任务不相关记忆。fail-closed 语义未受影响
   （空召回 no-op、损坏抛异常），非安全项；建议后续在 S4+ 派发时透传 task_id 过滤。
2. **配置字段容错方向**（`loop_core/role_orchestrator.py:_load_memory_injection_config`）：
   phases 若误写为字符串（如 `"S4"`）会被逐字符展开为 `["S","4"]` 导致永不匹配
   （fail-closed 方向，无风险）；memory_limit 非法值被 except 捕获回退默认。
   行为方向安全，可加 schema 校验。
3. **evidence-manifest 时序依赖**：HANDOFF 对 T-0104 manifest 的引用在清单生成前
   会使 `test_manifest_t0095.py` 暂时失败（本次运行已通过）。后续任务若在 evidence
   管线产出前更新 HANDOFF，会再现同类时序失败——建议主会话在生成清单后才更新
   HANDOFF 引用。
4. **每次派发重读配置文件**：`_load_memory_injection_config` 每次
   `build_dispatch_manifest` 调用都读盘解析 YAML（两个候选路径），性能开销可忽略，
   可考虑缓存；失败路径 fail-closed 已保证。

---

## 九、总结论

T-0104 落地与 D-03 设计保持一致：5 项设计的候选文本全部按基线落地（35/35 抽查通过，
含引号归一化复验）；约束零弱化专项六项全部实证通过（hooks/ 与 context_loader 及
治理内核 diff 为空、R10/R11 逐字未动、fail-closed 语义经子进程与运行时复验不变）；
超清单改动 role_loader.py 判定为合理必要的管道转发且默认行为 40 项输出逐字节一致；
独立全量回归 3636 passed / 64 skipped / 12 xfailed / 0 failed；版本载体未被改动。

**裁决：GO**（无 P1/P2 条件；4 项 P3 建议不阻塞交付，可后续迭代处理）。
