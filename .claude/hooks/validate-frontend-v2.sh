#!/bin/bash
# V2 Design System Validation Hook
# Source of truth: tiling-preview-v2.html + design-system.css v6.0
# Font: DM Sans | 51 tokens total: 35 v2 + 16 app-specific
#
# ERRORS (block edit):
#   1. Hardcoded hex colors in .vue/.css (use var(--token))
#   2. TypeScript 'any' type
#   3. !important in CSS
#   4. Missing <style scoped> in .vue files
#   5. Options API usage
#   6. Legacy/non-v2 token names
#
# WARNINGS (inform, don't block):
#   7. @media queries (prefer @container)
#   8. Inline style="" attributes
#   9. Direct axios import in components
#  10. Business calculations in frontend

FILE="$1"

# Only check frontend files
if [[ ! "$FILE" == *"frontend/src/"* ]]; then
  exit 0
fi

# Skip CSS asset files (they define tokens)
if [[ "$FILE" == *"assets/css/"* ]]; then
  exit 0
fi

# Skip config files
if [[ "$FILE" == *"config/"* ]]; then
  exit 0
fi

ERRORS=""
WARNINGS=""

# ════════════════════════════════════════
# ERRORS — block the edit
# ════════════════════════════════════════

# ── ERROR 1: Hardcoded hex colors ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *.css ]]; then
  HARDCODED=$(grep -n '#[0-9a-fA-F]\{3,8\}' "$FILE" 2>/dev/null \
    | grep -v '\/\/' | grep -v '\/\*' | grep -v 'var(--' \
    | grep -v 'data-testid' | grep -v 'import' | grep -v 'href=' \
    | grep -v 'url(' | grep -v 'source-map' | grep -v '<script' \
    | head -5)
  if [ -n "$HARDCODED" ]; then
    ERRORS="${ERRORS}\n  [DESIGN] Hardcoded hex color. Use v2 tokens (--red, --green, --ok, --warn, --err):\n${HARDCODED}\n"
  fi
fi

# ── ERROR 2: TypeScript 'any' ──
if [[ "$FILE" == *.ts ]] || [[ "$FILE" == *.vue ]]; then
  ANY_TYPE=$(grep -n ': any\b\|as any\b\|<any>' "$FILE" 2>/dev/null | head -5)
  if [ -n "$ANY_TYPE" ]; then
    ERRORS="${ERRORS}\n  [TYPE] 'any' type found. Use proper TypeScript types:\n${ANY_TYPE}\n"
  fi
fi

# ── ERROR 3: !important ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *.css ]]; then
  IMPORTANT=$(grep -n '!important' "$FILE" 2>/dev/null | head -5)
  if [ -n "$IMPORTANT" ]; then
    ERRORS="${ERRORS}\n  [CSS] !important found. Fix CSS specificity instead:\n${IMPORTANT}\n"
  fi
fi

# ── ERROR 4: Missing <style scoped> ──
if [[ "$FILE" == *.vue ]]; then
  HAS_STYLE=$(grep -c '<style' "$FILE" 2>/dev/null)
  if [ "$HAS_STYLE" -gt 0 ]; then
    UNSCOPED=$(grep -n '<style' "$FILE" 2>/dev/null | grep -v 'scoped' | grep -v '<!--' | head -3)
    if [ -n "$UNSCOPED" ]; then
      ERRORS="${ERRORS}\n  [SCOPE] <style> without 'scoped'. Use <style scoped>:\n${UNSCOPED}\n"
    fi
  fi
fi

# ── ERROR 5: Options API ──
if [[ "$FILE" == *.vue ]]; then
  OPTIONS_API=$(grep -n 'export default {' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | head -1)
  if [ -n "$OPTIONS_API" ]; then
    ERRORS="${ERRORS}\n  [VUE] Options API. Use <script setup lang=\"ts\">:\n${OPTIONS_API}\n"
  fi
fi

# ── ERROR 6: Legacy/non-v2 token names ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *.css ]]; then
  LEGACY=$(grep -n 'var(--text-primary)\|var(--text-body)\|var(--text-secondary)\|var(--text-muted)\|var(--text-disabled)\|var(--text-tertiary)\|var(--text-base)\|var(--text-sm)\|var(--text-xs)\|var(--text-lg)\|var(--text-2xs)\|var(--bg-surface)\|var(--bg-raised)\|var(--bg-base)\|var(--bg-input)\|var(--bg-overlay)\|var(--bg-elevated)\|var(--bg-subtle)\|var(--bg-deepest)\|var(--border-default)\|var(--border-subtle)\|var(--border-strong)\|var(--font-semibold)\|var(--font-medium)\|var(--font-bold)\|var(--font-mono)\|var(--font-sans)\|var(--brand)\|var(--brand-hover)\|var(--brand-text)\|var(--brand-subtle)\|var(--brand-muted)\|var(--space-\|var(--radius-\|var(--shadow-\|var(--transition-\|var(--duration-\|var(--palette-\|var(--color-primary)\|var(--color-danger)\|var(--color-success)\|var(--color-warning)\|var(--status-ok)\|var(--status-error)\|var(--status-warn)\|var(--hover)\|var(--active)\|var(--selected)\|var(--focus-ring)\|var(--focus-bg)' "$FILE" 2>/dev/null | head -8)
  if [ -n "$LEGACY" ]; then
    ERRORS="${ERRORS}\n  [V2] Legacy token found. Use v2 tokens:\n"
    ERRORS="${ERRORS}    Text: --t1 --t2 --t3 --t4 | Surfaces: --base --ground --surface --raised\n"
    ERRORS="${ERRORS}    Borders: --b1 --b2 --b3 | Status: --ok --warn --err | Brand: --red --green\n"
    ERRORS="${ERRORS}    Font: --font --mono --fs --fsl | Spacing: --pad --r --rs | Motion: --ease\n"
    ERRORS="${ERRORS}    Weights: literal 400/500/600/700 | Sizes: literal px values\n"
    ERRORS="${ERRORS}  Found:\n${LEGACY}\n"
  fi
fi

# ════════════════════════════════════════
# WARNINGS — inform but DON'T block
# ════════════════════════════════════════

# ── WARN 7: @media queries ──
if [[ "$FILE" == *.vue ]]; then
  MEDIA=$(grep -n '@media' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | grep -v '@media print' | grep -v 'prefers-reduced-motion' | head -3)
  if [ -n "$MEDIA" ]; then
    WARNINGS="${WARNINGS}\n  [LAYOUT] @media query. Prefer @container queries:\n${MEDIA}\n"
  fi
fi

# ── WARN 8: Inline styles ──
if [[ "$FILE" == *.vue ]]; then
  INLINE=$(grep -n 'style="' "$FILE" 2>/dev/null | grep -v ':style' | grep -v '<!--' | head -3)
  if [ -n "$INLINE" ]; then
    WARNINGS="${WARNINGS}\n  [STYLE] Inline style=\"\". Prefer CSS classes:\n${INLINE}\n"
  fi
fi

# ── WARN 9: Direct axios import ──
if [[ "$FILE" == *"components/"* ]] || [[ "$FILE" == *"views/"* ]] || [[ "$FILE" == *"stores/"* ]]; then
  DIRECT_AXIOS=$(grep -n "from 'axios'\|from \"axios\"\|import axios" "$FILE" 2>/dev/null | head -3)
  if [ -n "$DIRECT_AXIOS" ]; then
    WARNINGS="${WARNINGS}\n  [API] Direct axios import. Use api/ modules:\n${DIRECT_AXIOS}\n"
  fi
fi

# ── WARN 10: Business calculations in frontend ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *"stores/"* ]] || [[ "$FILE" == *"composables/"* ]]; then
  if [[ ! "$FILE" == *"utils/"* ]] && [[ ! "$FILE" == *"useDashboardInsights"* ]]; then
    BIZ_CALC=$(grep -n 'price.*\*\|cost.*\*\|margin.*\*\|\* hourly\|\* quantity\|_rate \*\|_cost \*\|_price \*' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | grep -v 'formatCurrency\|formatNumber\|formatPrice' | head -3)
    if [ -n "$BIZ_CALC" ]; then
      WARNINGS="${WARNINGS}\n  [DATA] Possible business calculation in frontend. Compute in backend:\n${BIZ_CALC}\n"
    fi
  fi
fi

# ── WARN 11: getPropertyValue with legacy tokens ──
if [[ "$FILE" == *.vue ]]; then
  LEGACY_JS=$(grep -n "getPropertyValue.*--color-\|getPropertyValue.*--status-\|getPropertyValue.*--brand\|getPropertyValue.*--text-\|getPropertyValue.*--bg-\|getPropertyValue.*--border-" "$FILE" 2>/dev/null | head -3)
  if [ -n "$LEGACY_JS" ]; then
    WARNINGS="${WARNINGS}\n  [JS] getPropertyValue with legacy token. Use v2: --ok, --err, --warn, --red, --t1..t4, --b1..b3:\n${LEGACY_JS}\n"
  fi
fi

# ════════════════════════════════════════
# REPORT
# ════════════════════════════════════════

if [ -n "$ERRORS" ] || [ -n "$WARNINGS" ]; then
  echo "═══════════════════════════════════════"
  echo "V2 DESIGN VALIDATION: $(basename "$FILE")"
  echo "═══════════════════════════════════════"

  if [ -n "$ERRORS" ]; then
    echo ""
    echo "ERRORS (must fix):"
    echo -e "$ERRORS"
  fi

  if [ -n "$WARNINGS" ]; then
    echo ""
    echo "WARNINGS (should fix):"
    echo -e "$WARNINGS"
  fi

  echo "Ref: tiling-preview-v2.html (visual) + design-system.css v6.0 (tokens)"
  echo "═══════════════════════════════════════"

  if [ -n "$ERRORS" ]; then
    exit 1
  fi
fi

exit 0
