# ADR-004: Implementační poznámky (Audit + WAL + Locking)

## Status
Implementováno (22.1.2026)

## Co bylo implementováno

### 1. AuditMixin - automatické audit fieldy
```python
# app/database.py
class AuditMixin:
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    created_by = Column(String)
    updated_by = Column(String)
    deleted_at = Column(DateTime)  # NULL = aktivní
    deleted_by = Column(String)
    version = Column(Integer)      # Optimistic locking
```

**Použití:** Všechny modely dědí `Base, AuditMixin`

### 2. WAL Mode - automaticky zapnuté
```python
# app/database.py -> init_db()
PRAGMA journal_mode=WAL
PRAGMA synchronous=NORMAL
PRAGMA cache_size=-64000  # 64MB
```

**Benefit:** Čtení neblokuje zápis. 10-100× rychlejší concurrent access.

### 3. Optimistic Locking - automatické
```python
# SQLAlchemy event listener
@event.listens_for(Base, 'before_update')
def receive_before_update(mapper, connection, target):
    if hasattr(target, 'version'):
        target.version += 1
```

**Benefit:** Detekce konfliktů při současných editacích.

### 4. Helper funkce
```python
# app/db_helpers.py
await soft_delete(db, part, deleted_by="user@example.com")
await restore(db, part)
is_deleted(part)
await get_active(db, Part, id)
await get_all_active(db, Part)
```

## Automatizace

**Nemusíš na to myslet!**

- ✅ Audit fieldy se vyplní automaticky
- ✅ WAL mode se zapne při startu
- ✅ Version se inkrementuje při UPDATE
- ✅ Soft delete = použij helper funkci

## Testy

```bash
pytest tests/test_audit_infrastructure.py -v
```

Testuje:
- WAL mode aktivní
- Audit fields fungují
- Version auto-increment
- Soft delete
- Restore
- Query filtering

## Migrace existující DB

**Pro přidání nových sloupců:**
```bash
# Smaž starou DB a vytvoř novou
rm gestima.db
uvicorn app.gestima_app:app --reload
# Tabulky se vytvoří s novými fieldy
```

**Nebo použij Alembic migration** (později).

## Použití v kódu

### Vytvoření záznamu
```python
part = Part(part_number="D123", name="Hřídel")
# created_at, version = automaticky
```

### Soft delete
```python
from app.db_helpers import soft_delete
await soft_delete(db, part, deleted_by="jan.novak@firma.cz")
```

### Query jen aktivní
```python
from app.db_helpers import get_all_active
active_parts = await get_all_active(db, Part)
```

### Detekce konfliktu
```python
# Frontend pošle expected_version
if part.version != expected_version:
    raise HTTPException(409, "Díl byl upraven jiným uživatelem")
```

## Reference
- ADR-001: Soft Delete Pattern
- ADR-003: Integer ID vs UUID
- SQLite WAL: https://www.sqlite.org/wal.html
