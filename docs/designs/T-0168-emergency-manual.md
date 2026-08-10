# T-0168 附录三：自救与逃生手册（人触发后门）

> 日期：2026-08-10 | 回答：优化加强制层后是否会自我锁死 + 如何自救
> 原则：**逃生开关只能由人触发**；治理可以锁住 AI，但永远锁不住人。

---

## 1. 会不会自我锁死？（诚实分析）

| 锁死场景 | 发生条件 | 现有防护 | 逃生开关作用 |
|---------|---------|---------|-------------|
| pending gate 卡写 | 状态损坏或误登记导致永远 pending | gate 审批（人）+ 防死锁豁免 | ✅ 放行写操作 |
| 质量门无限返工 | 验证方案写错/环境问题，verification 永远失败 | 3 轮上限 → escalation 升级人 | ✅ 跳过自动 FAIL |
| 状态文件损坏 | 半写/外部篡改导致 tasks/gates/state 不一致 | 事务写 + 备份 + verify_evidence_check | ✅ 放行 + 重建目录 |
| 扩展加载失败（Pi） | 扩展文件损坏/被删 | 无（静默失效——不锁死但治理消失） | 无关（治理已失效） |
| 平台强制层生效后（ZCode） | hooks 修复后 + 状态异常组合 | validate_state --repair/--auto-sync | ✅ 全放行 |

**结论**：现有防死锁设计（治理文件豁免、事务写、备份、escalation）已覆盖大部分；
新增逃生开关覆盖"人必须能突破一切治理"的最终保障。

## 2. 逃生开关（人触发，两平台）

### Pi agent（现在生效）
```
方式 A（最可靠）：启动 pi 前设置环境变量
    set MINI_LOOP_EMERGENCY=1    （Windows）
    或 export MINI_LOOP_EMERGENCY=1

方式 B（运行中）：创建逃生文件
    echo bypass > %USERPROFILE%\.pi\agent\EMERGENCY_BYPASS
```
效果：tool_call 拦截全放行（写操作不再被 pending gate/scope 拦）；
评审跳过"无验证方案即 FAIL"的质量门；每次放行写 `[emergency]` 事件留痕；
before_agent_start 注入"逃生模式已激活"提示。
恢复：删除 EMERGENCY_BYPASS 文件 / 取消环境变量后重启会话。

### ZCode（已预置，hooks 生效后即用；validate_state 现在生效）
```
方式 A：LOOP_ENGINE_EMERGENCY=1 启动
方式 B：创建逃生文件  ~/.loop-engine-emergency
```
效果：validate_state 的 pending gate 从 BLOCKER 降级为警告（现在生效）；
gate_guard / loop_enforcement 全放行（hooks 修复后生效）。
恢复：删除文件 / 取消环境变量。

## 3. 触发语义（为什么"仅人可触发"成立）

| 通道 | AI 能否触发 | 说明 |
|------|------------|------|
| 环境变量 | **不能** | 宿主进程环境由人启动时设置，AI 无法修改宿主 env（子进程 env 不影响宿主） |
| 逃生文件 | 能（技术上讲） | AI 有 write 工具可创建任意文件——但每次触发都写 `[emergency]` 事件留痕，滥用会被审计发现；且文件在治理范围外（~ 下），正常治理不拦截人写它 |

**诚实说明**：文件通道严格说 AI 也能创建；真正的"仅人"通道是环境变量。
文件通道的价值 = 运行中无需重启即可逃生 + 留痕可审计（AI 滥用 = 留证据）。

## 4. 锁死后的自救步骤（人操作）

```
1. 识别：会话被拦截/卡住，提示 pending gate / 验证失败循环
2. 逃生：设置环境变量（重启会话）或创建逃生文件（运行中立即生效）
3. 诊断：Pi 侧跑 scripts/verify_evidence_check.ts <项目> 定位数据问题；
          ZCode 侧跑 validate_state.py --auto-sync 修复漂移
4. 修复：批准/拒绝 pending gate；修正 verification 命令；或重建
          Pi: 删除 ~/.pi/agent/loop/<project>/（有 .bak 备份可恢复）
          ZCode: validate_state --repair 或按 KNOWN_ISSUES 指引
5. 恢复：删除逃生文件/取消环境变量 → 治理重新生效
6. 复盘：逃生事件在 events.jsonl / guard-events 留痕，可审计
```

## 5. 边界

- 逃生开关**只放行**，不修复——修复仍需人/工具按第 4 步做
- 逃生模式下的操作不留"治理证据"（写操作未过 gate）——恢复后建议补记
- 逃生开关是最后手段，常态应优先用升级协议（评审 3 轮 escalation）
