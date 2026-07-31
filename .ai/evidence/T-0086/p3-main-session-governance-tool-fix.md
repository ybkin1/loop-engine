# T-0086-P3 修复证据：主会话治理工具调用仍被 SETUP_INCOMPLETE 拦截

## 现象

T-0086-P2 配套修复（`is_governance_tool_command` 治理工具豁免 +
GOVERNANCE_TOOL 早退）后，子代理验证"同命令 EXIT=0"通过，但主会话
真实运行 `C:/Python312/python.exe .zcode/tools/validate_state.py .` 仍
输出：

```
[hook_common] WARNING: [auto-sync] loop_enforcement.py → plugin cache (SHA256 changed)
[__main__] WARNING: BLOCKED: SETUP_INCOMPLETE: runtime projection missing; DISPATCH_REQUIRED for active task T-0086
```

## 根因（两条，均经真实运行证据确认）

1. **命令形态差异（主因）**：主会话真实执行的 Bash 命令不是纯命令，而是
   复合形态（来自主会话 rollout 记录
   `~/.zcode/cli/rollout/model-io-sess_8d5d76d8-*.jsonl` 中的真实
   tool_use）：
   ```
   cd /c/Users/Administrator/ZCodeProject/loop-engine && C:/Python312/python.exe .zcode/tools/validate_state.py . 2>&1 | tail -5
   ```
   P2 的 `is_governance_tool_command` 对任何含 `&&`/`|` 的复合命令一律
   返回 False（安全设计），因此豁免从不生效 → `is_governance_read=False`
   → DISPATCH 门拦截。子代理验证的"纯命令"形态恰好被豁免，与主会话
   实际形态不一致 → 验证通过但主会话仍被拦。

2. **插件缓存一次性竞态**：主会话 hook 从插件缓存加载
   （`ZCODE_PLUGIN_ROOT` = `~/.zcode/cli/plugins/cache/
   zcode-plugins-official/loop-governance/1.0.0`，唯一含 hooks.json +
   .zcode-plugin 的安装根）。`auto_sync_to_plugin_cache` 在本进程启动后
   才把新代码复制进缓存 → 本次调用仍在用旧模块逻辑判定（输出中的
   `[auto-sync]` 警告即同步动作本身）。

3. **链上第二拦截点**：`path_guard.py` 的 T-0086-P1 执行形态检查把
   "解释器二进制在项目外"（`C:/Python312/python.exe`）当作"项目外引用"
   阻断——Windows 上解释器几乎总在项目外，脚本本身却在白名单目录内。

## 修复（hooks/scripts/ 三处）

- `loop_enforcement.py`：`is_governance_tool_command` 改为逐段校验——
  每段必须是：治理工具调用（python 家族解释器 + 白名单目录 .py 脚本 /
  直接执行白名单脚本）/ 项目根内 `cd`（支持 git-bash `/c/...` 形态）/
  无写语义的只读显示段（tail/head/grep/echo/cat 等，解释器执行形态
  不允许借道）。任一段带写能力（rm/写重定向/-m/-c/白名单外脚本/
  项目外 cd）→ 整体不豁免（fail-closed 保持）。新增自愈重执行：
  auto-sync 后检测本进程加载的 hook 文件已过期 → 暂存 hook 输入并
  `os.execv` 重执行一次（新代码判定当前命令，消除一次性竞态）。
- `path_guard.py`：P1 执行形态检查豁免治理工具调用（复用
  `loop_enforcement.is_governance_tool_command` 单一判定源）。
- 插件缓存已用 `.zcode/tools/sync_plugin_cache.py` + hook 自愈同步
  更新到 1.0.0 安装根。

## 验证

- 全量测试：`C:/Python312/python.exe -m pytest tests/ -q` →
  **2856 passed**（P2 时 2844，新增 12 例 P3 回归测试）。
- 7-hook 全链模拟（loop_enforcement → bash_content_guard → gate_guard →
  content_guard → ledger_guard → role_isolation → path_guard）：
  - `cd <root> && C:/Python312/python.exe .zcode/tools/{validate_state,
    repair_continuity, close_session}.py ... 2>&1 | tail -N` → 全链放行
  - 纯命令形态 → 全链放行
  - `&& rm -rf`、`> file` 写重定向、`cd /c/Windows`、`python -m pytest`、
    `python -c`、`sh /tmp/evil.sh` 等 → 仍被拦（写入拦截不放松）
  - Read 插件缓存参考文档（`.../1.0.0/skills/loop-governance/references/
    hook-protocol.md`）→ 放行（T-0086 只读豁免不回归）
- 陈旧缓存自愈：模拟缓存副本为旧代码 → hook 首跑自动同步并重执行 →
  EXIT=0（此前该场景 EXIT=2 BLOCKED）。
