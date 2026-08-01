"""
Retrospective — root-cause analysis + owned action items (B2 §3.3, T-0097).

The retro is where the learning loop turns an incident into a plan: a linked
root-cause analysis plus action items that must carry an **owner** and a
**deadline** (the second-failure doctrine blocks until such an owned, dated
action item exists — loop_core/second_failure.py consumes this state).

Design (mirrors gate_feedback / knowledge_store conventions):
- Retros are appended to ``.ai/evidence/observability/retrospectives.yaml``
  (append-style log: new retros appended, historical retros never edited —
  except status tracking below).
- Writing is idempotent: one incident + one root-cause fingerprint yields one
  deterministic retro id (``RT-`` prefix); re-creating dedups.
- Status tracking: action items transition open -> done; when *all* action
  items of a retro are done the retro auto-closes (``status: closed``).  A
  closed retro is immutable — no new action items, no status flips.
- Validation fails closed: unknown statuses, empty owner/description,
  unparseable deadline, or a malformed file raise instead of being silently
  dropped.

Referenced by:
- loop_core/second_failure.py — ``second_failure_block`` checks the linked
  retro for open action items
- tests/test_learning_loop.py — AC-02
"""
from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

RETROS_SCHEMA = "retrospectives"
RETROS_SCHEMA_VERSION = 1
DEFAULT_RETROS_RELATIVE_PATH = ".ai/evidence/observability/retrospectives.yaml"

ACTION_STATUS_OPEN = "open"
ACTION_STATUS_DONE = "done"
ACTION_STATUSES = (ACTION_STATUS_OPEN, ACTION_STATUS_DONE)

RETRO_STATUS_OPEN = "open"
RETRO_STATUS_CLOSED = "closed"
RETRO_STATUSES = (RETRO_STATUS_OPEN, RETRO_STATUS_CLOSED)

# T-0095 pattern: process-internal lock serializing retro / action-item
# read-modify-write.  Cross-process atomicity is covered by tmp+rename.
_RECORD_LOCK = threading.Lock()


class RetrospectiveError(Exception):
    """Base error for retro record / update failures."""


class InvalidRetrospectiveError(RetrospectiveError):
    """Raised when a retro or action item is malformed or violates the schema."""


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass
class ActionItem:
    """One owned, dated action item produced by a retrospective.

    Fields:
        id: Deterministic id — SHA-256 over
            retro_id|owner|normalized description ("AI-" prefix).
        owner: The role/person accountable for the item (non-empty).
        deadline: ISO date or datetime the item must be done by (parseable).
        status: open | done.
        description: What will be done (non-empty).
        done_at: ISO-8601 UTC timestamp when the item was marked done (None
            while open).
    """
    id: str
    owner: str
    deadline: str
    status: str
    description: str
    done_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner": self.owner,
            "deadline": self.deadline,
            "status": self.status,
            "description": self.description,
            "done_at": self.done_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionItem:
        if not isinstance(data, dict):
            raise InvalidRetrospectiveError(f"action_item 记录格式错误: {data!r}")
        for key in ("id", "owner", "deadline", "status", "description"):
            if key not in data or data[key] in (None, ""):
                raise InvalidRetrospectiveError(
                    f"action_item 记录缺少必需字段 '{key}'"
                )
        status = str(data["status"])
        if status not in ACTION_STATUSES:
            raise InvalidRetrospectiveError(
                f"action_item status 非法: {status!r}（允许 {ACTION_STATUSES}）"
            )
        validate_deadline(str(data["deadline"]))
        return cls(
            id=str(data["id"]),
            owner=str(data["owner"]),
            deadline=str(data["deadline"]),
            status=status,
            description=str(data["description"]),
            done_at=(
                str(data["done_at"]) if data.get("done_at") is not None
                else None
            ),
        )


@dataclass
class Retrospective:
    """One retrospective linked to an incident.

    Fields:
        retro_id: Deterministic id — SHA-256 over
            incident_id|normalized root_cause ("RT-" prefix).  One incident +
            one root-cause fingerprint -> one retro (dedup key).
        incident_id: The incident this retro analyzes.
        root_cause: The root-cause analysis (blameless: mechanisms, not
            individuals).
        action_items: Owned, dated action items (open/done).
        status: open | closed — closes automatically when every action item
            is done.
        created_at: ISO-8601 UTC timestamp of creation.
        updated_at: ISO-8601 UTC timestamp of the last status change.
        schema_version: Retro schema version (RETROS_SCHEMA_VERSION).
    """
    retro_id: str
    incident_id: str
    root_cause: str
    action_items: list[ActionItem] = field(default_factory=list)
    status: str = RETRO_STATUS_OPEN
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: int = RETROS_SCHEMA_VERSION

    @property
    def open_action_items(self) -> list[ActionItem]:
        return [item for item in self.action_items if item.status == ACTION_STATUS_OPEN]

    def to_dict(self) -> dict:
        return {
            "retro_id": self.retro_id,
            "incident_id": self.incident_id,
            "root_cause": self.root_cause,
            "action_items": [item.to_dict() for item in self.action_items],
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Retrospective:
        if not isinstance(data, dict):
            raise InvalidRetrospectiveError(f"retro 记录格式错误: {data!r}")
        for key in ("retro_id", "incident_id", "root_cause", "status"):
            if key not in data or data[key] in (None, ""):
                raise InvalidRetrospectiveError(
                    f"retro 记录缺少必需字段 '{key}'"
                )
        status = str(data["status"])
        if status not in RETRO_STATUSES:
            raise InvalidRetrospectiveError(
                f"retro status 非法: {status!r}（允许 {RETRO_STATUSES}）"
            )
        raw_items = data.get("action_items", [])
        if not isinstance(raw_items, list):
            raise InvalidRetrospectiveError(
                f"retro 记录格式错误（action_items 非列表）: {data!r}"
            )
        schema_version = int(data.get("schema_version", RETROS_SCHEMA_VERSION))
        if schema_version != RETROS_SCHEMA_VERSION:
            raise InvalidRetrospectiveError(
                f"不支持的 retro schema_version: {schema_version}"
            )
        return cls(
            retro_id=str(data["retro_id"]),
            incident_id=str(data["incident_id"]),
            root_cause=str(data["root_cause"]),
            action_items=[ActionItem.from_dict(rec) for rec in raw_items],
            status=status,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            schema_version=schema_version,
        )


# ── Helpers ────────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Normalize text for fingerprinting: collapse whitespace + casefold."""
    return " ".join(str(text).strip().split()).casefold()


def validate_deadline(deadline: str) -> None:
    """A deadline must be a parseable ISO date (YYYY-MM-DD) or datetime."""
    text = str(deadline).strip()
    if not text:
        raise InvalidRetrospectiveError("action_item deadline 不能为空")
    try:
        datetime.fromisoformat(text)
        return
    except ValueError:
        pass
    try:
        date.fromisoformat(text)
        return
    except ValueError as exc:
        raise InvalidRetrospectiveError(
            f"action_item deadline 无法解析: {deadline!r}"
        ) from exc


def make_retro_id(incident_id: str, root_cause: str) -> str:
    """Deterministic retro id for one incident + root-cause fingerprint."""
    fingerprint = "|".join([str(incident_id), _normalize(root_cause)])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"RT-{digest[:8].upper()}"


def make_action_item_id(
    retro_id: str, owner: str, description: str
) -> str:
    """Deterministic action-item id within a retro (dedup key)."""
    fingerprint = "|".join([str(retro_id), str(owner), _normalize(description)])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"AI-{digest[:6].upper()}"


def _retro_status_for(action_items: list[ActionItem]) -> str:
    """A retro is closed when it has items and every item is done; a retro
    with zero action items stays open (nothing owned yet — the second-failure
    doctrine treats that as unresolved)."""
    if action_items and all(
        item.status == ACTION_STATUS_DONE for item in action_items
    ):
        return RETRO_STATUS_CLOSED
    return RETRO_STATUS_OPEN


# ── Storage ────────────────────────────────────────────────────────────────


def retros_path(
    project_root: str | Path,
    relative_path: str | None = None,
) -> Path:
    """Absolute path of the retros file under the project root."""
    return Path(project_root) / (
        relative_path or DEFAULT_RETROS_RELATIVE_PATH
    )


def load_retrospectives(
    project_root: str | Path,
    relative_path: str | None = None,
) -> list[Retrospective]:
    """Load all recorded retros.  Missing / empty file -> empty list.

    Malformed entries fail closed: any record that violates the schema raises
    InvalidRetrospectiveError instead of being silently dropped.
    """
    path = retros_path(project_root, relative_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise RetrospectiveError(
            f"无法解析 retrospectives 文件 {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RetrospectiveError(f"retrospectives 文件格式错误（非 mapping）: {path}")
    if data.get("schema") not in (None, RETROS_SCHEMA):
        raise RetrospectiveError(
            f"不支持的 retrospectives schema: {data.get('schema')!r}（{path}）"
        )
    raw_retros = data.get("retrospectives", [])
    if not isinstance(raw_retros, list):
        raise RetrospectiveError(
            f"retrospectives 文件格式错误（retrospectives 非列表）: {path}"
        )
    return [Retrospective.from_dict(rec) for rec in raw_retros]


def _save_retros(path: Path, retros: list[Retrospective]) -> None:
    """Write all retros atomically (tmp file + rename), append-style log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": RETROS_SCHEMA,
        "schema_version": RETROS_SCHEMA_VERSION,
        "retrospectives": [retro.to_dict() for retro in retros],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(
            payload,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    os.replace(tmp, path)


def _find_retro(
    retros: list[Retrospective], retro_id: str
) -> Retrospective | None:
    for retro in retros:
        if retro.retro_id == retro_id:
            return retro
    return None


def create_retrospective(
    project_root: str | Path,
    *,
    incident_id: str,
    root_cause: str,
    action_items: list[dict] | None = None,
    created_at: str | None = None,
    relative_path: str | None = None,
) -> tuple[Retrospective, bool]:
    """Create one retrospective; idempotent for the same incident + root-cause.

    Args:
        project_root: Project root that contains the .ai/ governance tree.
        incident_id: The incident this retro analyzes (required).
        root_cause: The root-cause analysis text (required).
        action_items: Optional list of dicts with keys ``owner`` (required),
            ``deadline`` (required, ISO date/datetime) and ``description``
            (required).  Items start ``open``.
        created_at: Optional ISO timestamp; defaults to now (UTC).
        relative_path: Override for the retros file location (tests).

    Returns:
        (retro, created): retro is the stored record — either freshly created
        or the existing duplicate; created is True only when a new record was
        appended.
    """
    if not isinstance(incident_id, str) or not incident_id.strip():
        raise InvalidRetrospectiveError("incident_id 不能为空")
    if not isinstance(root_cause, str) or not root_cause.strip():
        raise InvalidRetrospectiveError("root_cause 不能为空")

    retro_id = make_retro_id(incident_id, root_cause)

    items: list[ActionItem] = []
    for spec in action_items or []:
        if not isinstance(spec, dict):
            raise InvalidRetrospectiveError(
                f"action_items 项必须为 mapping: {spec!r}"
            )
        owner = str(spec.get("owner") or "").strip()
        description = str(spec.get("description") or "").strip()
        deadline = str(spec.get("deadline") or "").strip()
        if not owner:
            raise InvalidRetrospectiveError(
                "action_item owner 不能为空（必须有人负责）"
            )
        if not description:
            raise InvalidRetrospectiveError("action_item description 不能为空")
        validate_deadline(deadline)
        items.append(ActionItem(
            id=make_action_item_id(retro_id, owner, description),
            owner=owner,
            deadline=deadline,
            status=ACTION_STATUS_OPEN,
            description=description,
        ))

    with _RECORD_LOCK:
        retros = load_retrospectives(project_root, relative_path)
        existing = _find_retro(retros, retro_id)
        if existing is not None:
            return existing, False

        now = created_at or datetime.now(timezone.utc).isoformat()
        retro = Retrospective(
            retro_id=retro_id,
            incident_id=incident_id.strip(),
            root_cause=root_cause.strip(),
            action_items=items,
            status=_retro_status_for(items),
            created_at=now,
            updated_at=now,
        )
        _save_retros(
            retros_path(project_root, relative_path),
            retros + [retro],
        )
        return retro, True


def add_action_item(
    project_root: str | Path,
    retro_id: str,
    *,
    owner: str,
    deadline: str,
    description: str,
    now: str | None = None,
    relative_path: str | None = None,
) -> tuple[Retrospective, ActionItem, bool]:
    """Append one open action item to an open retro.

    Idempotent per (retro_id, owner, normalized description).  A closed retro
    is immutable — adding an item to it raises.
    """
    if not isinstance(owner, str) or not owner.strip():
        raise InvalidRetrospectiveError(
            "action_item owner 不能为空（必须有人负责）"
        )
    if not isinstance(description, str) or not description.strip():
        raise InvalidRetrospectiveError("action_item description 不能为空")
    validate_deadline(deadline)

    with _RECORD_LOCK:
        path = retros_path(project_root, relative_path)
        retros = load_retrospectives(project_root, relative_path)
        retro = _find_retro(retros, retro_id)
        if retro is None:
            raise RetrospectiveError(f"retro 不存在: {retro_id}")
        if retro.status == RETRO_STATUS_CLOSED:
            raise RetrospectiveError(
                f"retro {retro_id} 已 closed（全部行动项 done），不可再添加行动项"
            )
        item_id = make_action_item_id(retro_id, owner, description)
        for item in retro.action_items:
            if item.id == item_id:
                return retro, item, False
        item = ActionItem(
            id=item_id,
            owner=owner.strip(),
            deadline=deadline.strip(),
            status=ACTION_STATUS_OPEN,
            description=description.strip(),
        )
        retro.action_items.append(item)
        retro.updated_at = now or datetime.now(timezone.utc).isoformat()
        _save_retros(path, retros)
        return retro, item, True


def update_action_item(
    project_root: str | Path,
    retro_id: str,
    action_item_id: str,
    *,
    status: str = ACTION_STATUS_DONE,
    done_at: str | None = None,
    now: str | None = None,
    relative_path: str | None = None,
) -> tuple[Retrospective, ActionItem]:
    """Transition one action item open -> done (AC-02).

    When the last open item becomes done the retro auto-closes.  A closed
    retro is immutable (no status flips after closure).  Setting the same
    status is a no-op.
    """
    if status not in ACTION_STATUSES:
        raise InvalidRetrospectiveError(
            f"action_item status 非法: {status!r}（允许 {ACTION_STATUSES}）"
        )
    with _RECORD_LOCK:
        path = retros_path(project_root, relative_path)
        retros = load_retrospectives(project_root, relative_path)
        retro = _find_retro(retros, retro_id)
        if retro is None:
            raise RetrospectiveError(f"retro 不存在: {retro_id}")
        item = next(
            (it for it in retro.action_items if it.id == action_item_id),
            None,
        )
        if item is None:
            raise RetrospectiveError(
                f"action_item 不存在: {action_item_id}（retro {retro_id}）"
            )
        if item.status == status:
            # Idempotent no-op (same status) — allowed even on a closed retro.
            return retro, item
        if retro.status == RETRO_STATUS_CLOSED:
            raise RetrospectiveError(
                f"retro {retro_id} 已 closed，行动项状态不可再变更（记录不可改写）"
            )
        item.status = status
        item.done_at = (
            done_at or datetime.now(timezone.utc).isoformat()
            if status == ACTION_STATUS_DONE
            else None
        )
        retro.status = _retro_status_for(retro.action_items)
        retro.updated_at = now or datetime.now(timezone.utc).isoformat()
        _save_retros(path, retros)
        return retro, item


# ── Retrieval ──────────────────────────────────────────────────────────────


def by_incident(
    project_root: str | Path,
    incident_id: str,
    relative_path: str | None = None,
) -> list[Retrospective]:
    """All retros linked to one incident, in recording order."""
    return [
        retro for retro in load_retrospectives(project_root, relative_path)
        if retro.incident_id == incident_id
    ]
