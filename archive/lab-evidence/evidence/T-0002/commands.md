# Commands For T-0002

## 2026-07-06

- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
  - Result before write-down: `[ok] state is usable`
- `git status --short`
  - Result: not a git repository
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py C:\Users\Administrator\.codex\loop-engine-lab --title "产出统一规范架构 Candidate v0.2.1" --allow-parallel`
  - Result: created `T-0002`
- Wrote `.ai/tasks/T-0002.md`
- Wrote `.ai/evidence/T-0002/unified-governance-architecture.candidate.v0.2.1.md`
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
  - Result after write-down: `[ok] state is usable`
- User approved overwriting GitHub repository `ybkin1/codex-rule` with current project content.
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py C:\Users\Administrator\.codex\loop-engine-lab --note "..."`
  - Result: rewrote `.ai/HANDOFF.md` for current T-0002 context.
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`
  - Result: `[ok] handoff audit passed`; warning remains for legacy `TBD` placeholders in some project memory files.
- `gh repo view ybkin1/codex-rule --json name,owner,isPrivate,defaultBranchRef,url`
  - Result: private repo exists; default branch `main`.
- `gh api repos/ybkin1/codex-rule/git/ref/heads/main --jq '.object.sha'`
  - Result: `65dd8518a4ea21d635d9cc0c1a6d7ef187da505f`
- `gh api repos/ybkin1/codex-rule/git/refs -f ref='refs/heads/backup-before-overwrite-20260706-171145' -f sha='65dd8518a4ea21d635d9cc0c1a6d7ef187da505f'`
  - Result: created remote backup branch `backup-before-overwrite-20260706-171145`.
- Replaced repository content in a temporary clone and created local commit `7f0259c209b8d1c3858f87e787397b193a60fd59`.
- `git push origin main`
  - Result: failed due to local network timeout connecting to `github.com:443`; remote `main` was not changed by this failed push.
- Used GitHub Git Data API to create a normal child commit of previous `main` with the replacement tree.
  - Previous remote `main`: `65dd8518a4ea21d635d9cc0c1a6d7ef187da505f`
  - Backup branch: `backup-before-overwrite-20260706-171145`
  - New remote `main`: `33689254aeda28837698825017316467410af7dd`
  - Tree: `1880c01755240be36d38b7d4fcffa260b8c2b852`
- Verified via GitHub API:
  - remote `main` points to `33689254aeda28837698825017316467410af7dd`
  - remote backup branch points to `65dd8518a4ea21d635d9cc0c1a6d7ef187da505f`
  - `README.md` and `.ai/HANDOFF.md` are readable from `main`

## 2026-07-06 Approval Record

- Read required project-governor context:
  - `.ai/state.yaml`
  - `.ai/HANDOFF.md`
  - `.ai/tasks/T-0002.md`
  - `.ai/evidence/T-0002/unified-governance-architecture.candidate.v0.2.1.md`
  - `.ai/evidence/T-0002/unified-governance-architecture.review-report.v0.2.1.md`
  - `.ai/PROGRESS.md`
  - `.ai/DECISIONS.md`
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
  - Result before approval record write-down: `[ok] state is usable`
- `git status --short; git log --oneline -5`
  - Result: not a git repository
- Created approval evidence:
  - `.ai/evidence/T-0002/unified-governance-architecture.approval.v0.2.1.md`
- Created artifact registry record:
  - `.ai/evidence/T-0002/artifact-registry.unified-governance-architecture.v0.2.1.yaml`
- Updated gate registry:
  - `.ai/gates.yaml`
- Updated project memory:
  - `.ai/PROGRESS.md`
  - `.ai/DECISIONS.md`
  - `.ai/HANDOFF.md`
- `C:\Python312\python.exe C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
  - Result after approval record write-down: `[ok] state is usable`
- `Get-FileHash -Algorithm SHA256` for candidate, review report, approval evidence, and artifact registry
  - Candidate SHA256: `23F0F8A17F33F31357CB21103882E18B3BE52CE6852E26572B6CE387DC1C736C`
  - Review report SHA256: `CB9F65E32C80F8F2613F28A211BA50DBCC411B9477A74C0C8CAB9DA55EE6EABD`
  - Approval evidence SHA256: `56AAC092CF631DF056B14689DE821B773F8A48752CE9BA1A10BC2D0F1D5FC431`
  - Artifact registry SHA256: `B6A226A43F445279E8F0256BFBF538D0EA22455D60B4EDB59334246E9E028837`
