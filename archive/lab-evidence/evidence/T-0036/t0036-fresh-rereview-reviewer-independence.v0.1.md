# T-0036 Fresh Rereview Independence Protocol v0.1

- Reviewer must be a newly spawned reviewer with no inherited conversation or repair-session conclusions.
- Reviewer receives the project root, Gate ID, exact disk sources, review questions, output schema, and read-only boundary only.
- Reviewer must read candidate implementation and tests directly from disk before reading repair executor conclusions.
- Reviewer must reproduce or adversarially test claims rather than copying repair reports.
- Reviewer may confirm, reject, narrow, or reclassify each finding and severity.
- Main L0 does not preselect the verdict and only checks scope, evidence completeness, disk drift, and governance projection.
- Reviewer may write only the exact fresh-rereview evidence paths named in the approved Gate; candidate and protected subjects remain read-only.

Reviewer identity: `/root/t0036_fresh_rereview`, spawned with `fork_turns: none` and no inherited conversation or repair-session conclusion.

Completion: reviewer independently produced the fresh freeze, commands/results, all nine dispositions, overall report, and boundary postcheck before notifying L0.
