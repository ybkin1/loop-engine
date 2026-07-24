# loop-demo-todo — 接口契约

## models.py

### TodoItem

```python
@dataclass
class TodoItem:
    id: int
    content: str
    done: bool = False
```

### 导出函数

| 函数 | 输入 | 输出 | 错误 | 幂等性 |
|------|------|------|------|--------|
| `create_todo(content: str, existing_ids: list[int]) -> TodoItem` | content: 非空字符串; existing_ids: 已有ID列表 | TodoItem(新ID=max(existing_ids)+1, content, done=False) | ValueError: content为空 | 否（每次创建新事项） |
| `mark_done(item: TodoItem) -> TodoItem` | item: 现有TodoItem | TodoItem(id, content, done=True) | ValueError: 已标记完成 | 是（重复标记不改变结果） |

## storage.py

### 导出函数

| 函数 | 输入 | 输出 | 错误 | 幂等性 |
|------|------|------|------|--------|
| `load_todos(filepath: str) -> list[TodoItem]` | filepath: JSON文件路径 | list[TodoItem] | FileNotFoundError→返回空列表; JSONDecodeError→返回空列表 | 是 |
| `save_todos(filepath: str, todos: list[TodoItem]) -> None` | filepath, todos | None | OSError→传播 | 是（覆盖写入） |

## cli.py

### 导出函数

| 函数 | 输入 | 输出 | 错误 | 幂等性 |
|------|------|------|------|--------|
| `main() -> int` | 无（从sys.argv读取） | exit code: 0=成功, 1=参数错误, 2=运行时错误 | — | 否 |
| `handle_add(args) -> str` | args: argparse.Namespace | 成功/错误消息字符串 | — | 否（创建新事项） |
| `handle_list(args) -> str` | args: argparse.Namespace | 格式化列表字符串 | — | 是 |
| `handle_done(args) -> str` | args: argparse.Namespace | 成功/错误消息字符串 | — | 条件（重复标记返回提示） |
| `handle_remove(args) -> str` | args: argparse.Namespace | 成功/错误消息字符串 | — | 否（删除不可逆） |

## 依赖清单

```
cli.py:
  允许依赖: src.models (TodoItem), src.storage (load_todos, save_todos), argparse, sys
  禁止依赖: 无

storage.py:
  允许依赖: src.models (TodoItem), json, pathlib
  禁止依赖: src.cli

models.py:
  允许依赖: dataclasses
  禁止依赖: src.cli, src.storage
```
