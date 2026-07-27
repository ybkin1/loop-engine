# Release Readiness

- Release ID:
- Artifact / commit:
- Target environment:
- Change summary:
- Risk tier:

## Required evidence

- [ ] Requirements and acceptance baseline locked
- [ ] Architecture and API compatibility reviewed
- [ ] Tests and regressions passed with reproducible commands
- [ ] Security review passed or explicit user-approved waiver exists
- [ ] Build and dependency provenance recorded
- [ ] Configuration and secret handling verified without exposing secrets
- [ ] Monitoring, logs, alerts and health checks verified
- [ ] Deployment, rollback and recovery runbooks tested
- [ ] Human Review Packet is readable and complete

## Decision

- Delivery manager: `READY | NOT_READY | BLOCKED`
- Release/operations engineer: `READY | NOT_READY | BLOCKED`
- User Gate: `pending | approved | rejected`
- Rollback trigger:
