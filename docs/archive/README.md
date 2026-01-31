# Archive - Legacy Documentation

**Last Updated:** 2026-01-30
**Purpose:** Historical documentation, superseded by current active docs

---

## 📁 Structure

### legacy-alpinejs/
Legacy Alpine.js workspace system (pre-v1.10.0 Vue SPA migration)

| File | Archived Date | Replaced By | Notes |
|------|--------------|-------------|-------|
| `WORKSPACE-STATUS.md` | 2026-01-30 | `frontend/WORKSPACE-GUIDE.md` | Alpine.js workspace modules (parts-list, part-material, part-operations, part-pricing) |

**Why archived:** Vue SPA workspace replaced Alpine.js modules. New system uses resizable panels instead of module registry.

---

### roadmaps-old/
Superseded roadmap documents

| File | Archived Date | Replaced By | Notes |
|------|--------------|-------------|-------|
| `SPRINT-ROADMAP.md` | 2026-01-30 | `ULTIMATE-ROADMAP-TO-BETA.md` | Original sprint planning (2026-01-29), superseded by ULTIMATE with progress tracking |
| `ROADMAP.md` | (existing) | `ULTIMATE-ROADMAP-TO-BETA.md` | Original roadmap before Vue migration |
| `UI_ROADMAP.md` | (existing) | `DESIGN-SYSTEM.md` | UI planning doc, merged into design system |
| `BETA-RELEASE-STATUS.md` | (existing) | `ULTIMATE-ROADMAP-TO-BETA.md` | Pre-Vue migration status report |

**Why archived:** ULTIMATE-ROADMAP-TO-BETA.md is now SINGLE SOURCE OF TRUTH for beta release planning.

---

### Other archived docs/
UI and reference documents

| File | Archived Date | Replaced By | Notes |
|------|--------------|-------------|-------|
| `UI-GUIDE.md` | (existing) | `DESIGN-SYSTEM.md` | UI patterns merged into comprehensive design system |
| `UI_REFERENCE.md` | (existing) | `DESIGN-SYSTEM.md` | Component reference merged |

---

## 🔍 How to Find Current Docs

| Need | Active Document |
|------|----------------|
| **Road to BETA** | `docs/ULTIMATE-ROADMAP-TO-BETA.md` |
| **Design tokens, components, patterns** | `docs/DESIGN-SYSTEM.md` |
| **Workspace layout system** | `frontend/WORKSPACE-GUIDE.md` |
| **Current status** | `docs/STATUS.md` |
| **Post-BETA backlog** | `docs/BACKLOG.md` |
| **Long-term vision** | `docs/VISION.md` |

---

## ⚠️ Important Notes

1. **No data loss:** All archived docs preserved for reference
2. **Archived ≠ Deleted:** Files kept for historical context
3. **Version history:** Check `CHANGELOG.md` for what replaced what
4. **ADRs unchanged:** Architectural decisions remain active in `docs/ADR/`

---

**Archive Policy:** Documents moved here when:
- Superseded by newer, more comprehensive docs
- Related to legacy tech (Alpine.js → Vue SPA)
- Outdated planning docs (roadmaps with no progress tracking)

**NOT archived:** ADRs, audit reports, sprint reports (historical value, not superseded)
