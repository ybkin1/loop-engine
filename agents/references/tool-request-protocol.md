# TOOL_REQUEST Protocol

When a sub-agent needs to execute a command (script, test runner, linter, etc.),
it outputs a TOOL_REQUEST block. The main agent detects this, executes the command,
and returns the result.

## Sub-agent output format:
```json
{
  "verdict": "NEEDS_TOOL",
  "tool_requests": [
    {
      "id": "req-1",
      "command": "python agents/quality-engineer/scripts/run_quality_gates.py $PROJECT_ROOT",
      "reason": "Run quality gates to verify code quality",
      "expected_output": "quality_report.json"
    }
  ]
}
```

## Main agent response format:
```json
{
  "tool_results": [
    {
      "id": "req-1",
      "exit_code": 0,
      "stdout": "...",
      "stderr": "...",
      "output_file": "quality_report.json"
    }
  ]
}
```

## Role → Tool mapping:
| Role | Script/Tool | Command |
|------|------------|---------|
| quality-engineer | run_quality_gates.py | `python agents/quality-engineer/scripts/run_quality_gates.py $ROOT` |
| quality-engineer | check_thresholds.py | `python agents/quality-engineer/scripts/check_thresholds.py ...` |
| security-engineer | run_security_scan.py | `python agents/security-engineer/scripts/run_security_scan.py $ROOT` |
| system-architect | analyze_dependencies.py | `python agents/system-architect/scripts/analyze_dependencies.py $ROOT` |
| module-architect | validate_contract.py | `python agents/module-architect/scripts/validate_contract.py $FILE` |
| test-engineer | pytest | `python -m pytest tests/ -v --tb=short` |
| developer | ruff | `python -m ruff check $FILE` |
