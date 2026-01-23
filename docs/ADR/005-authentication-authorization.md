# ADR-005: Authentication & Authorization

## Status
Přijato (23.1.2026)

## Kontext

Pro produkční nasazení (P0 requirement) musí Gestima implementovat autentizaci a autorizaci:
- **P0 BLOCKER:** Bez auth nelze nasadit do produkce
- **Bezpečnost:** Chránit business data (díly, operace, výpočty cen)
- **Multi-user:** Několik operátorů + management (read-only reporting)
- **Audit trail:** Vyplnit created_by/updated_by (vyžaduje user context)
- **Web aplikace:** Browser-based (Jinja2 + Alpine.js + HTMX), není pure REST API

## Rozhodnutí

### 1. Authentication: OAuth2 + JWT v HttpOnly Cookie

**Pattern:**
- OAuth2 Password Flow (username/password login)
- JWT token pro session identity
- **HttpOnly Cookie** pro storage (ne localStorage/sessionStorage)
- SameSite=Strict flag pro základní CSRF ochranu

**Proč Cookie místo Bearer Token?**
| Kritérium | HttpOnly Cookie | Authorization Header |
|-----------|-----------------|---------------------|
| XSS ochrana | ✅ JS nemůže číst | ❌ localStorage = XSS risk |
| Auto-submit | ✅ Browser automaticky | ❌ JS musí přidat header |
| HTMX/Alpine.js | ✅ Funguje out-of-box | ⚠️ Custom headers |
| CSRF | ⚠️ Potřebuje SameSite | ✅ Není problém |
| **Gestima kontext** | ✅ **Browser app** | ❌ Pro API clients |

**Závěr:** Pro browser-based aplikaci je Cookie **bezpečnější a jednodušší**.

### 2. Authorization: Role-Based Access Control (RBAC)

**3 role:**
- **ADMIN:** Full access (CRUD všeho + user management)
- **OPERATOR:** CRUD parts/operations/batches (pracovní role)
- **VIEWER:** Read-only (reporting, prohlížení)

**Proč ne permissions-based?**
- Pro Gestima (kalkulátor CNC) stačí jednoduché role
- Lze později rozšířit na granular permissions (pokud potřeba)
- Minimální complexity = snadnější údržba

### 3. Implementační detaily

**User Model:**
```python
class User(Base, AuditMixin):
    __tablename__ = "users"

    id: int                    # PK
    username: str              # Unique
    email: str                 # Unique
    hashed_password: str       # bcrypt
    role: UserRole             # Enum: ADMIN, OPERATOR, VIEWER
    is_active: bool            # Soft disable
```

**JWT Claims:**
```python
{
    "sub": username,           # Subject (user identifier)
    "role": "OPERATOR",        # Pro authorization
    "exp": 1234567890          # Expiration (30 min)
}
```

**Cookie Security:**
```python
response.set_cookie(
    key="access_token",
    value=jwt_token,
    httponly=True,        # XSS protection
    secure=True,          # HTTPS only (produkce)
    samesite="strict",    # CSRF protection
    max_age=1800,         # 30 min
)
```

**Dependencies:**
```python
# Inject do protected endpoints
async def get_current_user(request: Request) -> User:
    token = request.cookies.get("access_token")
    # Verify JWT, return User

async def require_role(min_role: UserRole):
    # Decorator pro role check
```

### 4. První admin (Bootstrap)

**CLI command:**
```bash
python gestima.py create-admin --username admin --email admin@gestima.local
# Prompt pro heslo (ne v argumentu!)
```

## Alternativy

### 1. Bearer Token v Authorization Header
- ❌ Vyžaduje localStorage = XSS risk
- ❌ Komplikovanější pro HTMX
- ✅ Standard pro pure REST API
- **Odmítnuto:** Gestima není pure API, je browser app

### 2. Session-based auth (server-side sessions)
- ✅ Jednodušší než JWT
- ❌ Potřebuje session table v DB
- ❌ Stateful (komplikace při škálování)
- **Odmítnuto:** JWT je industry standard, lépe škálovatelné

### 3. Full RBAC (Roles + Permissions table)
- ✅ Maximální flexibilita
- ❌ Over-engineering pro Gestima use case
- **Odmítnuto:** 3 role stačí, lze rozšířit později

### 4. OAuth2 social login (Google, Microsoft)
- ✅ Pohodlné pro uživatele
- ❌ Vyžaduje external dependencies
- ❌ Problém pro offline/intranet deployment
- **Odmítnuto:** Local auth je pro Gestima vhodnější

## Důsledky

### Pozitivní
- ✅ **P0 splněno:** Aplikace je production-ready (auth část)
- ✅ **Security:** HttpOnly Cookie = XSS protection
- ✅ **Audit trail:** Můžeme vyplnit created_by/updated_by
- ✅ **RBAC:** Jasná separace rolí
- ✅ **Industry standard:** OAuth2 + JWT = dobrá dokumentace

### Negativní
- ⚠️ **Complexity:** Přidává ~500 LOC (models, schemas, services, router)
- ⚠️ **Breaking change:** Všechny existující API endpointy vyžadují auth
- ⚠️ **Migration:** Potřeba vytvořit users tabulku
- ⚠️ **Bootstrap:** První admin musí být vytvořen CLI (ne přes UI)

### Dopad na existující kód

**API Endpoints:** Všechny chráněné
```python
# Před
@router.get("/api/parts")
async def get_parts(db: AsyncSession = Depends(get_db)):
    ...

# Po
@router.get("/api/parts")
async def get_parts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ✅ Auth required
):
    ...
```

**Audit Trail:** Konečně vyplněný
```python
# Před
part.created_by = None  # ❌ CHYBÍ

# Po
part.created_by = current_user.username  # ✅ VYPLNĚN
```

**Frontend:** Login flow
```
1. User otevře aplikaci
2. Redirect na /login (pokud není cookie)
3. Login form → POST /api/auth/login
4. Set HttpOnly Cookie → Redirect na /
5. Všechny fetch() automaticky posílají cookie
```

### Dependencies (nové)
```
python-jose[cryptography]>=3.3.0  # JWT
passlib[bcrypt]>=1.7.4             # Password hashing
```

### Bezpečnostní poznámky

**Token expiry:** 30 minut
- Kompromis: bezpečnost vs UX
- Pokud potřeba delší session → implementovat Refresh Token (není P0)

**Password policy:** Minimálně
- Min 8 znaků (enforced v Pydantic schema)
- Lze později rozšířit (uppercase, numbers, symbols)

**CSRF:** SameSite=Strict
- Základní ochrana stačí pro intranet app
- Pokud potřeba víc → Double Submit Cookie Pattern

**Rate limiting:** NENÍ v P0
- P1 requirement
- Implementovat později (slowapi middleware)

## Migrace (existující data)

**POZOR:** Audit trail pole (created_by, updated_by) jsou aktuálně NULL.

**Po implementaci auth:**
- Nové záznamy: vyplněné correctly
- Staré záznamy: zůstanou NULL (nebo jednorázový backfill s "system" user)

**Doporučení:** Přijmout NULL pro historická data.

## Související rozhodnutí

- **ADR-001:** Soft Delete Pattern - vyžaduje deleted_by (po auth vyplněno)
- **P0-3:** HTTPS - nutné pro `secure=True` cookie flag
- **P1:** Rate limiting - doplnit jako další vrstva security

## Reference

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
