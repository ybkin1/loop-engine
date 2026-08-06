# D-01 ZCode 原生会话数据调研（T-0120）

> 只读调研（candidate-only）：ZCode 原生会话的持久化位置/格式/元数据，
> 及其与 Qoder 外部会话（T-0112 撤销对象）的本质差异。

## 1. 持久化位置与格式

| 项 | 值 |
|----|-----|
| 根目录 | `C:\Users\Administrator\.zcode\cli\exec\` |
| 会话目录 | `sess_<uuid>\`（UUID 目录名即会话 ID） |
| 会话数量 | 646（审查时实测 647——活数据漂移；含 58 个 `sess_subagent_agent_<uuid>` 子代理会话目录；大量为空目录——会话创建但无工具调用） |
| 内容 | `call_<N>_<call_id>-stdout.log` / `-stderr.log`（bash 工具执行日志；子代理目录为 `tool_*-stdout/stderr.log` 变体，同属工具日志） |
| 规模 | 总 5.1 GB（日志含大量工具输出噪音） |
| 元数据 | 无结构化元数据文件；会话 ID = 目录名；目录 mtime 为粗略创建/活动时间；无 JSONL/转录 |

示例（当前会话）：
```
.zcode/cli/exec/sess_57932cf0-.../
  call_00_V9q0vYExqNOKosZeduc76261-stdout.log
  call_00_ET_EUs4vjX4eYVT87a2kjm56671-stdout.log
```

## 2. 数据性质

- **工具执行日志**：stdout/stderr 原始输出（pytest、git、grep 等命令结果），
  **不含 LLM 会话转录**（无 reasoning、无 reviewer verdict、无 findings）。
- **无审查证据形态**：不存在 reviewer_session_id/verdict/findings 等
  subagent_evidence_verifier 期望的结构化字段。
- **本地可访问**：同一 harness（ZCode）生成、文件系统内、与当前工作区同机。

## 3. 其他位置（非会话转录）

| 位置 | 内容 | 相关性 |
|------|------|--------|
| `.zcode/v2/` | bot-config/bot-state/bots-model-cache（运行时配置与状态） | 无（非会话数据） |
| `.zcode/export-log-stage/` | 暂存目录 | 无 |
| `.zcode/commands/`、`.zcode/skills/`、`.zcode/workspace/` | 命令/skill/工作区配置 | 无 |

## 4. 与 Qoder 会话的本质差异（T-0112 撤销对象）

| 维度 | Qoder（已撤销） | ZCode 原生会话 |
|------|----------------|----------------|
| 宿主 | 外部会话主机 | 本 harness（ZCode） |
| 位置 | 外部（工作区 .qoder/ 转录） | 本地 `~/.zcode/cli/exec/` |
| 可控性 | 外部生成、不可验证 | 本地文件系统直接可核验 |
| 内容形态 | 外部 transcripts | bash 工具日志（stdout/stderr） |
| 审查内容（verdict/findings） | 无（也是 T-0112 撤销主因之一） | 无 |

**结论**：ZCode 原生会话是"本地可核验的会话存在性/活动数据"（会话 ID 目录存在、
工具调用日志可查），但**不是审查内容证据**（无结构化 verdict/findings）。

## 5. 可信边界

- 会话目录存在性：可核验（`os.path.isdir`）——比 Qoder 外部 transcripts 强。
- 日志内容：进程可写（非防篡改介质）——不构成独立审查内容证据。
- 时间戳：目录 mtime 可被触摸（无防伪）——仅作粗略活动指示。
- 证据链防篡改：仍由 project_continuity（source_manifest 哈希）与
  evidence-manifest（不可变清单）承担，与日志本身无关。
