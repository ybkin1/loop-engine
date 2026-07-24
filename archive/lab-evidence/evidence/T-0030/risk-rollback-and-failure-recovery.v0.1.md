# Risk, Rollback, And Failure Recovery - T-0030

Risks: historical Markdown compatibility, new blockers, false blocking, action-mode scope expansion, Windows locks/partial writes, unauthorized T-0028 coupling, and CLI compatibility.

Controls: recheck hashes, preserve recovery sources, implement in phases, use a recovery journal, define deterministic rollback-or-roll-forward, never use old `close_session.py` to regenerate HANDOFF during rollback, rerun validator/audit/tests after recovery, and retain failure evidence.
