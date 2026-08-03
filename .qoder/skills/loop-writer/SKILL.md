# Loop Writer - Qoder Loop 工程写作 Skill

## Description

Loop 工程的写作角色 Skill。作为一次性 writer subagent，基于任务卡生成候选文档。

## When to Use

- 主线程调度 writer subagent 时
- 用户要求直接以 writer 角色生成候选文档

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## Inputs

- 任务卡（包含 task_id, run_id, objective, must_read, allowed_write, required_output）
- 角色 brief: `roles/writer-brief.md`
- must_read 中列出的上下文文件

## Execution

1. 读取 `roles/writer-brief.md` 了解角色约束
2. 读取任务卡中的 `must_read` 文件
3. 基于任务卡的 `objective` 生成候选文档
4. 将输出写入 `allowed_write` 指定的路径
5. 生成 write manifest（YAML 格式）记录产物清单

## Output Format

候选文档 + write manifest：

```yaml
write_manifest:
  task_id: <task_id>
  run_id: <run_id>
  role: writer
  outputs:
    - path: <output_path>
      description: <description>
  status: COMPLETE | BLOCKED
  blocked_reason: <if BLOCKED>
```

## Constraints

- 只写任务卡指定的候选文档
- 不把候选文档说成已批准
- 不修改 stable/ 或 registry/
- 不引入未授权工具
- 不假设测试/review/CI 可以替代用户批准
