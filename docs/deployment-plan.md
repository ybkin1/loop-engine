# 部署方案 — Loop Engine v1.0.0

## 部署方式

Loop Engine 是 ZCode 插件，部署即安装。

### 方式一：ZCode 界面安装
ZCode → Settings → Plugin Management → Discover → + → 选择本项目目录

### 方式二：命令行联结
```bash
mklink /J %USERPROFILE%\.zcode\plugin-workspace\loop-engine <项目路径>
```

### 方式三：Python 脚本安装
```bash
python scripts/install.py --project-root <目标项目>
```

## 环境要求

- Python 3.10+
- PyYAML >= 6.0
- ZCode（支持 hook 协议版本）
- Windows 10+ / macOS / Linux

## 部署验证

1. 插件在 ZCode Plugin Management 中可见
2. `loop-governance` 技能在会话中可被调用
3. 三个斜杠命令（`/loop-validate`, `/loop-verify-chain`, `/loop-cost`）可用
4. SessionStart hook 注入治理摘要

## 回滚方案

见 `docs/rollback-plan.md`（卸载即回滚：`python scripts/uninstall.py --project-root <目标>`）
