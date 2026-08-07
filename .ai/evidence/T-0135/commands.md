# T-0135 命令记录

- 2026-08-07 登记与批准：用户指示"可以，开始处理"（G-T-0135-REQUIREMENTS approved）
- 2026-08-07 实现：
  - loop_engine/cli_entries.py：6 入口薄封装（validate/check/heartbeat/delegation/
    conclusion/mutation）+ __main__ 分发（入口名剥离）；release/mutation 不注入 root
  - pyproject.toml：[project.scripts] 声明 6 入口（文档化可发现性）
  - scripts/release.py：step_guard_health 输出 [report] missing/drift/recompute 计数
    （可见性；verdict 语义零变更）
  - .gitignore：guard-events.jsonl + 轮转归档排除；git rm --cached 停止跟踪（历史保留）
  - tests/test_cli_entries.py（12 用例：声明/入口/6 入口精确 rc 冒烟/未知入口拒绝/
    report 可见性/gitignore 生效）
- 2026-08-07 审查 REPAIR_REQUIRED → P1×2 修复（check/mutation root 注入 + 直调分发令牌
  剥离 + 假阳性断言修正）→ 复核；P2-2（T-0134 evidence-manifest 缺失）一并修复
- 2026-08-07 全量回归 4227 passed（4 项为套件重写 security 证据的 pre-existing 漂移，
  --auto-sync 收敛后通过）
- 2026-08-07 收尾：gate 记录误入 delegations 列表已移正（gates 列表第 88 位）
