# ZCode Hook 协议摘要（loop-governance 实施依据）

来源：`zcode-guide:diagnosing-hooks` / `zcode-configuration-guide`（2026-07 核对）。

## 配置位置与启用

- 工作区配置：`<repo>/.zcode/config.json` 的顶层 `hooks` 键。
- **配置文件 hook 默认不运行**，必须显式 `"hooks": { "enabled": true, ... }`。
- 正确结构（注意是 `events`，不是 `scripts`）：

```json
{
  "hooks": {
    "enabled": true,
    "events": {
      "PreToolUse": [
        {
          "matcher": "Write|Edit",
          "hooks": [
            {
              "type": "process",
              "command": "C:\\Python312\\python.exe",
              "args": ["${ZCODE_PROJECT_DIR}/.zcode/skills/loop-governance/scripts/gate_guard.py"],
              "timeoutMs": 5000
            }
          ]
        }
      ]
    }
  }
}
```

> 历史教训：本项目旧版 config.json 写成了 `hooks.scripts[]`（含 event/script 字段），
> 不是有效 schema，**hook 从未真正运行过**——纸面执行的活标本。

## 事件与 matcher

- 事件恰好七个：`SessionStart`、`UserPromptSubmit`、`PreToolUse`、
  `PermissionRequest`、`PostToolUse`、`PostToolUseFailure`、`Stop`。
- matcher 是**大小写敏感的正则**，匹配值因事件而异：
  - `SessionStart` → `startup|resume|clear|compact` 之一
  - 工具类事件 → 工具名（`Bash`、`Write`、`Edit`、`Agent`……）；
    别名：`Task`↔`Agent`，`ApplyPatch`→`Write`/`Edit`
- 省略 matcher = 匹配全部；非法正则 = 静默永不匹配。

## hook 条目字段

- `type: "process"`：`command`（可执行文件）+ `args[]`（无 shell，最可移植）+
  `timeoutMs`（毫秒）。**只接受这几个字段**（另加 statusMessage）。
- `type: "command"`：`command`（shell 字符串）+ 可选 `shell`、`timeout`（**秒**）。
- 模板变量：`${ZCODE_PROJECT_DIR}` / `${CLAUDE_PROJECT_DIR}`、
  `${CLAUDE_SESSION_ID}`，在 command 和每个 args 元素中展开，也注入为环境变量。

## 退出码与输出

| 退出码 | 语义 |
|---|---|
| 0 | 通过 |
| 2 | 阻断（PreToolUse/PermissionRequest 中为 deny） |
| 其他非 0 | hook 错误（不是阻断） |

- stdout 可输出严格 schema 的 JSON（**多一个键就校验失败**），或空输出靠退出码。
- `additionalContext`（SessionStart 等）：注入会话上下文。
- PreToolUse 的 permissionDecision：`allow` / `ask` / `deny`。

本项目使用的 JSON 形态：

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
  "permissionDecisionReason": "..."}}
```

## 设计决策记录

1. **三个 hook 都用 `type: "process"` + args 数组**：无 shell 拼接，Windows 下可靠。
2. **gate_guard 用 exit 2 而不是 JSON deny**：退出码语义最稳定，不受 JSON schema
   严格校验影响。
3. **path_guard 默认 ask 而非 deny**：用户（非技术）当场点确认即可，
   符合"用户即信任锚"；deny 模式保留给高敏期。
4. **所有脚本 `sys.dont_write_bytecode = True`**：防止 hook 高频运行产生
   `__pycache__` 污染工作区（loop-engine-lab T-0032 事故教训）。
5. **hook 内部异常一律 exit 0（path_guard/session_brief）**：hook 故障不应
   瘫痪会话；gate_guard 的状态读取失败例外，默认 fail-closed。

## 排障速查

- hook 没运行 → 先查 `hooks.enabled: true`；再查事件名与 matcher 大小写。
- 配置改了没效果 → 检查 `events` 结构层级（常见错误：写成 scripts）。
- 超时被杀 → `timeout` 是秒、`timeoutMs` 是毫秒，别搞混。
- JSON 被丢弃 → schema 严格，多余键即失败；改用退出码。
