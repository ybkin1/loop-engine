# Architecture: User Management Service

## Database Layer

- All database access MUST go through `db.py` which provides parameterized query functions
- Direct SQL string construction is FORBIDDEN
- Connection credentials MUST come from environment variables

## API Layer

- `POST /login` — accepts `{"username": "...", "password": "..."}`, returns JWT
- `GET /users` — admin only, returns user list
- `GET /users/<id>` — returns single user profile

## Security Boundaries

- Input validation MUST happen in the API layer BEFORE reaching the database
- API keys for external services MUST be loaded from `os.environ`
- No secrets in source code, period.
