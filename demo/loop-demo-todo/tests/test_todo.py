"""Tests for loop-demo-todo CLI tool.

Covers:
- models: create_todo, mark_done, edge cases
- storage: load/save, empty files, corrupt data
- cli: command handling, error paths, boundary conditions
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add demo project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.models import TodoItem, create_todo, mark_done
from src.storage import load_todos, save_todos
from src.cli import handle_add, handle_list, handle_done, handle_remove, DATA_FILE


# ── Models tests ─────────────────────────────────────────────────────────


class TestCreateTodo:
    def test_create_with_content(self):
        item = create_todo("购买牛奶", [])
        assert item.content == "购买牛奶"
        assert item.done is False
        assert item.id == 1

    def test_create_with_existing_ids(self):
        item = create_todo("学Python", [1, 2, 5])
        assert item.id == 6

    def test_create_empty_content_raises(self):
        with pytest.raises(ValueError, match="不能为空"):
            create_todo("", [])

    def test_create_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="不能为空"):
            create_todo("   ", [])

    def test_create_strips_whitespace(self):
        item = create_todo("   hello   ", [])
        assert item.content == "hello"


class TestMarkDone:
    def test_mark_undone_item(self):
        item = TodoItem(id=1, content="test", done=False)
        result = mark_done(item)
        assert result.done is True

    def test_mark_already_done_raises(self):
        item = TodoItem(id=1, content="test", done=True)
        with pytest.raises(ValueError, match="已完成"):
            mark_done(item)

    def test_mark_done_is_idempotent_check(self):
        """mark_done raises on already-done items → idempotent behavior."""
        item = TodoItem(id=1, content="test", done=True)
        with pytest.raises(ValueError):
            mark_done(item)
        assert item.done is True  # State unchanged on error


# ── Storage tests ────────────────────────────────────────────────────────


class TestStorage:
    def test_save_and_load_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            items = [
                TodoItem(id=1, content="任务1", done=False),
                TodoItem(id=2, content="任务2", done=True),
            ]
            save_todos(filepath, items)
            loaded = load_todos(filepath)
            assert len(loaded) == 2
            assert loaded[0].content == "任务1"
            assert loaded[1].done is True
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_load_nonexistent_file(self):
        items = load_todos("/nonexistent/path/data.json")
        assert items == []

    def test_load_corrupt_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b"not valid json{{{")
            filepath = f.name
        try:
            items = load_todos(filepath)
            assert items == []
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_load_non_list_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"not": "a list"}')
            filepath = f.name
        try:
            items = load_todos(filepath)
            assert items == []
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_empty_list_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        try:
            save_todos(filepath, [])
            items = load_todos(filepath)
            assert items == []
        finally:
            Path(filepath).unlink(missing_ok=True)


# ── CLI tests ────────────────────────────────────────────────────────────


class TestCLI:
    def setup_method(self):
        """Use a temp data file for isolation."""
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        self._orig_data_file = sys.modules["src.cli"].DATA_FILE
        sys.modules["src.cli"].DATA_FILE = self._tmp.name

    def teardown_method(self):
        sys.modules["src.cli"].DATA_FILE = self._orig_data_file
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_add_todo(self):
        result = handle_add(_Args(content="购买牛奶"))
        assert "已添加" in result
        assert "购买牛奶" in result

    def test_add_empty_content(self):
        result = handle_add(_Args(content=""))
        assert "错误" in result

    def test_list_empty(self):
        result = handle_list(_Args())
        assert "暂无" in result

    def test_list_with_items(self):
        handle_add(_Args(content="任务1"))
        handle_add(_Args(content="任务2"))
        result = handle_list(_Args())
        assert "任务1" in result
        assert "任务2" in result

    def test_done_existing_item(self):
        handle_add(_Args(content="任务1"))
        result = handle_done(_Args(id=1))
        assert "已完成" in result

    def test_done_nonexistent_item(self):
        result = handle_done(_Args(id=999))
        assert "不存在" in result

    def test_done_already_done(self):
        handle_add(_Args(content="任务1"))
        handle_done(_Args(id=1))
        result = handle_done(_Args(id=1))
        assert "已完成" in result  # 提示已完成

    def test_remove_existing_item(self):
        handle_add(_Args(content="任务1"))
        result = handle_remove(_Args(id=1))
        assert "已删除" in result

    def test_remove_nonexistent_item(self):
        result = handle_remove(_Args(id=999))
        assert "不存在" in result

    def test_full_workflow(self):
        """End-to-end workflow: add → list → done → list → remove."""
        # Add
        r1 = handle_add(_Args(content="学Rust"))
        assert "已添加" in r1

        # List
        r2 = handle_list(_Args())
        assert "学Rust" in r2
        assert "⬜" in r2

        # Done
        r3 = handle_done(_Args(id=1))
        assert "已完成" in r3

        # List after done
        r4 = handle_list(_Args())
        assert "✅" in r4

        # Remove
        r5 = handle_remove(_Args(id=1))
        assert "已删除" in r5

        # List after remove
        r6 = handle_list(_Args())
        assert "暂无" in r6


# ── Helper ───────────────────────────────────────────────────────────────


class _Args:
    """Minimal argparse.Namespace mock."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        # Defaults
        self.__dict__.setdefault("command", "add")
        self.__dict__.setdefault("content", "")
        self.__dict__.setdefault("id", 0)
