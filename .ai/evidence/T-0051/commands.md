# T-0051 execution evidence

- Runtime Controller smoke tests: passed
- `pytest tests/test_runtime_controller.py -q`: 6 passed
- `pytest tests/test_runtime_controller.py tests/test_executor.py -q`: 39 passed
- `pytest tests --ignore=tests/lab -q`: 2325 passed, 60 skipped, 16 xfailed, 1 xpassed
- CompileGate: 89/89 files compiled successfully
- `C:\Python312\python.exe .zcode/tools/validate_state.py .`: state usable
- Full lab suite: 63 failed, 1 skipped; failures are legacy fixture/continuity contract tests and are recorded separately, not marked as passed
- Scope: controller/bootstrap/capability tests and integration wiring; full legacy compatibility remains open
