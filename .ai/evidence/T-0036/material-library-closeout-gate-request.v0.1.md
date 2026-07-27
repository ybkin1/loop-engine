# T-0036 版本冻结后行政收口 Gate 请求 v0.1

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

Status: `pending / user_decision_required`

Gate type: `T-0036 administrative closeout only`

## 收口决策

是否批准在后续收到精确执行请求后，将 T-0036 从 `active` 行政标记为 `completed`。

Gate 注册不等于批准；用户批准也不等于执行。当前阶段只注册 Gate 并等待用户批准。

## 前置事实

- 候选基线已被用户接受，版本身份为 `research-baseline-v0.1`。
- 最终版本冻结 manifest：`10202` bytes / SHA-256 `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`。
- 新旧 manifest 的 `65/65` subject triples 完全一致；磁盘验证 `65/65`，零漂移。
- T-0036 仍为 `active`；isolated candidate-path verification gap 为 `open / unwaived`。
- T-0037 review 尚未创建或执行。

## 收口目标与边界

后续获批并收到精确执行请求后，只能将 T-0036 在任务文件与 task graph 中行政标记为 `completed`，同步 baseline acceptance 与 version freeze 证据指针，并生成收口证据。

该 completed 只表示行政/候选基线阶段完成，不是产品 PASS，不是用户项目验收，不是 Runtime、Agent、Host、安装、激活或部署完成。candidate-path gap 仍开放，T-0037 review 仍需后续独立 Gate。

本 Gate 不修改 `materials/**`、65 个冻结对象、旧证据、candidate/global Project Governor、tests、`codex_loop` 或 Runtime；不创建、不修改、不执行 T-0037 review，不进入 Host Integration、迁移、权限、密钥、生产数据或真实项目。

## 用户决定

- 批准：`批准 G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`
- 拒绝：`拒绝 G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`，保持 T-0036 `active`。

批准后仍需另行发送：`执行 G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`。在此之前不得执行收口。
