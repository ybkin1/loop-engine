# Startup Routing Acceptance Report: T-0016

## Summary

PASS. The installed project-local `AGENTS.md` startup and operating rules are
present and match the expected post-installation hash. This smoke test did not
modify `AGENTS.md`, enter a real business project, write business code, enable
runtime/tool behavior, or perform any high-risk action.

## AGENTS.md Presence And Hash

```text
Path: C:\Users\Administrator\.codex\loop-engine-lab\AGENTS.md
SHA256: 7D9B688C8364E4E2AA79D6878376B19D1E98FBC850A8116E297C50AB18F391BA
```

## Installed Content Check

Verified `AGENTS.md` contains:

```text
Loop Engineering Method Operating Rules
Startup Routing
Gates And Boundaries
Evidence And Handoff
```

## Routing Expectations Checked

| Category | Expected Behavior | Result |
| --- | --- | --- |
| simple Q&A | simple Q&A, single-file explanation, and temporary read-only commands do not require project memory unless the user asks for governance | PASS |
| governed work | implementation, review, debugging, design, handoff, task-state, or governance work uses `$project-governor` | PASS |
| pending gate behavior | pending gates stop work unless the latest user message explicitly approves, rejects, or requests repair | PASS |
| real-project / high-risk boundary | real-project entry, implementation, build, deployment, rollback, `AGENTS.md` changes, runtime behavior changes, and high-risk actions require separate explicit gates | PASS |

## Non-Entry Confirmation

```text
No real business project was entered.
No real business project files were created or modified.
No business code was written.
No build, deploy, release, rollback, database, permission, secret, payment,
production-data, or migration action occurred.
No skill, MCP, external agent runtime, automation, protocol service, or tool
behavior was installed or enabled.
```

## Acceptance Conclusion

T-0016 satisfies the post-installation startup-rules acceptance / smoke-test
criteria within the approved verification-only scope.
