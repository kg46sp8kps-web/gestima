# GESTIMA Vue Migration - Testing Checklist

**Version:** 1.0
**Date:** 2026-01-29
**When to Execute:** After Phase 3 completion (all Vue pages implemented)

---

## 1. Backend Tests (Automated)

### 1.1 Run Full Test Suite

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=html

# Expected: 284+ tests passing (94%+)
```

### 1.2 Test Categories

| Category | Command | Expected |
|----------|---------|----------|
| Auth | `pytest tests/test_auth*.py -v` | All pass |
| Parts | `pytest tests/test_parts*.py -v` | All pass |
| Operations | `pytest tests/test_operations*.py -v` | All pass |
| Batches | `pytest tests/test_batches*.py -v` | All pass |
| Materials | `pytest tests/test_materials*.py -v` | All pass |
| Work Centers | `pytest tests/test_work_centers*.py -v` | Known failures (TODO) |
| Seed Data | `pytest tests/test_seed_scripts.py -v` | All pass |
| Security | `pytest tests/test_security*.py -v` | All pass |

### 1.3 Critical Backend Checks

```
□ Optimistic locking (409 on version mismatch)
□ Soft delete (deleted_at field, not actual DELETE)
□ Audit trail (created_by, updated_by)
□ Pagination (skip/limit on all list endpoints)
□ Eager loading (no N+1 queries)
□ Input validation (Pydantic schemas)
□ Role-based access (admin/operator/viewer)
```

---

## 2. Frontend Tests (Automated)

### 2.1 TypeScript Compilation

```bash
cd frontend
npm run type-check

# Expected: No errors
```

### 2.2 Build Check

```bash
cd frontend
npm run build

# Expected:
# - Build succeeds
# - Bundle < 100KB gzipped (current: ~59KB)
# - No warnings
```

### 2.3 Unit Tests (Vitest)

```bash
cd frontend
npm run test

# Tests for:
□ Pinia stores (auth, parts, batches, materials, workspace, ui)
□ API modules (client interceptors, error handling)
□ Composables (useDebounce, useBatchedList)
□ Utility functions
```

### 2.4 E2E Tests (Playwright)

```bash
cd frontend
npm run test:e2e

# Critical flows:
□ Login → Dashboard → Logout
□ Parts list → Select part → View pricing
□ Create batch → Freeze batch
□ Workspace layout switching
□ Dark mode toggle
```

---

## 3. Manual UI Testing

### 3.1 Authentication Flow

```
□ Login page loads (no flash)
□ Invalid credentials → Error toast
□ Valid login → Redirect to dashboard
□ Session persistence (refresh keeps logged in)
□ Logout → Redirect to login
□ Protected routes → Redirect to login if not authenticated
□ Role restrictions (admin pages for non-admin → 403)
```

### 3.2 Dashboard

```
□ User info displays correctly
□ Navigation menu works
□ All tiles clickable (Parts, Workspace, Admin, etc.)
□ Footer shows version
```

### 3.3 Parts List Page

```
□ Parts load with pagination
□ Search filters parts (part_number, name, article_number)
□ Column visibility toggle works
□ Row click → Part selection
□ Create new part → Modal/page
□ Edit part → Opens editor
□ Delete part → Confirmation → Soft delete
□ Duplicate part → Creates copy
□ Empty state when no results
□ Loading spinner during fetch
```

### 3.4 Workspace (CRITICAL - Phase 2 modules)

#### Layout & Navigation
```
□ Workspace loads at /workspace
□ 6 layout presets work (default, wide, tall, split, quad, custom)
□ Custom layout save/load from localStorage
□ Toolbar visible with layout selector
□ Dark mode toggle works
□ Panels resize correctly
□ Module lazy loading (no flash)
```

#### Parts List Module
```
□ Parts list loads in panel
□ Search with debounce (300ms)
□ Keyboard navigation (↑↓ arrows)
□ Part selection updates workspace context
□ Selected part highlighted
□ Pagination works
```

#### Part Pricing Module
```
□ Shows pricing for selected part
□ Cost breakdown bars render (material, machining, setup, overhead)
□ Batch sets dropdown loads
□ Create new batch set → Modal
□ Delete batch set → Confirmation
□ Add batch (quantity input)
□ Freeze batch set → Status changes
□ Clone batch set → New set created
□ Numbers format correctly (CZK, %)
```

#### Part Operations Module
```
□ Operations list for selected part
□ Add operation → New row
□ Delete operation → Confirmation
□ Work center dropdown loads
□ Inline editing (tp, tj fields)
□ Operation type auto-derived from work center
□ Kooperace toggle works
□ Reorder operations (drag or buttons)
```

#### Part Material Module
```
□ Stock shape dropdown (8 options)
□ Conditional dimension inputs based on shape:
  - round_bar: diameter, length
  - square_bar: width, length
  - flat_bar: width, height, length
  - hexagonal_bar: diameter, length
  - plate: width, height, thickness
  - tube: diameter, wall_thickness, length
□ Price category dropdown loads
□ Stock cost calculation displays (weight, price/kg, cost)
□ Material parser input works
□ Parser confidence indicators (✅ high, ⚠️ medium, ❌ low)
□ Apply parsed values button works
```

#### Batch Sets Module
```
□ Batch sets list for selected part
□ Status filter (all, draft, frozen)
□ Create set → Modal with name
□ Delete set → Confirmation (only draft sets)
□ Add batch to set → Quantity input
□ Remove batch from set
□ Freeze set → Confirmation → Status locked
□ Clone set → New draft set created
□ Frozen sets show 🔒 indicator
□ Frozen sets are read-only (no edit/delete)
```

### 3.5 Admin Pages

```
□ Master Data page loads
□ Material Norms CRUD
□ Price Categories CRUD
□ Units CRUD
□ Materials CRUD
□ Work Centers CRUD (with hourly rate breakdown)
□ Only accessible to Admin role
```

### 3.6 Settings Page

```
□ User profile editing
□ Password change
□ Preferences (if implemented)
```

---

## 4. Cross-Browser Testing

```
□ Chrome (latest)
□ Firefox (latest)
□ Safari (latest)
□ Edge (latest)
```

### Per Browser Check
```
□ Layout renders correctly
□ Dark mode works
□ Transitions smooth (no jank)
□ Forms submit correctly
□ Modals open/close
□ Dropdowns work
□ Toast notifications appear
```

---

## 5. Responsive Testing

```
□ Desktop (1920x1080)
□ Laptop (1366x768)
□ Tablet (768x1024)
□ Mobile (375x667) - if supported
```

### Per Resolution
```
□ Navigation accessible
□ Content readable
□ No horizontal scroll
□ Buttons clickable (touch targets)
□ Modals fit screen
```

---

## 6. Performance Testing

### 6.1 Metrics to Measure

```
□ Initial page load < 2s
□ Route transitions < 100ms
□ Parts list render < 500ms (100 items)
□ Workspace module switch < 200ms
□ API responses < 200ms
□ No memory leaks (monitor during extended use)
```

### 6.2 Lighthouse Audit

```bash
# Run Lighthouse on deployed app
# Target scores:
□ Performance: > 80
□ Accessibility: > 90
□ Best Practices: > 90
□ SEO: > 80
```

---

## 7. Security Testing

### 7.1 Authentication

```
□ JWT stored in HttpOnly cookie (not localStorage)
□ XSS protection (CSP headers)
□ CSRF protection (SameSite cookie)
□ Session timeout works (30 min)
□ Invalid token → Logout
```

### 7.2 Authorization

```
□ Viewer cannot access operator endpoints
□ Operator cannot access admin endpoints
□ API returns 403 for unauthorized access
□ Frontend hides unauthorized options
```

### 7.3 Input Validation

```
□ SQL injection attempts blocked
□ XSS attempts sanitized
□ Invalid data types rejected (422)
□ Oversize inputs rejected
```

---

## 8. Integration Testing

### 8.1 API ↔ Frontend Flow

```
□ Create part → Shows in list
□ Update part → Reflects changes
□ Delete part → Removed from list
□ Optimistic update → Rollback on error
□ Network error → Toast notification
□ 401 response → Redirect to login
□ 409 response → "Data changed" message
```

### 8.2 Real-time Updates (if implemented)

```
□ Changes by other users reflected
□ Conflict detection works
□ Notifications appear
```

---

## 9. Regression Testing

### After Each Major Change

```
□ All existing tests pass
□ No new console errors
□ No new TypeScript errors
□ Bundle size not increased significantly
□ Performance metrics maintained
```

---

## 10. Sign-off Checklist

| Area | Tested | Passed | Notes |
|------|--------|--------|-------|
| Backend Tests | □ | □ | |
| Frontend Build | □ | □ | |
| Unit Tests | □ | □ | |
| E2E Tests | □ | □ | |
| Manual UI | □ | □ | |
| Cross-browser | □ | □ | |
| Responsive | □ | □ | |
| Performance | □ | □ | |
| Security | □ | □ | |
| Integration | □ | □ | |

**Tested By:** _______________
**Date:** _______________
**Version:** _______________

---

## Quick Commands Reference

```bash
# Backend
pytest tests/ -v                    # All tests
pytest tests/ -v --cov=app          # With coverage
python gestima.py run               # Start server

# Frontend
cd frontend
npm run dev                         # Dev server
npm run build                       # Production build
npm run type-check                  # TypeScript check
npm run test                        # Unit tests
npm run test:e2e                    # E2E tests

# Both (parallel)
python gestima.py run &             # Backend (background)
cd frontend && npm run dev          # Frontend
```

---

**Version:** 1.0 (2026-01-29)
