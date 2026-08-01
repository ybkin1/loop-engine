"""
SLO gate — wave 2 release freeze (T-0093, B2 §1.4/§1.5).

Turns D2's *advisory* error-budget accounting (T-0090,
``governance_metrics.compute_error_budget`` → FREEZE_RECOMMENDED) into an
*enforced* release gate:

    budget HEALTHY       -> PASS
    budget CONSUMING     -> PASS (warning attached)
    budget FREEZE        -> BLOCK (ERROR_BUDGET_EXHAUSTED + budget detail)
    data insufficient    -> BLOCK (fail-closed; missing sources listed)
    gate disabled        -> PASS (note attached)

This is a new constraint on top of the existing checks — it never relaxes any
of them (T-0093 AC-06).  The gate only ever adds blocking conditions to the
release path.

Exemptions (T-0093 AC-03):
    ``record_slo_exemption()`` appends to
    ``.ai/evidence/observability/slo-exemptions.json`` (append-only — entries
    are never modified or deleted).  An exemption is *valid* while
    ``expires_at > now`` and ``approver`` is non-empty; a valid exemption
    turns a FREEZE decision into PASS (the reason names the exemption).  An
    expired exemption has no effect — the base decision stands (re-BLOCK).

Recovery (T-0093 AC-04):
    The budget is computed over a window when one is configured (explicit
    ``window`` argument, or ``window_start``/``window_end`` from
    ``.ai/slo.yaml``).  A window rollover therefore resets the budget and the
    gate auto-passes once the current window is healthy.

Data-completeness policy (fail-closed, B2 §2.5):
    The gate can decide only if the *budget-feeding* sources are readable:
    ``.ai/gates.yaml``, ``.ai/task_graph.yaml`` and
    ``.ai/evidence/observability/guard-events.jsonl``.  A missing or
    unparseable required source makes the gate BLOCK with the missing sources
    listed — never a guessed budget (never a silent zero).  Sources that are
    documented wave-2 wiring items (``phase_transitions.jsonl``,
    ``guard_decisions.jsonl``, ``runtime-events.jsonl``) are *not* gate
    inputs: their SLIs are reported as NOT_AVAILABLE in the warnings but
    cannot deadlock the gate, exactly as in D2's budget accounting
    (``compute_error_budget`` only sums computed SLI consumption).
    An SLI that is NOT_AVAILABLE *with its source present* (e.g. no decided
    gates in a phase) is likewise not a gate failure — it contributes zero
    consumption and is surfaced in the warnings.

Toggle (T-0093 AC-02):
    Default enabled (B2 wave 2 enforced).  Disable via environment variable
    ``LOOP_SLO_GATE_ENABLED=0|false|off|no`` (wins) or via
    ``.zcode/skills/loop-governance/config.yaml``:

        slo_gate:
          enabled: false

    When disabled the gate returns PASS with a note — advisory-only mode.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from loop_core.governance_metrics import (
    BUDGET_CONSUMING,
    BUDGET_FREEZE_RECOMMENDED,
    BUDGET_HEALTHY,
    NOT_AVAILABLE,
    SEVERITY_BUDGET,
    DataSourceUnavailableError,
    SliContext,
    _parse_dt,
    compute_error_budget,
    evaluate_sli,
    load_gates,
    load_guard_events,
    load_slo_config,
    load_tasks,
    rework_cycles_from_gates,
)

# ── Public constants ─────────────────────────────────────────────────────

GATE_DECISION_PASS = "PASS"
GATE_DECISION_BLOCK = "BLOCK"
GATE_STATUS_DISABLED = "DISABLED"
GATE_STATUS_NOT_AVAILABLE = "NOT_AVAILABLE"

GATE_BLOCK_CODE = "ERROR_BUDGET_EXHAUSTED"   # B2 §1.5 blocked_reason code

# Append-only exemption ledger (T-0093 AC-03).  Relative to project root.
EXEMPTIONS_REL = Path(".ai") / "evidence" / "observability" / "slo-exemptions.json"

# Budget-feeding data sources the gate requires to make a decision
# (fail-closed: missing/unparseable -> BLOCK with the sources listed).
REQUIRED_SOURCES: tuple[tuple[str, str], ...] = (
    (".ai/gates.yaml", "gates register"),
    (".ai/task_graph.yaml", "task graph"),
    (".ai/evidence/observability/guard-events.jsonl", "guard events"),
)

GATE_CONFIG_REL = Path(".zcode") / "skills" / "loop-governance" / "config.yaml"
ENV_ENABLED = "LOOP_SLO_GATE_ENABLED"

_DISABLED_ENV_VALUES = {"0", "false", "off", "no", "disabled"}
_ENABLED_ENV_VALUES = {"1", "true", "on", "yes", "enabled"}


# ── Toggle ───────────────────────────────────────────────────────────────


def slo_gate_enabled(root: str | Path, env: dict[str, str] | None = None) -> bool:
    """Resolve the ``slo_gate_enabled`` switch.

    Priority: ``LOOP_SLO_GATE_ENABLED`` env var (explicit value wins) then
    ``slo_gate.enabled`` in the loop-governance config.yaml; default True
    (B2 wave 2 enforced).  A missing/corrupt config falls back to the
    default — never guessed from partial data.
    """
    env = dict(os.environ) if env is None else env
    raw = (env.get(ENV_ENABLED) or "").strip().lower()
    if raw in _DISABLED_ENV_VALUES:
        return False
    if raw in _ENABLED_ENV_VALUES:
        return True
    cfg_path = Path(root) / GATE_CONFIG_REL
    try:
        doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    except Exception:
        doc = {}
    if isinstance(doc, dict):
        section = doc.get("slo_gate")
        if isinstance(section, dict) and "enabled" in section:
            return bool(section["enabled"])
    return True


# ── Exemptions ───────────────────────────────────────────────────────────


def load_exemptions(root: str | Path) -> list[dict[str, Any]]:
    """Read the append-only exemption ledger.

    A missing file is the normal state and yields ``[]``.  An unparseable
    file raises DataSourceUnavailableError — the gate treats that as "no
    valid exemption" (fail-closed: an unreadable override cannot override),
    while ``record_slo_exemption`` refuses to append to a corrupt ledger.
    """
    path = Path(root) / EXEMPTIONS_REL
    if not path.exists():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataSourceUnavailableError(
            f"slo-exemptions.json unparseable: {path}: {exc}"
        ) from exc
    records = doc.get("exemptions") if isinstance(doc, dict) else None
    if not isinstance(records, list):
        raise DataSourceUnavailableError(
            f"slo-exemptions.json has no 'exemptions' list: {path}"
        )
    return [r for r in records if isinstance(r, dict)]


def _next_exemption_id(records: list[dict[str, Any]]) -> str:
    highest = 0
    for r in records:
        rid = str(r.get("id", ""))
        if rid.startswith("SLO-EX-"):
            try:
                highest = max(highest, int(rid[len("SLO-EX-"):]))
            except ValueError:
                continue
    return f"SLO-EX-{highest + 1:04d}"


def record_slo_exemption(project_root: str | Path, reason: str,
                         expires_at: str, approver: str) -> dict[str, Any]:
    """Append one exemption record to the append-only ledger.

    Validation (T-0093 AC-03): ``reason`` non-empty, ``approver`` non-empty
    (an exemption must be explicitly approved by a named actor), and
    ``expires_at`` a parseable ISO-8601 timestamp.  A past ``expires_at`` is
    recordable but immediately invalid for the gate (that is how expiry is
    observed).  Returns the recorded entry.

    Raises ValueError on invalid arguments and DataSourceUnavailableError
    when the existing ledger cannot be read (never overwrite a corrupt
    append-only record).
    """
    reason = str(reason or "").strip()
    approver = str(approver or "").strip()
    if not reason:
        raise ValueError("record_slo_exemption: reason is required (non-empty)")
    if not approver:
        raise ValueError(
            "record_slo_exemption: approver is required "
            "(an exemption must be explicitly approved)"
        )
    expires = _parse_dt(expires_at)
    if expires is None:
        raise ValueError(
            f"record_slo_exemption: expires_at unparseable: {expires_at!r}"
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


def _valid_exemption(records: list[dict[str, Any]],
                     now: datetime) -> tuple[dict[str, Any] | None, list[str]]:
    """First valid exemption (expires_at > now, approver non-empty) plus
    warnings about entries that were considered and rejected."""
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
                f"exemption {r.get('id', '?')} has unparseable expires_at — invalid"
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


# ── Gate result ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SloGateResult:
    """Outcome of one SLO gate evaluation.

    ``decision`` is PASS or BLOCK.  ``budget`` carries the D2 budget detail
    (status/consumed/remaining/total) when computable, else None.  ``status``
    is the budget status, NOT_AVAILABLE (data insufficient), or DISABLED.
    """
    decision: str
    reason: str
    budget: dict[str, Any] | None
    status: str
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    exemption: dict[str, Any] | None = None
    gate_enabled: bool = True

    @property
    def passed(self) -> bool:
        return self.decision == GATE_DECISION_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "checker_id": "slo_gate",
            "decision": self.decision,
            "passed": self.passed,
            "reason": self.reason,
            "status": self.status,
            "budget": self.budget,
            "missing": list(self.missing),
            "warnings": list(self.warnings),
            "notes": list(self.notes),
            "exemption": self.exemption,
            "gate_enabled": self.gate_enabled,
        }


# ── Windowed budget computation ──────────────────────────────────────────


def _window_bounds(slo_config: dict[str, Any],
                   window: tuple[str, str] | None) -> tuple[datetime | None, datetime | None]:
    """Resolve the budget window: explicit argument wins, then the slo.yaml
    window_start/window_end, else no bounds (all data — D2 default)."""
    if window is not None:
        return _parse_dt(window[0]), _parse_dt(window[1])
    configured = slo_config.get("window")
    if configured and configured[0] and configured[1]:
        return _parse_dt(configured[0]), _parse_dt(configured[1])
    return None, None


def _compute_gate_budget(root: Path, slo_config: dict[str, Any],
                         window: tuple[str, str] | None,
                         releases: int) -> tuple[dict[str, Any], list[str], list[str]]:
    """Compute the error budget over the budget-feeding sources.

    Returns (budget, missing_sources, warnings).  Any required source that is
    missing or unparseable lands in ``missing_sources`` — the caller must
    then BLOCK (fail-closed).  NOT_AVAILABLE *SLIs* (source present, e.g. no
    decided gates in a phase, or a documented not-yet-wired SLI) do not block;
    they contribute zero consumption, exactly as in D2's accounting, and are
    surfaced in the warnings.
    """
    start, end = _window_bounds(slo_config, window)

    data: dict[str, Any] = {}
    missing: list[str] = []
    for rel, what in REQUIRED_SOURCES:
        try:
            if what == "gates register":
                data["gates"] = load_gates(root, since=start)
            elif what == "task graph":
                data["tasks"] = load_tasks(root)
            else:
                data["guard_events"] = load_guard_events(root)
        except DataSourceUnavailableError as exc:
            data["gates" if what == "gates register" else
                 "tasks" if what == "task graph" else "guard_events"] = None
            missing.append(f"{what} ({rel}): {exc}")

    if missing:
        return {}, missing, []

    gates = data["gates"]
    tasks = data["tasks"]
    events = data["guard_events"]

    # Window upper bound: events/gates recorded after the window end are not
    # part of the window's budget (D2's load_gates only filters by ``since``).
    if end is not None:
        gates = [g for g in gates if g.recorded_at is None or g.recorded_at <= end]
        events = [e for e in events
                  if (ts := _parse_dt(e.timestamp)) is None or ts <= end]
    if start is not None:
        events = [e for e in events
                  if (ts := _parse_dt(e.timestamp)) is None or ts >= start]

    ctx = SliContext(
        gates=gates,
        tasks=tasks,
        transitions=None,
        guard_events=events,
        executions=None,
        drift_events=None,
        guard_decisions=None,
        rework_by_task=rework_cycles_from_gates(gates),
        rework_total=sum(rework_cycles_from_gates(gates).values()),
        completed_tasks=len([t for t in tasks if t.status == "completed"]),
    )

    warnings: list[str] = []
    sli_results: list[dict[str, Any]] = []
    for sli in slo_config["slos"]:
        if sli.get("severity") != SEVERITY_BUDGET:
            continue  # hard-gate / informational SLIs are not budget-consuming
        result = evaluate_sli(sli, ctx)
        sli_results.append(result)
        if result.get("status") == NOT_AVAILABLE:
            warnings.append(
                f"sli:{result['sli_id']} NOT_AVAILABLE — "
                f"{result.get('reason')} (not budget-consumed)"
            )

    budget = compute_error_budget(
        sli_results,
        total_units=float(slo_config.get("budget_total_units", 100.0)),
        release_fee_units=float(slo_config.get("release_fee_units", 5.0)),
        releases=releases,
    )
    return budget, [], warnings


# ── Decision helpers ─────────────────────────────────────────────────────


def _disabled_result(budget: dict[str, Any] | None) -> SloGateResult:
    return SloGateResult(
        decision=GATE_DECISION_PASS,
        reason=(
            "slo gate disabled by config/env (LOOP_SLO_GATE_ENABLED or "
            "slo_gate.enabled=false) — advisory-only mode, no block applied"
        ),
        budget=budget,
        status=GATE_STATUS_DISABLED,
        gate_enabled=False,
        notes=["B2 wave 2 gate is off: budget is reported but never blocks"],
    )


def _data_insufficient(missing: list[str]) -> SloGateResult:
    return SloGateResult(
        decision=GATE_DECISION_BLOCK,
        reason=(
            "data insufficient (fail-closed): cannot determine the error "
            "budget — missing or unparseable required source(s): "
            + "; ".join(missing)
        ),
        budget=None,
        status=GATE_STATUS_NOT_AVAILABLE,
        missing=list(missing),
    )


def _decide_from_budget(root: Path, budget: dict[str, Any],
                        sli_warnings: list[str],
                        now: datetime) -> SloGateResult:
    """Map a computed D2 budget to a gate decision, honoring exemptions."""
    exemption: dict[str, Any] | None = None
    try:
        records = load_exemptions(root)
        exemption, exemption_warnings = _valid_exemption(records, now)
    except DataSourceUnavailableError as exc:
        exemption = None
        exemption_warnings = [str(exc)]
    warnings = list(sli_warnings) + exemption_warnings

    budget_status = str(budget.get("status", NOT_AVAILABLE))
    notes: list[str] = []
    if budget_status == BUDGET_HEALTHY:
        decision = GATE_DECISION_PASS
        reason = (
            "error budget healthy — release allowed "
            f"(consumed {budget['consumed_units']} / "
            f"{budget['total_units']} units)"
        )
    elif budget_status == BUDGET_CONSUMING:
        decision = GATE_DECISION_PASS
        reason = (
            "error budget within limits — release allowed "
            f"(consumed {budget['consumed_units']} / "
            f"{budget['total_units']} units, remaining "
            f"{budget['remaining_units']})"
        )
        warnings.append(
            f"budget CONSUMING: {budget['consumed_units']} units consumed of "
            f"{budget['total_units']}"
        )
    elif budget_status == BUDGET_FREEZE_RECOMMENDED:
        decision = GATE_DECISION_BLOCK
        reason = (
            f"{GATE_BLOCK_CODE}: error budget exhausted — release frozen "
            f"(consumed {budget['consumed_units']} / "
            f"{budget['total_units']} units, remaining "
            f"{budget['remaining_units']})"
        )
    else:
        decision = GATE_DECISION_BLOCK
        reason = (
            "budget status not determinable (fail-closed) — release frozen: "
            f"budget status={budget_status}"
        )

    if exemption is not None and decision == GATE_DECISION_BLOCK:
        decision = GATE_DECISION_PASS
        reason = (
            f"exemption {exemption['id']} in effect (approver="
            f"{exemption['approver']}, expires {exemption['expires_at']}) — "
            f"release allowed: {exemption['reason']}"
        )
        notes.append(
            f"valid exemption {exemption['id']} overrode a "
            f"{budget_status} budget decision"
        )

    return SloGateResult(
        decision=decision,
        reason=reason,
        budget=budget,
        status=budget_status,
        missing=[],
        warnings=warnings,
        notes=notes,
        exemption=exemption,
        gate_enabled=True,
    )


# ── Gate entry points ────────────────────────────────────────────────────


def check_slo_gate(project_root: str | Path,
                   budget: dict[str, Any] | None = None,
                   window: tuple[str, str] | None = None,
                   releases: int = 0,
                   now: datetime | None = None) -> SloGateResult:
    """Evaluate the SLO release gate (T-0093 wave 2).

    Parameters:
        project_root: repository root containing the ``.ai/`` sources.
        budget:      optional precomputed D2 budget dict (e.g. from
                     ``build_report(...).budget``); when given, the gate skips
                     its own computation and the caller asserts the data
                     sufficiency.
        window:      ``(start, end)`` ISO bounds; defaults to the slo.yaml
                     window, else all data.
        releases:    release count for the release fee (default 0 — no
                     release ledger exists yet).
        now:         clock for exemption validity (testability; defaults to
                     the current UTC time).

    Returns:
        SloGateResult with decision PASS/BLOCK.  BLOCK reasons are explicit:
        ``ERROR_BUDGET_EXHAUSTED`` with the budget detail, or a fail-closed
        data-insufficiency reason listing every missing/unparseable required
        source.
    """
    root = Path(project_root)
    now = now if now is not None else datetime.now(timezone.utc)

    if not slo_gate_enabled(root):
        return _disabled_result(budget)

    if budget is None:
        try:
            slo_config = load_slo_config(root)
        except DataSourceUnavailableError as exc:
            return _data_insufficient([str(exc)])
        return _check_with_config(root, slo_config, window=window,
                                  releases=releases, now=now)

    return _decide_from_budget(root, budget, sli_warnings=[], now=now)


def _check_with_config(project_root: str | Path,
                       slo_config: dict[str, Any],
                       window: tuple[str, str] | None = None,
                       releases: int = 0,
                       now: datetime | None = None) -> SloGateResult:
    """Gate evaluation over a resolved SLO config (shared by ``check_slo_gate``
    and the checker CLI's ``--slo`` override path).

    T-0095 dedup: this helper does NOT re-check ``slo_gate_enabled`` — the
    single toggle check lives in ``check_slo_gate`` (which covers the
    precomputed-budget path too); callers that bypass ``check_slo_gate``
    (the checker CLI's ``--slo`` path) are responsible for the one toggle
    check themselves.
    """
    root = Path(project_root)
    now = now if now is not None else datetime.now(timezone.utc)

    budget, missing, sli_warnings = _compute_gate_budget(
        root, slo_config, window, releases,
    )
    if missing:
        return _data_insufficient(missing)
    return _decide_from_budget(root, budget, sli_warnings=sli_warnings, now=now)
