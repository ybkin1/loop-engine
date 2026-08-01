"""
Knowledge Store — structured knowledge persistence + multi-axis retrieval.

D3 (T-0096): StaffDeck 知识库/记忆对标在 loop-engine 治理域的轻量落地。
沉淀决策（decision）/经验（lesson）/教训（pitfall）/最佳实践（best_practice）
四类结构化知识条目，支持按任务 / gate / 主题标签 / 关键词检索，并与
gate_feedback（T-0089）整合：``.ai/evidence/feedback/gate-lessons.yaml`` 是
**源**，本 store 是其**派生视图**（由 memory_service.extract_memories 聚合，
record_gate_lesson 内部不写 knowledge —— 无反向耦合）。

Design:
- Entries are appended to ``.ai/evidence/knowledge/knowledge-store.yaml``
  (append-style log: new entries appended, historical entries never edited).
- Writing is idempotent: same (source_type, source_id, kind, normalized
  content) fingerprint records at most once (dedup key is a deterministic
  SHA-256 entry_id).
- Retrieval: by_task / by_gate / by_tag / keyword search / combined query,
  all capped at a default limit (20) and ordered newest-first.
- Validation fails closed: missing fields / unknown kind / unknown source
  type / bad tags raise InvalidKnowledgeEntryError — the machine never
  guesses about its own memory (same principle as gate_feedback).

Referenced by:
- memory_service.py — extract_memories / recall (D3, T-0096)
- context_loader.py — optional memory injection (include_memories, T-0096)
- tests/test_knowledge_memory.py — AC-01 (schema/dedup/retrieval)
"""
from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

KNOWLEDGE_SCHEMA = "knowledge_store"
KNOWLEDGE_SCHEMA_VERSION = 1
DEFAULT_KNOWLEDGE_RELATIVE_PATH = ".ai/evidence/knowledge/knowledge-store.yaml"

# Entry kinds (知识条目类型)
KIND_DECISION = "decision"              # 决策
KIND_LESSON = "lesson"                  # 经验（教训性，从 gate 拒绝/修复派生）
KIND_PITFALL = "pitfall"                # 教训/坑
KIND_BEST_PRACTICE = "best_practice"    # 最佳实践
ENTRY_KINDS = (KIND_DECISION, KIND_LESSON, KIND_PITFALL, KIND_BEST_PRACTICE)

# Source types (来源类型)
SOURCE_TASK = "task"                    # 任务（验收报告等）
SOURCE_GATE = "gate"                    # gate 裁决（gate_lessons 派生）
SOURCE_LESSON = "lesson"                # lesson 记录
SOURCE_INCIDENT = "incident"            # 事件
SOURCE_TYPES = (SOURCE_TASK, SOURCE_GATE, SOURCE_LESSON, SOURCE_INCIDENT)

# Retrieval caps — 检索返回上限（组合过滤同样受此约束）
DEFAULT_SEARCH_LIMIT = 20
DEFAULT_QUERY_LIMIT = 20

# Tag rules: non-empty, no whitespace / separator characters, bounded length.
_TAG_MAX_LEN = 40
_TAG_MAX_COUNT = 32
_TAG_FORBIDDEN = frozenset(" \t\n\r\f\v,|;")

# T-0095 pattern: process-internal lock serializing put_entry's
# read-modify-write (load -> append -> save) so concurrent writers never
# overwrite each other's append. Cross-process atomicity is covered by the
# tmp+rename atomic write in _save_entries.
_PUT_LOCK = threading.Lock()


class KnowledgeStoreError(Exception):
    """Base error for knowledge store record / retrieval failures."""


class InvalidKnowledgeEntryError(KnowledgeStoreError):
    """Raised when an entry is malformed or violates the schema."""


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass
class KnowledgeEntry:
    """One structured knowledge record.

    Fields:
        entry_id: Deterministic id — SHA-256 over
            source_type|source_id|kind|normalized_content. Same fingerprint
            → same entry (dedup key).
        kind: decision | lesson | pitfall | best_practice.
        source_type: task | gate | lesson | incident.
        source_id: The concrete source (task id / gate id / lesson id / ...).
        task_id: Optional owning task (propagated from the source, e.g. the
            task a gate lesson belongs to). Enables by_task retrieval for
            entries whose source is not the task itself.
        tags: Topic labels (validated — bad tags are rejected).
        content: Free-text knowledge content (the retrievable body).
        recorded_at: ISO-8601 UTC timestamp of when the knowledge was
            recorded (propagated from the source where possible).
        version: Entry version (bumps when the entry is intentionally
            revised — the store is append-style, so today it is always 1).
        schema_version: Knowledge schema version (KNOWLEDGE_SCHEMA_VERSION).
    """
    entry_id: str
    kind: str
    source_type: str
    source_id: str
    content: str
    tags: list[str] = field(default_factory=list)
    task_id: str | None = None
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: int = 1
    schema_version: int = KNOWLEDGE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "task_id": self.task_id,
            "tags": list(self.tags),
            "content": self.content,
            "recorded_at": self.recorded_at,
            "version": self.version,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> KnowledgeEntry:
        if not isinstance(data, dict):
            raise InvalidKnowledgeEntryError(
                f"knowledge 记录格式错误: {data!r}"
            )
        required = (
            "entry_id", "kind", "source_type", "source_id",
            "content", "recorded_at",
        )
        for key in required:
            if key not in data or data[key] in (None, ""):
                raise InvalidKnowledgeEntryError(
                    f"knowledge 记录缺少必需字段 '{key}'"
                )
        kind = str(data["kind"])
        source_type = str(data["source_type"])
        if kind not in ENTRY_KINDS:
            raise InvalidKnowledgeEntryError(
                f"kind 非法: {kind!r}（允许 {ENTRY_KINDS}）"
            )
        if source_type not in SOURCE_TYPES:
            raise InvalidKnowledgeEntryError(
                f"source_type 非法: {source_type!r}（允许 {SOURCE_TYPES}）"
            )
        schema_version = int(
            data.get("schema_version", KNOWLEDGE_SCHEMA_VERSION)
        )
        if schema_version != KNOWLEDGE_SCHEMA_VERSION:
            raise InvalidKnowledgeEntryError(
                f"不支持的 knowledge schema_version: {schema_version}"
            )
        tags = _validate_tags(data.get("tags", []))
        task_id = data.get("task_id")
        if task_id is not None and (
            not isinstance(task_id, str) or not task_id.strip()
        ):
            raise InvalidKnowledgeEntryError(
                f"task_id 非法: {task_id!r}"
            )
        version = data.get("version", 1)
        if not isinstance(version, int) or version < 1:
            raise InvalidKnowledgeEntryError(
                f"version 非法: {version!r}"
            )
        return cls(
            entry_id=str(data["entry_id"]),
            kind=kind,
            source_type=source_type,
            source_id=str(data["source_id"]),
            content=str(data["content"]),
            tags=tags,
            task_id=str(task_id) if task_id else None,
            recorded_at=str(data["recorded_at"]),
            version=version,
            schema_version=schema_version,
        )


# ── Tag validation ─────────────────────────────────────────────────────────


def _validate_tag(tag: str) -> str:
    """Validate one tag, returning its normalized form.

    A bad tag (empty / whitespace / separator characters / over-long)
    raises InvalidKnowledgeEntryError — explicit rejection, never a guess.
    """
    if not isinstance(tag, str):
        raise InvalidKnowledgeEntryError(f"tag 非法（非字符串）: {tag!r}")
    normalized = tag.strip()
    if not normalized:
        raise InvalidKnowledgeEntryError("tag 不能为空")
    if len(normalized) > _TAG_MAX_LEN:
        raise InvalidKnowledgeEntryError(
            f"tag 过长（>{_TAG_MAX_LEN} 字符）: {tag!r}"
        )
    if any(ch in _TAG_FORBIDDEN for ch in normalized):
        raise InvalidKnowledgeEntryError(
            f"tag 含非法字符（空白/分隔符）: {tag!r}"
        )
    return normalized


def _validate_tags(tags: object) -> list[str]:
    """Validate a tag list: dedupe (case-insensitive), cap the count."""
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise InvalidKnowledgeEntryError(
            f"tags 非法（非列表）: {tags!r}"
        )
    seen: dict[str, str] = {}
    for raw in tags:
        normalized = _validate_tag(raw)
        key = normalized.casefold()
        if key not in seen:
            seen[key] = normalized
        if len(seen) > _TAG_MAX_COUNT:
            raise InvalidKnowledgeEntryError(
                f"tags 过多（>{_TAG_MAX_COUNT} 个）"
            )
    return list(seen.values())


# ── Fingerprint / Entry Id ─────────────────────────────────────────────────


def _normalize_content(text: str) -> str:
    """Normalize content for fingerprinting: collapse whitespace + casefold."""
    return " ".join(str(text).strip().split()).casefold()


def make_entry_id(
    kind: str,
    source_type: str,
    source_id: str,
    content: str,
) -> str:
    """Deterministic entry id for the given knowledge fingerprint.

    Same (kind, source_type, source_id, normalized content) always yields
    the same entry id — this is the dedup key.
    """
    fingerprint = "|".join([
        str(kind),
        str(source_type),
        str(source_id),
        _normalize_content(content),
    ])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"KE-{digest[:16].upper()}"


# ── Storage ────────────────────────────────────────────────────────────────


def knowledge_path(
    project_root: str | Path,
    relative_path: str | None = None,
) -> Path:
    """Absolute path of the knowledge store file under the project root."""
    return Path(project_root) / (
        relative_path or DEFAULT_KNOWLEDGE_RELATIVE_PATH
    )


def load_entries(
    project_root: str | Path,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Load all knowledge entries. Missing / empty file → empty list.

    Malformed entries fail closed: any record that violates the schema
    raises InvalidKnowledgeEntryError instead of being silently dropped —
    the machine never guesses about its own memory.
    """
    path = knowledge_path(project_root, relative_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise KnowledgeStoreError(
            f"无法解析 knowledge 文件 {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise KnowledgeStoreError(
            f"knowledge 文件格式错误（非 mapping）: {path}"
        )
    if data.get("schema") not in (None, KNOWLEDGE_SCHEMA):
        raise KnowledgeStoreError(
            f"不支持的 knowledge schema: {data.get('schema')!r}（{path}）"
        )
    raw_entries = data.get("entries", [])
    if not isinstance(raw_entries, list):
        raise KnowledgeStoreError(
            f"knowledge 文件格式错误（entries 非列表）: {path}"
        )
    return [KnowledgeEntry.from_dict(rec) for rec in raw_entries]


def _save_entries(path: Path, entries: list[KnowledgeEntry]) -> None:
    """Write all entries atomically (tmp file + rename), append-style log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": KNOWLEDGE_SCHEMA,
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "entries": [entry.to_dict() for entry in entries],
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


def put_entry(
    project_root: str | Path,
    *,
    kind: str,
    source_type: str,
    source_id: str,
    content: str,
    tags: list[str] | None = None,
    task_id: str | None = None,
    recorded_at: str | None = None,
    relative_path: str | None = None,
) -> tuple[KnowledgeEntry, bool]:
    """Record one knowledge entry; idempotent for identical fingerprints.

    Args:
        project_root: Project root that contains the .ai/ governance tree.
        kind: decision | lesson | pitfall | best_practice.
        source_type: task | gate | lesson | incident.
        source_id: The concrete source id (task / gate / lesson id).
        content: Free-text knowledge content (must be non-empty).
        tags: Optional topic labels (validated; bad tags are rejected).
        task_id: Optional owning task id (enables by_task retrieval).
        recorded_at: Optional ISO timestamp; defaults to now (UTC).
        relative_path: Override for the knowledge file location (tests).

    Returns:
        (entry, created): entry is the stored record — either freshly
        created or the existing duplicate; created is True only when a new
        record was appended.
    """
    if kind not in ENTRY_KINDS:
        raise InvalidKnowledgeEntryError(
            f"kind 非法: {kind!r}（允许 {ENTRY_KINDS}）"
        )
    if source_type not in SOURCE_TYPES:
        raise InvalidKnowledgeEntryError(
            f"source_type 非法: {source_type!r}（允许 {SOURCE_TYPES}）"
        )
    if not isinstance(source_id, str) or not source_id.strip():
        raise InvalidKnowledgeEntryError("source_id 不能为空")
    if not isinstance(content, str) or not content.strip():
        raise InvalidKnowledgeEntryError("content 不能为空")
    if task_id is not None and (
        not isinstance(task_id, str) or not task_id.strip()
    ):
        raise InvalidKnowledgeEntryError("task_id 非法")
    normalized_tags = _validate_tags(tags)

    entry_id = make_entry_id(kind, source_type, source_id, content)

    # T-0095 pattern: the read-modify-write below is serialized by a
    # process-internal lock so concurrent writers never lose records.
    # Validation above stays outside the lock.
    with _PUT_LOCK:
        entries = load_entries(project_root, relative_path)
        for existing in entries:
            if existing.entry_id == entry_id:
                # Same source + same content fingerprint → idempotent.
                return existing, False

        entry = KnowledgeEntry(
            entry_id=entry_id,
            kind=kind,
            source_type=source_type,
            source_id=source_id.strip(),
            content=content.strip(),
            tags=normalized_tags,
            task_id=task_id.strip() if task_id else None,
            recorded_at=recorded_at or datetime.now(timezone.utc).isoformat(),
        )
        _save_entries(
            knowledge_path(project_root, relative_path), entries + [entry]
        )
        return entry, True


# ── Retrieval ──────────────────────────────────────────────────────────────


def _ordered(entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
    """Newest first; stable on equal recorded_at (insertion order kept)."""
    return sorted(entries, key=lambda entry: entry.recorded_at, reverse=True)


def _capped(entries: list[KnowledgeEntry], limit: int) -> list[KnowledgeEntry]:
    """Cap the result list at ``limit`` (negative/zero → empty)."""
    return entries[: max(0, limit)]


def by_task(
    project_root: str | Path,
    task_id: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Entries associated with one task (owned task_id or task source)."""
    needle = str(task_id).strip()
    if not needle:
        raise InvalidKnowledgeEntryError("task_id 不能为空")
    matches = [
        entry for entry in load_entries(project_root, relative_path)
        if entry.task_id == needle
        or (entry.source_type == SOURCE_TASK and entry.source_id == needle)
    ]
    return _capped(_ordered(matches), limit)


def by_gate(
    project_root: str | Path,
    gate_id: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Entries derived from one gate (source_type == gate)."""
    needle = str(gate_id).strip()
    if not needle:
        raise InvalidKnowledgeEntryError("gate_id 不能为空")
    matches = [
        entry for entry in load_entries(project_root, relative_path)
        if entry.source_type == SOURCE_GATE and entry.source_id == needle
    ]
    return _capped(_ordered(matches), limit)


def by_tag(
    project_root: str | Path,
    tag: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Entries carrying one topic tag (case-insensitive match)."""
    needle = _validate_tag(tag).casefold()
    matches = [
        entry for entry in load_entries(project_root, relative_path)
        if any(existing.casefold() == needle for existing in entry.tags)
    ]
    return _capped(_ordered(matches), limit)


def search(
    project_root: str | Path,
    keyword: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Case-insensitive substring search over entry content.

    Matches content, tags, source_id, task_id, kind and entry_id. Empty
    keyword returns everything (still capped at ``limit``).
    """
    needle = str(keyword).casefold()
    matches: list[KnowledgeEntry] = []
    for entry in load_entries(project_root, relative_path):
        if not needle:
            matches.append(entry)
            continue
        haystack = " ".join([
            entry.content,
            " ".join(entry.tags),
            entry.source_id,
            entry.task_id or "",
            entry.kind,
            entry.entry_id,
        ]).casefold()
        if needle in haystack:
            matches.append(entry)
    return _capped(_ordered(matches), limit)


def query(
    project_root: str | Path,
    *,
    task_id: str | None = None,
    gate_id: str | None = None,
    tag: str | None = None,
    keyword: str | None = None,
    limit: int = DEFAULT_QUERY_LIMIT,
    relative_path: str | None = None,
) -> list[KnowledgeEntry]:
    """Combined retrieval — every supplied filter is AND-combined.

    Supports the memory-injection path (memory_service.recall): filter by
    task / gate / tag / keyword in any combination, newest first, capped at
    ``limit`` (top-N bound, e.g. 5 for context injection).
    """
    matches = load_entries(project_root, relative_path)
    if task_id is not None:
        matches = [
            entry for entry in matches
            if entry.task_id == task_id
            or (entry.source_type == SOURCE_TASK and entry.source_id == task_id)
        ]
    if gate_id is not None:
        matches = [
            entry for entry in matches
            if entry.source_type == SOURCE_GATE and entry.source_id == gate_id
        ]
    if tag is not None:
        needle = _validate_tag(tag).casefold()
        matches = [
            entry for entry in matches
            if any(existing.casefold() == needle for existing in entry.tags)
        ]
    if keyword is not None and str(keyword).strip():
        needle = str(keyword).casefold()
        matches = [
            entry for entry in matches
            if needle in " ".join([
                entry.content,
                " ".join(entry.tags),
                entry.source_id,
                entry.task_id or "",
                entry.kind,
            ]).casefold()
        ]
    return _capped(_ordered(matches), limit)
