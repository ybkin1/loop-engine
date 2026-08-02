# F-04 版本 bump 3.12.41（AC-05）

## 执行

```bash
$ C:/Python312/python.exe scripts/release.py bump --to 3.12.41 \
    --title "T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零"
[release] bump: 已更新 pyproject.toml -> 3.12.41
[release] bump: 已更新 CHANGELOG.md -> 3.12.41
[release] bump: 已更新 loop_core/__init__.py -> 3.12.41
[release] bump: 已更新 src/loop_engine/__init__.py -> 3.12.41
[release] bump: 已更新 README.md -> 3.12.41
[release] bump: 已更新 docs/06-delivery.md -> 3.12.41
[release] bump: 已更新 .zcode-plugin/plugin.json -> 3.12.41
[release] bump: 已更新 .ai/version-manifest.yaml -> 3.12.41
[release] bump 完成。约定：先 bump 再提交 —— 提交 subject 使用 v3.12.41，...
```

8 载体（pyproject.toml / CHANGELOG.md / loop_core/__init__.py /
src/loop_engine/__init__.py / README.md / docs/06-delivery.md /
.zcode-plugin/plugin.json / .ai/version-manifest.yaml）原子同步 3.12.41；
CHANGELOG 头部条目标题来自 `--title`（F-03 实机验证）。

## 连带维护

`tests/test_release_bump.py` 硬编码版本 3.12.40 → 3.12.41 共 7 处（T-0101 同款
"bump 机制连带维护"惯例；迷你项目 fixture 复制真实载体后断言旧条目）。

## 复验

- `pytest tests/test_version_consistency.py` → 7 passed（8 载体逐项 == pyproject）。
- `pytest tests/test_release_bump.py` → 13 passed。
- 全量回归：`test_pyproject_version_matches_git_head` 为瞬时失败项（pyproject=3.12.41
  vs git HEAD=3.12.40），按"先 bump 再提交"约定以 subject `v3.12.41` 提交后自愈
  （AC-05 version_sync PASS 提交后成立）。
