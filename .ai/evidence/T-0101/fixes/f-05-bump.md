# F-05 — 版本 bump 3.12.40（F-03 bump 机制闭环）— AC-06

## 执行

```text
$ python scripts/release.py bump --to 3.12.40 --title "T-0101 idle 稳态语义修复（NO_ACTIVE_TASK exit 3 分流 + 消费端对齐）"
[release] bump: 已更新 pyproject.toml -> 3.12.40
[release] bump: 已更新 CHANGELOG.md -> 3.12.40
[release] bump: 已更新 loop_core/__init__.py -> 3.12.40
[release] bump: 已更新 src/loop_engine/__init__.py -> 3.12.40
[release] bump: 已更新 README.md -> 3.12.40
[release] bump: 已更新 docs/06-delivery.md -> 3.12.40
[release] bump: 已更新 .zcode-plugin/plugin.json -> 3.12.40
[release] bump: 已更新 .ai/version-manifest.yaml -> 3.12.40
```

8 个载体全部同步为 3.12.40。

## 载体一致性验证

```text
$ python -m pytest tests/test_version_consistency.py -q
7 passed
```

`pyproject.toml`（唯一事实来源）与 CHANGELOG 头部 / loop_core `__version__` /
src/loop_engine `__version__` / README / docs/06-delivery.md / plugin.json /
version-manifest 投影逐项一致（test_version_consistency 为权威校验）。

## CHANGELOG

v3.12.40 条目正文补充为 T-0101 修复内容（5 项 Changed + 版本同步约定）。

> 已知小缺陷（F-03 既有，不在本任务范围）：`bump --title` 参数未被透传到
> CHANGELOG 更新（`VERSION_CARRIERS` 中 CHANGELOG 的 lambda 丢弃 title），
> bump 使用缺省标题。已通过手动完善 CHANGELOG 条目正文弥补；如需修复
> 可在后续任务处理。

## 提交约定（F-03："先 bump 再提交"）

- 全量回归在本任务树（pyproject=3.12.40，HEAD=ecac6a3 v3.12.39）运行时，
  `tests/test_release.py::test_pyproject_version_matches_git_head` 预期失败
  （version_sync 瞬时项）——这正是 F-03 约定的"先 bump 再提交"语义：
  主会话以 subject `v3.12.40: T-0101 ...` 提交后即自愈（与 T-0100
  "2 预期瞬时项提交后自愈"先例一致）。
- "版本 3.12.40 与 HEAD 一致"（AC-06）在提交时达成；idle 稳态 6/6 复验
  由主会话在提交后执行。

## bump 连带维护

`tests/test_release_bump.py` 硬编码当前仓库版本（T-0100 时代写死 3.12.39），
bump 后失效：`test_bump_invalid_version_is_usage_error` 断言
`load_version == "3.12.39"` 失败。已同步更新 4 处（docstring、CHANGELOG
降序断言、load_version 断言、原子写 replace 源串）为 3.12.40 →
`pytest tests/test_release_bump.py -q` 11 passed。

> 提示：bump 后续任务需同步检查 tests/test_release_bump.py 中的硬编码版本。

