## Summary

- What changed:
- Why:
- Risk level: low / medium / high

## Scope

- [ ] Backend (`app/`, `tests/`, `alembic/`)
- [ ] Frontend (`frontend/`)
- [ ] Infrastructure / CI / scripts
- [ ] Documentation / workflow

## Quality Gates

- [ ] `bash scripts/ai/docs-guard.sh`
- [ ] `bash scripts/ai/quality-gate.sh be` (if backend changed)
- [ ] `bash scripts/ai/quality-gate.sh fe` (if frontend changed)
- [ ] `bash scripts/ai/quality-gate.sh full` (if cross-stack changed)

## Agent Checklist

- [ ] `AGENTS.md` rules respected
- [ ] Backend rules (`app/AGENTS.md`) respected
- [ ] Frontend rules (`frontend/AGENTS.md`) respected
- [ ] `docs/ai/context-ledger.md` updated for non-trivial changes

## QA Evidence

- Backend tests:
- Frontend lint:
- Frontend build:
- E2E (if relevant):

## Audit Notes (if relevant)

- Security impact:
- Data integrity impact:
- Rollback plan:
