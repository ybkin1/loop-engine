# S2 Architecture — Simple Task Manager

## Phase ID
S2-architecture

## Task ID
TASK-VS-001

## Completion Date
2026-07-21

## Architecture Design

### System Overview
The Simple Task Manager is a three-tier web application. This architecture is based on the requirements established in S1-requirements (FR-01 through FR-06, NFR-01 through NFR-03).
- **Frontend**: Static HTML/CSS/JS served by a lightweight web server
- **Backend API**: RESTful JSON API built with Python (Flask-compatible)
- **Database**: SQLite for development, PostgreSQL-compatible schema

### Module Architecture

```
┌─────────────────────────────────────────────┐
│                 api-gateway                  │
│  ( routing, auth middleware, rate limiting ) │
└──────────┬──────────────────────┬───────────┘
           │                      │
    ┌──────▼──────┐        ┌──────▼──────┐
    │ auth-module │◄───────│ task-module │
    │             │ depends │             │
    └─────────────┘        └─────────────┘
```

- **api-gateway**: Top-level module. Routes requests, enforces authentication, applies rate limiting. No dependencies on other modules.
- **auth-module**: Handles user registration, login, password hashing, token management. Depends on api-gateway for middleware hooks.
- **task-module**: Handles task CRUD, search, filtering. Depends on auth-module (for user identity) and api-gateway.

### Dependency Rules
1. Dependencies flow downward in the diagram (no upward dependencies)
2. No circular dependencies allowed between modules
3. Each module exposes a clear public interface (contract)

### API Design
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/auth/login | POST | No | Authenticate user, return token |
| /api/auth/register | POST | No | Register new user |
| /api/tasks | GET | Yes | List user's tasks |
| /api/tasks | POST | Yes | Create a new task |
| /api/tasks/:id | PATCH | Yes | Update a task |

### Database Schema
- **users** table: id, username, password_hash, email, created_at
- **tasks** table: id, user_id (FK->users.id), title, description, status, due_date, created_at, updated_at

### Key Design Decisions
1. **Stateless API**: JWT-based authentication (no server-side sessions)
2. **Password Hashing**: bcrypt with configurable cost factor
3. **Input Validation**: All inputs validated at the API gateway layer before reaching modules
4. **Modular Structure**: Each module has its own directory with clear boundaries

### Role Verdicts
| Role | Verdict | Notes |
|------|---------|-------|
| system-architect | PASS | Architecture is sound, no circular dependencies |
| module-architect | PASS | Module contracts are well-defined |
| independent-reviewer | PASS | Architecture review complete, no issues found |
| security-engineer | PASS | Security concerns addressed in design (bcrypt, input validation at gateway) |
