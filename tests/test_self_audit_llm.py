"""
T-0091 AC-03 — self-audit LLM stage wiring tests (tools/loop_self_audit.py).

Fully mocked — no real network, no real config, no child processes:
- loop_self_audit.run is monkeypatched: every rule-based check returns a
  canned dict, so no subprocess ever starts;
- loop_self_audit.resolve_model_config is monkeypatched: a fixture
  ResolvedModelConfig (sk-test- fake key, .invalid base URL) or an
  LLMKeyError — the real ~/.zcode/v2/config.json is never read;
- the two driver classes the tool references are monkeypatched with fakes
  whose complete_json returns fixed JSON (or raises LLMError);
- PROJECT_ROOT is monkeypatched to tmp_path so every report lands under
  tmp_path/.ai/... — the real .ai/ tree is never touched;
- git_commit is monkeypatched (no git invocation).

AC mapping:
  AC-03a test_ac03a_*                  rule results -> LLM analysis -> report
                                       on disk (llm_status/model info masked/
                                       findings); driver picked by protocol;
                                       --provider/--model pass-through
  AC-03b test_ac03b_*                  config missing (KEY_MISSING / NO_MODEL)
                                       -> SKIPPED, rule results kept
  AC-03c test_ac03c_*                  LLM call failure (retry exhaustion /
                                       JSON not repairable) -> DEGRADED, rule
                                       results kept
  AC-03d test_ac03d_*                  no --llm -> behavior identical to the
                                       pre-T-0091 tool (structure/exit code/
                                       stdout; no LLM report)
  AC-03e test_ac03e_*                  reports contain no key / no internal
                                       address (synthetic 10.9.9.9 URL is
                                       masked, endpoint never persisted)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import tools.loop_self_audit as tool
from loop_core.llm.errors import ErrorCode, LLMError, LLMKeyError
from loop_core.llm.protocol_driver import JSONResult
from loop_core.llm.zcode_config import ResolvedModelConfig

FAKE_KEY = "sk-test-0123456789abcdef"      # fake test-only key (never real)
BASE_URL = "https://llm.test.invalid/v1"   # .invalid TLD — never resolvable
FAKE_GIT = "abc1234"

FIXED_LLM_OUTPUT = {
    "findings": [
        {"severity": "high", "finding": "compile 检查失败",
         "root_cause": "最近改动引入语法错误", "suggestion": "修复后重跑 self-audit"},
        {"severity": "info", "finding": "未知严重级别",
         "root_cause": "模型输出越界", "suggestion": "归一化为 medium"},
        {"severity": "low", "finding": "输出截断提示",
         "root_cause": "摘要超过截断阈值", "suggestion": "无需操作"},
        "not-a-dict",  # dropped by normalize_findings
    ],
}


# ── fakes ──────────────────────────────────────────────────────────────────


class _RecordingDriver:
    """Base fake driver: records constructor kwargs and complete_json calls."""

    name = "recording-driver"
    instances: list = []

    def __init__(self, **kwargs):
        type(self).instances.append(self)
        self.kwargs = kwargs
        self.calls: list = []

    def complete_json(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return JSONResult(
            text=json.dumps(FIXED_LLM_OUTPUT, ensure_ascii=False),
            data=FIXED_LLM_OUTPUT,
            model=kwargs.get("model") or "fake-model",
            operation=kwargs.get("operation", "audit"),
            attempts=1,
            repair_strategy="identity",
        )


class FakeAnthropicDriver(_RecordingDriver):
    name = "fake-anthropic-driver"
    instances = []


class FakeOpenAIDriver(_RecordingDriver):
    name = "fake-openai-driver"
    instances = []


# ── fixtures / helpers ─────────────────────────────────────────────────────


@pytest.fixture
def audit_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect every report under tmp_path, neutralise git, and install the
    fake driver classes — no test can touch the real .ai/ tree or start a
    subprocess."""
    monkeypatch.setattr(tool, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tool, "git_commit", lambda: FAKE_GIT)
    FakeAnthropicDriver.instances.clear()
    FakeOpenAIDriver.instances.clear()
    monkeypatch.setattr(tool, "AnthropicMessagesDriver", FakeAnthropicDriver)
    monkeypatch.setattr(tool, "OpenAICompatibleDriver", FakeOpenAIDriver)
    return tmp_path


def _config(protocol: str = "openai", model: str = "fixture-model",
            base_url: str = BASE_URL) -> ResolvedModelConfig:
    return ResolvedModelConfig(
        api_key=FAKE_KEY,
        provider_id="fixture-provider",
        model=model,
        base_url=base_url,
        protocol=protocol,
        source="file:fixture-provider",
    )


def _fake_run_all_pass(cmd: list, timeout: int = 300) -> dict:
    return {"rc": 0, "stdout": f"ok {cmd[0]}", "stderr": ""}


def _fake_run_compile_fails(cmd: list, timeout: int = 300) -> dict:
    if "compileall" in cmd:
        return {"rc": 1, "stdout": "compile failed",
                "stderr": "SyntaxError in loop_core/x.py"}
    return {"rc": 0, "stdout": "ok", "stderr": ""}


def _run_main(monkeypatch: pytest.MonkeyPatch, argv: list, run_fn) -> int:
    monkeypatch.setattr(tool, "run", run_fn)
    monkeypatch.setattr(sys, "argv", ["loop_self_audit", *argv])
    return tool.main()


def _read_rule_report(root: Path) -> dict:
    p = root / ".ai" / "evidence" / "T-0083" / "guard-health" / "self-audit.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _read_llm_report(root: Path) -> dict:
    p = root / ".ai" / "evidence" / "observability" / "self-audit-llm.json"
    return json.loads(p.read_text(encoding="utf-8"))


# ── AC-03a: wiring (rule results -> LLM analysis -> report on disk) ────────


@pytest.mark.parametrize("protocol", ["openai", "anthropic"])
def test_ac03a_llm_stage_wires_rule_results_and_writes_report(
        audit_env, monkeypatch, tmp_path, capsys, protocol):
    root = audit_env
    monkeypatch.setattr(tool, "resolve_model_config",
                        lambda **kw: _config(protocol=protocol))
    rc = _run_main(monkeypatch, ["--llm"], _fake_run_compile_fails)

    # rule-based verdict is untouched by the LLM stage
    assert rc == 2
    rule = _read_rule_report(root)
    assert rule["overall"] == "FAIL"
    assert rule["failed"] == ["compile"]

    # LLM report on disk with llm_status + masked model info + findings
    llm = _read_llm_report(root)
    assert llm["tool"] == "loop_self_audit"
    assert llm["kind"] == "llm-analysis"
    assert llm["llm_status"] == "OK"
    assert llm["git_commit"] == FAKE_GIT
    assert llm["timestamp"] == rule["timestamp"]
    assert llm["model"]["provider_id"] == "fixture-provider"
    assert llm["model"]["model"] == "fixture-model"
    assert llm["model"]["api_key"] == "<REDACTED>"
    assert llm["model"]["base_url"] == "<REDACTED>"
    assert llm["model"]["protocol"] == protocol
    assert llm["model"]["source"] == "file:fixture-provider"

    findings = llm["findings"]
    assert len(findings) == 3                       # non-dict item dropped
    assert set(findings[0]) == {"severity", "finding", "root_cause", "suggestion"}
    assert findings[0]["severity"] == "high"
    assert findings[1]["severity"] == "medium"      # "info" normalized
    assert findings[0]["finding"] == "compile 检查失败"

    # protocol -> driver selection
    if protocol == "anthropic":
        assert len(FakeAnthropicDriver.instances) == 1
        assert len(FakeOpenAIDriver.instances) == 0
        driver = FakeAnthropicDriver.instances[0]
    else:
        assert len(FakeOpenAIDriver.instances) == 1
        assert len(FakeAnthropicDriver.instances) == 0
        driver = FakeOpenAIDriver.instances[0]

    # the key/endpoint reached the driver (runtime use) but nothing else
    assert driver.kwargs["api_key"] == FAKE_KEY
    assert driver.kwargs["base_url"] == BASE_URL
    assert driver.kwargs["default_model"] == "fixture-model"

    # the redacted rule-based summary reached the LLM as the user message
    messages, call_kwargs = driver.calls[0]
    assert messages[0]["role"] == "system"
    assert call_kwargs["operation"] == "audit"
    user = messages[1]["content"]
    assert '"checks"' in user and '"compile"' in user and '"rc": 1' in user
    assert '"stdout_tail"' in user

    # summary embedded in the report; completion metadata recorded
    assert llm["analysis_summary"]["overall"] == "FAIL"
    assert llm["analysis_summary"]["checks"]["compile"]["status"] == "FAIL"
    assert llm["completion"]["repair_strategy"] == "identity"
    assert llm["completion"]["attempts"] == 1

    # stdout carries llm_status in --llm mode
    out = capsys.readouterr().out
    assert '"llm_status": "OK"' in out


def test_ac03a_provider_model_flags_passthrough(audit_env, monkeypatch, tmp_path):
    root = audit_env
    seen = {}

    def resolver(**kwargs):
        seen.update(kwargs)
        return _config()

    monkeypatch.setattr(tool, "resolve_model_config", resolver)
    rc = _run_main(monkeypatch, ["--llm", "--provider", "acme", "--model", "m-alpha"],
                   _fake_run_all_pass)
    assert rc == 0
    assert seen == {"preferred_provider": "acme", "preferred_model": "m-alpha"}
    assert _read_llm_report(root)["llm_status"] == "OK"


# ── AC-03b: config missing -> SKIPPED, rule results kept ───────────────────


def test_ac03b_config_missing_skips_llm_and_keeps_rule_results(audit_env, monkeypatch, tmp_path):
    root = audit_env

    def missing(**kwargs):
        raise LLMKeyError(
            "LLM model config missing: no API key in environment (checked: "
            "LLM_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, ZCODE_API_KEY) "
            "and no enabled provider with a non-empty api key in ZCode config "
            "~/.zcode/v2/config.json (set an environment variable or add "
            "options.apiKey to a provider).",
        )

    monkeypatch.setattr(tool, "resolve_model_config", missing)
    rc = _run_main(monkeypatch, ["--llm"], _fake_run_all_pass)

    assert rc == 0                                   # rule audit still passes
    rule = _read_rule_report(root)
    assert rule["overall"] == "PASS" and rule["failed"] == []

    llm = _read_llm_report(root)
    assert llm["llm_status"] == "SKIPPED"
    assert llm["reason"] == "KEY_MISSING"
    assert "LLM_API_KEY" in llm["detail"]            # enabling hint survives
    assert "findings" not in llm
    assert "llm_error" not in llm
    assert "model" not in llm
    assert llm["analysis_summary"]["overall"] == "PASS"
    # no driver was ever constructed; no key material persisted
    assert not FakeAnthropicDriver.instances
    assert not FakeOpenAIDriver.instances
    assert FAKE_KEY not in json.dumps(llm, ensure_ascii=False)


def test_ac03b_resolved_config_without_model_skips_llm(audit_env, monkeypatch, tmp_path):
    root = audit_env
    monkeypatch.setattr(tool, "resolve_model_config",
                        lambda **kw: _config(model=""))
    rc = _run_main(monkeypatch, ["--llm"], _fake_run_all_pass)
    assert rc == 0
    llm = _read_llm_report(root)
    assert llm["llm_status"] == "SKIPPED"
    assert llm["reason"] == "NO_MODEL"
    assert "--model" in llm["detail"]
    assert not FakeAnthropicDriver.instances and not FakeOpenAIDriver.instances


# ── AC-03c: LLM call failure -> DEGRADED, rule results kept ────────────────


@pytest.mark.parametrize("error", [
    LLMError(ErrorCode.SERVER_ERROR,
             "simulated upstream failure after retry exhaustion",
             operation="audit", attempts=3),
    LLMError(ErrorCode.INVALID_RESPONSE,
             "JSON repair failed for op=audit: fragment not parseable",
             operation="audit", attempts=3),
])
def test_ac03c_llm_failure_degrades_and_keeps_rule_results(audit_env, monkeypatch, tmp_path, error):
    root = audit_env
    monkeypatch.setattr(tool, "resolve_model_config", lambda **kw: _config())

    class RaisingDriver(_RecordingDriver):
        instances = []

        def complete_json(self, messages, **kwargs):
            self.calls.append((messages, kwargs))
            raise error

    monkeypatch.setattr(tool, "OpenAICompatibleDriver", RaisingDriver)
    rc = _run_main(monkeypatch, ["--llm"], _fake_run_compile_fails)

    # rule-based verdict preserved exactly
    assert rc == 2
    rule = _read_rule_report(root)
    assert rule["overall"] == "FAIL" and rule["failed"] == ["compile"]

    llm = _read_llm_report(root)
    assert llm["llm_status"] == "DEGRADED"
    assert llm["llm_error"]["error_code"] == error.code.value
    assert "findings" not in llm
    assert llm["model"]["api_key"] == "<REDACTED>"
    assert llm["analysis_summary"]["overall"] == "FAIL"
    assert FAKE_KEY not in json.dumps(llm, ensure_ascii=False)
    assert BASE_URL not in json.dumps(llm, ensure_ascii=False)


# ── AC-03d: no --llm -> behavior identical to pre-T-0091 ───────────────────


def test_ac03d_without_llm_flag_behavior_unchanged(audit_env, monkeypatch, tmp_path, capsys):
    root = audit_env

    # resolve_model_config / drivers must never be touched without --llm
    def forbidden(**kwargs):
        raise AssertionError("resolve_model_config must not run without --llm")

    monkeypatch.setattr(tool, "resolve_model_config", forbidden)
    rc = _run_main(monkeypatch, [], _fake_run_all_pass)

    assert rc == 0
    rule = _read_rule_report(root)
    assert set(rule) == {"tool", "version", "timestamp", "git_commit",
                         "results", "failed", "overall"}
    assert rule["tool"] == "loop_self_audit" and rule["version"] == "1.0"
    assert rule["git_commit"] == FAKE_GIT
    assert set(rule["results"]) == {"validate_state", "guard_health", "compile",
                                    "pytest_core", "security_scan", "static_analysis"}
    assert rule["failed"] == [] and rule["overall"] == "PASS"
    assert not (root / ".ai" / "evidence" / "observability" / "self-audit-llm.json").exists()
    assert not FakeAnthropicDriver.instances and not FakeOpenAIDriver.instances
    out = capsys.readouterr().out
    assert '"llm_status"' not in out                  # pre-T-0091 stdout shape

    # --quick path unchanged (only the two core checks)
    rc = _run_main(monkeypatch, ["--quick"], _fake_run_all_pass)
    assert rc == 0
    rule = _read_rule_report(root)
    assert set(rule["results"]) == {"validate_state", "guard_health"}
    assert not (root / ".ai" / "evidence" / "observability" / "self-audit-llm.json").exists()


# ── AC-03e: no key / no internal address in reports ────────────────────────


def test_ac03e_reports_contain_no_key_or_internal_address(audit_env, monkeypatch, tmp_path):
    root = audit_env
    monkeypatch.setattr(tool, "resolve_model_config", lambda **kw: _config())

    # one rule check emits secret-like material (synthetic values only) —
    # the summary must redact it before the prompt and before the report
    def _fake_run_leaky(cmd: list, timeout: int = 300) -> dict:
        if any("loop_guard_health" in str(part) for part in cmd):
            return {"rc": 0,
                    "stdout": "guard health https://10.9.9.9:3000/v1 ok",
                    "stderr": "token sk-leak-abcdef123456"}
        return {"rc": 0, "stdout": "ok", "stderr": ""}

    rc = _run_main(monkeypatch, ["--llm"], _fake_run_leaky)
    assert rc == 0

    llm_text = (root / ".ai" / "evidence" / "observability"
                / "self-audit-llm.json").read_text(encoding="utf-8")
    llm = json.loads(llm_text)

    # no fake key, no synthetic internal address, no endpoint anywhere
    assert FAKE_KEY not in llm_text
    assert "sk-test-" not in llm_text
    assert "sk-leak-" not in llm_text                 # summary redaction works
    assert "10.9.9.9" not in llm_text                 # IP-literal URL masked
    assert "localhost" not in llm_text
    assert "http://" not in llm_text                  # endpoint never persisted
    assert "llm.test.invalid" not in llm_text
    assert "<REDACTED>" in llm_text                   # masking actually applied

    # the redaction reached the prompt sent to the LLM
    driver = FakeOpenAIDriver.instances[0]
    user = driver.calls[0][0][1]["content"]
    assert "10.9.9.9" not in user and "sk-leak-" not in user
    assert "<REDACTED>" in user

    # the persisted summary embeds the redacted tails
    tail = llm["analysis_summary"]["checks"]["guard_health"]["stdout_tail"]
    assert "10.9.9.9" not in tail and "<REDACTED>" in tail

    # the rule-based report (pre-existing artifact) is untouched by LLM logic
    rule_text = (root / ".ai" / "evidence" / "T-0083" / "guard-health"
                 / "self-audit.json").read_text(encoding="utf-8")
    assert FAKE_KEY not in rule_text


def test_ac03e_skipped_and_degraded_reports_also_redacted(audit_env, monkeypatch, tmp_path):
    """SKIPPED / DEGRADED reports carry the same no-secret guarantee."""
    root = audit_env

    # SKIPPED: the KEY_MISSING hint must not echo any key value
    def missing(**kwargs):
        raise LLMKeyError(f"no key found for provider (sk-test-{FAKE_KEY[8:]})")

    monkeypatch.setattr(tool, "resolve_model_config", missing)
    _run_main(monkeypatch, ["--llm"], _fake_run_all_pass)
    llm = _read_llm_report(root)
    assert llm["llm_status"] == "SKIPPED"
    assert "sk-test-" not in json.dumps(llm, ensure_ascii=False)
    assert "10.9.9.9" not in json.dumps(llm, ensure_ascii=False)

    # DEGRADED: an error message that echoes the endpoint is masked
    def config(**kwargs):
        return _config(base_url="http://10.9.9.9:3000")

    monkeypatch.setattr(tool, "resolve_model_config", config)

    class EchoingDriver(_RecordingDriver):
        instances = []

        def complete_json(self, messages, **kwargs):
            raise LLMError(ErrorCode.CONNECTION_ERROR,
                           f"connect failed to http://10.9.9.9:3000/v1")

    monkeypatch.setattr(tool, "OpenAICompatibleDriver", EchoingDriver)
    _run_main(monkeypatch, ["--llm"], _fake_run_all_pass)
    llm = _read_llm_report(root)
    assert llm["llm_status"] == "DEGRADED"
    assert llm["llm_error"]["error_code"] == "CONNECTION_ERROR"
    assert "10.9.9.9" not in json.dumps(llm, ensure_ascii=False)
    assert FAKE_KEY not in json.dumps(llm, ensure_ascii=False)
