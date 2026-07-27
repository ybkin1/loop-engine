# Codex Loop Candidate

这是 `loop-engine-lab` 内的 Codex-only 本地候选实现。它把项目意图拆成角色合同、阶段、任务图、素材选择、bounded work packet、确定性检查和 Human Review Packet；它不会安装或修改 Codex 全局 skill、MCP、plugin、hook，也不会调用真实模型。

## 运行方式

在项目根目录执行：

```text
python -m codex_loop roles-validate
python -m codex_loop init --root <project-root> --project-id <id> --goal "<goal>"
python -m codex_loop select-materials --catalog materials/catalog.yaml --output <project-root>/.loop/materials-selection.json architecture quality
python -m codex_loop demo-t0036 --root <project-root>
python -m codex_loop verify --root <project-root>
```

`prepare-run` 只生成给 Codex 会话消费的 bounded invocation spec。调用者必须显式声明可用工具和写入目标：

```text
python -m codex_loop prepare-run --root <project-root> --role system-architect --task-id T-1 --phase-id P3 --purpose "design boundaries" --tool workspace_read --tool graph_check --tool schema_check --tool structured_write --write-target .loop/packets/architecture/design.json
```

输出位于 `<project-root>/.loop/runs/`。`READY_TO_INVOKE` 只表示准入检查通过；`capability_probe.status=NOT_RUN` 表示本候选没有把提示词存在、工具声明或模型响应冒充真实能力认证。

## 阶段与 Gate

初始化会固化 P0-P12 阶段快照和按角色串联的默认任务图。P1、P2、P3、P11 是用户必须决定的产品边界；其余质量、安全、成本、证据和发布条件由 Loop 内部检查，硬阻断或遇到重大取舍时再生成用户决策包。

每个角色只接收角色合同、项目 overlay、当前 work packet 和选定证据。角色输出不能直接改变阶段状态；状态、证据、finding 和用户决定由控制层持久化。
