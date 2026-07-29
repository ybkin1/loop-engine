# T-0055 基线审计命令记录

| 命令/动作 | 结果 |
|---|---|
| `rg` inventory agents roles | 11 个角色均存在 SKILL.md + CONTRACT.yaml |
| inspect `tools/loop_onboard.py` | 委托 RuntimeController.onboard_project，脚本自身会创建缺失 AGENTS.md 并输出 NO_ACTIVE_TASK；覆盖风险待专项复现 |
| inspect `version-manifest.yaml` | 发现 3.0.0 与当前 3.11.2 文件漂移 |
| inspect continuity manifest | 当前 manifest 不包含 HANDOFF/state/task_graph/gates 路径；哈希环结论保留 NOT_VERIFIED |
| inspect quality/test/review entrypoints | 发现单入口语义、0/0、skip/unavailable、回归比较范围等缺口 |
| `C:\Python312\python.exe .zcode/tools/validate_state.py <root>` | 当前仍失败：compile evidence 缺失；T-0055 HANDOFF/continuity 尚未完成基线切换投影 |

本阶段未修改运行时代码、角色合同、质量脚本或认证状态。
