# ADR-006: Role Hierarchy Pattern

**Status:** Accepted
**Date:** 2026-01-23
**Context:** P0-2 Authorization - Role Hierarchy Implementation

---

## Kontext

Původní implementace `require_role()` v `app/dependencies.py` používala strict porovnání:

```python
if current_user.role not in allowed_roles:
    raise HTTPException(403, "Access denied")
```

**Problém:**
- Admin nemůže přistupovat k endpointům vyžadujícím `OPERATOR` role
- Porušuje základní princip RBAC: vyšší role by měla dědit oprávnění nižších rolí
- V praxi: Admin musí ručně editovat díly, ale endpoint `/api/parts/{id}` vyžaduje `OPERATOR`

**Požadavek:**
- Admin >= Operator >= Viewer (hierarchie)
- Admin může vše co Operator
- Operator může vše co Viewer

---

## Rozhodnutí

Implementujeme **Role Hierarchy Helper Pattern**.

### Implementace (app/dependencies.py)

```python
# Role hierarchy
ROLE_HIERARCHY = {
    UserRole.ADMIN: 3,
    UserRole.OPERATOR: 2,
    UserRole.VIEWER: 1
}

def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """Admin >= Operator >= Viewer"""
    return ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required_role]

# Updated require_role()
def require_role(allowed_roles: list[UserRole]):
    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        min_required_role = min(allowed_roles, key=lambda r: ROLE_HIERARCHY[r])

        if not has_permission(current_user.role, min_required_role):
            raise HTTPException(403, f"Required role: {min_required_role.value} or higher")

        return current_user
    return _check_role
```

### Použití

```python
# Endpoint vyžaduje OPERATOR nebo vyšší
@router.put("/api/parts/{part_id}")
async def update_part(
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    # Admin i Operator mohou editovat
    pass
```

---

## Alternativy

### Option B: Enum Method (Pythonic)

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

    def __ge__(self, other):
        hierarchy = {"admin": 3, "operator": 2, "viewer": 1}
        return hierarchy[self.value] >= hierarchy[other.value]

# Použití:
if user.role >= required_role:
    allow_access()
```

**Proč jsme to neudělali:**
- Méně explicitní (magické metody)
- Hierarchie ukrytá v enum definici
- `has_permission()` je čitelnější než `>=` operator

---

## Důsledky

### Výhody

✅ **Admin může vše** - konečně Admin může editovat díly, batche, atd.
✅ **Explicitní hierarchie** - `ROLE_HIERARCHY` dict je čitelný
✅ **Jednoduchá změna** - stačí upravit čísla v dictu
✅ **Rychlé** - dict lookup je O(1)
✅ **Testovatelné** - `has_permission()` lze testovat izolovaně

### Nevýhody

❌ **Nelze "only Operator"** - nelze udělat endpoint pouze pro Operator (bez Admina)
  → Ale to není žádoucí use case v praxi

❌ **Další helper funkce** - přidává 1 funkci + 1 dict
  → Trade-off za explicitnost

### Rizika

⚠️ **Breaking change:** Pokud existují endpointy které záměrně blokují Admin, přestanou fungovat.
  → V našem případě žádné takové endpointy nejsou.

---

## Implementace

### Soubory změněny

- `app/dependencies.py` - přidán `ROLE_HIERARCHY` + `has_permission()`, upraven `require_role()`
- `tests/test_authentication.py` - přidáno 9 testů pro role hierarchy

### Testy

```bash
pytest tests/test_authentication.py -v
# 27/27 passed ✅
```

**Nové testy:**
- `test_has_permission_admin_can_do_operator`
- `test_has_permission_admin_can_do_viewer`
- `test_has_permission_operator_can_do_viewer`
- `test_has_permission_viewer_cannot_do_operator`
- `test_has_permission_operator_cannot_do_admin`
- `test_has_permission_same_role`
- `test_require_role_hierarchy_admin_on_operator_endpoint`
- `test_require_role_hierarchy_operator_on_viewer_endpoint`
- `test_require_role_hierarchy_viewer_denied_operator`

---

## Reference

- OWASP RBAC Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- Related: ADR-005 Authentication & Authorization

---

## Changelog

- 2026-01-23: Initial decision (Option A - Helper Pattern)
