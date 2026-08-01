# D7 异步任务队列 — 设计证据 (T-0090 AC-03)

## 1. 设计来源（StaffDeck 对标，T-0086 staffdeck-benchmark.md）

StaffDeck `backend/app/async_jobs.py`（ThreadPoolExecutor + 内存状态
queued→running→succeeded/failed + 历史裁剪）确定 D7 落点；租约语义参照
loop-engine 既有 `loop_core/dispatch_lease.py` 的防重复派发思想
（同一 key 已有 active 租约 → CONFLICT，不重复执行）。

| 维度 | StaffDeck async_jobs | D7 落点（loop_core/async_jobs.py） |
|------|----------------------|-----------------------------------|
| 执行 | ThreadPoolExecutor | `ThreadPoolExecutor`（`max_workers` 可配，默认 4，线程名前缀 `async-job`） |
| 状态 | queued→running→succeeded/failed | `JobStatus`：queued→running→succeeded/failed/cancelled（cancelled 为 loop-engine 扩展） |
| 防重复 | —（scheduled_tasks 租约式领取） | `submit` 租约防重复：queued/running 的同 `job_id` → `SubmitOutcome(accepted=False, reason="duplicate")`，回调不执行；终态 job_id 槽位释放可重提（对应 dispatch_lease 的 RELEASED） |
| 历史 | 裁剪 | `max_history`（默认 500）裁剪最旧终态记录；**活跃（queued/running）记录永不裁剪** |
| 持久化 | SQLite | 可选 append-only JSONL（`.ai/evidence/observability/jobs.jsonl` 或自定义路径），失败重试/审计可追溯 |

## 2. 状态机与租约语义

```
[submit] ──► queued ──► running ──► succeeded
                 │          │  └────► failed       (任务抛错，错误记录进 record)
                 │          └──────► cancelled     (协作式取消：任务内轮询后返回)
                 └────────► cancelled              (queued 中被取消 → 永不执行)

[submit 同 job_id，已有 queued/running] ──► SubmitOutcome(accepted=False, "duplicate")
[submit 同 job_id，已终态] ──► 槽位释放，重新入队（旧记录被替换，落盘日志保留全轨迹）
```

- **租约防重复（AC-03b）**：`submit` 在锁内检查 `_jobs[job_id]`；存在且为
  ACTIVE_STATES（queued/running）→ 返回 duplicate 标记，回调**绝不执行**。
  自动 job_id（`job-<sha256[:16]>`，由 fn module/qualname + args/kwargs
  确定性哈希生成）使"相同工作并发提交"同样收敛为单次执行。
- **协作式取消（AC-03d）**：`cancel(job_id)` 对 queued 立即终态化
  （`cancelled`，永不执行）；对 running 置 `cancel_requested` 标志，任务内
  通过 `cancel_requested(job_id)` 轮询（`cancel_requested` 为真时任务自行
  返回 → 终态 `cancelled`，结果丢弃）。
- **异常隔离（AC-03c）**：worker wrapper 捕获 `BaseException`（含
  SystemExit）→ `failed` + `error`/`error_type` 记录 + `logging.warning`；
  队列与后续任务不受影响（单 worker 场景有测试证明）。

## 3. 线程安全与关停

- 单一 `threading.Lock` 守护 `_jobs`（插入序 dict，最旧在前）/`_events`
  （每 job 一个 `threading.Event`，`wait(job_id, timeout)` 阻塞至终态，
  测试免 sleep 轮询）/落盘写。任务函数本身在锁外执行（不互相阻塞）。
- `shutdown(wait=True, timeout=None)` 优雅关停：停止接受新提交（此后
  `submit` 抛 `AsyncJobQueueError`），等待全部 queued/running 到达终态
  （可用 `timeout` 限界）；`wait=False` 立即返回，已提交任务后台跑完。
  幂等；`with` 上下文管理器自动关停。

## 4. 落盘（可选，append-only JSONL）

- 仅当 `persist_path` 显式传入时启用（默认关闭，测试/日常零 IO）；默认
  路径常量 `DEFAULT_JOB_LOG_PATH = ".ai/evidence/observability/jobs.jsonl"`。
- 每 job 最多 3 行：`submit` / `start` / `terminal`（一行一 JSON，含
  record 快照），**只追加不重写**；`read_log()` 可回读（损坏行跳过，
  可读前缀保留）。
- 观测纪律（镜像 loop_core/observability.py 的 U8 规则）：写入失败 →
  `persist_failures += 1` + `persist_last_error` + warning，**绝不抛给
  业务**；不可序列化结果降级为 `{"__non_serializable__": type, "repr": …}`
  标记而非失败。

## 5. 安全/治理红线（AC-06，无约束弱化）

- 本模块为**纯新增能力**：不触碰、不修改任何既有模块的裁决路径
  （enforcement/hard_constraints/guard_health 零依赖）；不弱化任何
  fail-closed 语义。
- 后台任务异常由 wrapper 捕获，不外泄、不崩进程；持久化失败同样吞并计数。
- 无真实凭据/外部服务：纯 stdlib（concurrent.futures/threading/json/hashlib）。

## 6. 验收映射（AC-03）

| 验收 | 测试类 | 测试 |
|------|--------|------|
| AC-03a 状态跟踪全周期 | `TestStateTracking` | queued→running→succeeded（单 worker 阻塞确定性观测）、failed+错误记录、active 计数 |
| AC-03b 租约防重复 | `TestLeaseDedup` | 8 线程并发同 job_id 只执行 1 次、running 中重复提交返回 duplicate 标记、终态槽位释放可重提、自动 job_id 确定性去重 |
| AC-03c 异常隔离 | `TestExceptionIsolation` | 抛错→failed+错误记录、队列继续工作、单 worker 存活、SystemExit 不杀队列 |
| AC-03d 协作式取消 | `TestCooperativeCancel` | queued 取消永不执行、running 任务轮询生效（cancelled+结果丢弃）、终态/未知取消 no-op |
| AC-03e 历史裁剪 | `TestHistoryTrimming` | 超 max_history 裁剪最旧、活跃任务永不裁剪、默认 500 |
| 附加 | `TestPersistence` / `TestShutdown` / `TestThreadSafety` | append-only 落盘+回读、写失败不阻断、优雅关停、并发提交安全 |

## 7. 风险与回退

| 风险 | 等级 | 缓解 |
|------|------|------|
| 取消是协作式（任务不轮询则不中止） | LOW | 文档明示 + `cancel_requested()` 轮询 API；queued 取消为强取消（绝不执行） |
| shutdown(wait=True) 遇永不结束任务会阻塞 | LOW | `timeout` 限界参数；wait=False 逃生口 |
| 自动 job_id 依赖参数可序列化性 | LOW | `json.dumps(default=str)` 兜底；非确定性对象参数时调用方可显式传 job_id |
| 线程池任务堆积无界 | LOW | 治理长任务量级小；历史裁剪 + 租约防重复抑制重复堆积 |
