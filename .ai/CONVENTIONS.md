# Conventions

## Code Style Snapshot

- TypeScript: ES2022 + Node16 modules, strict mode
- Python: PEP 8, type hints preferred, PyYAML for YAML handling
- File naming: kebab-case for files, PascalCase for classes, camelCase for functions
- Error handling: Custom `LoopError` class with `code` + `message` + `detail` + `recoverable`
- YAML I/O: Atomic write (write to .tmp then rename) to prevent corruption
- Path safety: All paths validated against traversal attacks, no `..` allowed in project root
- Test framework: vitest for TypeScript, pytest for Python
- No hardcoded secrets, no `any` types, no `console.log` in production code

## Project Commands

- Install: `npm install` (installs @modelcontextprotocol/sdk, yaml, commander)
- Build: `npm run build` (tsc → dist/)
- Test: `npm test` (vitest run)
- Dev: `npm run dev` (tsc --watch)
- Start: `npm start` (node dist/server/index.js)
- Python tests: `cd .ai && python -m pytest tests/`
- Python checks: `python .ai/checkers/run_governance_checks.py --gates --project-root .`
# Conventions

## Code Style Snapshot

- TBD

## Project Commands

- Install: TBD
- Test: TBD
- Run: TBD
