"""T-0089 U8 AC-03: guard-check observability — layered event recording.

Covers:
- AC-03a: guard check events are persisted and queryable after a check runs
  (guard_id / check_type / duration_ms / result / failure_reason / timestamp /
  source fields).
- AC-03b: observation failures never block business — a throwing recorder
  leaves the guard-health run results identical and the safety verdict intact.
- AC-03c: the observability switch (absent / enabled / failing) never changes
  enforcement BLOCK/PASS adjudication — contrast tests, both sides.
- AC-03d: the event file is append-only — history is never rewritten.
- plus: summary() aggregation (frequency/duration/failures), the on/off
  switch, and the lazy default evidence path.

Red line: enforcement_hub/hard_constraints adjudication semantics are NOT
touched by this feature — the contrast tests prove decisions are identical
with the observation layer absent, working, or failing.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loop_core.capability_registry import (
    CapabilityBinding,
    CapabilityRegistry,
    sha256_file,
)
from loop_core.enforcement_hub import EnforcementHub, quick_check
from loop_core.guard_health import GuardControl, GuardHealth, GuardHealthResult
from loop_core.observability import (
    CHECK_DEATH,
    CHECK_DRIFT,
    CHECK_HEALTH,
    CHECK_INTEGRITY,
    CHECK_MISSING,
    RESULT_FAIL,
    RESULT_PASS,
    RESULT_REPORT,
    GuardCheckEvent,
    GuardEventRecorder,
)

ROOT = Path(__file__).resolve().parent.parent

EVENT_PATH = Path(".ai") / "evidence" / "observability" / "guard-events.jsonl"


# ── Helpers ────────────────────────────────────────────────────────────


def _event(recorder, guard_id, check_type, result, duration_ms=0.0,
           failure_reason=None, capability_id=None) -> GuardCheckEvent:
    event = GuardCheckEvent(
        guard_id=guard_id,
        capability_id=capability_id,
        check_type=check_type,
        result=result,
        duration_ms=duration_ms,
        failure_reason=failure_reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="registry:test",
    )
    recorder.record(event)
    return event


def _norm(results: list[GuardHealthResult]) -> list[dict]:
    """Health results minus the volatile checked_at timestamp."""
    return [{k: v for k, v in r.to_dict().items() if k != "checked_at"}
            for r in results]


def _decision_sig(decision) -> tuple:
    return (decision.allowed, decision.blocker_count,
            decision.enforcement_level.value, decision.reason,
            len(decision.violations))


def _boom(self, line):
    raise OSError("simulated observation write failure")


def _make_clean_project(root: Path) -> Path:
    """A governed project where an in-scope write is allowed (mirrors
    TestShouldAllowWrite.test_write_within_scope_allowed)."""
    import yaml
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text(
        "schema_version: 1\nproject_name: test\n"
        "current_phase: S4-implementation\nloop_mode: FULL\n",
        encoding="utf-8")
    (root / ".ai" / "gates.yaml").write_text(
        yaml.dump({"schema_version": 1, "gates": [
            {"id": "G-S1-APPROVED", "gate_type": "requirements",
             "status": "approved"},
            {"id": "G-S2-APPROVED", "gate_type": "architecture",
             "status": "approved"},
            {"id": "G-S4-APPROVED", "gate_type": "implementation",
             "status": "approved"},
            {"id": "G-S4-REVIEW", "gate_type": "implementation",
             "status": "approved"},
        ]}),
        encoding="utf-8")
    (root / ".ai" / "task_graph.yaml").write_text(
        yaml.dump({"schema_version": 1, "tasks": [
            {"id": "T-test", "status": "active",
             "allowed_paths": ["src/main.py", "tests/"]},
        ]}),
        encoding="utf-8")
    return root


def _make_corrupt_project(root: Path) -> Path:
    """Unparseable state.yaml — enforcement must FAIL CLOSED (BLOCK)."""
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "state.yaml").write_text("a: [1, 2\n", encoding="utf-8")
    return root


def _pass_scenarios(root: Path) -> list[tuple]:
    """Deterministic PASS scenarios (no governance files required)."""
    hub = EnforcementHub(root)
    return [
        _decision_sig(hub.check_role_isolation_enforcement("dev", "reviewer")),
        _decision_sig(hub.check_evidence_freshness_enforcement()),
    ]


def _block_scenarios(root: Path) -> list[tuple]:
    """Deterministic BLOCK scenarios."""
    hub = EnforcementHub(root)
    return [
        _decision_sig(hub.should_allow_write("outside.py", ["src/main.py"])),
        _decision_sig(hub.check_role_isolation_enforcement("dev", "dev")),
        _decision_sig(quick_check(root)),
    ]


# ── AC-03a: events persisted, queryable after a check ──────────────────


def test_events_persisted_after_integrity_check(tmp_path):
    """AC-03a: after integrity_check() runs, events are queryable from the
    append-only file with guard_id / check_type / duration_ms / result /
    failure_reason / timestamp / source fields.  A temp project with no hook
    scripts makes every control fail fast (FileNotFoundError -> BROKEN,
    fail-closed preserved) and the default registry produces DRIFT reports;
    an unregistered checker file produces a MISSING report."""
    root = tmp_path / "proj"
    (root / ".ai" / "checkers").mkdir(parents=True)
    (root / ".ai" / "checkers" / "rogue_checker.py").write_text(
        "y = 2\n", encoding="utf-8")
    rec = GuardEventRecorder(root / EVENT_PATH)
    gh = GuardHealth(root, observability=rec)
    integrity = gh.integrity_check()

    # The check itself kept its fail-closed semantics (missing hooks -> BROKEN)
    assert integrity["overall"] == "FAIL"
    assert integrity["missing"], "fixture must produce a MISSING finding"

    lines = rec.path.read_text(encoding="utf-8").splitlines()
    events = rec.read_events()
    assert lines and len(lines) == len(events), "one JSON object per line"
    for line in lines:
        json.loads(line)  # every line parses

    # All five check types are recorded by one integrity check
    types = {e.check_type for e in events}
    assert types == {CHECK_HEALTH, CHECK_DEATH, CHECK_MISSING, CHECK_DRIFT,
                     CHECK_INTEGRITY}

    # health events: one per battery control.  In this tmp project every hook
    # script is missing — the python interpreter itself exits rc=2 ("can't open
    # file"), which the battery reads as a DENY: the 5 negative controls appear
    # blocked (health PASS), the 3 positive controls appear blocked too
    # (health FAIL, reason recorded).
    health = [e for e in events if e.check_type == CHECK_HEALTH]
    assert len(health) == len(gh.battery())
    pass_health = [e for e in health if e.result == RESULT_PASS]
    fail_health = [e for e in health if e.result == RESULT_FAIL]
    assert len(pass_health) == 5 and len(fail_health) == 3
    assert all(e.failure_reason is None for e in pass_health)
    assert all("expected PASS got block" in e.failure_reason for e in fail_health)
    for e in health:
        assert e.guard_id in {"gate_guard", "content_guard",
                              "bash_content_guard", "ledger_guard", "path_guard"}
        assert isinstance(e.duration_ms, float) and e.duration_ms >= 0
        assert e.timestamp
        assert e.source.startswith("registry:")
        assert e.event_id

    # death events: one per guard — ledger_guard/path_guard have only negative
    # controls (all blocked -> ALIVE -> PASS); the three multi-control guards
    # are BROKEN (a positive control got blocked) -> FAIL.  The fail-closed
    # overall verdict stays FAIL.
    death = [e for e in events if e.check_type == CHECK_DEATH]
    assert len(death) == 5
    assert {e.guard_id for e in death if e.result == RESULT_PASS} == {
        "ledger_guard", "path_guard"}
    dead = [e for e in death if e.result == RESULT_FAIL]
    assert {e.guard_id for e in dead} == {
        "gate_guard", "content_guard", "bash_content_guard"}
    assert all(e.failure_reason for e in dead)

    # missing/drift are REPORT-level events with a reason — never a verdict
    missing = [e for e in events if e.check_type == CHECK_MISSING]
    assert len(missing) == 1
    assert missing[0].result == RESULT_REPORT
    assert ".ai/checkers/rogue_checker.py" in missing[0].guard_id
    drift = [e for e in events if e.check_type == CHECK_DRIFT]
    assert drift and all(e.result == RESULT_REPORT for e in drift)
    assert all(e.capability_id for e in drift), "drift events carry the binding id"

    # integrity: exactly one event, matching the returned overall verdict
    integrity_events = [e for e in events if e.check_type == CHECK_INTEGRITY]
    assert len(integrity_events) == 1
    assert integrity_events[0].result == integrity["overall"]


def test_health_pass_and_death_alive_events_recorded(monkeypatch, tmp_path):
    """AC-03a (PASS side): a healthy control records a PASS health event and a
    death event with result PASS (ALIVE) — recorded on the real repo with a
    minimal battery so the run is fast and deterministic."""
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    gh = GuardHealth(ROOT, observability=rec)
    monkeypatch.setattr(GuardHealth, "battery", lambda self: [
        GuardControl("GC-003", "content_guard", "clean content passes",
                     "positive",
                     {"tool_name": "Write",
                      "tool_input": {"file_path": "tests/tmp_clean_test.py",
                                     "content": "x = 1\n"}}, False),
    ])
    results = gh.run()
    assert results[0].status == "ALIVE"

    events = rec.read_events()
    health = [e for e in events if e.check_type == CHECK_HEALTH]
    assert len(health) == 1 and health[0].result == RESULT_PASS
    assert health[0].failure_reason is None
    death = [e for e in events if e.check_type == CHECK_DEATH]
    assert len(death) == 1 and death[0].result == RESULT_PASS
    assert death[0].guard_id == "content_guard"


def test_integrity_pass_event_recorded(monkeypatch, tmp_path):
    """AC-03a: a PASS integrity verdict records a PASS integrity event even
    when missing/drift scans are clean."""
    impl = tmp_path / ".ai" / "checkers" / "compile_gate.py"
    impl.parent.mkdir(parents=True)
    impl.write_text("x = 1\n", encoding="utf-8")
    registry = CapabilityRegistry()
    registry.register(CapabilityBinding(
        capability_id="compile_gate", provider_id="checker",
        implementation_path=".ai/checkers/compile_gate.py",
        version="v1", contract_version="checker-result.schema.yaml@1",
        implementation_hash=sha256_file(impl)))
    registry.seal()
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    gh = GuardHealth(tmp_path, registry=registry, observability=rec)
    monkeypatch.setattr(GuardHealth, "run", lambda self: [GuardHealthResult(
        guard="gate_guard", status="ALIVE", blocked=1, negative_total=1,
        allowed=1, positive_total=1, errors=[])])

    integrity = gh.integrity_check()
    assert integrity["overall"] == "PASS"
    assert integrity["missing"] == [] and integrity["drift"] == []

    events = rec.read_events()
    integrity_events = [e for e in events if e.check_type == CHECK_INTEGRITY]
    assert len(integrity_events) == 1
    assert integrity_events[0].result == RESULT_PASS
    assert integrity_events[0].failure_reason is None


# ── AC-03b: observation failures never block business ──────────────────


def test_observation_failure_never_blocks_guard_health(monkeypatch, tmp_path):
    """AC-03b: a throwing observation write leaves the health-check business
    result identical; the failure is counted in-memory, never raised."""
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    gh_ok = GuardHealth(tmp_path, observability=rec)
    results_ok = gh_ok.run()
    event_count = len(rec.read_events())
    assert event_count > 0

    monkeypatch.setattr(GuardEventRecorder, "_append_line", _boom)
    gh_bad = GuardHealth(tmp_path, observability=rec)
    results_bad = gh_bad.run()  # must complete without raising

    assert _norm(results_bad) == _norm(results_ok)
    assert rec.failures == event_count, "every observation write failed and was counted"
    assert rec.last_error and "simulated observation write failure" in rec.last_error
    # the failed writes left the readable history intact (nothing partial)
    assert len(rec.read_events()) == event_count


def test_observation_failure_does_not_swallow_safety_block(monkeypatch, tmp_path):
    """AC-03b / red line: while the observation layer is failing, the safety
    BLOCK (fail-closed) still fires — an observation exception never swallows
    the security verdict, and the enforcement path never touches the recorder."""
    root = _make_corrupt_project(tmp_path / "proj")
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    monkeypatch.setattr(GuardEventRecorder, "_append_line", _boom)

    hub = EnforcementHub(root)
    decision = hub.should_allow_write("x.py", allowed_paths=["x.py"])

    assert decision.allowed is False
    assert decision.blocker_count == 1
    assert "FAIL CLOSED" in decision.reason
    assert rec.failures == 0, "enforcement has zero coupling to the recorder"


# ── AC-03c: observability switch never changes BLOCK/PASS ──────────────


def test_observability_state_never_changes_enforcement_verdicts(tmp_path, monkeypatch):
    """AC-03c contrast: enforcement verdicts (BLOCK stays BLOCK, PASS stays
    PASS) are identical with the observation layer absent, working, or
    failing — EnforcementHub is fully independent of it."""
    clean = _make_clean_project(tmp_path / "clean")
    blocked = _make_clean_project(tmp_path / "blocked")
    import yaml
    (blocked / ".ai" / "gates.yaml").write_text(
        yaml.dump({"schema_version": 1, "gates": [
            {"id": "G-B", "status": "blocked"},
        ]}),
        encoding="utf-8")
    corrupt = _make_corrupt_project(tmp_path / "corrupt")
    rec = GuardEventRecorder(tmp_path / "events.jsonl")

    def all_scenarios(root: Path) -> list[tuple]:
        return _pass_scenarios(root) + _block_scenarios(root)

    baseline = (all_scenarios(clean) + all_scenarios(blocked)
                + all_scenarios(corrupt))
    working = (all_scenarios(clean) + all_scenarios(blocked)
               + all_scenarios(corrupt))
    assert len(rec.read_events()) == 0, "adjudication writes nothing to the recorder"

    monkeypatch.setattr(GuardEventRecorder, "_append_line", _boom)
    failing = (all_scenarios(clean) + all_scenarios(blocked)
               + all_scenarios(corrupt))

    assert failing == working == baseline
    # explicit contrast: the PASS scenarios stayed PASS, the BLOCK scenarios
    # (out-of-scope write, self-review, blocked/fail-closed quick_check) stayed
    # BLOCK — in every observability state, including the failing one.
    assert all(s[0] is True for s in _pass_scenarios(clean))
    blocks = _block_scenarios(blocked) + _block_scenarios(corrupt)
    assert all(s[0] is False for s in blocks)
    assert rec.failures == 0


def test_observability_switch_never_changes_health_results(monkeypatch, tmp_path):
    """AC-03c (guard side): health verdicts are identical whether observation
    is on, off, or failing."""
    on = GuardHealth(tmp_path, observability=GuardEventRecorder(tmp_path / "a.jsonl")).run()
    off = GuardHealth(tmp_path, observability=False).run()
    monkeypatch.setattr(GuardEventRecorder, "_append_line", _boom)
    failing = GuardHealth(
        tmp_path, observability=GuardEventRecorder(tmp_path / "b.jsonl")
    ).run()
    assert _norm(failing) == _norm(on) == _norm(off)


# ── AC-03d: append-only — history is never rewritten ───────────────────


def test_event_file_is_append_only_never_rewrites_history(tmp_path):
    """AC-03d: earlier event lines are byte-identical after later writes —
    nothing is rewritten, reordered, or truncated."""
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    e1 = _event(rec, "gate_guard", CHECK_HEALTH, RESULT_PASS, duration_ms=1.0)
    line_after_first = rec.path.read_text(encoding="utf-8")

    e2 = _event(rec, "content_guard", CHECK_DEATH, RESULT_FAIL,
                duration_ms=2.0, failure_reason="expected BLOCK got pass")
    line_after_second = rec.path.read_text(encoding="utf-8")
    assert line_after_second.startswith(line_after_first)

    e3 = _event(rec, "guard_health", CHECK_INTEGRITY, RESULT_PASS, duration_ms=3.0)
    lines = rec.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert lines[0] == line_after_first.strip(), "first event line unchanged"
    assert lines[1] == line_after_second.splitlines()[1], "second event line unchanged"

    events = rec.read_events()
    assert [e.event_id for e in events] == [e1.event_id, e2.event_id, e3.event_id]
    assert [e.guard_id for e in events] == ["gate_guard", "content_guard",
                                            "guard_health"]


# ── Aggregation query: summary() ───────────────────────────────────────


def test_summary_aggregates_frequency_duration_failures(tmp_path):
    """summary(): per guard / per result — frequency, duration (total/avg/max)
    and failure counts; observation-layer failures are surfaced separately."""
    rec = GuardEventRecorder(tmp_path / "events.jsonl")
    _event(rec, "content_guard", CHECK_HEALTH, RESULT_PASS, duration_ms=10.0)
    _event(rec, "content_guard", CHECK_HEALTH, RESULT_FAIL, duration_ms=30.0,
           failure_reason="boom")
    _event(rec, "gate_guard", CHECK_DEATH, RESULT_PASS, duration_ms=5.0)
    _event(rec, "gate_guard", CHECK_DEATH, RESULT_FAIL, duration_ms=15.0,
           failure_reason="dormant")

    s = rec.summary()
    assert s["total_events"] == 4
    assert s["by_result"] == {RESULT_PASS: 2, RESULT_FAIL: 2}
    assert s["observability_failures"] == 0

    cg = s["by_guard"]["content_guard"]
    assert cg["total"] == 2 and cg["failures"] == 1
    assert cg["results"] == {RESULT_PASS: 1, RESULT_FAIL: 1}
    assert cg["duration_ms"]["total"] == 40.0
    assert cg["duration_ms"]["avg"] == 20.0
    assert cg["duration_ms"]["max"] == 30.0

    gg = s["by_guard"]["gate_guard"]
    assert gg["total"] == 2 and gg["failures"] == 1
    assert gg["results"] == {RESULT_PASS: 1, RESULT_FAIL: 1}
    assert gg["duration_ms"]["avg"] == 10.0


# ── Switch / laziness / default evidence path ──────────────────────────


def test_recorder_can_be_disabled(tmp_path):
    """可开关: a disabled recorder is a no-op and creates no file; enabling it
    resumes recording."""
    rec = GuardEventRecorder(tmp_path / "events.jsonl", enabled=False)
    _event(rec, "g", CHECK_HEALTH, RESULT_PASS)
    assert not rec.path.exists()
    rec.set_enabled(True)
    _event(rec, "g", CHECK_HEALTH, RESULT_PASS)
    assert rec.path.exists()
    assert len(rec.read_events()) == 1


def test_guard_health_observability_switch_off_creates_no_file(tmp_path):
    """可开关 (GuardHealth level): observability=False means no recorder, no
    evidence file — and the health check still runs normally."""
    gh = GuardHealth(tmp_path, observability=False)
    results = gh.run()
    assert results, "health check business unaffected"
    assert not (tmp_path / EVENT_PATH).exists()


def test_guard_health_default_recorder_uses_evidence_path(tmp_path):
    """默认开且惰性: with no observability argument, events land at
    <root>/.ai/evidence/observability/guard-events.jsonl and no file is
    created before the first check."""
    gh = GuardHealth(tmp_path)
    assert not (tmp_path / EVENT_PATH).exists(), "lazy: no file before first event"
    gh.run()
    events = gh.observability.read_events()
    assert (tmp_path / EVENT_PATH).exists()
    assert events and all(e.source.startswith("registry:") for e in events)


def test_custom_recorder_path_is_honored(tmp_path):
    """A caller-provided GuardEventRecorder overrides the default path."""
    custom = tmp_path / "custom" / "events.jsonl"
    rec = GuardEventRecorder(custom)
    gh = GuardHealth(tmp_path, observability=rec)
    gh.run()
    assert custom.exists()
    assert not (tmp_path / EVENT_PATH).exists()
    assert rec.read_events()


# ═══════════════════════════════════════════════════════════════════════
# T-0095 item 3: guard-events.jsonl 轮转/上限（AC-03）
# ═══════════════════════════════════════════════════════════════════════


class TestT0095EventRotation:
    """Rotation on line/byte thresholds with archive retention — no event
    loss while an archive slot remains."""

    def _event_id(self, rec, guard_id="g_rot", seq=0):
        event = GuardCheckEvent(
            guard_id=guard_id, check_type=CHECK_HEALTH, result=RESULT_PASS,
            duration_ms=1.0, timestamp=datetime.now(timezone.utc).isoformat(),
            source="registry:test",
        )
        rec.record(event)
        return event.event_id

    def test_line_threshold_rotates_and_no_event_lost(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path, max_lines=3, max_bytes=1 << 30,
                                 max_archives=2)
        ids = [self._event_id(rec) for _ in range(4)]
        # after 4 records the file rotated at least once: main holds <= 3
        # lines and the archive holds the overflow
        assert path.exists()
        main_lines = len(path.read_text(encoding="utf-8").splitlines())
        assert main_lines <= 3, main_lines
        archive = Path(f"{path}.1")
        assert archive.exists(), "rotation must create the .1 archive"
        # every event is still readable through the recorder (no loss)
        seen = [e.event_id for e in rec.read_events()]
        assert seen == ids, "rotation must not lose or reorder events"

    def test_byte_threshold_triggers_rotation(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path, max_lines=1 << 30, max_bytes=64,
                                 max_archives=2)
        self._event_id(rec)
        self._event_id(rec)
        assert Path(f"{path}.1").exists(), "byte threshold must rotate"
        assert len(rec.read_events()) == 2

    def test_archive_cap_keeps_only_recent_archives(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path, max_lines=2, max_bytes=1 << 30,
                                 max_archives=1)
        # two rotations -> .2 must have been dropped, only .1 remains
        for _ in range(6):
            self._event_id(rec)
        assert Path(f"{path}.1").exists()
        assert not Path(f"{path}.2").exists()
        # dropped archive is by design; the retained window is still readable
        assert len(rec.read_events()) >= 2

    def test_below_threshold_no_rotation(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path, max_lines=100, max_bytes=1 << 30,
                                 max_archives=2)
        for _ in range(3):
            self._event_id(rec)
        assert not Path(f"{path}.1").exists()
        assert len(rec.read_events()) == 3


# ═══════════════════════════════════════════════════════════════════════
# T-0111 D4-6: 读侧损坏行计数（与写侧 failures 对称；不再静默丢弃）
# ═══════════════════════════════════════════════════════════════════════

class TestT0111ReadCorruptCounting:
    """损坏行被跳过但被计数 + warning，summary() 上报 read_corrupt_lines；
    可读历史（前缀与后缀）全部保留。"""

    def test_corrupt_line_counted_history_preserved(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path)
        good1 = _event(rec, "gate_guard", CHECK_HEALTH, RESULT_PASS)
        path.write_text(path.read_text(encoding="utf-8")
                        + "this is not json {{{[[[\n")
        good2 = _event(rec, "gate_guard", CHECK_HEALTH, RESULT_FAIL,
                       failure_reason="boom")
        s = rec.summary()  # 单次读：损坏行计 1，可读历史全部保留
        assert s["read_corrupt_lines"] == 1
        assert s["total_events"] == 2
        assert s["by_result"] == {RESULT_PASS: 1, RESULT_FAIL: 1}
        # 计数器为进程内累计（与写侧 failures 同语义）：再读一次 +1
        rec.read_events()
        assert rec.read_corrupt_lines == 2

    def test_corrupt_line_in_middle_keeps_suffix(self, tmp_path):
        """中段损坏不再截断后缀（旧实现整文件 abort，后缀丢失）。"""
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path)
        e1 = _event(rec, "gate_guard", CHECK_HEALTH, RESULT_PASS)
        raw = path.read_text(encoding="utf-8")
        path.write_text(raw + "corrupt {{{\n")
        e2 = _event(rec, "gate_guard", CHECK_HEALTH, RESULT_PASS)
        events = rec.read_events()
        assert [e.event_id for e in events] == [e1.event_id, e2.event_id]
        assert rec.read_corrupt_lines == 1

    def test_corrupt_line_in_archive_counted(self, tmp_path):
        """轮转归档内的损坏行同样计数（读归档与读主文件一致）。"""
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path, max_lines=2, max_bytes=1 << 30,
                                 max_archives=2)
        for _ in range(3):
            _event(rec, "g_rot", CHECK_HEALTH, RESULT_PASS)
        archive = Path(f"{path}.1")
        assert archive.exists()
        archive.write_text(archive.read_text(encoding="utf-8")
                           + "broken {{{\n")
        events = rec.read_events()
        assert rec.read_corrupt_lines == 1
        assert len(events) == 3

    def test_repair_check_type_constant_and_recording(self, tmp_path):
        """T-0111: check_type="repair" 事件常量 + 记录 + 回读（AC-01
        事件层断言，与 tools 写入点同 schema）。"""
        from loop_core.observability import CHECK_REPAIR
        assert CHECK_REPAIR == "repair"
        path = tmp_path / "events.jsonl"
        rec = GuardEventRecorder(path)
        event = GuardCheckEvent(
            guard_id="repair_continuity",
            check_type=CHECK_REPAIR,
            result=RESULT_PASS,
            duration_ms=0.0,
            failure_reason="SOURCE_DRIFT fixed=1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="tool:validate_state",
        )
        rec.record(event)
        read = rec.read_events()
        assert len(read) == 1
        assert read[0].check_type == CHECK_REPAIR
        assert read[0].guard_id == "repair_continuity"
        assert read[0].result == RESULT_PASS
        assert "fixed=1" in read[0].failure_reason


def test_rotation_failure_never_blocks_recording(tmp_path, monkeypatch):
    """A rotation that cannot happen (archive rename fails) must not make
    record() fail — observation never blocks the business path."""
    path = tmp_path / "events.jsonl"
    rec = GuardEventRecorder(path, max_lines=1, max_bytes=1 << 30,
                             max_archives=1)
    _event(rec, "g_rot", CHECK_HEALTH, RESULT_PASS)

    def _broken_replace(src, dst):
        raise OSError("simulated rotation rename failure")

    monkeypatch.setattr("loop_core.observability.os.replace",
                        _broken_replace)
    # record() must still succeed (append proceeds) — no exception and
    # no observation failure counted
    _event(rec, "g_rot", CHECK_HEALTH, RESULT_PASS)
    assert rec.failures == 0
    assert len(rec.read_events()) == 2
