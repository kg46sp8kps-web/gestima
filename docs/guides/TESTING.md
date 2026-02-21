# GESTIMA - Testing Guide

## Commands

```bash
# Backend
pytest tests/ -v                                    # All tests
pytest tests/ -v -m critical                        # Critical only
pytest tests/ -v --cov=app --cov-report=html        # With coverage

# Frontend
cd frontend
npm run type-check                                  # TypeScript
npm run build                                       # Build check
npm run test                                        # Vitest unit tests
```

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| test_authentication.py | 27 | Auth + RBAC + role hierarchy |
| test_backup.py | 10 | Backup/restore/list/cleanup |
| test_rate_limiting.py | 9 | Rate limiter + config |
| test_pricing.py | 9 | Material cost calculations |
| test_conditions.py | — | Cutting conditions |
| test_error_handling.py | 6 | Transaction error handling |

## Rules

1. **Critical functions MUST have tests** — prices, times, batches, auth
2. **No hardcoded DB values** — use `result.price_per_kg`, not magic numbers
3. **Test edge cases** — zero, negative, missing data, max values
4. **Float tolerance** — `pytest.approx(expected, rel=0.01)`
5. **Mark critical tests** — `@pytest.mark.critical`
6. **Async tests** — `@pytest.mark.asyncio`

## Pre-deploy Checklist

```
pytest tests/ -v                    # All backend tests pass?
cd frontend && npm run build        # Frontend builds?
cd frontend && npm run type-check   # No TS errors?
```
