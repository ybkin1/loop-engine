# 回滚方案 — Loop Engine v1.0.0

## 触发条件

- 插件注册后 hook 导致 ZCode 会话异常
- 治理运行时安装后项目无法正常工作
- 用户决定不再使用 Loop 工程

## 回滚命令

```bash
python scripts/uninstall.py --project-root <目标项目>
```

## 回滚行为

1. `.ai/` 目录备份至 `.ai.backup-<timestamp>/`（保留用户数据）
2. `.zcode/skills/loop-governance/` 移除
3. 项目其他文件不受影响

## 数据回滚

- `.ai/tasks/` 和 `.ai/evidence/` 通过备份保留，可手动恢复
- 如需完全恢复：将 `.ai.backup-<timestamp>/` 重命名为 `.ai/`

## 时间估计

- 执行时间：<1 秒
- 手动恢复数据时间：<1 分钟

## 验证方法

- 确认 `.zcode/skills/loop-governance/` 已删除
- 确认 `.ai.backup-<timestamp>/` 存在
- 重启 ZCode 会话，hook 不再生效

## 负责人

用户本人（Loop Engine 是本地插件，无远程部署，用户完全控制安装和卸载）
