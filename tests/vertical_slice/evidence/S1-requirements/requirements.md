# S1 Requirements — Simple Task Manager

## Phase ID
S1-requirements

## Task ID
TASK-VS-001

## Completion Date
2026-07-20

## Requirements Document

### Functional Requirements

#### FR-01: User Registration
Users must be able to create an account by providing a username, password, and email address. The system must validate that usernames and emails are unique.

#### FR-02: User Login
Users must be able to log in with their username and password. Upon successful authentication, a session token is issued.

#### FR-03: Task List View
Authenticated users must be able to view a list of their personal tasks, showing title, status, and due date.

#### FR-04: Task Creation
Authenticated users must be able to create a new task by providing a title. Description and due date are optional.

#### FR-05: Task Update
Authenticated users must be able to update their own task's title, status, and due date.

#### FR-06: Task Search
Authenticated users must be able to search their tasks by keyword in the title.

### Non-Functional Requirements

#### NFR-01: Security
All passwords must be hashed before storage. All user inputs must be validated and sanitized to prevent injection attacks. API endpoints must check authentication tokens.

#### NFR-02: Performance
Task list queries must be efficient — no N+1 query patterns. The dashboard page must load within 2 seconds for users with up to 500 tasks.

#### NFR-03: Architecture
The system must use a modular architecture with clear separation between authentication, task management, and API routing concerns. Modules must not have circular dependencies.

### Acceptance Criteria
- [AC-01] User can register, log in, create tasks, and view task list
- [AC-02] Invalid login credentials show an error message
- [AC-03] Password storage uses industry-standard hashing
- [AC-04] Task search does not allow SQL injection
- [AC-05] Empty task list shows an appropriate message

### Role Verdicts
| Role | Verdict | Notes |
|------|---------|-------|
| product-manager | PASS | Requirements are complete and cover all user stories |
| system-architect | PASS | Requirements are feasible within the proposed architecture |
| quality-engineer | PASS | Acceptance criteria are testable and measurable |
| security-engineer | PASS | Security requirements (NFR-01) are adequate as a baseline |
