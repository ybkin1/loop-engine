# Requirements: User Management Service

## Security Requirements

- FR-SEC-01: ALL user input MUST be validated and sanitized before use
- FR-SEC-02: Database queries MUST use parameterized queries, NEVER string concatenation
- FR-SEC-03: API keys and secrets MUST be stored in environment variables, NEVER hardcoded
- FR-SEC-04: Authentication tokens MUST be validated on every request

## Functional Requirements

- FR-001: Users can register with email and password
- FR-002: Users can login and receive a JWT token
- FR-003: Users can view their own profile
- FR-004: Admin users can list all users
