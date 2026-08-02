# F-03 release.py bump `--title` 透传（AC-03）

## 根因（T-0101 独立审查 P3 观察项 #2）

`scripts/release.py` `VERSION_CARRIERS` 中 CHANGELOG 更新器为
`lambda c, v: _update_changelog(c, v)`（T-0100 F-03 引入）：`_update_changelog` 本身
支持 `title` 参数，但 lambda 不接收/不传递 —— `cmd_bump(title=...)` 的 title 被丢弃，
`bump --title "..."` 的 CHANGELOG 条目恒用缺省标题"版本同步（release.py bump 子命令）"。

## 改动

`scripts/release.py`：

1. `VERSION_CARRIERS` 从二元组 `(path, updater)` 升级为三元组
   `(path, updater, use_title)`，仅 `CHANGELOG.md` 为 `(_update_changelog, True)`，
   其余 7 个载体 `False`（签名 `(content, version)` 不变，改动面最小）。
2. `cmd_bump()`：`for rel_path, updater, use_title in VERSION_CARRIERS`，
   `new_content = updater(content, version, title) if use_title else updater(content, version)`。
3. `_print_plan` 的解包同步为 `rel, _, _`。

## 测试

`tests/test_release_bump.py`：

- 新增 `test_bump_title_passthrough_to_changelog`：`cmd_bump(root, "9.8.7", title="自定义标题")`
  → CHANGELOG 头部新条目标题含"自定义标题"、不含缺省标题；旧条目保留。
- 连带维护 `test_bump_carrier_failure_reports_error` 到三元组契约
  （`bad_updater(content, version, title="")` 仍抛 ValueError → exit 1 语义不变）。

复验：`pytest tests/test_release_bump.py` → 13 passed；CLI 实机验证（F-04）：
`release.py bump --to 3.12.41 --title "T-0102 — ..."` → CHANGELOG 头部条目
`## v3.12.41 (2026-08-02) — T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零`。

## 约束

仅透传单参数；`_update_changelog` 的 heading 格式、降序插入、"先 bump 再提交"文案均不变；
test_version_consistency 只认第一个 `## vX.Y.Z` 的契约不受影响（7 passed）。
