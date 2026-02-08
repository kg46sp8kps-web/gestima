---
name: gestima-backend-patterns
description: Backend coding patterns for FastAPI, SQLAlchemy, and Pydantic in Gestima
---

# Gestima Backend Patterns (Quick Reference)

**Full architecture:** `docs/reference/ARCHITECTURE.md`
**Hook-enforced rules:** `docs/core/RULES.md`

## Transaction Handling (L-008) — HOOK BLOCKS

```python
try:
    db.add(entity)
    db.commit()
    db.refresh(entity)
except Exception:
    db.rollback()
    raise
```

## Pydantic Validation (L-009) — HOOK BLOCKS

```python
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0)
    price: float = Field(..., ge=0)
```

## Router Pattern

```python
@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.create(data)
```

Business logika VŽDY v `app/services/`, NE v routeru (L-001).

## Project Structure

```
app/models/     → SQLAlchemy modely
app/schemas/    → Pydantic schémata
app/services/   → Business logika
app/routers/    → API endpointy
tests/          → pytest testy
```
