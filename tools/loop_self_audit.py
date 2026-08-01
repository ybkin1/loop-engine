#!/usr/bin/env python3
"""loop_self_audit.py — Loop self-audit (dogfooding) runner (T-0083 AC-04, T-0091 AC-03).

Runs the full baseline audit battery that T-0082 Phase 0 performed MANUALLY,
now scripted: validate_state + guard health + compile + pytest + security
scan + static analysis. Output: .ai/evidence/T-0083/guard-health/self-audit.json

With --llm (T-0091 AC-03): the rule-based results are collected into a
redacted summary (per-check rc/status + truncated key outputs — no keys, no
endpoints), analysed by an LLM through loop_core.llm
(resolve_model_config -> protocol driver by resolved protocol -> complete_json),
and the structured findings ({severity, finding, root_cause, suggestion}) are
written to .ai/evidence/observability/self-audit-llm.json.

Fail-safe: the LLM stage NEVER blocks the rule-based audit.  A missing/usable
config marks llm_status=SKIPPED (with the enabling hint from the resolution
error), a failed LLM call (retries exhausted / JSON not repairable) marks
llm_status=DEGRADED and keeps the rule-based result.

Usage:
  python tools/loop_self_audit.py            # full audit
  python tools/loop_self_audit.py --quick    # validate_state + guard health only
  python tools/loop_self_audit.py --llm      # + LLM semantic analysis (auto model config)
  python tools/loop_self_audit.py --llm --provider acme --model m-alpha
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_core.llm.anthropic_driver import AnthropicMessagesDriver
from loop_core.llm.errors import LLMError, LLMKeyError
from loop_core.llm.openai_driver import OpenAICompatibleDriver
from loop_core.llm.zcode_config import ResolvedModelConfig, resolve_model_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── LLM stage constants (T-0091 AC-03) ─────────────────────────────────────
LLM_OPERATION = "audit"        # output-policy operation (OUTPUT_TOKEN_CAPS)
LLM_MAX_FINDINGS = 20          # report size bound for model findings
LLM_SEVERITIES = frozenset({"high", "medium", "low"})
_FINDING_KEYS = ("severity", "finding", "root_cause", "suggestion")

# Report/prompt sanitization (AC-03e): api-key-like tokens and literal-IP /
# localhost URLs are masked in every field that lands in a report or prompt.
_SK_KEY_RE = re.compile(r"(?i)\bsk-[a-z0-9_-]{8,}\b")
_IP_URL_RE = re.compile(r"(?i)https?://(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]{1,5})?")
_LOCALHOST_URL_RE = re.compile(r"(?i)https?://localhost(?::[0-9]{1,5})?")

SYSTEM_PROMPT = (
    "你是 Loop 工程治理审计员。你会收到一次规则式自审计的结果摘要 JSON"
    "（validate_state / guard health / compile / pytest / security scan / "
    "static analysis 各检查项的 rc、状态与关键输出尾部）。"
    "请基于摘要中的事实做语义分析：识别风险发现、推断根因、给出可执行的修复建议，"
    "并只输出结构化 JSON。"
)

USER_PROMPT_TEMPLATE = (
    "规则式审计结果摘要（JSON）：\n{summary}\n\n"
    "请输出一个 JSON 对象，格式如下（不要输出其他内容）：\n"
    "{{\n"
    '  "findings": [\n'
    '    {{"severity": "high|medium|low", "finding": "风险发现", '
    '"root_cause": "根因", "suggestion": "修复建议"}}\n'
    "  ]\n"
    "}}\n"
    "约束：severity 只取 high/medium/low；findings 可为空数组；"
    "每条 finding 必须基于摘要中出现的检查项，不得编造摘要外的事实。"
)


def run(cmd: list[str], timeout: int = 300) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(PROJECT_ROOT))
        return {"rc": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"rc": -1, "stdout": "", "stderr": f"TIMEOUT>{timeout}s"}
    except FileNotFoundError:
        return {"rc": -2, "stdout": "", "stderr": "command not found"}


def git_commit() -> str:
    """Short HEAD sha (seam for tests)."""
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
        cwd=str(PROJECT_ROOT)).stdout.strip()


def rule_report_path() -> Path:
    return PROJECT_ROOT / ".ai" / "evidence" / "T-0083" / "guard-health" / "self-audit.json"


def llm_report_path() -> Path:
    return PROJECT_ROOT / ".ai" / "evidence" / "observability" / "self-audit-llm.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ── LLM stage (T-0091 AC-03) ───────────────────────────────────────────────


def sanitize_text(text: str, *, secrets: tuple[str, ...] = ()) -> str:
    """Mask api-key-like tokens, literal-IP/localhost URLs, and the exact
    secret strings the caller knows about (resolved key/endpoint).

    AC-03e: everything that lands in the LLM prompt or in the persisted
    report passes through here, so no key and no internal endpoint can leak.
    """
    if not text:
        return text
    out = text
    for secret in secrets:
        if secret and len(secret) >= 6 and secret in out:
            out = out.replace(secret, "<REDACTED>")
    out = _SK_KEY_RE.sub("<REDACTED>", out)
    out = _IP_URL_RE.sub("https://<REDACTED>", out)
    out = _LOCALHOST_URL_RE.sub("https://<REDACTED>", out)
    return out


def build_llm_summary(results: dict, failed: list) -> dict:
    """Redacted per-check summary (rc/status + truncated key outputs) that is
    sent to the LLM and embedded in the LLM report (AC-03a)."""
    checks = {}
    for name, r in results.items():
        checks[name] = {
            "rc": r.get("rc"),
            "status": "FAIL" if name in failed else "PASS",
            "stdout_tail": sanitize_text((r.get("stdout") or "")[-800:]),
            "stderr_tail": sanitize_text((r.get("stderr") or "")[-400:]),
        }
    return {
        "checks": checks,
        "failed": list(dict.fromkeys(failed)),
        "overall": "FAIL" if failed else "PASS",
    }


def _model_info(cfg: ResolvedModelConfig) -> dict:
    """Audit-safe model metadata: api_key is masked by to_dict(); the endpoint
    (which may be an internal address at runtime) is never persisted — only
    its presence is recorded."""
    info = cfg.to_dict()
    has_endpoint = bool(info.pop("base_url", ""))
    info["base_url"] = "<REDACTED>" if has_endpoint else ""
    return info


def normalize_findings(data: object) -> list[dict]:
    """Coerce the model's JSON into a bounded list of
    {severity, finding, root_cause, suggestion} dicts; unknown severities
    normalize to "medium"; non-dict items are dropped."""
    if not isinstance(data, dict):
        return []
    raw = data.get("findings")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict) or len(out) >= LLM_MAX_FINDINGS:
            continue
        finding = {}
        for key in _FINDING_KEYS:
            value = item.get(key)
            finding[key] = sanitize_text(str(value)) if value is not None else ""
        if finding["severity"] not in LLM_SEVERITIES:
            finding["severity"] = "medium"
        out.append(finding)
    return out


def _make_driver(cfg: ResolvedModelConfig):
    """Protocol driver for the resolved config (module-level class references
    let tests monkeypatch them)."""
    kwargs = dict(api_key=cfg.api_key, default_model=cfg.model or None)
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    if cfg.protocol == "anthropic":
        return AnthropicMessagesDriver(**kwargs)
    return OpenAICompatibleDriver(**kwargs)


def run_llm_stage(summary: dict, *, provider: str | None = None,
                  model: str | None = None) -> dict:
    """LLM semantic-analysis stage.  Never raises; returns a report fragment
    whose llm_status is one of OK / SKIPPED / DEGRADED.

    - config resolution failure (KEY_MISSING / CONFIGURATION_ERROR / no model)
      -> SKIPPED with the enabling hint;
    - LLM call failure (retries exhausted / JSON not repairable / auth ...)
      -> DEGRADED, rule-based results untouched;
    - success -> OK with structured findings.
    """
    fragment: dict = {"analysis_summary": summary}
    try:
        cfg = resolve_model_config(preferred_provider=provider, preferred_model=model)
    except LLMKeyError as exc:
        fragment.update(llm_status="SKIPPED", reason="KEY_MISSING",
                        detail=sanitize_text(str(exc)))
        return fragment
    except LLMError as exc:  # CONFIGURATION_ERROR etc. — also a config gap
        fragment.update(llm_status="SKIPPED", reason=exc.code.value,
                        detail=sanitize_text(str(exc)))
        return fragment
    fragment["model"] = _model_info(cfg)
    if not cfg.model:
        fragment.update(
            llm_status="SKIPPED", reason="NO_MODEL",
            detail="No model resolved for the LLM stage — set a model in the "
                   "config or pass --model <name>.",
        )
        return fragment
    try:
        driver = _make_driver(cfg)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": USER_PROMPT_TEMPLATE.format(
                 summary=json.dumps(summary, ensure_ascii=False, indent=2))},
        ]
        result = driver.complete_json(messages, operation=LLM_OPERATION,
                                      model=cfg.model, temperature=0.2)
    except LLMError as exc:
        fragment.update(
            llm_status="DEGRADED",
            llm_error={
                "error_code": exc.code.value,
                "message": sanitize_text(str(exc), secrets=(cfg.api_key, cfg.base_url)),
            },
        )
        return fragment
    fragment.update(
        llm_status="OK",
        completion={
            "model": result.model,
            "attempts": result.attempts,
            "repair_strategy": result.repair_strategy,
        },
        findings=normalize_findings(result.data),
    )
    return fragment


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop self-audit")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--llm", action="store_true",
                        help="enable the LLM semantic-analysis stage (T-0091 AC-03); "
                             "model config: env LLM_API_KEY/ANTHROPIC_API_KEY/... "
                             "or ~/.zcode/v2/config.json")
    parser.add_argument("--provider", metavar="ID", default=None,
                        help="preferred provider id for the LLM stage (only with --llm)")
    parser.add_argument("--model", metavar="NAME", default=None,
                        help="preferred model name for the LLM stage (only with --llm)")
    args = parser.parse_args()

    results: dict[str, dict] = {}

    # 1. validate_state
    results["validate_state"] = run([
        sys.executable, str(PROJECT_ROOT / ".zcode" / "tools" / "validate_state.py"),
        str(PROJECT_ROOT),
    ])

    # 2. Guard health
    results["guard_health"] = run([
        sys.executable, str(PROJECT_ROOT / "tools" / "loop_guard_health.py"), "--json",
    ])

    if not args.quick:
        # 3. compile
        results["compile"] = run([sys.executable, "-m", "compileall", "-q", "loop_core/"])
        # 4. pytest (core only to bound runtime)
        results["pytest_core"] = run([
            sys.executable, "-m", "pytest", "tests/test_loop_core.py",
            "tests/test_verdicts.py", "tests/test_guard_health.py", "-q", "--tb=line",
        ])
        # 5. security scan
        results["security_scan"] = run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from loop_core.security_scanner import scan_security; "
            "r = scan_security('loop_core', task_id='T-0083', phase='S5-quality', git_commit='self-audit'); "
            "print(f'critical={r.critical} high={r.high} verdict={r.verdict.value}')",
        ])
        # 6. static analysis
        results["static_analysis"] = run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0,'.'); "
            "from loop_core.static_analyzer import analyze_project; "
            "r = analyze_project('loop_core', task_id='T-0083', phase='S5-quality', git_commit='self-audit'); "
            "print(f'errors={r.errors} warnings={r.warnings} verdict={r.verdict.value}')",
        ])

    # Verdict computation
    checks = {}
    if args.quick:
        checks = {"validate_state", "guard_health"}
    else:
        checks = set(results.keys())
    failed = [k for k, r in results.items()
              if k in checks and r.get("rc", -1) != 0 and k not in ("validate_state",)]
    # validate_state returns 2 when NO_ACTIVE_TASK (expected idle) — treat rc 0/2 as OK
    if results.get("validate_state", {}).get("rc") not in (0, 2):
        failed.append("validate_state")
    # guard health: rc 0 = PASS, rc 2 = guard broken
    gh = results.get("guard_health", {})
    if gh.get("rc") == 2:
        failed.append("guard_health")

    report = {
        "tool": "loop_self_audit",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "results": results,
        "failed": failed,
        "overall": "PASS" if not failed else "FAIL",
    }
    _write_json(rule_report_path(), report)

    if args.llm:
        # T-0091 AC-03: LLM semantic analysis — never blocks the rule audit.
        summary = build_llm_summary(results, failed)
        try:
            fragment = run_llm_stage(summary, provider=args.provider, model=args.model)
        except Exception as exc:  # last-resort fail-safe (unexpected bug)
            fragment = {
                "llm_status": "DEGRADED",
                "analysis_summary": summary,
                "llm_error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": sanitize_text(f"{type(exc).__name__}: {exc}"),
                },
            }
        _write_json(llm_report_path(), {
            "tool": "loop_self_audit",
            "kind": "llm-analysis",
            "version": "1.0",
            "timestamp": report["timestamp"],
            "git_commit": report["git_commit"],
            **fragment,
        })
        print(json.dumps({"overall": report["overall"], "failed": failed,
                          "llm_status": fragment.get("llm_status")}, indent=2))
    else:
        print(json.dumps({"overall": report["overall"], "failed": failed}, indent=2))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
