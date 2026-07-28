# G-T-0055-SOURCE-TRUTH-SYNC-REPAIR — 执行证据

## Gate 信息

| 字段 | 值 |
|------|-----|
| Gate ID | G-T-0055-SOURCE-TRUTH-SYNC-REPAIR |
| 父 Gate | G-T-0055-AUTONOMOUS-FULL-EXECUTION |
| 类型 | scope-expansion |
| 状态 | approved / executed |
| 批准时间 | 2026-07-28T14:00:00+08:00 |
| 批准者 | user (explicit) |

## 问题背景

ZCode plugin cache 中存在项目源文件（`tools/server.py`、`loop_core/role_capability.py`）的独立副本。
旧同步逻辑 `sync_plugin_cache.py` 依赖 mtime 比较，导致：
1. 源文件写入后可能被旧缓存覆盖（mtime 竞争）
2. 破坏真实的 Git diff 和测试证据
3. plugin cache 版本目录选择不正确

## 修复内容

### 1. `.zcode/tools/sync_plugin_cache.py`

| 变更 | 说明 |
|------|------|
| 新增 `RUNTIME_FILES` 常量 | 明确定义需要同步的运行时文件映射 |
| 新增 `_sha256()` 函数 | SHA-256 内容哈希替代 mtime 比较 |
| 新增 `_copy_verified()` 函数 | 写后哈希校验，失败时抛出 OSError |
| 修复 `find_plugin_cache()` | 正确选择带 `.zcode-plugin` 标记的版本目录，按 `st_mtime_ns` 取最新 |
| 重写 `sync_hook_scripts()` | hook 脚本同步改用 SHA-256 比较 |
| 新增 `sync_runtime_files()` | 运行时文件独立同步函数，使用哈希比较和写后校验 |
| 修复返回值 | `sync_hook_scripts`、`sync_config` 现在返回实际同步数量（之前硬编码返回 0） |

### 2. `tests/test_plugin_cache_sync.py` (新增)

9 个测试覆盖：

| 测试 | 覆盖场景 |
|------|---------|
| `test_runtime_files_sync_by_hash_even_when_cache_mtime_is_newer` | stale-mtime + 幂等性 |
| `test_runtime_sync_post_write_hash_verification_detects_mismatch` | 写后哈希校验 |
| `test_runtime_sync_idempotent_no_redundant_writes` | 幂等同步 |
| `test_hook_scripts_sync_by_hash_skips_identical_cache` | hook 脚本哈希跳过 |
| `test_hook_scripts_sync_by_hash_detects_content_change` | hook 脚本内容变更检测 |
| `test_find_plugin_cache_returns_none_when_no_cache` | 缓存不存在 |
| `test_find_plugin_cache_selects_version_with_dot_zcode_plugin_marker` | 版本目录选择 |
| `test_copy_verified_preserves_file_content` | 正常复制完整性 |
| `test_sync_skips_missing_source_file` | 缺失源文件跳过 |

### 3. 其他文件（属于 G-T-0055-AUTONOMOUS-FULL-EXECUTION 范围）

| 文件 | 变更 |
|------|------|
| `loop_core/role_capability.py` | 新增 `ROLE_IDS` 元组(12角色)、认证过期/重验证字段 |
| `tests/test_role_capability.py` | 适配 12 角色变更 |
| `tools/server.py` | 修复 `arguments.get` → `args.get` 变量名 |

## 验证结果

### 聚焦测试

```
tests/test_plugin_cache_sync.py .........  9 passed
tests/test_role_capability.py ............ 28 passed
Total: 37 passed in 0.57s
```

### 全量回归测试

```
2459 passed, 60 skipped, 16 xfailed, 29 warnings in 94.71s
```

### 编译检查

```
OK: sync_plugin_cache.py
OK: tools/server.py
OK: loop_core/role_capability.py
```

### 幂等性验证

```
首次运行: [sync] 1 runtime files synced and verified. (exit 2)
二次运行: (no output, exit 0) — 幂等确认
```

### validate_state

```
[ok] state is usable
```

## Git Diff 统计

```
8 files changed, 427 insertions(+), 37 deletions(-)
```

## 关键设计决策

1. **项目工作树为 source-of-truth**：所有同步从项目目录向 plugin cache 单向进行
2. **SHA-256 替代 mtime**：消除 mtime 竞争条件，确保内容完整性
3. **写后哈希校验**：`_copy_verified` 在每次写入后立即校验，哈希不匹配时抛异常
4. **版本目录选择**：优先选择带 `.zcode-plugin` 标记的版本目录，按 `st_mtime_ns` 取最新

## 约束遵守

- [x] 未修改 AGENTS.md
- [x] 未启用外部 MCP/Agent/Skill
- [x] 未进入真实业务项目
- [x] 未涉及 deploy/rollback/database/permission/secret/payment/production_data/migration
- [x] 测试通过视为 evidence，不替代用户验收
