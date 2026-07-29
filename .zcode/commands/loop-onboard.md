---
description: 一键接入 Loop 工程治理（创建 .ai/ + 安装角色 Agent）
allowed-tools: Read, Bash, Write, Edit
---

# Loop 工程一键接入

检查当前项目是否已接入 Loop 工程。如果未接入，执行完整接入流程。

## 步骤

1. 检查项目根是否存在 `.ai/state.yaml`
   - 如果存在 → 已接入，输出当前状态
   - 如果不存在 → 继续

2. 运行接入脚本：
   ```bash
   python $LOOP_ENGINE_ROOT/tools/loop_onboard.py "$PROJECT_ROOT"
   ```

3. 验证接入结果：
   - `.ai/state.yaml` 已创建
   - `agents/developer/SKILL.md` 已安装
   - `agents/independent-reviewer/SKILL.md` 已安装
   - `agents/test-engineer/SKILL.md` 已安装

4. 提示用户：下次打开项目时 Loop 治理自动生效
