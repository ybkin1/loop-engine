# Coding Standards

## Style

- Match the existing codebase.
- Keep changes scoped to the active task.
- Do not hardcode secrets, passwords, tokens, or API keys.
- 注释密度与既有代码一致；中文注释用中文，英文注释用英文，不混用。

## Verification

- Record commands and results in `.ai/evidence/<task-id>/commands.md`.
- 测试断言必须验证真实语义（行为/返回值/副作用），禁止 `assertTrue(True)`
  类假通过占位（T-0177 P3-4 起强制）。
- 修复缺陷必须附带回归测试（先失败后通过），且测试模拟真实调用路径
  （hook 脚本测试应模拟真实 stdin JSON + 逃生分支 + fail-closed 路径，
  不测"模拟世界里的模拟行为"，T-0177 D-00 根因一）。

## Hook 脚本（hooks/scripts/）

- 统一从 `hook_common` 导入 `EXIT_PASS` / `EXIT_BLOCK`，禁止各自重复定义
  （T-0177 P3-7 批 C wiring 完成）。
- 逃生开关统一走 `hook_common.emergency_active()`：内容标记 + 24h TTL +
  审计留痕 + fail-open（逃生不可被阻断）。
- 任何新检查必须定义 fail-closed 语义（状态不可读 → 阻断写入），并在异常
  路径测试中覆盖。

## 收口（全局一致性）

- 任务收口时除本地证据外，必须核对全局真相：PROGRESS.md 当前状态、
  角色数量/契约、docs 编号、CONTRACTS 声明（T-0177 D-00 根因五/六）。
- KNOWN_ISSUES 中未解决项必须在收口措辞中同步引用，不得在已知失效时
  宣称"全绿"（诚实性债务红线，T-0177 D-00 根因六）。
