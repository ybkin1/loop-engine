# Independent Subagent Test Review Execution Protocol Candidate v0.1

## Purpose

Define how code-complete testing and review may be executed through
independent, read-only, or subagent workflows when appropriate, without letting
subagents approve gates or expand scope.

## Preconditions

- A test review plan exists and has passed plan audit or has recorded approved
  repairs.
- Code-complete scope is known: changed paths, affected modules, APIs, data,
  config, and user scenarios.
- Required test commands, environment, data strategy, and report schema are
  known.
- Separate gates exist for real-project entry and implementation if this is a
  real project. This protocol does not grant those gates.

## Execution Roles

- Main thread: owns state, scope, gate boundaries, synthesis, and final report.
- Test executor: runs approved test commands and records raw evidence.
- Scenario reviewer: walks through scenarios against code and tests.
- Falsification auditor: assumes bugs exist and attempts boundary, state,
  exception, type, order, permission, injection, and resource attacks.
- Report auditor: checks that reports cite evidence and do not overclaim.

## Subagent Boundary

Subagents may support read-only review and bounded analysis after deterministic
startup checks. They may not approve gates, modify source or governance state
without approved write scope, install or enable tool behavior, enter a real
project, deploy, rollback, or touch databases, permissions, secrets, payments,
production data, or migrations.

## Evidence Rules

Every execution unit must record:

- input scope and exact files/commands inspected
- command, environment, and exit code if a command is run
- raw result or pointer to raw evidence
- interpretation and limitation
- affected scenario, requirement, or gate
- reviewer identity or role label

## Test Execution Quality Controls

- Reject weak assertions such as constant truth assertions, empty tests, only
  null checks without behavioral claims, and swallowed exceptions.
- Distinguish assertion failures from environment failures. Retry only
  transient infrastructure failures, never assertion failures.
- Record skipped/todo tests with reason, owner, and recovery plan.
- Mark flaky tests and fail quality if flaky count exceeds the agreed limit.
- Require security tests when auth, authorization, PII, external input, file
  upload, encryption, or secret handling is in scope.

## Fan-In Synthesis

The main thread must aggregate subagent/test/review outputs into one evidence
chain and state which findings are accepted, rejected, duplicate, deferred, or
blocked. Conflicting reviewer conclusions must be resolved by evidence, not by
majority vote alone. Any Critical finding blocks a pass verdict.

## Output

This protocol expects later execution to produce test execution evidence,
scenario review evidence, falsification audit evidence, and a final synthesis.
This T-0024 document defines the protocol only.
