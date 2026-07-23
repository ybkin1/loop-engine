# T-0036 F003 Repair Commands v0.1

## Preflight

- Global Project Governor validator: exit 0.
- Four allowed candidate subjects and five protected registration subjects: exact SHA-256/size/mtime_ns match.

## RED

- Focused zero-test stdout spoof test failed as expected because the old runner returned success.

## GREEN

- Focused RUN_002 through RUN_009: 8/8, exit 0.
- Full suite after final code changes: 64/64, exit 0.
- Exact adapter structured run: 64 discovered IDs, 64 tests run, clean structured outcome, exit 0.

## Final Checks

- Canonical envelope hash, nonce, unique IDs, adapter fingerprint, and test fingerprint: pass.
- Python AST parse: pass.
- Global validator and HANDOFF audit after closeout projection: exit 0.
- Candidate inventory: 17 files, 2 directories, 0 reparse, 0 cache/compiled artifacts.
- Other candidate subjects: 12/12 unchanged.
- Changed candidate subjects: 5/5 final manifest match.
- Broader protected subjects: 33/33 unchanged.
- Temporary adapter envelope directory: removed after persistent hashes/results were recorded.
