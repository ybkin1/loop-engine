"""
Vertical Slice Contract Conformance Engine (U2 — T-0087).

Implements the StaffDeck-style contract flattening pattern
(OpenBMB/StaffDeck contracts/agent/v1: golden scenarios + requirement
registry + conformance report + gate_decision) for loop-engine's
``tests/vertical_slice/`` slice.

The engine observes the pre-generated slice evidence through four
observation planes:

- domain        — decisions and artifacts (task cards, AC, gate
                  decisions, acceptance results)
- events        — the governance event stream (task registration ->
                  gate approval -> implementation -> acceptance ->
                  convergence)
- conversation  — pre/post states of every stage transition
- state         — legal state-machine transitions (loop_core
                  state_machine: PHASE_TRANSITIONS / REENTRY_TRANSITIONS
                  / can_approve_gate)

It then runs the golden-scenario assertions registered in the
requirement registry and produces a conformance report with a
fail-closed gate decision:

    PASS  -> every registered requirement is covered by golden-scenario
             assertions AND all assertions pass
    FAIL  -> any requirement is uncovered (missing) or has at least one
             failed assertion (partial)

Usage (CLI):

    python tests/vertical_slice/conformance.py [--registry R]
        [--scenarios D] [--evidence D] [--report OUT.json]

Exit code is 0 on PASS, 1 on FAIL.

Programmatic:

    from conformance import run_conformance, write_report
    report = run_conformance(registry_path, scenarios_dir, evidence_root)
    write_report(report, report_path)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the repo root is importable so this module works standalone (CLI).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from loop_core.state_machine import (  # noqa: E402
    GateStatus,
    Phase,
    can_approve_gate,
    can_transition_phase,
    validate_reentry,
)

# The four observation planes (order matters for report readability).
PLANES = ("domain", "events", "conversation", "state")

GATE_SEMANTICS = (
    "fail-closed: PASS only if every registered requirement is covered by "
    "golden-scenario assertions and all assertions pass; any failed or "
    "uncovered requirement yields FAIL"
)

try:
    import yaml as _yaml

    HAS_YAML = True
except ImportError:  # pragma: no cover - yaml is a dev dependency
    _yaml = None
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Default locations (relative to repo root)
# ---------------------------------------------------------------------------

DEFAULT_REGISTRY = (
    REPO_ROOT / "tests" / "vertical_slice" / "contract_planes"
    / "requirement-registry.yaml"
)
DEFAULT_SCENARIOS = (
    REPO_ROOT / "tests" / "vertical_slice" / "contract_planes"
    / "golden_scenarios"
)
DEFAULT_EVIDENCE = REPO_ROOT / "tests" / "vertical_slice" / "evidence"
DEFAULT_REPORT = (
    REPO_ROOT / ".ai" / "evidence" / "T-0087" / "contract-planes"
    / "conformance-report.json"
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    """Load a JSON file (used for evidence and scenario fixtures)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml_or_json(path: Path) -> dict:
    """Load a YAML file, falling back to JSON (registry loader)."""
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    text = _read_text(path)
    if HAS_YAML:
        data = _yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    return json.loads(text)


def _resolve_json_path(data, dotted_path: str):
    """Resolve a dotted path through dicts and list indices.

    Example: ``delivery_decision.decision_history.0.decision``
    """
    value = data
    for segment in dotted_path.split("."):
        if isinstance(value, list) and segment.isdigit():
            value = value[int(segment)]
        elif isinstance(value, dict) and segment in value:
            value = value[segment]
        else:
            raise KeyError(
                f"json_path '{dotted_path}' not resolvable at segment '{segment}'"
            )
    return value


# ---------------------------------------------------------------------------
# Check runner — the single source of truth for assertions. A check returns
# (ok: bool, message: str). Every assertion runs against real evidence files
# or the loop_core state machine — there is no hard-coded "pass".
# ---------------------------------------------------------------------------


def run_check(check: dict, evidence_root: Path) -> tuple[bool, str]:
    """Run a single assertion check against ``evidence_root``."""
    ctype = check.get("type")

    if ctype == "file_exists":
        path = evidence_root / check["path"]
        if not path.is_file():
            return False, f"file missing: {check['path']}"
        if check.get("non_empty", True) and path.stat().st_size == 0:
            return False, f"file empty: {check['path']}"
        return True, f"file exists: {check['path']}"

    if ctype == "text_contains":
        content = _read_text(evidence_root / check["path"])
        if check["needle"] not in content:
            return False, (
                f"needle '{check['needle']}' not found in {check['path']}"
            )
        return True, f"'{check['needle']}' found in {check['path']}"

    if ctype == "text_matches":
        content = _read_text(evidence_root / check["path"])
        if not re.search(check["pattern"], content):
            return False, (
                f"pattern /{check['pattern']}/ not matched in {check['path']}"
            )
        return True, f"/{check['pattern']}/ matched in {check['path']}"

    if ctype == "json_equals":
        data = load_json(evidence_root / check["path"])
        actual = _resolve_json_path(data, check["json_path"])
        if actual != check["expected"]:
            return False, (
                f"{check['path']} [{check['json_path']}] == {actual!r}, "
                f"expected {check['expected']!r}"
            )
        return True, f"{check['json_path']} == {check['expected']!r}"

    if ctype == "json_contains":
        data = load_json(evidence_root / check["path"])
        value = _resolve_json_path(data, check["json_path"])
        if not isinstance(value, list):
            return False, (
                f"{check['path']} [{check['json_path']}] is not a list"
            )
        expected = check["expected"]
        if isinstance(expected, dict):
            found = any(
                isinstance(item, dict)
                and all(item.get(k) == v for k, v in expected.items())
                for item in value
            )
        else:
            found = expected in value
        if not found:
            return False, (
                f"{check['path']} [{check['json_path']}] does not contain "
                f"{expected!r}"
            )
        return True, f"{check['json_path']} contains {expected!r}"

    if ctype == "count_equals":
        data = load_json(evidence_root / check["path"])
        value = _resolve_json_path(data, check["json_path"])
        if isinstance(value, (list, dict)):
            if len(value) != check["expected"]:
                return False, (
                    f"{check['path']} [{check['json_path']}] has {len(value)} "
                    f"items, expected {check['expected']}"
                )
            return True, f"{check['json_path']} has {check['expected']} items"
        return False, (
            f"{check['path']} [{check['json_path']}] is neither a list nor a "
            f"dict (got {type(value).__name__})"
        )

    if ctype == "state_transition":
        result = can_transition_phase(
            Phase(check["from_phase"]), Phase(check["to_phase"])
        )
        if not result.allowed:
            return False, "; ".join(result.errors)
        return True, (
            f"transition {check['from_phase']} -> {check['to_phase']} is legal"
        )

    if ctype == "state_transition_forbidden":
        result = can_transition_phase(
            Phase(check["from_phase"]), Phase(check["to_phase"])
        )
        if result.allowed:
            return False, (
                f"transition {check['from_phase']} -> {check['to_phase']} "
                f"is allowed but must be forbidden (negative control)"
            )
        return True, (
            f"transition {check['from_phase']} -> {check['to_phase']} "
            f"correctly forbidden"
        )

    if ctype == "state_path":
        # Reachability through PHASE_TRANSITIONS: the evidence chain may
        # legitimately skip intermediate phases (e.g. the vertical slice
        # skips S3-interface), so consecutive evidence phases must be
        # connected by a legal multi-step path, not necessarily a direct
        # edge.
        reachable = _is_reachable(
            Phase(check["from_phase"]), Phase(check["to_phase"])
        )
        if not reachable:
            return False, (
                f"no legal path from {check['from_phase']} to "
                f"{check['to_phase']} in PHASE_TRANSITIONS"
            )
        return True, (
            f"legal path exists from {check['from_phase']} to "
            f"{check['to_phase']}"
        )

    if ctype == "reentry":
        result = validate_reentry(
            Phase(check["entry_phase"]), check["change_type"]
        )
        expected = bool(check.get("allowed", True))
        if result.allowed != expected:
            return False, (
                f"reentry {check['change_type']} -> {check['entry_phase']} "
                f"allowed={result.allowed}, expected {expected}; "
                + "; ".join(result.errors)
            )
        return True, (
            f"reentry {check['change_type']} -> {check['entry_phase']} "
            f"allowed={result.allowed} (expected {expected})"
        )

    if ctype == "gate_approval":
        data = load_json(evidence_root / check["path"])
        raw_verdicts = _resolve_json_path(data, check["json_path"])
        # Evidence stores role verdicts either flat ("PASS") or nested
        # ({"verdict": "BLOCKED", ...}). Normalize to the flat form that
        # can_approve_gate expects.
        verdicts = {
            role: (v.get("verdict") if isinstance(v, dict) else v)
            for role, v in raw_verdicts.items()
        }
        result = can_approve_gate(
            GateStatus.PENDING, verdicts, check.get("required_roles", [])
        )
        expected = bool(check.get("expected", False))
        if result.allowed != expected:
            return False, (
                f"gate approval allowed={result.allowed}, expected {expected}; "
                + "; ".join(result.errors)
            )
        return True, (
            f"gate approval allowed={result.allowed} (expected {expected}) "
            f"with required roles {check.get('required_roles', [])}"
        )

    return False, f"unknown check type: {ctype!r}"


def _is_reachable(from_phase: Phase, to_phase: Phase) -> bool:
    """BFS reachability over PHASE_TRANSITIONS (directed graph)."""
    from loop_core.state_machine import PHASE_TRANSITIONS

    seen = {from_phase}
    queue = [from_phase]
    while queue:
        current = queue.pop(0)
        if current == to_phase:
            return True
        for nxt in PHASE_TRANSITIONS.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


# ---------------------------------------------------------------------------
# Scenario interpretation — each plane has its own observation model
# ---------------------------------------------------------------------------


def plane_items(scenario: dict, plane: str) -> list[tuple[str, list[dict]]]:
    """Return [(ref, [checks])] for one plane of a golden scenario.

    - domain / state: flat list of checks, ref = check id (or index)
    - events:         one item per event, ref = event_id, check = event.check
    - conversation:   one item per stage, ref = stage_id,
                      checks = stage.pre + stage.post
    """
    planes = scenario.get("planes", {})
    items: list[tuple[str, list[dict]]] = []
    if plane in ("domain", "state"):
        for i, check in enumerate(planes.get(plane, [])):
            items.append((check.get("id", f"{plane}-check-{i}"), [check]))
    elif plane == "events":
        for event in planes.get(plane, []):
            items.append((event["event_id"], [event["check"]]))
    elif plane == "conversation":
        for stage in planes.get(plane, []):
            items.append(
                (stage["stage_id"], list(stage.get("pre", [])) + list(stage.get("post", [])))
            )
    return items


def run_scenario(scenario: dict, evidence_root: Path) -> dict:
    """Run every plane assertion of one golden scenario. Returns a summary."""
    result = {
        "scenario_id": scenario["scenario_id"],
        "title": scenario.get("title", ""),
        "planes": {},
        "passed": True,
    }
    for plane in PLANES:
        items = plane_items(scenario, plane)
        plane_result = {"items_total": len(items), "items_passed": 0, "passed": True}
        for ref, checks in items:
            failures = []
            for check in checks:
                ok, msg = run_check(check, evidence_root)
                if not ok:
                    failures.append(msg)
            if not failures:
                plane_result["items_passed"] += 1
            else:
                plane_result["passed"] = False
        result["planes"][plane] = plane_result
        if not plane_result["passed"]:
            result["passed"] = False
    return result


# ---------------------------------------------------------------------------
# Coverage evaluation — binds registry requirements to scenario assertions
# ---------------------------------------------------------------------------


def evaluate_coverage(
    entry: dict, scenarios_by_id: dict, evidence_root: Path
) -> tuple[bool, list[str]]:
    """Evaluate one covered_by entry: (passed, failure messages)."""
    scenario = scenarios_by_id.get(entry["scenario"])
    if scenario is None:
        return False, [f"scenario '{entry['scenario']}' not found"]
    plane = entry["plane"]
    if plane not in PLANES:
        return False, [f"unknown plane '{plane}'"]
    items = plane_items(scenario, plane)
    if not items:
        return False, [
            f"plane '{plane}' of scenario {scenario['scenario_id']} has no items"
        ]
    ref = entry.get("ref")
    if ref is None:
        selected = items
    else:
        selected = [it for it in items if it[0] == ref]
        if not selected:
            return False, [
                f"ref '{ref}' not found in {scenario['scenario_id']} "
                f"plane '{plane}'"
            ]
    failures = []
    for _, checks in selected:
        for check in checks:
            ok, msg = run_check(check, evidence_root)
            if not ok:
                failures.append(
                    f"{scenario['scenario_id']}:{plane}:{ref or '*'}: {msg}"
                )
    return not failures, failures


# ---------------------------------------------------------------------------
# Conformance run
# ---------------------------------------------------------------------------


def run_conformance(
    registry_path: Path,
    scenarios_dir: Path,
    evidence_root: Path,
) -> dict:
    """Run the full conformance suite and return the report dict.

    Fail-closed gate: PASS iff every registered requirement is covered
    and all bound assertions pass.
    """
    registry = load_yaml_or_json(Path(registry_path))

    scenarios_by_id: dict[str, dict] = {}
    scenario_results: dict[str, dict] = {}
    for fixture in sorted(Path(scenarios_dir).glob("*.json")):
        scenario = load_json(fixture)
        scenarios_by_id[scenario["scenario_id"]] = scenario
        scenario_results[scenario["scenario_id"]] = run_scenario(
            scenario, Path(evidence_root)
        )

    requirements_report = []
    total_failed_assertions = 0
    for req in registry.get("requirements", []):
        coverage = []
        for entry in req.get("covered_by", []):
            passed, failures = evaluate_coverage(
                entry, scenarios_by_id, Path(evidence_root)
            )
            total_failed_assertions += len(failures)
            coverage.append(
                {
                    "scenario": entry["scenario"],
                    "plane": entry["plane"],
                    "ref": entry.get("ref"),
                    "passed": passed,
                    "failures": failures,
                }
            )
        covered = len(req.get("covered_by", [])) > 0
        if not covered:
            status = "missing"
        elif any(not c["passed"] for c in coverage):
            status = "partial"
        else:
            status = "implemented"
        requirements_report.append(
            {
                "requirement_id": req["requirement_id"],
                "description": req.get("description", ""),
                "plane": req.get("plane", ""),
                "declared_status": req.get("status", ""),
                "status": status,
                "coverage": coverage,
                "passed": status == "implemented",
            }
        )

    n_implemented = sum(1 for r in requirements_report if r["status"] == "implemented")
    n_partial = sum(1 for r in requirements_report if r["status"] == "partial")
    n_missing = sum(1 for r in requirements_report if r["status"] == "missing")
    scenarios_total = len(scenario_results)
    scenarios_passed = sum(1 for r in scenario_results.values() if r["passed"])
    all_pass = (
        requirements_report
        and n_implemented == len(requirements_report)
        and total_failed_assertions == 0
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_semantics": GATE_SEMANTICS,
        "sources": {
            "registry": str(Path(registry_path)),
            "scenarios_dir": str(Path(scenarios_dir)),
            "evidence_root": str(Path(evidence_root)),
        },
        "scenarios": scenario_results,
        "requirements": requirements_report,
        "summary": {
            "total_requirements": len(requirements_report),
            "covered": len(requirements_report) - n_missing,
            "implemented": n_implemented,
            "partial": n_partial,
            "missing": n_missing,
            "failed_assertions": total_failed_assertions,
            "scenarios_total": scenarios_total,
            "scenarios_passed": scenarios_passed,
        },
        "gate_decision": "PASS" if all_pass else "FAIL",
    }
    return report


def write_report(report: dict, path: Path) -> Path:
    """Write the conformance report to ``path`` (creates parent dirs)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_summary(report: dict) -> None:
    s = report["summary"]
    print(f"gate_decision: {report['gate_decision']}  "
          f"({report['gate_semantics']})")
    print(
        f"requirements: {s['total_requirements']} total / "
        f"{s['covered']} covered / {s['implemented']} implemented / "
        f"{s['partial']} partial / {s['missing']} missing"
    )
    print(
        f"scenarios: {s['scenarios_passed']}/{s['scenarios_total']} passed "
        f"| failed_assertions: {s['failed_assertions']}"
    )
    for req in report["requirements"]:
        if not req["passed"]:
            print(f"  FAIL {req['requirement_id']} [{req['status']}] {req['description']}")
            for cov in req["coverage"]:
                for failure in cov["failures"]:
                    print(f"      - {failure}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Vertical slice contract conformance engine (fail-closed)."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    report = run_conformance(args.registry, args.scenarios, args.evidence)
    write_report(report, args.report)
    _print_summary(report)
    print(f"report written: {args.report}")
    return 0 if report["gate_decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
