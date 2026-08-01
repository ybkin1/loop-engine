# U7 — evidence 可靠投递：幂等 + 退避重试 + 卡死重置（设计证据）

- 任务: T-0089（G-T-0089-REQUIREMENTS approved）
- 对标: T-0086 staffdeck-benchmark — StaffDeck `backend/app/channels/service_outbox.py` 的
  "幂等键 + 条件领取 + 指数退避 + 卡死重置" 模式
- 目标函数: `.zcode/tools/governor_lib.py::transactional_write_texts`
- 验收: AC-02（幂等有测试 / 退避重试有测试 / 卡死重置有测试；AC-02d 向后兼容）
- 状态: implemented（2026-07-31）

## 1. 现状与差距

现有 `transactional_write_texts(base, changes)` 已具备：

1. **journal marker**：`{base}/.project-governor-transaction.json`，记录 transaction_id /
   entries（staged/backup 路径、原指纹）/ committed 列表，逐文件提交并增量更新 journal；
2. **并发检测**：提交前对每个目标文件做 sha256 指纹比对，发现外部改动即抛
   `RuntimeError("Concurrent modification detected: ...")`；
3. **回滚**：任一步失败时逆序恢复 backup / 删除新建文件，finally 清理 staged/backup 与 marker。

与 StaffDeck outbox 对照的差距：

| StaffDeck outbox 模式 | loop-engine 现状 | U7 落地 |
|---|---|---|
| 幂等键（唯一约束 + 去重） | 无：同内容重复提交会重复写盘 | 内容指纹（sha256）幂等表 |
| 指数退避重试 | 无：失败直接抛出，调用方自行处理 | RetryPolicy 指数退避 + 上限 |
| 卡死重置（120s 超时） | 无：遗留 marker 永远阻塞后续写入（需人工删除） | stale_timeout_seconds 安全重置 |

## 2. 设计决策

所有新能力均为**可选参数**，默认关闭；纯默认路径的代码语义与旧实现逐行等价（见 §4）。

### D1 幂等（`idempotent: bool = False`）

- 开启时，提交前对每个目标文件计算内容指纹
  `sha256(text.encode("utf-8")).hexdigest()`（与目标路径共同作为幂等键）。
- 幂等记录存于专用表 `{base}/.project-governor-idempotency.json`
  （dotfile，与 marker 同级，不进入业务文件）；结构：
  `{ "<path>": {"fingerprint": "<sha256>", "written_at": "<iso>", "transaction_id": "<tx>"} }`。
  每路径一条记录 → 同路径同指纹重复提交**不产生重复记录**。
- 命中幂等（同路径同指纹）→ 跳过该文件（不 stage、不写盘、不产生 tmp/bak），
  计入返回 `TransactionResult.skipped`；未命中 → 正常写入，全部提交成功后原子更新表
  （`.{name}.tmp` + `os.replace`，避免半写损坏）。
- 表损坏（JSON 解析失败 / 非对象）→ fail-closed：抛明确错误拒绝写入，
  不静默跳过（避免误判幂等导致丢写）。
- 提交失败回滚时表不更新（文件已回滚，幂等记录保持旧值，下次重写并重记）。
- 已知权衡：表更新发生在全部提交成功之后，若进程在"提交成功 → 表落盘"之间崩溃，
  该次写入的幂等记录丢失（下次同内容会重写）。正常流程下由 journal marker 串行化，
  重复提交不会并发；设计上接受该窗口（StaffDeck 同级别保证）。

### D2 退避重试（`retry: RetryPolicy | dict | bool | None = None`）

- `RetryPolicy(max_attempts=3, backoff_base_seconds=1.0, backoff_multiplier=2.0)`；
  亦接受 dict（三个键的子集）或 `True`（默认策略）；`None`/`False` 关闭（默认）。
- 每次重试 sleep = `backoff_base_seconds * backoff_multiplier ** (attempt - 1)`（指数退避）。
- 重试对象：`(OSError, RuntimeError)` —— 覆盖 IO 错误与并发检测冲突
  （"Concurrent modification detected"）。非法策略（max_attempts<1、负基数、
  未知键）→ `GovernanceError("INVALID_RETRY_POLICY")` 明确拒绝。
- **超上限 → 重抛最后一次异常**（绝不静默丢弃）；失败后 journal 一致性：
  每次 attempt 是完整独立事务（重新生成 transaction_id、独立 marker、独立回滚），
  前一次失败的 marker/staged/backup 已由 finally 清理。
- 极端情况：自身 attempt 回滚本身失败（`recovered=False`，marker 遗留）→
  `_recover_marker_for_retry` 识别 journal 中 transaction_id 为本进程所有，
  经无并发写者双读校验后清理再重试（不破坏他人 marker）。
- 返回值：启用 retry 时返回 `TransactionResult(written, skipped, attempts)`。

### D3 卡死重置（`stale_timeout_seconds: float | None = None`）

- journal 新增 `created_at`（`now_precise()` ISO 带时区）；向后兼容：旧 journal
  无 `created_at` 时回退用 marker 文件 mtime 判定陈旧性。
- 判定：`age = now - created_at > stale_timeout_seconds` → 陈旧。
- **重置前置校验（双保险）**：
  1. 陈旧性校验：不陈旧 → `RuntimeError("Active Project Governor transaction in progress ...")`
     拒绝（即有并发写者/活动事务时拒绝）；
  2. 无并发写者校验：陈旧后 sleep 一个 settle 间隔（50ms），期间 journal 必须
     **字节级稳定**（双读一致）；不一致（另一写者仍在提交）→
     `RuntimeError("Concurrent writer detected while resetting stale transaction ...")`
     拒绝，不删除任何东西。
- 校验通过后：journal 标记 `status: "stale"` + `marked_stale_at` → 清理 entries 中
  残留的 staged/backup → 删除 marker → 允许全新写入。
- 损坏的 journal（非法 JSON / 非对象）→ 拒绝重置且**不删除**（fail-closed，
  防误删他人状态），报 "Corrupt transaction journal (reset refused)"。
- 与 marker 的既有语义一致：marker 存在 = 事务未完结；`stale_timeout_seconds=None`
  （默认）时保持旧行为——存在即抛 "Unresolved Project Governor transaction"。

### D4 返回值

- `TransactionResult(written: list[str], skipped: list[str], attempts: int = 1)`。
- 纯默认路径（idempotent=False 且 retry=None）仍返回 `None` —— 现有调用方
  （close_session.py / install.py / upgrade.py）不受影响。

## 3. 文件清单

| 文件 | 变更 |
|---|---|
| `.zcode/tools/governor_lib.py` | `transactional_write_texts` 重构为 wrapper + `_transactional_write_texts_once`；新增 `RetryPolicy`、`TransactionResult`、幂等表读写、陈旧恢复、重试循环；journal 增加 `created_at`；新增 `time`/`dataclasses` 导入 |
| `tests/test_reliable_delivery.py` | 新增 18 个测试（AC-02a..d 四组） |
| `.ai/evidence/T-0089/reliable-delivery/design.md` | 本文档 |

## 4. 向后兼容性论证（AC-02d）

- 新参数全部 keyword-only 且带默认值；默认路径调用链：
  `transactional_write_texts(base, changes)` → `_coerce_retry_policy(None)` 返回 None →
  `_transactional_write_texts_once(..., stale_timeout_seconds=None)` → marker 存在即抛
  `Unresolved Project Governor transaction`（消息不变）→ 事务体与旧实现逐行等价
  （staged/backup 命名、指纹比对、回滚、finally 清理均未改动）。
- 唯一增量：journal JSON 多一个 `created_at` 字段（无外部消费者，仅存在性检查）。
- 回归证据：
  - `tests/lab/test_project_governor_consistency.py`（134 项含 5 subtests 的
    test_operations/test_cross_layer_safety 联合回归）全绿；
  - 新增 `BackwardCompatibilityTests`：默认成功语义、重复提交不建表、
    未决 marker 报错不删 marker、部分提交回滚 —— 与旧行为逐一对照。

## 5. 测试矩阵（AC-02）

| AC | 测试类 | 测试 | 断言要点 |
|---|---|---|---|
| AC-02a | IdempotentWriteTests | duplicate_submission_skips_write_and_records_once | 同内容二次提交 skipped、内容不变、表仅 1 条记录 |
| AC-02a | IdempotentWriteTests | different_content_writes_and_updates_fingerprint | 异内容正常写、指纹更新、新指纹可去重 |
| AC-02a | IdempotentWriteTests | partial_duplicate_multi_path_transaction | 多文件混合：重复的跳过、变更的写入 |
| AC-02a | IdempotentWriteTests | skipped_write_leaves_no_staged_files_or_marker | 跳过不产生 tmp/bak/marker |
| AC-02b | BackoffRetryTests | retry_succeeds_after_failures_with_exponential_backoff | 失败 2 次后成功，sleep=[0.01, 0.02]（指数退避），attempts=3 |
| AC-02b | BackoffRetryTests | retry_exhaustion_raises_clear_error_not_silent_drop | 超上限重抛原异常，无静默丢写，marker 干净 |
| AC-02b | BackoffRetryTests | retry_recovers_from_concurrent_modification_conflict | 并发检测冲突按策略重试成功 |
| AC-02b | BackoffRetryTests | first_attempt_success_reports_one_attempt / invalid_retry_policy_rejected | 首次成功 attempts=1；非法策略拒绝 |
| AC-02c | StaleRecoveryTests | stale_marker_reset_allows_rewrite_and_cleans_leftovers | 陈旧 marker 重置、残留 tmp/bak 清理、可重写 |
| AC-02c | StaleRecoveryTests | fresh_marker_refused_as_concurrent_writer | 未陈旧 marker 拒绝且不删除 |
| AC-02c | StaleRecoveryTests | stale_marker_with_active_writer_refused | settle 期 journal 变化（并发写者）→ 拒绝 |
| AC-02c | StaleRecoveryTests | legacy_journal_without_created_at_uses_mtime / corrupt_journal_refused_not_deleted | 旧 journal mtime 回退；损坏 journal 拒绝且不删 |
| AC-02d | BackwardCompatibilityTests | 4 项（默认成功/重复提交/未决 marker/部分提交回滚） | 默认行为与旧实现一致，返回 None |

运行：`python -m pytest tests/test_reliable_delivery.py -v` → 18 passed。

## 6. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 幂等改造影响现有写入 | LOW | 可选参数默认关闭；AC-02d 测试 + lab 回归证明零影响 |
| 重试掩盖永久性错误 | LOW | 仅重试 (OSError, RuntimeError) 瞬时类失败；上限后明确重抛 |
| 卡死重置误删活动事务 | LOW | 陈旧性 + 双读字节稳定性双重前置校验；失败即拒绝且不删除 |
| 幂等表损坏导致误判 | LOW | fail-closed 报错；原子落盘（tmp+replace） |
