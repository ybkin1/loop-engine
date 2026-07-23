"""Todo item data model."""
from dataclasses import dataclass


@dataclass
class TodoItem:
    """A single todo item."""
    id: int
    content: str
    done: bool = False


def create_todo(content: str, existing_ids: list[int]) -> TodoItem:
    """Create a new TodoItem with auto-incremented ID.

    Args:
        content: The todo description (non-empty string).
        existing_ids: List of already-used IDs.

    Returns:
        A new TodoItem.

    Raises:
        ValueError: If content is empty.
    """
    if not content or not content.strip():
        raise ValueError("事项内容不能为空")
    new_id = max(existing_ids) + 1 if existing_ids else 1
    return TodoItem(id=new_id, content=content.strip())


def mark_done(item: TodoItem) -> TodoItem:
    """Mark a todo item as done (idempotent).

    Args:
        item: The TodoItem to mark.

    Returns:
        The item with done=True.

    Raises:
        ValueError: If item is already marked done.
    """
    if item.done:
        raise ValueError(f"事项 #{item.id} 已完成")
    item.done = True
    return item
