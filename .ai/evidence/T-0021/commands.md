# T-0021 commands.md

## 2026-07-21 决策记录

- 用户明确消息：`批准 G-INSTALL-LOOP-GOVERNANCE-RUNTIME-V1`
- 动作：登记任务 T-0021、在 gates.yaml 注册并记录 gate 决策、更新 state.yaml
- 验证：`C:\Python312\python.exe .zcode\tools\validate_state.py`

## 2026-07-21 执行记录（用户精确执行请求后）

用户消息：`执行已批准的 G-INSTALL-LOOP-GOVERNANCE-RUNTIME-V1`

1. `cp .zcode/config.json .zcode/config.json.bak-governance-v1` — 备份旧配置
2. `rm -rf .zcode/skills/loop-governance && cp -r candidates/.../payload/.zcode/skills .zcode/` — 安装技能包（18 文件）
3. `cp candidates/.../payload/.zcode/config.json .zcode/config.json` — 替换 hooks 配置
4. 清理候选复制带入的 `__pycache__`（scripts/ 与 tests/ 各一处）
5. 验证：`python -m unittest discover -s .zcode/skills/loop-governance/tests -v` → **15 tests OK（2.1s）**
6. 验证：`python .zcode/tools/validate_state.py` → **[ok] state is usable**
7. 验证：config.json JSON 合法，hooks.enabled=true，events=[SessionStart, PreToolUse]
8. 登记：gates.yaml execution_status=completed；task_graph T-0021=completed；state.yaml current_task_id=null；重写 HANDOFF.md

旧 hook 文件 `.zcode/tools/hooks/block_on_pending_gate.py|.bat` 按 gate 范围保留未动。
live-fire 验证（第 2-4 步）需用户在新会话进行，已写入 HANDOFF。
