# Backend Rules (Codex)

Platí pro práci v `app/`, `tests/`, `alembic/`.

## Povinné principy

- Auth na každém endpointu (`get_current_user` nebo `require_role`)
- `safe_commit()` pro write operace
- `soft_delete()` místo `db.delete()`
- Optimistic locking: update schema obsahuje `version: int`
- Audit trail: `AuditMixin` + `set_audit()`
- Business logika patří do `services/`, ne do routerů

## Model/db změny

Než upravíš `app/models/*.py`, nejdřív grepni všechny reference modelu/fieldů a uprav vše v jednom průchodu.

Doporučené ověření:

```bash
python3 gestima.py test
```

## Definice hotovo

Backend změna je hotová jen pokud:
- endpointy mají správné auth + validaci
- testy pro success + auth + validation + conflict scénáře existují
- `quality-gate.sh be` projde
