"""JSON file-based storage for todo items."""
import json
from pathlib import Path
from typing import Optional

from src.models import TodoItem


def _ensure_dir(filepath: str) -> None:
    """Ensure the parent directory exists."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def load_todos(filepath: str) -> list[TodoItem]:
    """Load todo items from a JSON file.

    Args:
        filepath: Path to the JSON data file.

    Returns:
        List of TodoItem. Empty list if file doesn't exist or is corrupt.
    """
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [
            TodoItem(id=item["id"], content=item["content"], done=item.get("done", False))
            for item in data
            if isinstance(item, dict) and "id" in item and "content" in item
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def save_todos(filepath: str, todos: list[TodoItem]) -> None:
    """Save todo items to a JSON file.

    Args:
        filepath: Path to the JSON data file.
        todos: List of TodoItem to save.

    Raises:
        OSError: If the file cannot be written.
    """
    _ensure_dir(filepath)
    data = [
        {"id": item.id, "content": item.content, "done": item.done}
        for item in todos
    ]
    Path(filepath).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
