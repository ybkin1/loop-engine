"""T-0087 U1 AC-01/02/03: capability registry + guard_health integration tests.

Proves:
- AC-01: registry seal() immutability (register after seal raises) and
  deterministic snapshots (same input -> same canonical json -> same sha256).
- AC-02: guard_health three-way integrity — death (existing battery, fail-closed)
  + missing (file exists but unregistered) + drift (hash/version changed) —
  with missing/drift proven REPORT-level (never flip overall) and death proven
  fail-closed (still flips overall).
- AC-03: rehydrate is fail-closed — version/contract mismatch raises ValueError,
  unknown capability raises LookupError, tampered snapshot_id raises ValueError.
"""
import hashlib
import json
from pathlib import Path

import pytest

from loop_core.capability_registry import (
    CapabilityBinding,
    CapabilityRegistry,
    build_default_registry,
    sha256_file,
)
from loop_core.guard_health import GuardHealth, GuardHealthResult

ROOT = Path(__file__).resolve().parent.parent


def make_file(tmp_path: Path, rel: str, content: str) -> Path:
    fp = tmp_path / rel
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    return fp


def make_binding(capability_id: str, impl_path: str,
                 version: str = "1.0", contract_version: str = "checker-result.schema.yaml@1",
                 impl_hash: str = "") -> CapabilityBinding:
    return CapabilityBinding(
        capability_id=capability_id,
        provider_id="checker",
        implementation_path=impl_path,
        version=version,
        contract_version=contract_version,
        description=f"test binding {capability_id}",
        health_required=True,
        implementation_hash=impl_hash,
    )


# ── AC-01: seal immutability + deterministic snapshot ──────────────────────

def test_default_registry_registers_all_governance_assets():
    """The built-in registry covers .ai/checkers/ (3) + .ai/guards/ (1)."""
    registry = build_default_registry(ROOT)
    assert registry.sealed
    snap = registry.snapshot()
    assert set(snap.entries) == {
        "compile_gate", "run_governance_checks", "validate_gate_register",
        "policy_guard",
    }
    providers = {b.provider_id for b in snap.entries.values()}
    assert providers == {"checker", "guard"}
    for b in snap.entries.values():
        # versions derive from actual file content (sha256 prefix here)
        impl = ROOT / b.implementation_path
        assert impl.exists()
        assert b.implementation_hash == sha256_file(impl)
        assert b.version == b.implementation_hash[:12]
        assert b.contract_version


def test_seal_prevents_register_after_seal():
    """AC-01: register() after seal() raises RuntimeError (immutability)."""
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    registry.seal()
    assert registry.sealed
    with pytest.raises(RuntimeError):
        registry.register(make_binding("b", ".ai/checkers/b.py"))
    # The frozen registry still serves the pre-seal binding.
    assert registry.require("a").capability_id == "a"


def test_register_duplicate_raises_before_seal():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    with pytest.raises(ValueError):
        registry.register(make_binding("a", ".ai/checkers/other.py"))


def test_snapshot_deterministic_same_input_same_fingerprint():
    """AC-01: same bindings -> same canonical json -> same sha256 snapshot_id."""
    def build() -> CapabilityRegistry:
        r = CapabilityRegistry()
        r.register(make_binding("zeta", ".ai/checkers/z.py", impl_hash="h1"))
        r.register(make_binding("alpha", ".ai/checkers/a.py", impl_hash="h2"))
        r.register(make_binding("mid", ".ai/guards/m.py", impl_hash="h3"))
        r.seal()
        return r

    s1 = build().snapshot()
    s2 = build().snapshot()          # same input, different instance
    assert s1.canonical_json == s2.canonical_json
    assert s1.snapshot_id == s2.snapshot_id
    assert len(s1.snapshot_id) == 64  # sha256 hexdigest
    # canonical json is key-sorted regardless of registration order
    assert s1.canonical_json == json.dumps(
        [make_binding("alpha", ".ai/checkers/a.py", impl_hash="h2").to_dict(),
         make_binding("mid", ".ai/guards/m.py", impl_hash="h3").to_dict(),
         make_binding("zeta", ".ai/checkers/z.py", impl_hash="h1").to_dict()],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )


def test_snapshot_id_is_sha256_of_canonical_json():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py", impl_hash="x"))
    snap = registry.snapshot()
    assert snap.snapshot_id == hashlib.sha256(snap.canonical_json.encode("utf-8")).hexdigest()


def test_snapshot_entries_are_read_only_mapping():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    snap = registry.snapshot()
    with pytest.raises(TypeError):
        snap.entries["b"] = make_binding("b", ".ai/checkers/b.py")  # type: ignore[index]


def test_snapshot_requested_filters_unknown_raises():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    registry.register(make_binding("b", ".ai/checkers/b.py"))
    subset = registry.snapshot(requested=["b"])
    assert list(subset.entries) == ["b"]
    with pytest.raises(LookupError):
        registry.snapshot(requested=["a", "ghost"])


def test_require_missing_raises_lookup_error():
    """AC-01/03: a missing capability is never silently absent."""
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    with pytest.raises(LookupError):
        registry.require("not_there")
    assert registry.require("a").capability_id == "a"


# ── AC-03: fail-closed rehydration ─────────────────────────────────────────

def test_rehydrate_roundtrip_ok():
    registry = build_default_registry(ROOT)
    payload = registry.snapshot().to_dict()
    restored = registry.rehydrate(payload)
    assert restored.snapshot_id == payload["snapshot_id"]
    assert dict(restored.entries) == dict(registry.snapshot().entries)


def _repack(entries: list[dict]) -> dict:
    """Rebuild a consistent payload id for mutated entries.

    A registry issuing an older snapshot signs the entries it actually holds —
    so a version/contract mismatch carries a VALID snapshot_id. That is the
    realistic rehydrate-failure scenario: the payload is internally consistent
    but no longer matches the current (sealed) registry.
    """
    canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"))
    return {"snapshot_id": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "entries": entries}


def test_rehydrate_version_mismatch_raises_value_error():
    """AC-03: version mismatch -> ValueError, no silent downgrade."""
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py", version="1.0", impl_hash="h"))
    entries = registry.snapshot().to_dict()["entries"]
    entries[0]["version"] = "9.9"
    with pytest.raises(ValueError, match="version mismatch"):
        registry.rehydrate(_repack(entries))


def test_rehydrate_contract_mismatch_raises_value_error():
    """AC-03: contract mismatch -> ValueError, no silent downgrade."""
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py", contract_version="schema@1"))
    entries = registry.snapshot().to_dict()["entries"]
    entries[0]["contract_version"] = "schema@2"
    with pytest.raises(ValueError, match="contract mismatch"):
        registry.rehydrate(_repack(entries))


def test_rehydrate_unknown_capability_raises_lookup_error():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    entries = registry.snapshot().to_dict()["entries"]
    entries.append(make_binding("ghost", ".ai/checkers/ghost.py").to_dict())
    with pytest.raises(LookupError):
        registry.rehydrate(_repack(entries))


def test_rehydrate_tampered_snapshot_id_raises_value_error():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    payload = registry.snapshot().to_dict()
    payload["snapshot_id"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot_id mismatch"):
        registry.rehydrate(payload)


def test_rehydrate_accepts_json_string():
    registry = CapabilityRegistry()
    registry.register(make_binding("a", ".ai/checkers/a.py"))
    payload = json.dumps(registry.snapshot().to_dict())
    assert registry.rehydrate(payload).snapshot_id == registry.snapshot().snapshot_id


# ── AC-02: guard_health missing / drift detection ──────────────────────────

def _make_guard_health(root: Path, registry: CapabilityRegistry) -> GuardHealth:
    return GuardHealth(root, registry=registry)


def test_missing_detection_finds_unregistered_file(tmp_path):
    """AC-02: a checker file that exists but is not registered -> MISSING."""
    make_file(tmp_path, ".ai/checkers/compile_gate.py", "x = 1\n")
    make_file(tmp_path, ".ai/checkers/rogue_checker.py", "y = 2\n")
    registry = CapabilityRegistry()
    registry.register(make_binding(
        "compile_gate", ".ai/checkers/compile_gate.py",
        impl_hash=sha256_file(tmp_path / ".ai/checkers/compile_gate.py")))
    findings = _make_guard_health(tmp_path, registry).missing_detection()
    assert len(findings) == 1
    assert findings[0]["finding"] == "MISSING"
    assert findings[0]["severity"] == "report"
    assert findings[0]["implementation_path"] == ".ai/checkers/rogue_checker.py"
    assert findings[0]["provider_id"] == "checker"


def test_missing_detection_clean_when_all_registered(tmp_path):
    make_file(tmp_path, ".ai/checkers/compile_gate.py", "x = 1\n")
    registry = CapabilityRegistry()
    registry.register(make_binding(
        "compile_gate", ".ai/checkers/compile_gate.py",
        impl_hash=sha256_file(tmp_path / ".ai/checkers/compile_gate.py")))
    assert _make_guard_health(tmp_path, registry).missing_detection() == []


def test_drift_detection_reports_hash_change(tmp_path):
    """AC-02: registered hash != current file hash -> DRIFT."""
    impl = make_file(tmp_path, ".ai/guards/policy_guard.py", "DECISIONS = set()\n")
    original_hash = sha256_file(impl)
    registry = CapabilityRegistry()
    registry.register(CapabilityBinding(
        capability_id="policy_guard", provider_id="guard",
        implementation_path=".ai/guards/policy_guard.py",
        version=original_hash[:12], contract_version="guard-decision.schema.yaml@1",
        description="", health_required=True, implementation_hash=original_hash))
    assert _make_guard_health(tmp_path, registry).drift_detection() == []

    # drift: implementation changes after registration
    impl.write_text("DECISIONS = {'allow', 'deny'}\n", encoding="utf-8")
    findings = _make_guard_health(tmp_path, registry).drift_detection()
    assert len(findings) == 1
    assert findings[0]["finding"] == "DRIFT"
    assert findings[0]["severity"] == "report"
    assert findings[0]["capability_id"] == "policy_guard"
    assert findings[0]["expected_hash"] == original_hash
    assert findings[0]["actual_hash"] == sha256_file(impl)
    assert findings[0]["actual_hash"] != original_hash


def test_drift_detection_reports_missing_registered_file(tmp_path):
    registry = CapabilityRegistry()
    registry.register(make_binding(
        "compile_gate", ".ai/checkers/compile_gate.py", impl_hash="deadbeef"))
    findings = _make_guard_health(tmp_path, registry).drift_detection()
    assert len(findings) == 1
    assert findings[0]["finding"] == "DRIFT"
    assert "missing" in findings[0]["message"]


def test_live_repo_has_no_missing_or_drift():
    """The real governance assets are all registered and unmodified."""
    gh = GuardHealth(ROOT)
    assert gh.missing_detection() == []
    assert gh.drift_detection() == []


def test_missing_drift_are_report_level_and_never_flip_overall(monkeypatch, tmp_path):
    """AC-02: MISSING/DRIFT present, all guards ALIVE -> overall stays PASS."""
    make_file(tmp_path, ".ai/checkers/rogue_checker.py", "y = 2\n")
    make_file(tmp_path, ".ai/checkers/compile_gate.py", "x = 1\n")
    registry = CapabilityRegistry()
    registry.register(make_binding(
        "compile_gate", ".ai/checkers/compile_gate.py",
        impl_hash=sha256_file(tmp_path / ".ai/checkers/compile_gate.py")))
    gh = _make_guard_health(tmp_path, registry)
    monkeypatch.setattr(GuardHealth, "run", lambda self: [GuardHealthResult(
        guard="gate_guard", status="ALIVE", blocked=1, negative_total=1,
        allowed=1, positive_total=1, errors=[])])

    integrity = gh.integrity_check()
    assert integrity["missing"], "fixture must produce a MISSING finding"
    assert integrity["overall"] == "PASS", \
        "missing/drift are REPORT-level: must not flip overall to FAIL"


def test_death_detection_stays_fail_closed(monkeypatch, tmp_path):
    """AC-02: death (DORMANT/BROKEN) still flips overall to FAIL — not relaxed."""
    make_file(tmp_path, ".ai/checkers/rogue_checker.py", "y = 2\n")
    registry = CapabilityRegistry()
    registry.register(make_binding(
        "compile_gate", ".ai/checkers/compile_gate.py",
        impl_hash=sha256_file(tmp_path / ".ai/checkers/compile_gate.py")))
    gh = _make_guard_health(tmp_path, registry)
    monkeypatch.setattr(GuardHealth, "run", lambda self: [GuardHealthResult(
        guard="gate_guard", status="DORMANT", blocked=0, negative_total=1,
        allowed=0, positive_total=0, errors=[])])

    integrity = gh.integrity_check()
    assert integrity["missing"], "fixture must produce a MISSING finding"
    assert integrity["overall"] == "FAIL", \
        "death detection must stay fail-closed even when missing/drift exist"
