"""second_failure_gate.py — second-failure gate 判定外部模块（T-0124 拆分）。

从 loop_core/second_failure.py 拆出：`_disabled_result` / `_data_insufficient` /
`_linked_retro` / `second_failure_block`（主判定链）。壳文件保留同名函数
（函数内委托），本模块对壳符号一律**函数内延迟 import**（避免循环导入，
模块加载完成后再解析）。行为逐字节等价。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _disabled_result():
    """Gate disabled result（原实现；符号延迟取自壳模块）。"""
    from loop_core.second_failure import (
        GATE_DECISION_PASS,
        GATE_STATUS_DISABLED,
        SecondFailureGateResult,
    )
    return SecondFailureGateResult(
        decision=GATE_DECISION_PASS,
        reason=(
            "second-failure gate disabled by config/env "
            "(LOOP_SECOND_FAILURE_GATE_ENABLED or second_failure_gate."
            "enabled=true required) — advisory-only mode, no block applied"
        ),
        status=GATE_STATUS_DISABLED,
        gate_enabled=False,
        notes=[
            "B2 §3.4 wave 1 advisory: second-failure blocks are opt-in; "
            "enabling only adds blocking conditions, never relaxes checks"
        ],
    )


def _data_insufficient(missing: list[str]):
    """Data-insufficient fail-closed result（原实现；符号延迟取自壳模块）。"""
    from loop_core.second_failure import (
        GATE_DECISION_BLOCK,
        GATE_STATUS_NOT_AVAILABLE,
        SecondFailureGateResult,
    )
    return SecondFailureGateResult(
        decision=GATE_DECISION_BLOCK,
        reason=(
            "data insufficient (fail-closed): cannot verify second-failure "
            "state — unparseable required source(s): " + "; ".join(missing)
        ),
        status=GATE_STATUS_NOT_AVAILABLE,
        blocking=[{"error": f"unparseable evidence: {m}"} for m in missing],
    )


def _linked_retro(retros: list[Any], record) -> Any | None:
    """The retro associated with a second failure: prefer the retro of the
    second (recurring) incident, fall back to the first incident's retro."""
    for retro in retros:
        if retro.incident_id == record.second_incident_id:
            return retro
    for retro in retros:
        if retro.incident_id == record.first_incident_id:
            return retro
    return None


def second_failure_block(
    project_root: str | Path,
    now: datetime | None = None,
):
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
    from loop_core.second_failure import (
        GATE_BLOCK_CODE,
        GATE_DECISION_BLOCK,
        GATE_DECISION_PASS,
        GATE_STATUS_BLOCKED,
        GATE_STATUS_PASS,
        SecondFailureError,
        SecondFailureGateResult,
        _valid_exemption,
        load_exemptions,
        load_second_failures,
        second_failure_gate_enabled,
    )

    root = Path(project_root)
    now = now if now is not None else datetime.now(timezone.utc)

    if not second_failure_gate_enabled(root):
        return _disabled_result()

    missing: list[str] = []
    try:
        from loop_core.incidents import load_incidents
        from loop_core.retrospectives import load_retrospectives

        incidents = load_incidents(root)
        retros = load_retrospectives(root)
        records = load_second_failures(root)
    except Exception as exc:
        missing.append(f"{type(exc).__name__}: {exc}")
    if missing:
        return _data_insufficient(missing)
    if incidents is None or retros is None or records is None:  # pragma: no cover
        return _data_insufficient(["evidence load failed"])

    blocking: list[dict[str, Any]] = []
    notes: list[str] = []
    for record in records:
        if record.status == "resolved":
            notes.append(
                f"second failure {record.second_failure_id} explicitly "
                f"resolved — not blocking"
            )
            continue
        retro = _linked_retro(retros, record)
        if retro is not None and getattr(retro, "status", "open") == "closed":
            notes.append(
                f"second failure {record.second_failure_id}: linked retro "
                f"{retro.retro_id} closed (all action items done) — loop "
                f"closed, not blocking"
            )
            continue
        open_items = [
            item for item in getattr(retro, "action_items", [])
            if getattr(item, "status", "") == "open"
        ] if retro is not None else []
        if open_items:
            notes.append(
                f"second failure {record.second_failure_id}: linked retro "
                f"{retro.retro_id} has {len(open_items)} open action item(s) "
                f"(owner(s): {', '.join(item.owner for item in open_items)}) "
                f"— owned plan exists, not blocking"
            )
            continue
        blocking.append({
            "second_failure_id": record.second_failure_id,
            "first_incident_id": record.first_incident_id,
            "second_incident_id": record.second_incident_id,
            "category": record.category,
            "source_id": record.source_id,
            "reason": (
                "unresolved second failure: no open action item in the "
                "linked retrospective"
                + (f" (linked retro {retro.retro_id} has no open items)"
                   if retro is not None else " (no retrospective yet)")
            ),
            "task_draft": dict(record.task_draft),
        })

    exemption: dict[str, Any] | None = None
    exemption_warnings: list[str] = []
    try:
        exemption, exemption_warnings = _valid_exemption(
            load_exemptions(root), now
        )
    except SecondFailureError as exc:
        exemption_warnings = [str(exc)]

    if blocking:
        decision = GATE_DECISION_BLOCK
        reason = (
            f"{GATE_BLOCK_CODE}: {len(blocking)} unresolved second "
            f"failure(s) — the phase cannot promote until an owned, dated "
            f"action item exists for each recurring class: "
            + "; ".join(
                f"{b['second_failure_id']} ({b['category']} @ "
                f"{b['source_id']}, {b['first_incident_id']} -> "
                f"{b['second_incident_id']})" for b in blocking
            )
        )
        status = GATE_STATUS_BLOCKED
        if exemption is not None:
            decision = GATE_DECISION_PASS
            reason = (
                f"exemption {exemption['id']} in effect (approver="
                f"{exemption['approver']}, expires {exemption['expires_at']}) "
                f"— release allowed: {exemption['reason']}"
            )
            notes.append(
                f"valid exemption {exemption['id']} overrode "
                f"{len(blocking)} unresolved second failure(s)"
            )
            status = GATE_STATUS_PASS
    else:
        decision = GATE_DECISION_PASS
        reason = (
            "no unresolved second failure — all recurring classes have an "
            "owned, dated action item or a closed loop"
        )
        status = GATE_STATUS_PASS
        if exemption is not None:
            notes.append(
                f"valid exemption {exemption['id']} present (no block anyway)"
            )

    return SecondFailureGateResult(
        decision=decision,
        reason=reason,
        status=status,
        blocking=blocking,
        warnings=list(exemption_warnings),
        notes=notes,
        exemption=exemption,
        gate_enabled=True,
    )
