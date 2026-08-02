# G3-11 security scan (AC-03 item 11) — findings classification
command: C:/Python312/python.exe agents/security-engineer/scripts/run_security_scan.py --project-root . --output-dir .ai/evidence/T-0099/quality/security-scan
recorded_at: 2026-08-02T02:43:01+00:00
verdict: BLOCKED (exit 2) — 3/4 scan items not passing
evidence: security_report.json (14,486 bytes) + security_summary.md (this dir)

## Per-scan result
| scan            | status  | detail |
|-----------------|---------|--------|
| dependency_scan | blocked | H:1 C:0 M:0 L:0 (source: pip-audit) |
| secret_scan     | blocked | 7 findings (all test fixtures / doc examples / string templates) |
| injection_scan  | blocked | HIGH:26 MEDIUM:4 |
| permission_audit| pass    | 0 high-risk unauthenticated routes (5 checked) |

## Classification (verified by quality engineer)

### dependency_scan — FAIL-CLOSED SYNTHESIS, no confirmed CVE
- _run_pip_audit(): if pip-audit exits nonzero, the scanner synthesizes HIGH:1 (fail-closed).
- In this environment pip-audit CRASHES: `ModuleNotFoundError: No module named 'venv'`
  (Python 3.12 install lacks stdlib venv) — verified by direct `pip-audit -r requirements.txt --format json` (exit 120).
- requirements.txt contains only `PyYAML>=6.0` (single runtime dep, consistent with pyproject).
- Verdict: NO confirmed vulnerability; scan cannot prove zero known CVEs until pip-audit runs
  in a complete Python environment. → finding F-04 (environment/tooling) + F-06 (scanner design).

### secret_scan — 7 findings, all non-secret by inspection
- scripts/certification_runner.py:686 `pwd='{password}'` — string template placeholder (no secret value)
- tests/test_guard_health.py:32, tests/test_hook_guards.py:24/44, tests/test_verdicts.py:215 — test data
- tests/seeded_defects/test_project/src/user_service.py:12 `sk-abc...` — deliberately seeded defect fixture
- agents/references/role-capability-profiles.md:757 `password = "changeme"` — documentation example
- Verdict: false positives (no real credential material); scanner lacks allowlist/self-exclusion → F-06.

### injection_scan — 26 HIGH / 4 MEDIUM, dominated by self-referential and fixture matches
- scanner flags its OWN rule tables: scripts/security_scan.py:42-47, agents/security-engineer/scripts/run_security_scan.py:337-352 (regex patterns for os.system/eval/exec/pickle/yaml/dangerouslySetInnerHTML as literal strings)
- tests that intentionally exercise those patterns: test_code_quality.py:97, test_content_guard_semantic.py:194/211, test_release.py:321 (sys.path insert, not SQL), tests/lab/test_project_governor_consistency.py:1082
- seeded_defects fixtures (deliberately vulnerable sample code): tests/seeded_defects/sample_code/user_service.py, tests/seeded_defects/test_project/src/user_service.py
- tools/loop_onboard.py:147-148 — f-string print statements falsely flagged as "SQL concatenation"
- .zcode/tools/governor_lib.py:465 `yaml.load(..., Loader=UniqueKeyLoader)` — UniqueKeyLoader subclasses yaml.SafeLoader (verified at .zcode/tools/governor_lib.py:451) → safe, false positive
- archive/lab-candidates/scripts/governor_lib.py:191 — archived code, same false positive
- Verdict: no genuine exploitable injection surface found in shipped code; all 26 HIGH matches are
  scanner self-flags, test fixtures, or pattern-mismatch false positives → F-06 (scanner needs
  allowlist/source triage). Not a product vulnerability finding.

## Conclusion
BLOCKED verdict is driven by scanner design (fail-closed synthesis + no false-positive triage)
and a broken pip-audit environment — NOT by confirmed vulnerabilities in the codebase.
No P0/P1 security defect in business code identified by this scan run.
