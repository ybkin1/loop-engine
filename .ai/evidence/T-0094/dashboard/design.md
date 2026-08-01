# T-0094 D4 — AutoPlan Dashboard 升级设计证据

- 任务：T-0094（前端产品层 — AutoPlan dashboard 升级，D4）
- Gate：G-T-0094-REQUIREMENTS（approved）
- 对标：StaffDeck 前端产品层（可视化层；不引入完整 React 栈）
- 实现文件：
  - `loop_core/dashboard_views.py`（核心可视化层：四个视图 + 快照渲染）
  - `tools/tool_dashboard.py`（MCP 工具扩展：4 个新 handler）
  - `tools/loop_dashboard.py`（新增 argparse CLI）
  - `tests/test_dashboard.py`（23 个测试，AC-01~AC-04）
- 产出物：`.ai/evidence/observability/dashboard-snapshot.md`（文本报告）、
  `.ai/evidence/observability/dashboard-snapshot.html`（自包含 HTML）

## 1. 设计目标与范围

把 T-0081 的 AutoPlan dashboard（仅 JSON/markdown 健康摘要）升级为可视化层：

1. 任务图视图（节点 + 依赖边 + 状态汇总 + 拓扑顺序）
2. gate 视图（pending/approved/rejected 统计 + 决策记录）
3. 指标 + guard 健康视图（D2 metrics-report + U8 guard-events）
4. 快照报告（文本 + 自包含 HTML）

范围边界（与 T-0094 REQUIREMENTS 一致）：

- **不引入完整 React 栈** — 可视化层为纯 Python 生成静态视图（stdout/文件/MCP JSON），
  无构建链、无前端依赖。
- **数据源只读** — task_graph.yaml / gates.yaml / metrics-report.json /
  guard-events.jsonl 零修改；快照内嵌 sha256 作为只读证明（AC-04）。
- **缺失数据 fail-closed** — 任一数据源缺失/不可解析 → 该视图 NOT_AVAILABLE +
  原因说明，绝不猜测、绝不静默置零（复用 T-0090 B2 §2.5 语义）。

## 2. 数据流

```
task_graph.yaml ──┐
gates.yaml ───────┤
metrics-report.json ─┤── DashboardViews(root) ── 4 个 view dict ──┬─ render_text() ── dashboard-snapshot.md
guard-events.jsonl ─┘       （只读加载）                          ├─ render_html()  ── dashboard-snapshot.html
                                                                  └─ build_snapshot()（含 source_hashes）── JSON
```

- 所有加载器以只读方式打开文件（`open(..., "rb"/"r")`），无任何写路径。
- `build_snapshot()` 对 4 个数据源计算 sha256 写入 `source_hashes`；
  测试用生成前后哈希相等证明零修改。
- 视图是纯函数：同一提交 + 同一数据源 → 可复现输出（B2 §2.3 可复现性原则）。

## 3. 视图设计（AC 映射）

### AC-01 任务图视图（`task_graph_view`）

- 节点：`tasks` 列表 → {task_id, title, status, phase}（早期任务无 phase → null，显示 "-"）。
- 边：显式 `edges` 列表 + 每个任务的 `depends_on`（标量或列表均可）合并去重，
  按 (from, to) 字典序稳定排序。
- 状态汇总：{total, completed, in_progress, pending, other, by_status}。
- **依赖链正确性（拓扑顺序）**：Kahn 算法（入度 + 队列），候选按 task_id
  字典序出队保证确定性；边仅约束已知任务（指向未知 id 的边保留展示但不参与排序）；
  环/自环节点进入 `unresolved_tasks`（追加在末尾，绝不丢弃）。
- 渲染顺序即拓扑顺序（`ordered_nodes`）。

真实数据验证：81 任务 / 80 completed / 1 in_progress（T-0094）；
链 `T-0082→T-0083→T-0085→…→T-0094` 与 `T-0040→T-0041…T-0044→T-0046→T-0047→T-0048`
均按序出现（见 dashboard-snapshot.md 第 1 节）。

### AC-02 gate 视图（`gate_view`）

- 统计：pending / approved / rejected / other / total（按 status 归一化小写）+ by_decision。
- 决策记录：仅 status ∈ {approved, rejected} 的 gate，含
  {gate_id, task_id, gate_type, status, decision, approval_actor, recorded_at}；
  排序：recorded_at 降序（最新在前），无时间戳的记录置尾（按 gate_id 稳定）。

真实数据：86 gates，全部 approved（by_decision 86/0/0）。

### AC-03 指标 + guard 健康视图（`metrics_view` + `guard_health_view`）

- `metrics_view`：读取 metrics-report.json（D2 产出物，只读透传）：
  - 顶层：report_status、binding（task_id/git_commit/timestamp）、window；
  - error_budget：{status, total_units, remaining_units, consumed_units}；
  - 关键 dora 项（10 项精选）：gate_rejection_rate、gate_decision_coverage、
    approval_latency、task_cycle_time、phase_dwell_time、task_rework_cycles、
    guard_anomaly_rate、guard_events_summary、execution_cycle_time 等，
    每项折叠为 {status, value, basis/reason}；报告内 NOT_AVAILABLE 项原样透传
    （带 reason，如 phase_dwell_time: "phase_transitions.jsonl absent"）。
- `guard_health_view`：**直接从 guard-events.jsonl 重新计算**（不依赖报告快照）：
  total_events、fail_count、avg_duration_ms、by_guard（guard_id/total/fail）、
  by_result、by_check_type。严格逐行解析：损坏行 → 整源 NOT_AVAILABLE。

### AC-04 快照报告（`build_snapshot` + `render_text` + `render_html`）

- `build_snapshot()`：4 个视图 + binding（tool 身份/时间/commit）+ source_hashes；
  任一视图 NOT_AVAILABLE → 整体 status = NOT_VERIFIED（fail-closed）。
- `render_text()`：markdown 文本报告（章节 1~4 + 数据源哈希表）。
- `render_html()`：**单文件自包含 HTML**：
  - 内联 `<style>`（唯一外部引用为系统字体族名，非网络资源）；
  - 无 `<script>`、无 `src=`/`href=`/`@import`/`url(`/`<img>`、无 http(s) 链接；
  - 全部用户内容经 `html.escape`；仅表格/列表渲染。
- 文件写出：`write_snapshot_files()` → `.ai/evidence/observability/dashboard-snapshot.{md,html}`
  （可 `--out` 重定向到任意目录，测试中写入临时目录证明不污染数据源）。

## 4. 接口

### MCP 工具（tools/tool_dashboard.py，新增 handler）

| method | 返回 |
|---|---|
| `dashboard_task_graph` | AC-01 视图 dict |
| `dashboard_gates` | AC-02 视图 dict |
| `dashboard_guard_health` | {metrics, guard_health} 视图 |
| `dashboard_snapshot` | format=json/markdown/html 快照 |

（`dashboard_status` 保留 T-0081 原有行为不变。）

### CLI（tools/loop_dashboard.py）

```
python tools/loop_dashboard.py                 # 文本快照 → stdout
python tools/loop_dashboard.py --html          # 自包含 HTML → stdout
python tools/loop_dashboard.py --json          # JSON 快照 → stdout
python tools/loop_dashboard.py --snapshot [--out <dir|file.md|.html|.json>]
```

`--out` 语义：后缀 .md/.html/.json → 单文件；目录或无后缀 → 写 md+html。

## 5. 测试设计（tests/test_dashboard.py，23 个）

| AC | 测试 | 断言要点 |
|---|---|---|
| AC-01 | `test_nodes_edges_and_status_summary` | 节点字段、3 条边（edges 列表 + depends_on 标量/列表合并）、汇总 {2/1/1/4} |
| AC-01 | `test_topological_order_follows_dependency_chain` | T-100<T-101<T-102、T-103<T-102；ordered_nodes 同序 |
| AC-01 | `test_topological_order_reports_cycles` | 环节点进 unresolved，不崩溃不丢弃 |
| AC-01 | `test_missing/unparseable_task_graph_is_not_available` | 缺失/损坏 → NOT_AVAILABLE |
| AC-01 | `test_real_repo_view_is_self_consistent` | 视图与源文件直接解析结果一致（不随数据变化失效） |
| AC-02 | `test_counts_pending_approved_rejected` | 1/2/1 统计 + by_status/by_decision |
| AC-02 | `test_decision_records_fields_and_order` | 字段齐全；recorded_at 降序、无时间戳置尾；pending 不出现 |
| AC-02 | `test_missing_gates_register_is_not_available` + 真实数据一致性 | |
| AC-03 | `test_metrics_view_budget_and_key_items` | HEALTHY/100 预算；rejection 0.0；NOT_AVAILABLE 项带 reason 透传 |
| AC-03 | `test_guard_health_stats` | 4 事件/1 FAIL/avg 250ms；by_guard/by_result/by_check_type |
| AC-03 | `test_missing_metric_sources_are_not_available` + 真实数据一致性 | |
| AC-04 | `test_text_report_sections` / `test_text_report_marks_missing_data` | 章节齐全；全缺失 → NOT_VERIFIED + NOT_AVAILABLE |
| AC-04 | `test_html_is_self_contained` | 无 script/src/href/http(s)/@import/url(/img；内联 style；表格 |
| AC-04 | `test_snapshot_files_written_with_readonly_hash_proof` | **4 数据源生成前后 sha256 逐字节相等**；快照哈希与文件一致 |
| AC-04 | `test_snapshot_json_roundtrip` | JSON 往返结构完整 |
| CLI | `test_cli_text_json_html_stdout` / `test_cli_snapshot_writes_files` / `test_cli_snapshot_single_file` | 三种 stdout 格式；--snapshot 写目录/单文件 |
| MCP | `test_mcp_handlers` | 4 个新 handler success + 结构 |

## 6. 验证结果

- `pytest tests/test_dashboard.py -q` → **23 passed**
- 全量 `pytest tests/ -q` → **3476 passed, 63 skipped, 12 xfailed**（无回归，基线 ≥3453）
- 快照 Status：PASS（4 数据源全部可用）；真实数据哈希见
  `dashboard-snapshot.md` 尾部 / HTML "Data source hashes" 节。

## 7. 只读与合规

- 实现仅读写允许路径：`loop_core/`、`tools/`、`tests/`、`.ai/evidence/…`；
- 数据源（`.ai/task_graph.yaml`、`.ai/gates.yaml`、
  `.ai/evidence/observability/metrics-report.json`、`guard-events.jsonl`）
  仅以读模式打开；测试哈希证明零修改；
- 快照文件是唯一新增写入物（观测性 evidence 目录，属 T-0094 允许路径）。
