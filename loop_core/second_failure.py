"""
Second-failure doctrine — recurrence detection + release block (B2 §3.4,
T-0097).

"the second failure is the process's fault" (Amazon COE, B2 §3.1): when the
*same failure class* recurs (same category + same root-cause fingerprint:
source + normalized cause), the loop must not wait for a human to notice.
This module:

1. ``detect_second_failure`` — pure function: group incidents by
   (category, source_type, source_id, normalized root cause); every recurrence
   beyond the first yields a SecondFailureRecord pairing the previous and the
   new occurrence, with a **task draft** (title/scope/reason).  Drafts are
   only persisted to ``.ai/evidence/observability/second-failures.yaml``
   (report level) — they are **never auto-registered into task_graph**
   (T-0097 constraint: drafts need user approval).
2. ``record_second_failure`` — persist detection results idempotently.
3. ``second_failure_block`` — the gate (fail-closed):
       unresolved second failure (its linked retro has NO open action item)
           -> BLOCK with details
       linked retro has an open action item   -> PASS
       linked retro closed (all items done)   -> PASS (loop closed)
       record explicitly resolved             -> PASS
       valid exemption                        -> PASS (SLO-style)
       unparseable evidence                   -> BLOCK (fail-closed)
       missing evidence files                 -> PASS (no records -> nothing
                                                 detected; absence is not
                                                 evidence of failure)
   Toggle: ``LOOP_SECOND_FAILURE_GATE_ENABLED`` env var or
   ``second_failure_gate.enabled`` in config.yaml.  **Default disabled**
   (wave 1 advisory / opt-in): enabling only *adds* blocking conditions,
   never relaxes existing checks.
4. Exemptions mirror slo_gate (T-0093 AC-03): append-only JSON ledger
   ``.ai/evidence/observability/second-failure-exemptions.json`` with
   reason / expires_at / approver; valid while unexpired + approver non-empty.

Referenced by:
- .ai/checkers/second_failure_checker.py — compile_gate-style CLI (0/1/2)
- hooks/scripts/loop_enforcement.py — optional S6 release wiring (opt-in)
- tests/test_learning_loop.py — AC-03
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

import yaml

SECOND_FAILURES_SCHEMA = "second_failures"
SECOND_FAILURES_SCHEMA_VERSION = 1
DEFAULT_SECOND_FAILURES_RELATIVE_PATH = (
    ".ai/evidence/observability/second-failures.yaml"
)

DEFAULT_MIN_RECURRENCES = 2

GATE_DECISION_PASS = "PASS"
GATE_DECISION_BLOCK = "BLOCK"
GATE_STATUS_DISABLED = "DISABLED"
GATE_STATUS_NOT_AVAILABLE = "NOT_AVAILABLE"
GATE_STATUS_BLOCKED = "BLOCKED"
GATE_STATUS_PASS = "PASS"

GATE_BLOCK_CODE = "SECOND_FAILURE_UNRESOLVED"  # B2 §1.5-style blocked_reason code

# Append-only exemption ledger (SLO-style, T-0093 AC-03 pattern).
EXEMPTIONS_REL = Path(".ai") / "evidence" / "observability" / \
    "second-failure-exemptions.json"

# Evidence the gate requires to make a decision (fail-closed: unparseable
# -> BLOCK listing the file; *missing* files are normal — no records).
REQUIRED_EVIDENCE = (
    (".ai/evidence/observability/incidents.yaml", "incident records"),
    (".ai/evidence/observability/retrospectives.yaml", "retrospectives"),
    (".ai/evidence/observability/second-failures.yaml", "second-failure report"),
)

GATE_CONFIG_REL = Path(".zcode") / "skills" / "loop-governance" / "config.yaml"
ENV_ENABLED = "LOOP_SECOND_FAILURE_GATE_ENABLED"

_DISABLED_ENV_VALUES = {"0", "false", "off", "no", "disabled"}
_ENABLED_ENV_VALUES = {"1", "true", "on", "yes", "enabled"}

# T-0095 pattern: process-internal lock serializing report writes.
_RECORD_LOCK = threading.Lock()


class SecondFailureError(Exception):
    """Base error for second-failure record / gate failures."""


class InvalidSecondFailureError(SecondFailureError):
    """Raised when a second-failure record is malformed or violates the schema."""


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass
class SecondFailureRecord:
    """One detected recurrence of a failure class.

    Fields:
        second_failure_id: Deterministic id — SHA-256 over
            first_incident_id|second_incident_id ("SF-" prefix).
        first_incident_id: The earlier occurrence of the same class.
        second_incident_id: The recurring occurrence.
        category: The shared incident category.
        root_cause_fingerprint: The normalized (category, source_type,
            source_id, cause) key that matched.
        source_type / source_id: The shared source.
        task_draft: {title, scope, reason} — the suggested follow-up task.
            Draft only: NEVER auto-registered into task_graph; user approval
            is required.
        status: open | resolved.
        detected_at: ISO-8601 UTC timestamp of detection.
        schema_version: Second-failure schema version.
    """
    second_failure_id: str
    first_incident_id: str
    second_incident_id: str
    category: str
    root_cause_fingerprint: str
    source_type: str
    source_id: str
    task_draft: dict[str, str]
    status: str = "open"
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: int = SECOND_FAILURES_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "second_failure_id": self.second_failure_id,
            "first_incident_id": self.first_incident_id,
            "second_incident_id": self.second_incident_id,
            "category": self.category,
            "root_cause_fingerprint": self.root_cause_fingerprint,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "task_draft": dict(self.task_draft),
            "status": self.status,
            "detected_at": self.detected_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SecondFailureRecord:
        if not isinstance(data, dict):
            raise InvalidSecondFailureError(
                f"second-failure 记录格式错误: {data!r}"
            )
        required = (
            "second_failure_id", "first_incident_id", "second_incident_id",
            "category", "root_cause_fingerprint", "source_type", "source_id",
            "task_draft", "status", "detected_at",
        )
        for key in required:
            if key not in data or data[key] in (None, ""):
                raise InvalidSecondFailureError(
                    f"second-failure 记录缺少必需字段 '{key}'"
                )
        status = str(data["status"])
        if status not in ("open", "resolved"):
            raise InvalidSecondFailureError(
                f"second-failure status 非法: {status!r}（允许 open/resolved）"
            )
        draft = data["task_draft"]
        if not isinstance(draft, dict) or not all(
            draft.get(k) for k in ("title", "scope", "reason")
        ):
            raise InvalidSecondFailureError(
                f"task_draft 非法: {draft!r}（需要 title/scope/reason）"
            )
        schema_version = int(
            data.get("schema_version", SECOND_FAILURES_SCHEMA_VERSION)
        )
        if schema_version != SECOND_FAILURES_SCHEMA_VERSION:
            raise InvalidSecondFailureError(
                f"不支持的 second-failure schema_version: {schema_version}"
            )
        return cls(
            second_failure_id=str(data["second_failure_id"]),
            first_incident_id=str(data["first_incident_id"]),
            second_incident_id=str(data["second_incident_id"]),
            category=str(data["category"]),
            root_cause_fingerprint=str(data["root_cause_fingerprint"]),
            source_type=str(data["source_type"]),
            source_id=str(data["source_id"]),
            task_draft={k: str(v) for k, v in draft.items()},
            status=status,
            detected_at=str(data["detected_at"]),
            schema_version=schema_version,
        )


@dataclass(frozen=True)
class SecondFailureGateResult:
    """Outcome of one second-failure gate evaluation.

    ``decision`` is PASS or BLOCK.  ``blocking`` carries per-record detail
    (ids, category, why) when the gate blocks; ``exemption`` the overriding
    exemption when one is in effect; ``gate_enabled`` False when the toggle
    is off (advisory mode).
    """
    decision: str
    reason: str
    status: str
    blocking: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    exemption: dict[str, Any] | None = None
    gate_enabled: bool = True

    @property
    def passed(self) -> bool:
        return self.decision == GATE_DECISION_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "checker_id": "second_failure",
            "decision": self.decision,
            "passed": self.passed,
            "reason": self.reason,
            "status": self.status,
            "blocking": list(self.blocking),
            "warnings": list(self.warnings),
            "notes": list(self.notes),
            "exemption": self.exemption,
            "gate_enabled": self.gate_enabled,
        }


# ── Toggle ─────────────────────────────────────────────────────────────────


def second_failure_gate_enabled(
    root: str | Path, env: dict[str, str] | None = None
) -> bool:
    """Resolve the ``second_failure_gate.enabled`` switch.

    Priority: ``LOOP_SECOND_FAILURE_GATE_ENABLED`` env var (explicit value
    wins) then ``second_failure_gate.enabled`` in the loop-governance
    config.yaml; **default False** (wave 1 advisory / opt-in — the gate only
    adds blocking conditions when a project explicitly enables it).  A
    missing/corrupt config falls back to the default.
    """
    env = dict(os.environ) if env is None else env
    raw = (env.get(ENV_ENABLED) or "").strip().lower()
    if raw in _ENABLED_ENV_VALUES:
        return True
    if raw in _DISABLED_ENV_VALUES:
        return False
    cfg_path = Path(root) / GATE_CONFIG_REL
    try:
        doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    except Exception:
        doc = {}
    if isinstance(doc, dict):
        section = doc.get("second_failure_gate")
        if isinstance(section, dict) and "enabled" in section:
            return bool(section["enabled"])
    return False


# ── Detection (pure) ───────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Normalize text for fingerprinting: collapse whitespace + casefold."""
    return " ".join(str(text).strip().split()).casefold()


def _cause_text(incident: Any) -> str:
    """Root-cause text of an incident for fingerprinting (root_cause if
    present, else scope — mirrors loop_core.incidents._cause_text)."""
    cause = getattr(incident, "root_cause", None)
    if cause is not None and str(cause).strip():
        return str(cause)
    return str(getattr(incident, "scope", ""))


def root_cause_fingerprint(incident: Any) -> str:
    """The (category, source_type, source_id, normalized cause) key.

    Two incidents with the same key are the same failure class — this is the
    recurrence definition (AC-03: 同类别 + 同根因指纹（来源+归一化原因）).
    """
    return "|".join([
        str(getattr(incident, "category", "")),
        str(getattr(incident, "source_type", "")),
        str(getattr(incident, "source_id", "")),
        _normalize(_cause_text(incident)),
    ])


def make_second_failure_id(
    first_incident_id: str, second_incident_id: str
) -> str:
    """Deterministic id for one recurrence pair (dedup key)."""
    fingerprint = "|".join([str(first_incident_id), str(second_incident_id)])
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"SF-{digest[:8].upper()}"


def _task_draft(
    first: Any, second: Any, fingerprint: str
) -> dict[str, str]:
    """The suggested follow-up task draft (title/scope/reason).

    Draft only — NEVER auto-registered into task_graph (T-0097 constraint):
    the user must approve before the draft becomes a real task.
    """
    first_id = str(getattr(first, "incident_id", "?"))
    second_id = str(getattr(second, "incident_id", "?"))
    category = str(getattr(second, "category", "other"))
    source_id = str(getattr(second, "source_id", ""))
    return {
        "title": (
            f"[draft] Fix recurring {category} ({source_id}) "
            f"— second failure"
        ),
        "scope": (
            f"Second-failure doctrine (B2 §3.4): 同类别 + 同根因指纹复发，"
            f"先例 {first_id} → 复发 {second_id}（fingerprint: "
            f"{fingerprint}）。范围：消除该失败类的根因，并加机器可验证的"
            f"回归防护（测试/fixture/审计）。"
        ),
        "reason": (
            f"同类别 {category}、同根因指纹（来源 {source_id}）第二次发生："
            f"{first_id} → {second_id}。按 second-failure doctrine，第二次失败"
            f"是流程的失败，需要 owner 行动项。任务草稿须经用户批准后才能"
            f"登记 task_graph（T-0097：不自动登记）。"
        ),
    }


def detect_second_failure(
    incidents: list[Any],
    min_recurrences: int = DEFAULT_MIN_RECURRENCES,
) -> list[SecondFailureRecord]:
    """Detect recurrences: same category + same root-cause fingerprint.

    Pure function over incident records in recording order.  Every occurrence
    at index >= (min_recurrences - 1) of a class yields one
    SecondFailureRecord pairing it with the immediately previous occurrence.
    Records keep incident recording order.
    """
    try:
        threshold = int(min_recurrences)
    except (TypeError, ValueError) as exc:
        raise InvalidSecondFailureError(
            f"min_recurrences 非法: {min_recurrences!r}"
        ) from exc
    if threshold < 2:
        raise InvalidSecondFailureError(
            "min_recurrences 必须 >= 2（第一次发生是教训，第二次才是复发）"
        )

    groups: dict[str, list[Any]] = {}
    for incident in incidents:
        groups.setdefault(root_cause_fingerprint(incident), []).append(incident)

    records: list[SecondFailureRecord] = []
    for fingerprint, occurrences in groups.items():
        for index in range(threshold - 1, len(occurrences)):
            first = occurrences[index - 1]
            second = occurrences[index]
            records.append(SecondFailureRecord(
                second_failure_id=make_second_failure_id(
                    str(getattr(first, "incident_id", "?")),
                    str(getattr(second, "incident_id", "?")),
                ),
                first_incident_id=str(getattr(first, "incident_id", "?")),
                second_incident_id=str(getattr(second, "incident_id", "?")),
                category=str(getattr(second, "category", "other")),
                root_cause_fingerprint=fingerprint,
                source_type=str(getattr(second, "source_type", "")),
                source_id=str(getattr(second, "source_id", "")),
                task_draft=_task_draft(first, second, fingerprint),
            ))
    return records


# ── Persistence (report level) ─────────────────────────────────────────────


def second_failures_path(
    project_root: str | Path,
    relative_path: str | None = None,
) -> Path:
    """Absolute path of the second-failure report under the project root."""
    return Path(project_root) / (
        relative_path or DEFAULT_SECOND_FAILURES_RELATIVE_PATH
    )


def load_second_failures(
    project_root: str | Path,
    relative_path: str | None = None,
) -> list[SecondFailureRecord]:
    """Load the second-failure report.  Missing / empty file -> empty list.

    Malformed entries fail closed (InvalidSecondFailureError).
    """
    path = second_failures_path(project_root, relative_path)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise SecondFailureError(
            f"无法解析 second-failures 文件 {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise SecondFailureError(
            f"second-failures 文件格式错误（非 mapping）: {path}"
        )
    if data.get("schema") not in (None, SECOND_FAILURES_SCHEMA):
        raise SecondFailureError(
            f"不支持的 second-failures schema: {data.get('schema')!r}（{path}）"
        )
    raw = data.get("second_failures", [])
    if not isinstance(raw, list):
        raise SecondFailureError(
            f"second-failures 文件格式错误（second_failures 非列表）: {path}"
        )
    return [SecondFailureRecord.from_dict(rec) for rec in raw]


def _save_second_failures(
    path: Path, records: list[SecondFailureRecord]
) -> None:
    """Write the report atomically (tmp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SECOND_FAILURES_SCHEMA,
        "schema_version": SECOND_FAILURES_SCHEMA_VERSION,
        "second_failures": [record.to_dict() for record in records],
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


def record_second_failure(
    project_root: str | Path,
    incidents: list[Any] | None = None,
    min_recurrences: int = DEFAULT_MIN_RECURRENCES,
    relative_path: str | None = None,
) -> tuple[list[SecondFailureRecord], list[bool]]:
    """Detect recurrences and persist new records to the report.

    Idempotent: a recurrence pair already in the report is never duplicated
    (dedup key = second_failure_id).  Loads incidents from
    ``.ai/evidence/observability/incidents.yaml`` when not passed in.

    Returns:
        (all_records, created_flags) — created_flags aligned with
        all_records (True where the record was newly appended).
    """
    if incidents is None:
        from loop_core.incidents import load_incidents
        incidents = load_incidents(project_root)
    detected = detect_second_failure(incidents, min_recurrences)

    with _RECORD_LOCK:
        path = second_failures_path(project_root, relative_path)
        existing = load_second_failures(project_root, relative_path)
        existing_ids = {record.second_failure_id for record in existing}
        created_flags: list[bool] = []
        merged: list[SecondFailureRecord] = []
        for record in detected:
            if record.second_failure_id in existing_ids:
                created_flags.append(False)
                continue
            existing_ids.add(record.second_failure_id)
            created_flags.append(True)
            merged.append(record)
        if merged:
            _save_second_failures(path, existing + merged)
        return existing + merged, created_flags


def resolve_second_failure(
    project_root: str | Path,
    second_failure_id: str,
    resolved_at: str | None = None,
    relative_path: str | None = None,
) -> SecondFailureRecord:
    """Explicitly resolve a second-failure record (status -> resolved).

    The report is a derived artifact, so status updates are allowed (unlike
    the append-only incident ledger).  Resolution also happens automatically
    when the linked retro closes (all action items done) — see
    ``second_failure_block``.
    """
    with _RECORD_LOCK:
        path = second_failures_path(project_root, relative_path)
        records = load_second_failures(project_root, relative_path)
        target = next(
            (r for r in records if r.second_failure_id == second_failure_id),
            None,
        )
        if target is None:
            raise SecondFailureError(
                f"second-failure 记录不存在: {second_failure_id}"
            )
        target.status = "resolved"
        _save_second_failures(path, records)
        return target


# ── Exemptions (SLO-style) ─────────────────────────────────────────────────


def load_exemptions(root: str | Path) -> list[dict[str, Any]]:
    """Read the append-only exemption ledger.  Missing file -> [].

    Unparseable file raises SecondFailureError — the gate treats that as "no
    valid exemption" (fail-closed: an unreadable override cannot override),
    while ``record_second_failure_exemption`` refuses to append to a corrupt
    ledger.
    """
    path = Path(root) / EXEMPTIONS_REL
    if not path.exists():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SecondFailureError(
            f"second-failure-exemptions.json unparseable: {path}: {exc}"
        ) from exc
    records = doc.get("exemptions") if isinstance(doc, dict) else None
    if not isinstance(records, list):
        raise SecondFailureError(
            f"second-failure-exemptions.json has no 'exemptions' list: {path}"
        )
    return [r for r in records if isinstance(r, dict)]


def _next_exemption_id(records: list[dict[str, Any]]) -> str:
    highest = 0
    for r in records:
        rid = str(r.get("id", ""))
        if rid.startswith("SF-EX-"):
            try:
                highest = max(highest, int(rid[len("SF-EX-"):]))
            except ValueError:
                continue
    return f"SF-EX-{highest + 1:04d}"


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO date or datetime into a timezone-aware datetime (UTC for
    naive / date-only values)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            d = date.fromisoformat(text)
        except ValueError:
            return None
        return datetime.combine(d, time.min, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def record_second_failure_exemption(
    project_root: str | Path, reason: str, expires_at: str, approver: str
) -> dict[str, Any]:
    """Append one exemption record to the append-only ledger.

    Validation (SLO-style, T-0093 AC-03): ``reason`` non-empty, ``approver``
    non-empty (an exemption must be explicitly approved by a named actor),
    ``expires_at`` a parseable ISO-8601 timestamp.  A past ``expires_at`` is
    recordable but immediately invalid for the gate.  Returns the recorded
    entry.  Raises ValueError on invalid arguments and SecondFailureError
    when the existing ledger cannot be read (never overwrite a corrupt
    append-only record).
    """
    reason = str(reason or "").strip()
    approver = str(approver or "").strip()
    if not reason:
        raise ValueError(
            "record_second_failure_exemption: reason is required (non-empty)"
        )
    if not approver:
        raise ValueError(
            "record_second_failure_exemption: approver is required "
            "(an exemption must be explicitly approved)"
        )
    expires = _parse_dt(expires_at)
    if expires is None:
        raise ValueError(
            f"record_second_failure_exemption: expires_at unparseable: "
            f"{expires_at!r}"
        )

    root_path = Path(project_root)
    path = root_path / EXEMPTIONS_REL
    records = load_exemptions(root_path)  # corrupt ledger -> raises, no append
    entry = {
        "id": _next_exemption_id(records),
        "reason": reason,
        "expires_at": expires.astimezone(timezone.utc).isoformat(),
        "approver": approver,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"schema_version": 1, "exemptions": [*records, entry]}
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return entry


def _valid_exemption(
    records: list[dict[str, Any]], now: datetime
) -> tuple[dict[str, Any] | None, list[str]]:
    """First valid exemption (expires_at > now, approver non-empty) plus
    warnings about entries considered and rejected."""
    warnings: list[str] = []
    for r in records:
        expires = _parse_dt(r.get("expires_at"))
        approver = str(r.get("approver") or "").strip()
        if not approver:
            warnings.append(
                f"exemption {r.get('id', '?')} has no approver — invalid"
            )
            continue
        if expires is None:
            warnings.append(
                f"exemption {r.get('id', '?')} has unparseable expires_at — "
                f"invalid"
            )
            continue
        if expires <= now:
            warnings.append(
                f"exemption {r.get('id', '?')} expired at "
                f"{expires.isoformat()} — no longer effective"
            )
            continue
        return r, warnings
    return None, warnings


# ── Gate ───────────────────────────────────────────────────────────────────


def _disabled_result() -> SecondFailureGateResult:
    """Gate disabled result（T-0124 拆分：实现移至 second_failure_gate 外部模块）。"""
    from loop_core.second_failure_gate import _disabled_result as _impl
    return _impl()


def _data_insufficient(missing: list[str]) -> SecondFailureGateResult:
    """Data-insufficient fail-closed result（T-0124 拆分：委托外部模块）。"""
    from loop_core.second_failure_gate import _data_insufficient as _impl
    return _impl(missing)


def _linked_retro(retros: list[Any], record: SecondFailureRecord) -> Any | None:
    """The retro associated with a second failure: prefer the retro of the
    second (recurring) incident, fall back to the first incident's retro.
    （T-0124 拆分：委托外部模块）"""
    from loop_core.second_failure_gate import _linked_retro as _impl
    return _impl(retros, record)


def second_failure_block(
    project_root: str | Path,
    now: datetime | None = None,
) -> SecondFailureGateResult:
    """Evaluate the second-failure gate (fail-closed, B2 §3.4).

    Decision table:
      toggle disabled                       -> PASS (DISABLED, advisory)
      any required evidence unparseable     -> BLOCK (NOT_AVAILABLE, files
                                               listed)
      no second-failure records             -> PASS
      every blocking record's linked retro
        has an open action item             -> PASS (owned plan exists)
      linked retro closed (all items done)  -> PASS for that record (loop
                                               closed — completion closes the
                                               failure)
      record explicitly resolved            -> PASS for that record
      record unresolved (no retro, or retro
        with no open action items)          -> BLOCK (SECOND_FAILURE_UNRESOLVED
                                               + per-record detail)
      valid exemption                       -> PASS (reason names exemption)

    Missing evidence *files* are normal (no incidents recorded yet) and do
    not block — absence of records is not evidence; unparseable evidence is.
    """
    # T-0124 拆分：主判定链移至 second_failure_gate 外部模块（行为等价；
    # 函数内 import 保持模块 dir() 逐名一致）
    from loop_core.second_failure_gate import second_failure_block as _impl
    return _impl(project_root, now)
