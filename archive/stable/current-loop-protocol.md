# Current Loop Protocol

状态：candidate

本文件当前只是 loop 工程协议的候选入口，不代表已安装或已批准协议。

## Loop 定义

默认循环：

```text
discover -> plan -> execute/verify -> iterate
```

在文档生成和协议优化场景中，默认执行链路为：

```text
writer -> reviewer-plan -> reviewer -> repair -> reviewer
```

## 主线程职责

主线程负责：

- 创建 run。
- 生成任务卡。
- 选择角色背景提示词。
- 指定输入文档和输出路径。
- 检查 subagent 输出是否符合任务卡。
- 根据评审结论决定通过、返工、阻塞或升级给用户。

主线程禁止：

- 把候选文档说成正式协议。
- 把评审通过说成用户批准。
- 让 subagent 自由选择输出目录。
- 未经用户 gate 安装协议、修改真实业务项目或触发生产动作。

## Subagent 规则

每个 subagent 都是一次性执行单元，只能执行任务卡里的单个任务。

subagent 必须：

- 读取 `must_read`。
- 只写入 `allowed_write`。
- 输出任务卡要求的文件。
- 遇到权限、输入缺失、目标冲突时返回 `BLOCKED`。

## Promotion 规则

`runs/` 中的候选文档只有满足以下条件才可进入 `stable/`：

- reviewer 返回 `PASS`。
- 没有阻塞项。
- 输出路径正确。
- registry 可追踪来源 run。
- 不涉及权限扩大。
- 涉及用户 gate 时已获得明确批准。

