#!/usr/bin/env python3
"""loop-demo-todo — A simple CLI todo manager.

Usage:
    todo add <content>     Add a new todo item
    todo list              List all todo items
    todo done <id>         Mark item as done
    todo remove <id>       Remove an item
"""
import argparse
import sys
from pathlib import Path

from src.models import TodoItem, create_todo, mark_done
from src.storage import load_todos, save_todos

DATA_FILE = str(Path.home() / ".loop-demo-todo" / "data.json")


def handle_add(args) -> str:
    """Handle the 'add' command."""
    todos = load_todos(DATA_FILE)
    existing_ids = [t.id for t in todos]
    try:
        item = create_todo(args.content, existing_ids)
    except ValueError as e:
        return f"错误: {e}"
    todos.append(item)
    save_todos(DATA_FILE, todos)
    return f"已添加 #{item.id}: {item.content}"


def handle_list(args) -> str:
    """Handle the 'list' command."""
    todos = load_todos(DATA_FILE)
    if not todos:
        return "暂无待办事项"
    lines = ["待办事项:"]
    for item in todos:
        status = "✅" if item.done else "⬜"
        lines.append(f"  #{item.id} [{status}] {item.content}")
    return "\n".join(lines)


def handle_done(args) -> str:
    """Handle the 'done' command."""
    todos = load_todos(DATA_FILE)
    for item in todos:
        if item.id == args.id:
            try:
                mark_done(item)
            except ValueError as e:
                return str(e)
            save_todos(DATA_FILE, todos)
            return f"已完成 #{item.id}: {item.content}"
    return f"事项 #{args.id} 不存在"


def handle_remove(args) -> str:
    """Handle the 'remove' command."""
    todos = load_todos(DATA_FILE)
    for i, item in enumerate(todos):
        if item.id == args.id:
            removed = todos.pop(i)
            save_todos(DATA_FILE, todos)
            return f"已删除 #{removed.id}: {removed.content}"
    return f"事项 #{args.id} 不存在"


def main() -> int:
    """CLI entry point. Returns exit code."""
    parser = argparse.ArgumentParser(
        prog="todo",
        description="简单命令行待办事项管理工具",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="添加待办事项")
    add_parser.add_argument("content", help="待办内容")

    # list
    subparsers.add_parser("list", help="列出所有待办事项")

    # done
    done_parser = subparsers.add_parser("done", help="标记事项为完成")
    done_parser.add_argument("id", type=int, help="事项编号")

    # remove
    remove_parser = subparsers.add_parser("remove", help="删除事项")
    remove_parser.add_argument("id", type=int, help="事项编号")

    try:
        parsed = parser.parse_args()
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    handlers = {
        "add": handle_add,
        "list": handle_list,
        "done": handle_done,
        "remove": handle_remove,
    }

    handler = handlers.get(parsed.command)
    if handler is None:
        print(f"未知命令: {parsed.command}", file=sys.stderr)
        return 1

    result = handler(parsed)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
