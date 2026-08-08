# T-0160 独立审查记录

审查范围：Pi agent Loop 工程升级（pi-agent-extensions mini-loop v2 整合）。

## 审查方法

- 独立审查，不依赖执行线程自述：检查源码（govern.ts / index.ts / events.ts /
  state.ts / delegate.ts 等）、测试输出、迁移实测产物
- 验证路径：pi-agent-extensions 仓库（ad56377）+ 运行时
  `~/.pi/agent/loop/C_Users_Administrator_pi-test-lab/` 迁移产物

## 发现

| # | 严重度 | 内容 |
|---|--------|------|
| 1 | P2 | `index.ts` task-scope/task-focus 的事件类型复用 `task.created`（detail 区分），语义略混——非阻断，后续可加 `task.scope_updated` 事件类型 |
| 2 | P2 | delegate.ts 委派完成后不刷新 handoff.md（由后续 review_task 兜底刷新）——时效性瑕疵，非阻断 |
| 3 | P3 | 反幻觉闸门依赖 reviewer 子进程 tool_call 计数；极端情况下评审经 git diff 纯文本验证但无 read/bash 调用会被误拦——保守方向（宁可误拦不可放过） |

## 结论

- 治理机制与 ZCode 语义对齐：gate 生命周期（gates.json 单一事实源）、
  validate 校验链（fail-closed）、证据 SHA256 锚定（篡改检测实测生效）、
  事件溯源（stateSha256 + replay-check）、HANDOFF 投影（JSON 块契约）
- 用户雏形（执行委派 P0-A / 配额 P0-C / 产物校验）完整保留并同步回源码仓库
- 测试 17/17（govern.test.ts）+ tsc 无错误；pi-test-lab 迁移实测
  T-001/T-010/T-011 保留 + evidence 锚定一致 + validate [ok]
- hooks/ 零改动、loop_core 零触碰；发现 P2×2 / P3×1，均非阻断

VERDICT: PASS（条件性，P2 留档不阻塞）
