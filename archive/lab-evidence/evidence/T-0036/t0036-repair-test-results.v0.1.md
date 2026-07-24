# T-0036 Repair Test Results v0.1

Controlled final command executed by `validation_runner.py`:

`C:\Python312\python.exe -B C:\Users\Administrator\.codex\loop-engine-lab\candidates\T-0030-project-governor-repair\tests\test_project_governor_consistency.py -v`

- Status: `bound`
- Exit code: `0`
- Tests: `58`
- Runtime reported by unittest: `82.692s`
- stdout bytes/hash: `0` / `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- stderr bytes/hash: `9539` / `2C324B64F4ACF127B45C16C1243E9048D5998B96A2913F23312E7BC4A31DC028`
- Candidate target pre/post: `16/16`, identical.
- Protected subject pre/post: `33/33`, identical.
- EvidenceManifest/v1: `27` files, `211022` bytes, file hash `7B44EA2B87455E9303315EB07230B190DAD3BAE87F9CE0FA73F2BCB68778387C`.
- Final controlled manifest SHA-256: `36C90E2DBF03B97D5ADCFE932E82E32BC834234E17D0C7663F0965B925320ACD`.

No skipped or xfail result was used. Existing vulnerable-interface tests were replaced with stronger fail-closed/controlled-runner assertions, while the original 37-test RED result remains immutable evidence.
