# T-0036 Independent Review Validation v0.1

## Fingerprints

- T-0035 final manifest: 37/37 match SHA-256, size, and `mtime_ns`.
- T-0036 freeze manifest: 60/60 match.
- T-0035 logical Gate: 63 fields, 11102 canonical JSON bytes, expected SHA-256 match.

## Candidate Tests

Exact command:

```text
C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\tests\test_project_governor_consistency.py -v
```

Environment: `PYTHONDONTWRITEBYTECODE=1`, inherited `PYTHONPATH` removed.

Result:

```text
Ran 28 tests in 17.477s
OK
```

Exit code: `0`.

## Validators And Audits

- Candidate `validate_state.py`: exit `0`, state usable.
- Global `validate_state.py`: exit `0`, state usable.
- Candidate `audit_handoff.py`: exit `0`, audit passed.
- Global `audit_handoff.py`: exit `0`, audit passed.

## Boundary

- Candidate: 10 files, 2 directories, 0 cache/compiled artifacts, 0 reparse points.
- PATH/PYTHONPATH candidate entries: 0/0.
- Protected manifest and discovery checks: no drift/reference detected.

Tests and validators passed, but the content review found nine issues and returned `REPAIR_REQUIRED`.
