"""
Contract Plane Tests for the Vertical Slice (U2 — T-0087).

Validates the StaffDeck-style contract flattening pattern applied to
``tests/vertical_slice/``:

1. The 4 observation plane definitions (domain / events / conversation /
   state) are well-formed and cover the expected ids.
2. Golden scenario fixtures validate against the scenario JSON Schema and
   carry unique, cross-referenced ids.
3. The requirement registry validates against the registry JSON Schema,
   covers all 4 planes, and every covered_by ref resolves to a real
   scenario assertion.
4. Golden scenario assertions pass against the real slice evidence.
5. The conformance gate is fail-closed: real evidence -> PASS; corrupted
   evidence or uncovered requirement -> FAIL (both branches tested).
6. The conformance report is written to .ai/evidence/T-0087/contract-planes/
   and the registry mirror there stays byte-identical to the canonical
   registry (no drift).

These tests do NOT call AI agents — they run deterministic assertions
against structured evidence and the loop_core state machine.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# Ensure the repo root and this package are importable.
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC_ROOT))
sys.path.insert(0, str(_THIS_DIR))

import pytest
import jsonschema

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

import conformance  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONTRACT_DIR = _THIS_DIR / "contract_planes"
EVIDENCE_DIR = _THIS_DIR / "evidence"
SCENARIOS_DIR = CONTRACT_DIR / "golden_scenarios"
REGISTRY_PATH = CONTRACT_DIR / "requirement-registry.yaml"
PLANES_PATH = CONTRACT_DIR / "planes.yaml"
SCENARIO_SCHEMA_PATH = CONTRACT_DIR / "scenario.schema.json"
REGISTRY_SCHEMA_PATH = CONTRACT_DIR / "registry.schema.json"

EVIDENCE_DIR_T0087 = _SRC_ROOT / ".ai" / "evidence" / "T-0087" / "contract-planes"
EVIDENCE_REGISTRY_PATH = EVIDENCE_DIR_T0087 / "requirement-registry.yaml"
REPORT_PATH = EVIDENCE_DIR_T0087 / "conformance-report.json"

PLANE_IDS = ("domain", "events", "conversation", "state")


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict:
    if not HAS_YAML:
        pytest.skip("PyYAML not installed")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _scenario_fixtures() -> list[dict]:
    return [
        _load_json(f)
        for f in sorted(SCENARIOS_DIR.glob("*.json"))
    ]


def _registry() -> dict:
    return _load_yaml(REGISTRY_PATH)


# ---------------------------------------------------------------------------
# 1. Observation plane definitions
# ---------------------------------------------------------------------------


class TestPlanesDefinition:
    """The 4 observation planes must be defined and referenced consistently."""

    def test_planes_file_exists_and_is_valid_yaml(self):
        planes = _load_yaml(PLANES_PATH)
        assert isinstance(planes, dict), "planes.yaml must be a YAML object"
        assert planes.get("schema_version") == 1

    def test_exactly_four_planes_with_expected_ids(self):
        planes = _load_yaml(PLANES_PATH)
        ids = [p["id"] for p in planes["planes"]]
        assert ids == list(PLANE_IDS), (
            f"Plane ids {ids} != expected {list(PLANE_IDS)}"
        )

    def test_each_plane_has_required_fields(self):
        planes = _load_yaml(PLANES_PATH)
        for plane in planes["planes"]:
            for field in ("id", "name", "description", "observables"):
                assert field in plane and plane[field], (
                    f"Plane '{plane.get('id')}' missing field '{field}'"
                )
            assert isinstance(plane["observables"], list) and plane["observables"], (
                f"Plane '{plane['id']}' observables must be a non-empty list"
            )

    def test_registry_planes_subset_of_defined_planes(self):
        """Every registry requirement must map to a defined plane."""
        planes = _load_yaml(PLANES_PATH)
        plane_ids = {p["id"] for p in planes["planes"]}
        for req in _registry()["requirements"]:
            assert req["plane"] in plane_ids, (
                f"Requirement {req['requirement_id']} references unknown "
                f"plane '{req['plane']}'"
            )


# ---------------------------------------------------------------------------
# 2. Golden scenario fixture schemas
# ---------------------------------------------------------------------------


class TestScenarioFixtures:
    """Golden scenario fixtures must be schema-valid and self-consistent."""

    @pytest.fixture(scope="class")
    def scenario_schema(self):
        return _load_json(SCENARIO_SCHEMA_PATH)

    @pytest.fixture(scope="class")
    def fixtures(self):
        return _scenario_fixtures()

    def test_at_least_two_scenarios(self, fixtures):
        assert len(fixtures) >= 2, (
            f"Expected at least 2 golden scenarios, got {len(fixtures)}"
        )

    @pytest.mark.parametrize(
        "idx", range(len(_scenario_fixtures())), ids=lambda i: f"fixture-{i}"
    )
    def test_fixture_validates_against_scenario_schema(self, fixtures, scenario_schema, idx):
        fixture = fixtures[idx]
        try:
            jsonschema.validate(fixture, scenario_schema)
        except jsonschema.ValidationError as exc:
            pytest.fail(
                f"{fixture.get('scenario_id')} fails scenario schema: {exc.message}"
            )

    def test_scenario_ids_are_unique(self, fixtures):
        ids = [f["scenario_id"] for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate scenario ids: {ids}"

    def test_every_scenario_has_all_four_planes(self, fixtures):
        for fixture in fixtures:
            for plane in PLANE_IDS:
                assert plane in fixture["planes"], (
                    f"{fixture['scenario_id']} missing plane '{plane}'"
                )

    def test_event_ids_unique_within_scenario(self, fixtures):
        for fixture in fixtures:
            event_ids = [e["event_id"] for e in fixture["planes"]["events"]]
            assert len(event_ids) == len(set(event_ids)), (
                f"{fixture['scenario_id']} duplicate event ids: {event_ids}"
            )

    def test_stage_ids_unique_within_scenario(self, fixtures):
        for fixture in fixtures:
            stage_ids = [s["stage_id"] for s in fixture["planes"]["conversation"]]
            assert len(stage_ids) == len(set(stage_ids)), (
                f"{fixture['scenario_id']} duplicate stage ids: {stage_ids}"
            )

    def test_check_ids_unique_within_domain_and_state(self, fixtures):
        for fixture in fixtures:
            for plane in ("domain", "state"):
                check_ids = [
                    c.get("id", f"index-{i}")
                    for i, c in enumerate(fixture["planes"][plane])
                ]
                assert len(check_ids) == len(set(check_ids)), (
                    f"{fixture['scenario_id']} duplicate check ids in "
                    f"plane '{plane}': {check_ids}"
                )

    def test_event_phases_are_known_phases(self, fixtures):
        from loop_core.state_machine import Phase

        known = {p.value for p in Phase}
        for fixture in fixtures:
            for event in fixture["planes"]["events"]:
                assert event["phase"] in known, (
                    f"{fixture['scenario_id']} event {event['event_id']} has "
                    f"unknown phase '{event['phase']}'"
                )


# ---------------------------------------------------------------------------
# 3. Requirement registry
# ---------------------------------------------------------------------------


class TestRequirementRegistry:
    """The registry must be schema-valid and every coverage ref resolvable."""

    @pytest.fixture(scope="class")
    def registry_schema(self):
        return _load_json(REGISTRY_SCHEMA_PATH)

    @pytest.fixture(scope="class")
    def registry(self):
        return _registry()

    @pytest.fixture(scope="class")
    def fixtures(self):
        return {f["scenario_id"]: f for f in _scenario_fixtures()}

    def test_registry_validates_against_schema(self, registry, registry_schema):
        try:
            jsonschema.validate(registry, registry_schema)
        except jsonschema.ValidationError as exc:
            pytest.fail(f"Registry fails schema validation: {exc.message}")

    def test_at_least_eight_requirements(self, registry):
        assert len(registry["requirements"]) >= 8, (
            f"Expected at least 8 requirements, got {len(registry['requirements'])}"
        )

    def test_every_plane_has_at_least_two_requirements(self, registry):
        per_plane: dict[str, int] = {}
        for req in registry["requirements"]:
            per_plane[req["plane"]] = per_plane.get(req["plane"], 0) + 1
        for plane in PLANE_IDS:
            assert per_plane.get(plane, 0) >= 2, (
                f"Plane '{plane}' has {per_plane.get(plane, 0)} requirements, "
                f"expected >= 2"
            )

    def test_all_requirements_declared_implemented(self, registry):
        for req in registry["requirements"]:
            assert req["status"] == "implemented", (
                f"{req['requirement_id']} declared status is "
                f"'{req['status']}', expected 'implemented' (current assets "
                f"must be fully covered)"
            )

    def test_every_coverage_ref_resolves(self, registry, fixtures):
        """Every covered_by {scenario, plane, ref} must exist in a fixture."""
        for req in registry["requirements"]:
            for entry in req["covered_by"]:
                scenario = fixtures.get(entry["scenario"])
                assert scenario is not None, (
                    f"{req['requirement_id']} references missing scenario "
                    f"'{entry['scenario']}'"
                )
                items = conformance.plane_items(scenario, entry["plane"])
                refs = [ref for ref, _ in items]
                if entry.get("ref") is not None:
                    assert entry["ref"] in refs, (
                        f"{req['requirement_id']} ref '{entry['ref']}' not "
                        f"found in {entry['scenario']} plane '{entry['plane']}' "
                        f"(available: {refs})"
                    )

    def test_coverage_is_bidirectionally_consistent(self, registry, fixtures):
        """scenario.requirements_covered must exactly match the requirements
        that reference the scenario."""
        for scenario_id, scenario in fixtures.items():
            referencing = sorted({
                req["requirement_id"]
                for req in registry["requirements"]
                for entry in req["covered_by"]
                if entry["scenario"] == scenario_id
            })
            declared = sorted(scenario.get("requirements_covered", []))
            assert referencing == declared, (
                f"Scenario {scenario_id} requirements mismatch: "
                f"referenced by registry {referencing} != declared {declared}"
            )


# ---------------------------------------------------------------------------
# 4. Golden scenario assertions against the real evidence
# ---------------------------------------------------------------------------


class TestGoldenScenarioAssertions:
    """Every golden scenario must pass against the real slice evidence."""

    @pytest.mark.parametrize("scenario_id", [f["scenario_id"] for f in _scenario_fixtures()])
    def test_scenario_all_planes_pass(self, scenario_id):
        scenario = _load_json(SCENARIOS_DIR / f"{scenario_id}.json")
        result = conformance.run_scenario(scenario, EVIDENCE_DIR)
        assert result["passed"], (
            f"Golden scenario {scenario_id} failed — see conformance "
            f"report for failing assertions"
        )

    @pytest.mark.parametrize("plane", PLANE_IDS)
    def test_every_scenario_has_assertions_per_plane(self, plane):
        """Each plane must carry at least one assertion in every scenario
        (scenarios describe expectations on all 4 planes)."""
        for fixture in _scenario_fixtures():
            items = conformance.plane_items(fixture, plane)
            assert items, (
                f"{fixture['scenario_id']} plane '{plane}' has no assertions"
            )


# ---------------------------------------------------------------------------
# 5. Conformance gate (fail-closed)
# ---------------------------------------------------------------------------


class TestConformanceGate:
    """gate_decision must be PASS on the real evidence and FAIL when any
    assertion fails or any requirement is uncovered."""

    def _run(self, registry_path=REGISTRY_PATH, evidence_root=EVIDENCE_DIR):
        return conformance.run_conformance(
            Path(registry_path), SCENARIOS_DIR, Path(evidence_root)
        )

    def test_real_evidence_gate_is_pass(self):
        report = self._run()
        summary = report["summary"]
        assert report["gate_decision"] == "PASS", (
            f"gate_decision should be PASS on current evidence; "
            f"summary: {summary}"
        )
        assert summary["failed_assertions"] == 0
        assert summary["missing"] == 0 and summary["partial"] == 0
        assert summary["implemented"] == summary["total_requirements"]
        assert summary["covered"] == summary["total_requirements"]
        assert summary["scenarios_passed"] == summary["scenarios_total"]

    def test_all_requirements_pass_on_real_evidence(self):
        report = self._run()
        for req in report["requirements"]:
            assert req["passed"], (
                f"{req['requirement_id']} did not pass: "
                f"status={req['status']}, coverage failures: "
                f"{[c['failures'] for c in req['coverage'] if not c['passed']]}"
            )
            assert req["status"] == req["declared_status"] == "implemented"

    def test_report_has_required_structure(self):
        report = self._run()
        for key in ("generated_at", "gate_semantics", "sources", "scenarios",
                    "requirements", "summary", "gate_decision"):
            assert key in report, f"Report missing key: {key}"
        assert "fail-closed" in report["gate_semantics"]
        for req in report["requirements"]:
            for key in ("requirement_id", "description", "plane",
                        "declared_status", "status", "coverage", "passed"):
                assert key in req, f"Requirement entry missing key: {key}"

    def test_gate_fails_closed_on_failed_assertion(self, tmp_path):
        """Corrupting one evidence fact must flip the gate to FAIL."""
        evidence_copy = tmp_path / "evidence"
        shutil.copytree(EVIDENCE_DIR, evidence_copy)
        dd_path = evidence_copy / "S6-delivery" / "delivery_decision.json"
        dd = _load_json(dd_path)
        dd["delivery_decision"]["final_decision"] = "NOGO"
        dd_path.write_text(
            json.dumps(dd, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        report = self._run(evidence_root=evidence_copy)
        summary = report["summary"]
        assert report["gate_decision"] == "FAIL", (
            "gate_decision must be FAIL when an assertion fails (fail-closed)"
        )
        assert summary["failed_assertions"] > 0
        assert summary["partial"] > 0
        # The corrupted fact must be the one that failed — proof the gate is
        # driven by real assertions, not by a hard-coded PASS.
        failed_msgs = [
            failure
            for req in report["requirements"]
            for cov in req["coverage"]
            for failure in cov["failures"]
        ]
        assert any("final_decision" in msg for msg in failed_msgs), (
            f"Expected a failure mentioning final_decision, got: {failed_msgs}"
        )

    def test_gate_fails_closed_on_missing_coverage(self, tmp_path):
        """A requirement without any coverage must yield FAIL (missing)."""
        registry = _registry()
        registry["requirements"][0]["covered_by"] = []
        tmp_registry = tmp_path / "registry.yaml"
        tmp_registry.write_text(
            yaml.dump(registry, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

        report = self._run(registry_path=tmp_registry)
        summary = report["summary"]
        assert report["gate_decision"] == "FAIL", (
            "gate_decision must be FAIL when a requirement is uncovered"
        )
        assert summary["missing"] == 1
        missing_req = next(
            r for r in report["requirements"]
            if r["status"] == "missing"
        )
        assert missing_req["requirement_id"] == registry["requirements"][0]["requirement_id"]
        assert not missing_req["passed"]

    def test_gate_fails_closed_on_unknown_ref(self, tmp_path):
        """A coverage ref pointing at a non-existent assertion must yield FAIL."""
        registry = _registry()
        registry["requirements"][0]["covered_by"][0]["ref"] = "does-not-exist"
        tmp_registry = tmp_path / "registry.yaml"
        tmp_registry.write_text(
            yaml.dump(registry, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

        report = self._run(registry_path=tmp_registry)
        assert report["gate_decision"] == "FAIL", (
            "gate_decision must be FAIL when a coverage ref is unresolvable"
        )
        assert report["summary"]["partial"] >= 1

    def test_conformance_report_written_to_evidence(self):
        """The conformance report artifact is generated and PASSing."""
        report = conformance.run_conformance(
            REGISTRY_PATH, SCENARIOS_DIR, EVIDENCE_DIR
        )
        conformance.write_report(report, REPORT_PATH)
        assert REPORT_PATH.is_file(), f"Report not written: {REPORT_PATH}"
        on_disk = _load_json(REPORT_PATH)
        assert on_disk["gate_decision"] == "PASS"
        assert on_disk["summary"] == report["summary"]


# ---------------------------------------------------------------------------
# 6. Registry mirror (evidence) must not drift
# ---------------------------------------------------------------------------


class TestRegistryEvidenceMirror:
    """The registry snapshot under .ai/evidence/T-0087/contract-planes/ must
    stay byte-identical to the canonical registry (anti-drift)."""

    def test_evidence_registry_mirror_matches_canonical(self):
        assert EVIDENCE_REGISTRY_PATH.is_file(), (
            f"Evidence registry mirror missing: {EVIDENCE_REGISTRY_PATH}"
        )
        canonical = REGISTRY_PATH.read_bytes()
        mirror = EVIDENCE_REGISTRY_PATH.read_bytes()
        assert mirror == canonical, (
            "Evidence registry mirror drifted from canonical registry — "
            "re-sync .ai/evidence/T-0087/contract-planes/requirement-registry.yaml"
        )
