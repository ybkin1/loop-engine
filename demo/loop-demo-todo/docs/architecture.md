# loop-demo-todo — 系统架构

## 架构概览

单模块 CLI 工具，采用命令-处理器模式。

```
CLI入口 (cli.py)
  ├── 命令解析器 (argparse)
  ├── 任务存储层 (storage.py)
  └── 任务模型 (models.py)
```

## 模块清单

| 模块 | 路径 | 职责 |
|------|------|------|
| CLI入口 | `src/cli.py` | 参数解析、命令路由、输出格式化 |
| 任务存储 | `src/storage.py` | JSON 文件读写、数据持久化 |
| 任务模型 | `src/models.py` | TodoItem 数据结构定义 |

## 依赖方向

```
cli.py → storage.py → models.py
cli.py → models.py（只读引用）
```

禁止方向：storage.py 不依赖 cli.py

## 数据流

```
用户输入 → cli.py(解析) → storage.py(读写) → ~/.loop-demo-todo/data.json
                                    ↑
                            models.py(TodoItem)
```

## 技术选型

| 选型 | 理由 |
|------|------|
| Python 3.10+ | 目标用户（开发者）环境、标准库丰富 |
| argparse | 标准库，零依赖 |
| JSON 文件 | 简单持久化，人类可读 |
| pytest | 标准测试框架 |

## 安全边界

- 用户数据存储在 `~/.loop-demo-todo/` 下，不访问其他路径
- JSON 解析使用标准库，无注入风险
- 无网络访问、无外部依赖（除 pytest 开发依赖）

## 部署结构

```
pip install -e .  # 或直接 python -m src.cli
```
