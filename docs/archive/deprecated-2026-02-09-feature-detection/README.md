# Deprecated: Feature Detection Approach (2026-02-09)

**Status:** DEPRECATED
**Reason:** Pivot to Proxy Features ML Architecture (ADR-042)

---

## Why deprecated?

### Original Approach (Feature Detection):
**Goal:** Detect manufacturing features (pockets, holes, grooves, threads) from STEP geometry

**Problem:**
- OCCT cannot reliably distinguish features (50% accuracy)
- Same geometry = different features (hole vs boss, pocket vs step)
- Requires manufacturing context (stock, tolerance, assembly) which STEP doesn't contain
- Even commercial CAM software (SolidCAM) achieves only 70-80% accuracy

**Circular dependency:**
- Need features for ML training → Can't detect features → Can't train ML

---

## New Approach (Proxy Features):

**Goal:** Measure geometric complexity metrics instead of naming features

**Advantages:**
- ✅ Deterministic (OCCT measurements are precise)
- ✅ No ambiguous classification (concave_ratio is objective)
- ✅ ML learns correlations automatically (high cavity_volume = slow, regardless of "pocket" label)
- ✅ Robust to edge cases (doesn't break on ambiguous geometry)

**Key insight:**
> "You don't need to know WHAT a feature is, you need to know HOW COMPLEX the part is"

---

## Archived Files:

1. **041-ml-time-estimation-architecture.md** - Original ML plan with feature detection
2. **FEATURE-EXTRACTION-DESIGN.md** - 60+ features (pocket_count, hole_count, etc.)
3. **PHASE1-COMPLETION-REPORT.md** - Implementation report for feature detection
4. **PHASE2-HANDOFF-PROMPT.md** - Handoff for DB/UI (now obsolete)

---

## See instead:

- **ADR-042:** Proxy Features ML Architecture (new approach)
- **docs/guides/PROXY-FEATURES-GUIDE.md:** Implementation guide
- **CLAUDE.local.md:** Updated strategy (2026-02-09)

---

**Date archived:** 2026-02-09
**Archived by:** Strategic pivot based on OCCT limitations analysis
