"""
Incident Record — structured failure/incident registry (B2 §3.2, T-0097).

The learning loop (B2 design §3) starts with a blameless, structured record of
what failed: an incident is a *factual* entry (category, severity, timeline,
source), not a verdict.  The retro (loop_core/retrospectives.py) and the
second-failure doctrine (loop_core/second_failure.py) consume these records.

Design (mirrors gate_feedback / knowledge_store conventions):
- Records are appended to ``.ai/evidence/observability/incidents.yaml``
  (append-style log: new records appended, historical records never edited).
- Recording is idempotent: same (source_type, source_id, category, normalized
  root-cause fingerprint) records at most once — the dedup key is a
  deterministic SHA-256 incident id (``IN-`` prefix).
- Retrieval: by_category / by_status / by_severity / search(keyword) /
  by_source — all fail closed on invalid filters.
- Validation fails closed: unknown category/severity/status/source_type,
  empty required fields, or a malformed file raise instead of being silently
  dropped — the machine never guesses about its own memory.
- ``register_gate_rejection_incident`` bridges gate_feedback (T-0089): a gate
  with >= 2 recorded rejections (decision rejected/repair_requested) is
  automatically registered as a ``gate_rejection`` incident (AC-04).

Referenced by:
- loop_core/retrospectives.py — retro links ``incident_id``
- loop_core/second_failure.py — recurrence detection groups incidents
- tests/test_learning_loop.py — AC-01 / AC-04
"""
from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

INCIDENTS_SCHEMA = "incidents"
INCIDENTS_SCHEMA_VERSION = 1
DEFAULT_INCIDENTS_RELATIVE_PATH = ".ai/evidence/observability/incidents.yaml"

# Incident categories (B2 §3.2 trigger types, adapted to T-0097 scope).
CATEGORY_GATE_REJECTION = "gate_rejection"
CATEGORY_GUARD_FAILURE = "guard_failure"
CATEGORY_REGRESSION = "regression"
CATEGORY_SLO_BREACH = "slo_breach"
CATEGORY_OTHER = "other"
CATEGORIES = (
    CATEGORY_GATE_REJECTION,
    CATEGORY_GUARD_FAILURE,
    CATEGORY_REGRESSION,
    CATEGORY_SLO_BREACH,
    CATEGORY_OTHER,
)

# Severity ladder — maps to the B2 P1/P2/P3 spirit without inventing a new
# taxonomy: critical = governance silent / guard death (P1 class), high = gate
# mis-decision with recovery (P2), medium/low = near-miss / process friction.
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITIES = (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW)

# Incident lifecycle.
STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUSES = (STATUS_OPEN, STATUS_RESOLVED, STATUS_CLOSED)

# Where the incident came from — ``source_id`` (e.g. the gate id) is the
# concrete reference.
SOURCE_TYPES = ("gate", "guard", "task", "slo", "manual", "other")

# Default rejection threshold for the gate_lessons bridge (AC-04).
DEFAULT_MIN_GATE_REJECTIONS = 2

# T-0095 pattern: process-internal lock serializing record_incident's
# read-modify-write (load -> append -> save).  Cross-process atomicity is
# covered by the tmp+rename atomic write in _save_incidents.
_RECORD_LOCK = threading.Lock()


class IncidentError(Exception):
    """Base error for incident record / retrieval failures."""


class InvalidIncidentError(IncidentError):
    """Raised when an incident record is malformed or violates the schema."""


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass
class IncidentRecord:
    """One structured incident record.

    Fields:
        incident_id: Deterministic id — SHA-256 over
            category|source_type|source_id|normalized root cause|occurred_at.
            Same fingerprint -> same incident (dedup key).  ``occurred_at``
            is part of the key so that *two occurrences* of the same failure
            class are two distinct incidents (recurrence is detectable by
            loop_core/second_failure.py), while re-recording the *same*
            occurrence is idempotent.
        category: gate_rejection | guard_failure | regression | slo_breach |
            other.
        severity: critical | high | medium | low.
        scope: Human-readable impact scope (what broke / what was affected).
        occurred_at: ISO-8601 UTC timestamp of when the failure occurred.
        discovered_at: ISO-8601 UTC timestamp of when it was discovered.
        resolution: Optional text describing the containment/fix (blameless:
            names actions and mechanisms, never individuals).
        status: open | resolved | closed.
        source_type: gate | guard | task | slo | manual | other.
        source_id: Concrete origin reference (e.g. gate id, guard id).
        title: Optional short title (searchable).
        root_cause: Optional root-cause summary — the normalized fingerprint
            input for second-failure detection (falls back to scope).
        recorded_at: ISO-8601 UTC timestamp of when the record was written.
        schema_version: Incident schema version (INCIDENTS_SCHEMA_VERSION).
    """
    incident_id: str
    category: str
    severity: str
    scope: str
    occurred_at: str
    discovered_at: str
    status: str
    source_type: str
    source_id: str
    title: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: int = INCIDENTS_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "category": self.category,
            "severity": self.severity,
            "scope": self.scope,
            "occurred_at": self.occurred_at,
            "discovered_at": self.discovered_at,
            "status": self.status,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "root_cause": self.root_cause,
            "resolution": self.resolution,
            "recorded_at": self.recorded_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> IncidentRecord:
        if not isinstance(data, dict):
            raise InvalidIncidentError(f"incident 记录格式错误: {data!r}")
        required = (
            "incident_id", "category", "severity", "scope",
            "occurred_at", "discovered_at", "status",
            "source_type", "source_id", "recorded_at",
        )
        for key in required:
            if key not in data or data[key] in (None, ""):
                raise InvalidIncidentError(
                    f"incident 记录缺少必需字段 '{key}'"
                )
        category = str(data["category"])
        severity = str(data["severity"])
        status = str(data["status"])
        source_type = str(data["source_type"])
        if category not in CATEGORIES:
            raise InvalidIncidentError(
                f"category 非法: {category!r}（允许 {CATEGORIES}）"
            )
        if severity not in SEVERITIES:
            raise InvalidIncidentError(
                f"severity 非法: {severity!r}（允许 {SEVERITIES}）"
            )
        if status not in STATUSES:
            raise InvalidIncidentError(
                f"status 非法: {status!r}（允许 {STATUSES}）"
            )
        if source_type not in SOURCE_TYPES:
            raise InvalidIncidentError(
                f"source_type 非法: {source_type!r}（允许 {SOURCE_TYPES}）"
            )
        schema_version = int(
            data.get("schema_version", INCIDENTS_SCHEMA_VERSION)
        )
        if schema_version != INCIDENTS_SCHEMA_VERSION:
            raise InvalidIncidentError(
                f"不支持的 incident schema_version: {schema_version}"
            )
        return cls(
            incident_id=str(data["incident_id"]),
            category=category,
            severity=severity,
            scope=str(data["scope"]),
            occurred_at=str(data["occurred_at"]),
            discovered_at=str(data["discovered_at"]),
            status=status,
            source_type=source_type,
            source_id=str(data["source_id"]),
            title=str(data["title"]) if data.get("title") is not None else None,
            root_cause=(
                str(data["root_cause"]) if data.get("root_cause") is not None
                else None
            ),
            resolution=(
                str(data["resolution"]) if data.get("resolution") is not None
                else None
            ),
            recorded_at=str(data["recorded_at"]),
            schema_version=schema_version,
        )


# ── Fingerprint / Incident Id ──────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Normalize text for fingerprinting: collapse whitespace + casefold."""
    return " ".join(str(text).strip().split()).casefold()


def _cause_text(root_cause: str | None, scope: str) -> str:
    """The root-cause text used for fingerprinting: root_cause if present,
    else the scope — an incident always fingerprints on something."""
    if root_cause is not None and str(root_cause).strip():
        return str(root_cause)
    return scope


def make_incident_id(
    category: str,
    source_type: str,
    source_id: str,
    root_cause: str | None,
    scope: str,
    occurred_at: str | None = None,
) -> str:
    """Deterministic incident id for the given fingerprint.

    Same (category, source_type, source_id, normalized root cause,
    occurred_at) always yields the same incident id — this is the dedup key
    (AC-01).  ``occurred_at`` distinguishes *occurrences*: two failures of
    the same class at different times are two incidents (recurrence), while
    re-recording the same occurrence is idempotent.
    """
    fingerprint = "|".join([
        str(category),
        str(source_type),
        str(source_id),
        _normalize(_cause_text(root_cause, scope)),
        _normalize(occurred_at) if occurred_at else "",
    ])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"IN-{digest[:10].upper()}"


# ── Storage ────────────────────────────────────────────────────────────────


def incidents_path(
    project_root: str | Path,
    relative_path: str | None = None,
) -> Path:
    """Absolute path of the incidents file under the project root."""
    return Path(project_root) / (
        relative_path or DEFAULT_INCIDENTS_RELATIVE_PATH
    )


def load_incidents(
    project_root: str | Path,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """Load all recorded incidents.  Missing / empty file -> empty list.

    Malformed entries fail closed: any record that violates the schema raises
    InvalidIncidentError instead of being silently dropped.
    """
    path = incidents_path(project_root, relative_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise IncidentError(
            f"无法解析 incidents 文件 {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise IncidentError(f"incidents 文件格式错误（非 mapping）: {path}")
    if data.get("schema") not in (None, INCIDENTS_SCHEMA):
        raise IncidentError(
            f"不支持的 incidents schema: {data.get('schema')!r}（{path}）"
        )
    raw_incidents = data.get("incidents", [])
    if not isinstance(raw_incidents, list):
        raise IncidentError(f"incidents 文件格式错误（incidents 非列表）: {path}")
    return [IncidentRecord.from_dict(rec) for rec in raw_incidents]


def _save_incidents(path: Path, incidents: list[IncidentRecord]) -> None:
    """Write all incidents atomically (tmp file + rename), append-style log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": INCIDENTS_SCHEMA,
        "schema_version": INCIDENTS_SCHEMA_VERSION,
        "incidents": [incident.to_dict() for incident in incidents],
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


def record_incident(
    project_root: str | Path,
    *,
    category: str,
    severity: str,
    scope: str,
    source_type: str,
    source_id: str,
    occurred_at: str | None = None,
    discovered_at: str | None = None,
    status: str = STATUS_OPEN,
    resolution: str | None = None,
    title: str | None = None,
    root_cause: str | None = None,
    recorded_at: str | None = None,
    relative_path: str | None = None,
) -> tuple[IncidentRecord, bool]:
    """Record one incident; idempotent for identical fingerprints.

    Args:
        project_root: Project root that contains the .ai/ governance tree.
        category: gate_rejection | guard_failure | regression | slo_breach |
            other.
        severity: critical | high | medium | low.
        scope: Impact scope description (required).
        source_type: gate | guard | task | slo | manual | other.
        source_id: Concrete origin reference, e.g. the gate id.
        occurred_at / discovered_at: Optional ISO-8601 timestamps; default to
            now (UTC).
        status: open | resolved | closed (default open).
        resolution: Optional containment/fix description.
        title: Optional short title.
        root_cause: Optional root-cause summary; feeds the dedup fingerprint
            and second-failure detection (falls back to scope).
        recorded_at: Optional ISO timestamp; defaults to now (UTC).
        relative_path: Override for the incidents file location (tests).

    Returns:
        (incident, created): incident is the stored record — either freshly
        created or the existing duplicate; created is True only when a new
        record was appended.
    """
    if category not in CATEGORIES:
        raise InvalidIncidentError(
            f"category 非法: {category!r}（允许 {CATEGORIES}）"
        )
    if severity not in SEVERITIES:
        raise InvalidIncidentError(
            f"severity 非法: {severity!r}（允许 {SEVERITIES}）"
        )
    if status not in STATUSES:
        raise InvalidIncidentError(
            f"status 非法: {status!r}（允许 {STATUSES}）"
        )
    if source_type not in SOURCE_TYPES:
        raise InvalidIncidentError(
            f"source_type 非法: {source_type!r}（允许 {SOURCE_TYPES}）"
        )
    if not isinstance(scope, str) or not scope.strip():
        raise InvalidIncidentError("scope 不能为空")
    if not isinstance(source_id, str) or not source_id.strip():
        raise InvalidIncidentError("source_id 不能为空")

    now = recorded_at or datetime.now(timezone.utc).isoformat()
    occurred = occurred_at or now

    incident_id = make_incident_id(
        category, source_type, source_id, root_cause, scope, occurred
    )

    # T-0095 pattern: the read-modify-write is serialized by a process-internal
    # lock so concurrent recorders never lose records.  Validation above stays
    # outside the lock.
    with _RECORD_LOCK:
        incidents = load_incidents(project_root, relative_path)
        for existing in incidents:
            if existing.incident_id == incident_id:
                # Same source + same fingerprint (incl. occurrence time) ->
                # idempotent.
                return existing, False

        incident = IncidentRecord(
            incident_id=incident_id,
            category=category,
            severity=severity,
            scope=scope.strip(),
            occurred_at=occurred,
            discovered_at=discovered_at or now,
            status=status,
            source_type=source_type,
            source_id=source_id.strip(),
            title=(
                title.strip()
                if isinstance(title, str) and title.strip()
                else None
            ),
            root_cause=(
                root_cause.strip()
                if isinstance(root_cause, str) and root_cause.strip()
                else None
            ),
            resolution=(
                resolution.strip()
                if isinstance(resolution, str) and resolution.strip()
                else None
            ),
            recorded_at=now,
        )
        _save_incidents(
            incidents_path(project_root, relative_path),
            incidents + [incident],
        )
        return incident, True


# ── Retrieval ──────────────────────────────────────────────────────────────


def by_category(
    project_root: str | Path,
    category: str,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """All incidents of one category, in recording order."""
    if category not in CATEGORIES:
        raise InvalidIncidentError(
            f"category 非法: {category!r}（允许 {CATEGORIES}）"
        )
    return [
        incident for incident in load_incidents(project_root, relative_path)
        if incident.category == category
    ]


def by_status(
    project_root: str | Path,
    status: str,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """All incidents in one lifecycle status (open/resolved/closed)."""
    if status not in STATUSES:
        raise InvalidIncidentError(
            f"status 非法: {status!r}（允许 {STATUSES}）"
        )
    return [
        incident for incident in load_incidents(project_root, relative_path)
        if incident.status == status
    ]


def by_severity(
    project_root: str | Path,
    severity: str,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """All incidents of one severity (critical/high/medium/low)."""
    if severity not in SEVERITIES:
        raise InvalidIncidentError(
            f"severity 非法: {severity!r}（允许 {SEVERITIES}）"
        )
    return [
        incident for incident in load_incidents(project_root, relative_path)
        if incident.severity == severity
    ]


def search(
    project_root: str | Path,
    keyword: str,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """Case-insensitive substring search over incident content.

    Matches incident_id, category, severity, status, scope, title,
    root_cause, resolution, source_type and source_id.  Empty keyword returns
    everything.
    """
    needle = str(keyword).casefold()
    if not needle:
        return load_incidents(project_root, relative_path)
    results: list[IncidentRecord] = []
    for incident in load_incidents(project_root, relative_path):
        haystack = " ".join([
            incident.incident_id,
            incident.category,
            incident.severity,
            incident.status,
            incident.scope,
            incident.title or "",
            incident.root_cause or "",
            incident.resolution or "",
            incident.source_type,
            incident.source_id,
        ]).casefold()
        if needle in haystack:
            results.append(incident)
    return results


def by_source(
    project_root: str | Path,
    source_type: str,
    source_id: str | None = None,
    relative_path: str | None = None,
) -> list[IncidentRecord]:
    """All incidents from one source type (optionally one concrete source id).

    Examples: by_source(root, "gate", "G-T-0005-CLOSEOUT-REVIEW") or
    by_source(root, "guard").
    """
    if source_type not in SOURCE_TYPES:
        raise InvalidIncidentError(
            f"source_type 非法: {source_type!r}（允许 {SOURCE_TYPES}）"
        )
    return [
        incident for incident in load_incidents(project_root, relative_path)
        if incident.source_type == source_type
        and (source_id is None or incident.source_id == source_id)
    ]


# ── gate_lessons integration (AC-04) ──────────────────────────────────────


def register_gate_rejection_incident(
    project_root: str | Path,
    gate_id: str,
    *,
    min_rejections: int = DEFAULT_MIN_GATE_REJECTIONS,
    severity: str = SEVERITY_MEDIUM,
    task_id: str | None = None,
    relative_path: str | None = None,
    lessons_relative_path: str | None = None,
) -> tuple[IncidentRecord | None, bool]:
    """Register a ``gate_rejection`` incident from gate_lessons counters.

    Counts rejected / repair_requested lessons recorded by gate_feedback
    (T-0089) for the given gate; when the count reaches ``min_rejections``
    (default 2 — AC-04) an incident is registered with source_type "gate" and
    source_id = gate_id.  Recording is idempotent: re-running with the same
    count dedups to the existing incident.

    Args:
        project_root: Project root with the .ai/ governance tree.
        gate_id: The gate whose rejection history is counted.
        min_rejections: Rejection count that triggers registration (>= 2).
        severity: Severity for the registered incident (default medium).
        task_id: Optional task context for the incident scope text.
        relative_path: Override for the incidents file location (tests).
        lessons_relative_path: Override for the gate-lessons file location.

    Returns:
        (incident, created): incident is None when the threshold is not yet
        reached; created is True only when a new record was appended.
    """
    if not isinstance(gate_id, str) or not gate_id.strip():
        raise InvalidIncidentError("gate_id 不能为空")
    try:
        threshold = int(min_rejections)
    except (TypeError, ValueError) as exc:
        raise InvalidIncidentError(
            f"min_rejections 非法: {min_rejections!r}"
        ) from exc
    if threshold < 2:
        raise InvalidIncidentError(
            "min_rejections 必须 >= 2（一次拒绝是普通门禁事件，不是 incident）"
        )

    from loop_core.gate_feedback import (
        DECISION_REJECTED,
        DECISION_REPAIR_REQUESTED,
        load_lessons,
    )

    lessons = load_lessons(project_root, lessons_relative_path)
    rejections = [
        lesson for lesson in lessons
        if lesson.gate_id == gate_id
        and lesson.decision in (DECISION_REJECTED, DECISION_REPAIR_REQUESTED)
    ]
    if len(rejections) < threshold:
        return None, False

    count = len(rejections)
    root_cause = f"gate rejection count={count}"
    scope = (
        f"gate {gate_id} 被拒绝 {count} 次（gate_lessons 计数 >= {threshold}，"
        f"重复同类拒绝表明流程性问题未闭环）"
    )
    if task_id:
        scope = f"{scope}（task: {task_id}）"
    # Deterministic occurrence time: the last rejection lesson's recorded_at.
    # Re-running the bridge with the same lessons dedups (same fingerprint);
    # a *new* rejection (newest lesson time moves) is a new occurrence ->
    # a new incident, which the second-failure detector can pair (AC-04 +
    # recurrence).
    occurred_at = max(
        (lesson.recorded_at for lesson in rejections), default=None
    )
    return record_incident(
        project_root,
        category=CATEGORY_GATE_REJECTION,
        severity=severity,
        scope=scope,
        source_type="gate",
        source_id=gate_id,
        title=f"Repeated rejections at {gate_id}",
        root_cause=root_cause,
        occurred_at=occurred_at,
        relative_path=relative_path,
    )
