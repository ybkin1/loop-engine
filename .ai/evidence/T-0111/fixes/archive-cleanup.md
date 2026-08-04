# T-0111 清理/防篡改链收尾（D3-3 归档保留 + 归档核对 + D3-7 留档）

日期：2026-08-03
涉及文件：`loop_core/execution_ledger.py`（D3-3）；只读核对：
`.ai/archive/`、`tests/test_ai_doc_links.py`

## 1. D3-3：execution_ledger 归档保留 N 份 + 跨归档链延续

**改动前缺陷**（roadmap D3-3）：checkpoint 归档旧文件后**无保留策略**
（归档即重置链——`_MAX_ENTRIES` 触发 rename 后新链从 root 重开），
历史归档无限堆积且与活动链脱节（归档即断链）。

**落地**（`loop_core/execution_ledger.py`）：

1. **保留 N 份**：`max_archives` 构造参数（默认 `DEFAULT_MAX_ARCHIVES=3`，
   与 guard-events 轮转保留档对齐）；checkpoint 后清理最旧归档
   （`_prune_archives`：仅保留最近 N 份，OSError 吞错不阻断写入）。
2. **跨归档链延续**：活动文件为空时 `_last_chain_hash()` 从最新归档尾
   哈希续接（不再重置 root）——全部保留历史构成一条连续链。
3. **验证面**：
   - `verify_chain()`：活动链，续接点 = 最新归档尾（归档尾被篡改/丢失
     会在活动验证暴露）；
   - `verify_archive_chain()`：全保留历史（归档段内链 + 段间延续 + 活动
     段）。**有界保留固有边界**：最旧保留段的锚条（首条）前驱已被清理
     ，锚条自身链路不可验证——段内其余与全部延续段严格验证（文档化，
     测试 `test_oldest_retained_anchor_link_is_bounded`）。
4. **归档命名防重**：同秒多次 checkpoint 用 `-<n>` 后缀；`_archives()`
   以 (ts, seq) 排序键排序（字符串序会把 `-n` 文件排在无后缀之前，
   颠倒新旧——实现中已显式解析排序）。

**防篡改链价值**：历史段篡改在 `verify_archive_chain` 可见（段内 mismatch）；
最新归档尾被篡改同时破坏活动链（续接点错位）；中间段删除造成链空洞
（后续段首条 prev 对不上）。保留策略的清理是"有界历史"设计：超出
N 份的旧段按策略丢弃（与 guard-events 轮转同语义），保留下来的历史
保持连续可验。

**测试**（tests/test_execution_ledger.py::TestArchiveRetentionAndContinuity，
7 项全绿）：

| 用例 | 断言 |
|------|------|
| retention_keeps_N_and_prunes_oldest | 9 条/阈值 3/max=2 → 恰 2 份归档 + archive_chain 通过 |
| default_retention_is_three | 默认 max_archives=3（4 次 checkpoint 后保留 3 份） |
| live_chain_continues_from_archive_tail | checkpoint 后新条目从归档尾续接，双验证通过 |
| tampered_oldest_archive_detected | 最旧保留段段内篡改 → archive_chain False；活动链不受影响 |
| oldest_retained_anchor_link_is_bounded | 锚条篡改不在可验证面（前驱已清理，文档化边界） |
| tampered_newest_archive_detected | 最新归档段内篡改 → archive_chain False；活动链仅依赖尾值 |
| archive_gap_reported | 中间归档删除 → archive_chain False（链空洞）；活动链仍通过 |

既有 `test_auto_checkpoint_archives_and_resets` 保持通过（链延续后
verify_chain 语义兼容）。

## 2. 归档文档核对（.ai/archive 无悬挂引用）

- `test_ai_doc_links.py` 全绿（8 passed）：README Switchboard 三节/目录
  四态/归档分类表、`.ai/` 顶层文档引用全解析、归档计划文件存在且原
  位置已清空（PLAN-20260729-001/002 → `.ai/archive/plans/`）。
- `.ai/archive/plans/*.yaml` 内容复核：仅含模板占位引用
  （`.ai/evidence/{task_id}/`，doc-link 检查器对 `<...>` 占位符免判），
  无真实悬挂路径。
- 结论：归档区无悬挂引用，README 归档说明与磁盘状态一致。

## 3. D3-7 记录留档（不实施）

roadmap 排布：dev.py `open("a")` 日志无轮转 → **不实施（记录留档）**。
依据：audit 已分类"文档化即可"（dev 内部工具、影响低）；本任务终态
审计确认未触碰 dev.py（不在 allowed_paths，git status 无该文件条目）。
如后续需要，可对齐 T-0095 轮转模板（DEFAULT_MAX_LINES/BYTES/ARCHIVES）
与 guard-events/execution_ledger 的 max_archives 语义实施。
