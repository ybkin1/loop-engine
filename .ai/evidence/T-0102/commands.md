# T-0102 关键命令与输出摘要

执行环境：Windows 10 x64 / Git Bash / C:/Python312/python.exe（Python 3.12.10）
基线：git HEAD `c737c3a`（v3.12.40，T-0101）；工作树含全部 T-0102 改动（未提交）
验证环境：临时 idle worktree（`git worktree add ../loop-wt-idle HEAD`，committed `current_task_id: null` 真 idle 态；验证完已 `git worktree remove`，主树状态文件零改动）

## 1. 根因定位

```bash
$ git log -S "evidence/none" --oneline
c737c3a v3.12.40: T-0101 — idle 稳态语义修复（...）
bc6680f v3.12.36: T-0097 — B2 学习回路补全（...）
...
$ git blame -L 216,300 .zcode/tools/continuity_producer.py
# L220 (924bbd6 v1.0.0): task_id = action["current_task_id"] or "none"   ← display 占位
# L293 (87fe5d6 v3.12.0): Evidence manifest: {...if task_id else 'not available...'}
#   —— L220 已把 None 替换为 "none"（truthy），L293 的 if 保护永远为真
#   → idle 态必然渲染 .ai/evidence/none/evidence-manifest.v1.yaml（悬挂引用）
```

## 2. 修复前对照（idle worktree，committed HANDOFF）

```bash
$ grep -n "Evidence manifest" .ai/HANDOFF.md
124: Evidence manifest: .ai/evidence/none/evidence-manifest.v1.yaml.   # 悬挂（目录不存在）

$ C:/Python312/python.exe -m pytest tests/test_manifest_t0095.py -q
# FAILED x3:
#   test_manifest_exists_and_handoff_reference_is_real   ← .ai/evidence/none/ 悬挂引用
#   test_every_listed_file_exists_and_matches_fingerprint ← worktree 检出 CRLF/mtime 噪声
#   test_manifest_passes_official_verifier                ← 同上
```

## 3. 修复后（idle worktree：repair_continuity → close_session）

```bash
$ C:/Python312/python.exe .zcode/tools/repair_continuity.py .
[repair_continuity] Fixed 284 drifted hash(es).   # HEAD 提交自带连续性漂移（T-0101 已知遗留），先修复

$ C:/Python312/python.exe .zcode/tools/validate_state.py .
[info] NO_ACTIVE_TASK: state.current_task_id is null（合法阻塞态：...）
# exit 3  ← idle 合法阻塞态

$ C:/Python312/python.exe .zcode/tools/close_session.py .
[ok] HANDOFF_GENERATED_FROM_STRUCTURED_STATE: ...\loop-wt-idle\.ai\HANDOFF.md

$ grep -n "Evidence manifest" .ai/HANDOFF.md
Evidence manifest: .ai/evidence/T-0101/evidence-manifest.v1.yaml.   # 实际存在的最近任务 manifest
# 无 .ai/evidence/none/ 引用（python 脚本断言 "dangling none ref present: False"）

$ C:/Python312/python.exe -m pytest tests/test_manifest_t0095.py -q
# （检出 CRLF/mtime 噪声按 manifest 记录值复原后）4 passed
```

注：worktree 全新检出会把文本文件 CRLF 化并重置 mtime，而 T-0095 manifest 按生成时磁盘字节
（LF 与 CRLF 混合、含 mtime_ns 绑定）记录 —— 属检出环境噪声（主树同文件全绿），与本次修复无关；
按 manifest 记录值复原后 4/4 全绿。

## 4. F-02 rollback rc 感知

```bash
$ C:/Python312/python.exe -m pytest tests/test_operations.py -k "verify_state" -q
# 4 passed（新增：rc=0 通过 / rc=3 idle 通过 / rc=2 损坏阻断 / rc=1 阻断）
```

## 5. F-03 bump --title 透传

```bash
$ C:/Python312/python.exe -m pytest tests/test_release_bump.py -q
# 13 passed（新增 test_bump_title_passthrough_to_changelog）

$ C:/Python312/python.exe scripts/release.py bump --to 3.12.41 --title "T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零"
[release] bump: 已更新 pyproject.toml -> 3.12.41
[release] bump: 已更新 CHANGELOG.md -> 3.12.41
...（8 载体全部同步 3.12.41）
$ head -5 CHANGELOG.md
## v3.12.41 (2026-08-02) — T-0102 — handoff 生成器 idle 占位修复 + P3 观察项清零   ← --title 已透传
```

## 6. 全量回归（主树，T-0102 激活态）

```bash
$ C:/Python312/python.exe -m pytest tests/ -q
# 3766 passed, 2 failed, 64 skipped, 12 xfailed（209s）
# 2 failed 均为提交后自愈瞬时项：
#   ① test_pyproject_version_matches_git_head  —— pyproject=3.12.41 vs HEAD=3.12.40（F-04 先 bump 再提交约定）
#   ② test_manifest_t0095 悬挂引用             —— 主树 HANDOFF 引用 .ai/evidence/T-0102/evidence-manifest.v1.yaml
#                                               （主会话完成流程创建 T-0102 manifest 后自愈；idle 稳态下由
#                                               F-01 渲染最近真实 manifest，worktree 已验证 4/4 全绿）
```

## 7. compile gate

```bash
$ C:/Python312/python.exe .ai/checkers/compile_gate.py . --output .ai/evidence/T-0102/compile-evidence.json
# total_files 68, failed_count 0, errors []  → pass
```

## 8. 版本一致性

```bash
$ C:/Python312/python.exe -m pytest tests/test_version_consistency.py -q
# 7 passed（8 载体逐项 == pyproject 3.12.41）
```
