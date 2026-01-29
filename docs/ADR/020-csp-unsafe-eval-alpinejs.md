# ADR-020: CSP 'unsafe-eval' for Alpine.js

**Status:** Accepted
**Date:** 2026-01-28
**Author:** Roy (audit fix)
**Context:** Sprint 2 - Security headers implementation

---

## Problem

Alpine.js requires `'unsafe-eval'` in Content Security Policy (CSP) to function. Without it:

```javascript
// Console error:
Uncaught EvalError: Evaluating a string as JavaScript violates
the following Content Security Policy directive because
'unsafe-eval' is not an allowed source of script
```

**Symptoms:**
- UI freezes (reactive updates fail)
- Login button stuck at "Přihlašování..."
- RSS feeds infinite loading spinner
- All Alpine.js directives (`x-data`, `x-show`, `@click`) broken

**Root Cause:**
Alpine.js uses `new AsyncFunction()` for reactivity - a form of `eval()` - which requires CSP `'unsafe-eval'` permission.

---

## Decision

**Accept `'unsafe-eval'` in CSP** with pragmatic justification:

```python
# app/gestima_app.py
csp_policy = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Alpine.js eval
    "style-src 'self' 'unsafe-inline'",
    "connect-src 'self'",
    # ...
])
```

---

## Rationale

### Why Allow 'unsafe-eval'?

1. **All reactive frameworks require it**
   - Alpine.js: `new AsyncFunction()`
   - Vue.js: Template compilation
   - React: JSX runtime (if not precompiled)

2. **Alternatives are impractical**
   - **CSP build Alpine.js**: Compile templates at build time
     - ❌ Complex tooling (Webpack, Vite)
     - ❌ Not compatible with Jinja2 server-side rendering
     - ❌ Breaks inline `<script>` components

   - **Switch to Vanilla JS**: No framework
     - ❌ Rewrite entire frontend (~20 templates)
     - ❌ Lose reactivity, state management
     - ❌ Massive dev effort (weeks)

3. **Risk Mitigation**
   - **XSS protection:** All user input sanitized (Pydantic, Jinja2 escaping)
   - **No eval() in app code:** Only Alpine.js internals use it
   - **Strict CSP elsewhere:** `connect-src 'self'`, `frame-ancestors 'none'`
   - **Local vendor files:** No CDN dependencies

4. **Industry Standard**
   - Most Alpine.js/Vue apps use `'unsafe-eval'`
   - Trade-off: Functionality vs extreme CSP strictness

---

## Consequences

### Positive ✅

- Alpine.js works (reactive UI, state management)
- No frontend rewrite needed
- Pragmatic balance: security + functionality

### Negative ❌

- `'unsafe-eval'` = broader XSS attack surface
- Not "perfect" CSP score (but perfect ≠ practical)
- Future XSS bugs could leverage eval (mitigated by input sanitization)

### Neutral ⚖️

- CSP nonces (v2.0): Can replace `unsafe-eval` with hash/nonce
- Pre-compiled Alpine.js (v3.0): Stricter CSP possible

---

## Implementation Details

### CSP Header
```python
# Before (Alpine.js broken):
"script-src 'self' 'unsafe-inline'"

# After (Alpine.js works):
"script-src 'self' 'unsafe-inline' 'unsafe-eval'"
```

### Vendor Files (Offline Support)
```
app/static/js/vendor/
├── alpine.min.js  (43 KB, local)
├── htmx.min.js    (48 KB, local)
```

**No CDN dependencies!** App runs 100% offline.

---

## Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| CSP build Alpine.js | Stricter CSP | Complex, breaks Jinja2 | ❌ Reject |
| Vanilla JS rewrite | No unsafe-eval | Weeks of work, lose reactivity | ❌ Reject |
| Switch to React/Vue | Modern framework | Overkill, same CSP issue | ❌ Reject |
| **Accept unsafe-eval** | **Works now, pragmatic** | **XSS risk (mitigated)** | ✅ **Accept** |

---

## Future Improvements (v2.0+)

1. **CSP Nonces**
   - Generate random nonce per request
   - Replace `'unsafe-inline'` with `'nonce-{random}'`
   - More work, but stricter CSP

2. **Pre-compiled Alpine.js**
   - Build step compiles templates
   - Remove `'unsafe-eval'` requirement
   - Requires tooling (Vite + Alpine.js compiler)

3. **Hybrid Approach**
   - Critical pages (login): Vanilla JS, strict CSP
   - Dashboard: Alpine.js + `'unsafe-eval'`
   - Per-route CSP headers

---

## Related

- [docs/SERVER-TROUBLESHOOTING.md](../SERVER-TROUBLESHOOTING.md) - Alpine.js / UI nefunguje
- Sprint 2: Security headers implementation
- ADR-007: HTTPS + Caddy deployment

---

**TL;DR:**
`'unsafe-eval'` je **nutné** pro Alpine.js. Trade-off: funkční UI vs perfektní CSP skóre. Pragmaticky akceptujeme s mitigací (input sanitization, local vendor files).
