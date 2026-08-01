"""T-0092 AC-01..AC-04: agent eval stack tests (loop_core/evals.py).

Covers the B1 §1 foundation:
- AC-01 schema: EvalCase fields complete; illegal cases are rejected loudly
  (EvalValidationError) — never silently coerced.
- AC-02 runner: >=3 rule assertion types scored (text_contains /
  text_matches / json_equals / exit_code), optional LLM judge (mock driver:
  success, mismatch, failure, abstain, no driver -> SKIP), exception
  isolation (one crashing case never aborts the suite).
- AC-03 report: ReportBinding-style stats/details/git_commit/timestamp and
  JSON persistence.
- AC-04 builtin samples: >=4 guard positive/negative cases, all runnable
  offline, aligned with guard_health battery GC ids.

No real LLM is ever called (driver is a scripted fake); no hooks are
invoked; no constraint semantics are touched.
"""
import json
from types import SimpleNamespace

import pytest

from loop_core.evals import (
    DEFAULT_SUITE_ID,
    EvalCase,
    EvalCaseResult,
    EvalRunner,
    EvalValidationError,
    EvalVerdict,
    ExecResult,
    build_llm_driver,
    builtin_cases,
    default_executor,
    dump_cases_yaml,
    load_cases,
    score_llm,
    score_rule,
)
from loop_core.llm.protocol_driver import JSONResult
from loop_core.verdicts import Verdict


# ── helpers ────────────────────────────────────────────────────────────────

def make_case(**overrides) -> EvalCase:
    base = {
        "case_id": "EVAL-TEST-001",
        "title": "test case",
        "input": {"tool_call": {"tool_name": "Write"},
                  "guard_response": {"decision": "block"}},
        "expected": {"decision": "block"},
        "rule": {"type": "json_equals",
                 "params": {"json_path": "guard_response.decision",
                            "expected": "block"}},
        "severity": "high",
        "version": "1",
        "tags": ["test"],
    }
    base.update(overrides)
    return EvalCase.from_dict(base)


def run(cases, **kwargs) -> list[EvalCaseResult]:
    return EvalRunner(cases, **kwargs).run()


# ── AC-01: schema validation ───────────────────────────────────────────────

class TestSchema:
    def test_legal_case_passes(self):
        c = make_case()
        assert c.case_id == "EVAL-TEST-001"
        assert c.severity == "high"
        assert c.version == "1"
        assert c.rule_type == "json_equals"
        assert c.tags == ["test"]
        assert c.to_dict()["case_id"] == "EVAL-TEST-001"

    def test_flat_rule_params_accepted(self):
        c = EvalCase.from_dict({
            "case_id": "EVAL-TEST-FLAT",
            "title": "flat rule form",
            "input": "hello world",
            "rule": {"type": "text_contains", "value": "world"},
            "severity": "low",
        })
        assert c.rule_type == "text_contains"

    def test_missing_case_id_rejected(self):
        with pytest.raises(EvalValidationError, match="case_id"):
            make_case(case_id="")

    def test_missing_title_rejected(self):
        with pytest.raises(EvalValidationError, match="title"):
            make_case(title="")

    def test_missing_input_rejected(self):
        with pytest.raises(EvalValidationError, match="input"):
            make_case(input=None)

    def test_missing_rule_rejected(self):
        with pytest.raises(EvalValidationError, match="rule"):
            make_case(rule=None)

    def test_unknown_assertion_type_rejected(self):
        with pytest.raises(EvalValidationError, match="unknown assertion type"):
            make_case(rule={"type": "regex_magic"})

    def test_invalid_severity_rejected(self):
        with pytest.raises(EvalValidationError, match="invalid severity"):
            make_case(severity="urgent")

    def test_llm_rule_missing_prompt_rejected(self):
        with pytest.raises(EvalValidationError, match="prompt"):
            make_case(rule={"type": "llm", "expected_conclusion": "PASS"})

    def test_llm_rule_bad_conclusion_rejected(self):
        with pytest.raises(EvalValidationError, match="expected_conclusion"):
            make_case(rule={"type": "llm", "prompt": "grade it",
                            "expected_conclusion": "MAYBE"})

    def test_text_matches_invalid_regex_rejected(self):
        with pytest.raises(EvalValidationError, match="not a valid regex"):
            make_case(rule={"type": "text_matches", "params": {"pattern": "(["}})

    def test_exit_code_without_command_rejected(self):
        with pytest.raises(EvalValidationError, match="command"):
            make_case(input="no command here",
                      rule={"type": "exit_code", "params": {"expected": 0}})

    def test_non_dict_entry_rejected(self):
        with pytest.raises(EvalValidationError, match="mapping"):
            EvalCase.from_dict("not-a-dict")  # type: ignore[arg-type]

    def test_duplicate_case_id_rejected_by_runner(self):
        with pytest.raises(EvalValidationError, match="duplicate case_id"):
            EvalRunner([make_case(), make_case()])


# ── AC-02: runner — rule assertions ────────────────────────────────────────

class TestRunnerRuleScoring:
    def test_text_contains_pass(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-TC-1", "title": "t", "input": "guard blocked the write",
            "rule": {"type": "text_contains", "params": {"value": "blocked"}},
            "severity": "medium",
        })
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.PASS and r.reason is None

    def test_text_contains_fail(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-TC-2", "title": "t", "input": "guard allowed the write",
            "rule": {"type": "text_contains", "params": {"values": ["blocked", "denied"]}},
            "severity": "medium",
        })
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.FAIL
        assert "missing expected substring" in r.reason

    def test_text_matches_pass_and_fail(self):
        ok = EvalCase.from_dict({
            "case_id": "EVAL-TM-1", "title": "t",
            "input": "hook path_guard: DENY rc=2",
            "rule": {"type": "text_matches",
                     "params": {"pattern": r"path_guard: (DENY|BLOCK)"}},
            "severity": "medium",
        })
        bad = EvalCase.from_dict({
            "case_id": "EVAL-TM-2", "title": "t",
            "input": "hook path_guard: allow rc=0",
            "rule": {"type": "text_matches", "params": {"pattern": r"\bDENY\b"}},
            "severity": "medium",
        })
        res = run([ok, bad]).results
        assert res[0].verdict is EvalVerdict.PASS
        assert res[1].verdict is EvalVerdict.FAIL

    def test_json_equals_pass_and_fail(self):
        ok = make_case()  # guard_response.decision == block
        bad = make_case(case_id="EVAL-JE-2",
                        input={"guard_response": {"decision": "allow"}})
        res = run([ok, bad]).results
        assert res[0].verdict is EvalVerdict.PASS
        assert res[1].verdict is EvalVerdict.FAIL
        assert "differs from expected" in res[1].reason

    def test_json_equals_unparsable_output_fails(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-JE-3", "title": "t", "input": "not json at all",
            "rule": {"type": "json_equals",
                     "params": {"expected": {"decision": "block"}}},
            "severity": "medium",
        })
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.FAIL
        assert "not valid JSON" in r.reason

    def test_json_equals_json_path_missing_field_fails(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-JE-4", "title": "t",
            "input": {"guard_response": {"decision": "block"}},
            "rule": {"type": "json_equals",
                     "params": {"json_path": "guard_response.decisions",
                                "expected": "block"}},
            "severity": "medium",
        })
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.FAIL
        assert "not found" in r.reason

    def test_exit_code_with_fake_executor(self):
        cases = [
            EvalCase.from_dict({
                "case_id": "EVAL-EC-1", "title": "t",
                "input": {"command": "ignored"},
                "rule": {"type": "exit_code", "params": {"expected": 0}},
                "severity": "low",
            }),
            EvalCase.from_dict({
                "case_id": "EVAL-EC-2", "title": "t",
                "input": {"command": "ignored"},
                "rule": {"type": "exit_code", "params": {"expected": 0}},
                "severity": "low",
            }),
        ]
        fake = {c.case_id: c for c in cases}
        def executor(case):
            return ExecResult(output="", exit_code=0 if case.case_id.endswith("1") else 3)
        res = run(cases, executor_fn=executor).results
        assert res[0].verdict is EvalVerdict.PASS
        assert res[1].verdict is EvalVerdict.FAIL
        assert "exit_code 3 != expected 0" in res[1].reason

    def test_rule_assertion_count_meets_requirement(self):
        # AC-02: >=3 rule assertion types exercised. We count the scored types.
        from loop_core.evals import RULE_ASSERTION_TYPES
        assert len(RULE_ASSERTION_TYPES) >= 3
        assert {"text_contains", "text_matches", "json_equals", "exit_code"} <= RULE_ASSERTION_TYPES


# ── AC-02: runner — LLM judge (fully mocked) ───────────────────────────────

class FakeDriver:
    """Scripted ProtocolDriver stand-in — never touches a real API."""

    def __init__(self, verdict: str = "PASS", error: Exception | None = None):
        self.verdict = verdict
        self.error = error
        self.calls: list = []

    def complete_json(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.error is not None:
            raise self.error
        return JSONResult(
            text='{"verdict": "%s"}' % self.verdict,
            data={"verdict": self.verdict, "reason": "mock"},
            model="fake-model", operation=kwargs.get("operation", "agent_eval"),
        )


def llm_case(case_id: str) -> EvalCase:
    return EvalCase.from_dict({
        "case_id": case_id, "title": "llm judge case",
        "input": {"trajectory": ["read", "write", "read"]},
        "rule": {"type": "llm", "prompt": "was the trajectory sane?",
                 "expected_conclusion": "PASS"},
        "severity": "high",
    })


class TestLLMJudge:
    def test_llm_verdict_matches_expected_passes(self):
        [r] = run([llm_case("EVAL-LLM-1")], llm_driver=FakeDriver("PASS")).results
        assert r.verdict is EvalVerdict.PASS

    def test_llm_verdict_mismatch_fails(self):
        [r] = run([llm_case("EVAL-LLM-2")], llm_driver=FakeDriver("FAIL")).results
        assert r.verdict is EvalVerdict.FAIL
        assert "judge concluded FAIL, expected PASS" in r.reason

    def test_llm_driver_failure_skips(self):
        driver = FakeDriver(error=RuntimeError("provider down"))
        [r] = run([llm_case("EVAL-LLM-3")], llm_driver=driver).results
        assert r.verdict is EvalVerdict.SKIP
        assert "failed" in r.reason

    def test_llm_judge_abstain_skips(self):
        # B1 §1.3 escape_hatch: judge may return Unknown instead of grading.
        [r] = run([llm_case("EVAL-LLM-4")], llm_driver=FakeDriver("UNKNOWN")).results
        assert r.verdict is EvalVerdict.SKIP
        assert "abstained" in r.reason

    def test_llm_non_object_response_skips(self):
        driver = FakeDriver("PASS")
        driver.complete_json = lambda *a, **k: JSONResult(
            text="[]", data=[], model="fake", operation="agent_eval")
        [r] = run([llm_case("EVAL-LLM-5")], llm_driver=driver).results
        assert r.verdict is EvalVerdict.SKIP

    def test_no_driver_skips_not_blocks(self):
        # Fail-safe: no LLM available -> SKIPPED, suite still passes.
        mixed = [
            make_case(case_id="EVAL-MIX-1"),
            llm_case("EVAL-LLM-6"),
            llm_case("EVAL-LLM-7"),
        ]
        result = run(mixed)  # no llm_driver argument
        assert result.stats["skipped"] == 2
        assert result.stats["passed"] == 1
        assert result.stats["failed"] == 0
        assert result.overall is Verdict.PASS  # SKIP never blocks

    def test_score_llm_directly_without_driver(self):
        verdict, reason = score_llm(llm_case("EVAL-LLM-8"), None)
        assert verdict is EvalVerdict.SKIP and "unavailable" in reason

    def test_build_llm_driver_returns_none_without_config(self, monkeypatch):
        # No resolvable config -> None (fail-safe), never raises.  The
        # resolver is patched so the host's real config/keys cannot leak in.
        import loop_core.llm.zcode_config as zc

        def no_config(*args, **kwargs):
            raise RuntimeError("no model config")

        monkeypatch.setattr(zc, "resolve_model_config", no_config)
        assert build_llm_driver() is None


# ── AC-02: default executor + exception isolation ──────────────────────────

class TestExecutorAndIsolation:
    def test_default_executor_runs_command_case(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-EXEC-1", "title": "subprocess case",
            "input": {"command": [__import__("sys").executable, "-c",
                                  "import sys; sys.exit(3)"]},
            "rule": {"type": "exit_code", "params": {"expected": 3}},
            "severity": "low",
        })
        exec_result = default_executor(case)
        assert exec_result.exit_code == 3
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.PASS

    def test_default_executor_timeout_is_captured_as_error(self):
        case = EvalCase.from_dict({
            "case_id": "EVAL-EXEC-2", "title": "timeout case",
            "input": {"command": [__import__("sys").executable, "-c",
                                  "import time; time.sleep(5)"]},
            "rule": {"type": "exit_code",
                     "params": {"expected": 0, "timeout": 0.3}},
            "severity": "low",
        })
        [r] = run([case]).results
        assert r.verdict is EvalVerdict.FAIL
        assert r.reason.startswith("ERROR:")
        assert "timed out" in r.reason

    def test_exception_isolation_single_case_crash(self):
        def exploding(case):
            if case.case_id == "EVAL-ISO-2":
                raise RuntimeError("executor exploded")
            return ExecResult(output=case.input)

        cases = [
            make_case(case_id="EVAL-ISO-1"),
            make_case(case_id="EVAL-ISO-2"),
            make_case(case_id="EVAL-ISO-3"),
        ]
        result = run(cases, executor_fn=exploding)
        by_id = {r.case_id: r for r in result.results}
        assert by_id["EVAL-ISO-1"].verdict is EvalVerdict.PASS
        assert by_id["EVAL-ISO-2"].verdict is EvalVerdict.FAIL
        assert by_id["EVAL-ISO-2"].reason.startswith("ERROR:")
        assert by_id["EVAL-ISO-3"].verdict is EvalVerdict.PASS
        assert result.stats["failed"] == 1 and result.stats["passed"] == 2
        assert len(result.results) == 3  # suite completed

    def test_stats_and_by_severity_aggregation(self):
        cases = [
            make_case(case_id="EVAL-AGG-1", severity="critical"),
            make_case(case_id="EVAL-AGG-2", severity="high",
                      input={"guard_response": {"decision": "allow"}}),  # fails
            llm_case("EVAL-AGG-3"),
        ]
        result = run(cases)  # no driver -> llm case skipped
        assert result.stats == {"total": 3, "passed": 1, "failed": 1, "skipped": 1}
        assert result.by_severity["critical"]["passed"] == 1
        assert result.by_severity["high"]["failed"] == 1
        assert result.by_severity["low"]["total"] == 0
        assert result.overall is Verdict.FAIL


# ── AC-03: report ──────────────────────────────────────────────────────────

class TestReport:
    def _report(self, tmp_path, cases, **kw):
        from loop_core.evals import EvalReport
        result = run(cases)
        return EvalReport(result, task_id="T-0092", phase="S6-delivery",
                          gate_id="G-T-0092-EVAL", **kw)

    def test_stats_and_details(self, tmp_path):
        from loop_core.evals import EvalReport
        report = self._report(tmp_path, [
            make_case(case_id="EVAL-RPT-1"),
            make_case(case_id="EVAL-RPT-2",
                      input={"guard_response": {"decision": "allow"}}),
            llm_case("EVAL-RPT-3"),
        ])
        d = report.to_dict()
        assert d["type"] == "eval_report"
        assert d["schema_version"] == "1"
        assert d["stats"] == {"total": 3, "passed": 1, "failed": 1, "skipped": 1}
        assert d["verdict"] == "FAIL"
        assert len(d["cases"]) == 3
        case0 = d["cases"][0]
        assert {"case_id", "severity", "result", "duration_ms", "reason"} <= set(case0)
        assert case0["case_id"] == "EVAL-RPT-1"
        assert case0["severity"] == "high"
        assert case0["result"] == "PASS"
        assert d["by_severity"]["high"]["failed"] == 1

    def test_binding_fields_present(self, tmp_path):
        from loop_core.evals import EvalReport
        report = self._report(tmp_path, [make_case(case_id="EVAL-RPT-4")])
        d = report.to_dict()
        assert d["task_id"] == "T-0092"
        assert d["phase"] == "S6-delivery"
        assert d["gate_id"] == "G-T-0092-EVAL"
        assert d["git_commit"]  # repo has a HEAD
        assert d["timestamp"]
        assert d["tool_name"] == "loop-eval"
        assert d["suite"]["suite_id"] == DEFAULT_SUITE_ID
        assert report.validate() == []

    def test_validate_lists_missing_binding_fields(self, tmp_path):
        from loop_core.evals import EvalReport
        result = run([make_case(case_id="EVAL-RPT-5")])
        report = EvalReport(result, task_id="", phase="")
        missing = report.validate()
        assert "task_id" in missing and "phase" in missing
        assert "git_commit" not in missing  # resolved from the repo

    def test_write_persists_report_json(self, tmp_path):
        from loop_core.evals import EvalReport
        report = self._report(tmp_path, [
            make_case(case_id="EVAL-RPT-6"),
            llm_case("EVAL-RPT-7"),
        ])
        out = report.write(tmp_path / "eval-report.json")
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["verdict"] == "PASS"          # SKIP does not fail
        assert payload["stats"]["skipped"] == 1
        assert payload["stats"]["passed"] == 1
        assert payload["cases"][1]["result"] == "SKIP"

    def test_skip_only_suite_verdict_is_pass(self, tmp_path):
        from loop_core.evals import EvalReport
        result = run([llm_case("EVAL-RPT-8")])  # no driver -> SKIP
        report = EvalReport(result, task_id="T-0092", phase="S6-delivery")
        assert report.verdict is Verdict.PASS


# ── AC-04: builtin guard sample set ────────────────────────────────────────

class TestBuiltinCases:
    def test_builtin_set_has_at_least_four_cases(self):
        cases = builtin_cases()
        assert len(cases) >= 4

    def test_builtin_mix_of_positive_and_negative(self):
        cases = builtin_cases()
        tags = [t for c in cases for t in c.tags]
        assert "negative" in tags and "positive" in tags
        severities = {c.severity for c in cases}
        assert {"critical", "high", "medium"} <= severities

    def test_builtin_aligned_with_guard_health_gc_ids(self):
        gc_tags = [t for c in builtin_cases() for t in c.tags
                   if t.startswith("aligns:GC-")]
        assert len(gc_tags) >= 4  # maps to guard_health battery controls

    def test_all_builtin_cases_run_pass_offline(self):
        cases = builtin_cases()
        result = run(cases)  # rule mode, no driver, no subprocess
        assert result.stats["total"] == len(cases) >= 4
        assert result.stats["failed"] == 0
        assert result.stats["passed"] == len(cases)
        assert result.overall is Verdict.PASS

    def test_builtin_yaml_export_round_trip(self, tmp_path):
        out = dump_cases_yaml(builtin_cases(), tmp_path / "builtin-cases.yaml")
        assert out.exists()
        reloaded = load_cases(out)
        assert [c.case_id for c in reloaded] == [c.case_id for c in builtin_cases()]


# ── case file loading ──────────────────────────────────────────────────────

class TestLoadCases:
    def test_load_yaml_file(self, tmp_path):
        f = tmp_path / "cases.yaml"
        f.write_text(
            "schema_version: 1\ncases:\n"
            "  - case_id: YAML-1\n    title: yaml case\n    input: hello guard\n"
            "    rule: {type: text_contains, params: {value: guard}}\n"
            "    severity: medium\n",
            encoding="utf-8",
        )
        cases = load_cases(f)
        assert len(cases) == 1 and cases[0].case_id == "YAML-1"

    def test_load_json_file(self, tmp_path):
        f = tmp_path / "cases.json"
        f.write_text(json.dumps({"cases": [
            {"case_id": "JSON-1", "title": "json case", "input": "x",
             "rule": {"type": "text_matches", "params": {"pattern": "x"}},
             "severity": "low"},
        ]}), encoding="utf-8")
        cases = load_cases(f)
        assert len(cases) == 1 and cases[0].rule_type == "text_matches"

    def test_load_rejects_illegal_case_in_file(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(
            "cases:\n  - case_id: BAD-1\n    title: bad\n    input: x\n"
            "    rule: {type: teleport}\n    severity: low\n",
            encoding="utf-8",
        )
        with pytest.raises(EvalValidationError, match="unknown assertion type"):
            load_cases(f)

    def test_unsupported_suffix_rejected(self, tmp_path):
        f = tmp_path / "cases.txt"
        f.write_text("x", encoding="utf-8")
        with pytest.raises(EvalValidationError, match="unsupported case file suffix"):
            load_cases(f)
