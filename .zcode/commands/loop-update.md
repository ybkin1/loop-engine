---
description: 更新 Loop 工程到最新版本
allowed-tools: Read, Bash, Write, Edit
---

# Loop 工程更新

将当前项目的 Loop 工程更新到最新版本。

## 步骤

1. 定位 Loop 工程源仓库：
   ```bash
   cd $LOOP_ENGINE_ROOT && git pull
   ```

2. 同步 Agent 角色：
   ```bash
   python $LOOP_ENGINE_ROOT/tools/loop_onboard.py "$PROJECT_ROOT" --update
   ```

3. 同步 Hook 脚本到插件缓存：
   ```bash
   python $LOOP_ENGINE_ROOT/.zcode/tools/sync_plugin_cache.py "$LOOP_ENGINE_ROOT"
   ```

4. 验证更新：
   - Hook 脚本已同步
   - Agent 角色已更新
   - 运行 validate_state.py 确认
