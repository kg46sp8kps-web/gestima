#!/bin/bash
# Validates frontend files against design system rules.
# Called by Claude Code hooks after editing .vue/.ts/.css files in frontend/.
# Exit 1 = block the edit (ERRORS), Exit 0 = allow (may include WARNINGS).
#
# ERRORS (block edit):
#   1. Hardcoded hex colors (use CSS variables)
#   2. TypeScript 'any' type (use proper types)
#   3. !important in CSS (fix specificity)
#   4. @media queries in components (use @container)
#   5. Missing <style scoped> in .vue files
#   6. Hardcoded px font sizes (use --text-* tokens)
#   7. Options API usage (use <script setup>)
#
# WARNINGS (inform but allow):
#   8. Inline style="" attributes
#   9. Direct axios import in components
#  10. Raw rgb/rgba/hsl colors in components
#  11. Direct lucide-vue-next import

FILE="$1"

# Only check frontend files
if [[ ! "$FILE" == *"frontend/src/"* ]]; then
  exit 0
fi

# Skip design-system.css itself (it defines the tokens)
if [[ "$FILE" == *"design-system.css"* ]]; then
  exit 0
fi

# Skip base CSS files that legitimately define styles
if [[ "$FILE" == *"assets/css/"* ]]; then
  exit 0
fi

ERRORS=""
WARNINGS=""

# ════════════════════════════════════════
# ERRORS — these BLOCK the edit
# ════════════════════════════════════════

# ── ERROR 1: Hardcoded hex colors ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *.css ]]; then
  HARDCODED=$(grep -n '#[0-9a-fA-F]\{3,8\}' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | grep -v 'var(--' | grep -v 'data-testid' | grep -v 'import' | grep -v 'href=' | grep -v 'url(' | grep -v 'source-map' | head -5)
  if [ -n "$HARDCODED" ]; then
    ERRORS="${ERRORS}\n  [DESIGN] Hardcoded hex color. Use var(--token) from design-system.css:\n${HARDCODED}\n"
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

# ── ERROR 4: @media queries (use @container instead) ──
if [[ "$FILE" == *.vue ]]; then
  MEDIA=$(grep -n '@media' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | grep -v '@media print' | head -3)
  if [ -n "$MEDIA" ]; then
    ERRORS="${ERRORS}\n  [LAYOUT] @media query found. Use @container queries instead:\n${MEDIA}\n"
  fi
fi

# ── ERROR 5: Missing <style scoped> in .vue files ──
if [[ "$FILE" == *.vue ]]; then
  HAS_STYLE=$(grep -c '<style' "$FILE" 2>/dev/null)
  if [ "$HAS_STYLE" -gt 0 ]; then
    UNSCOPED=$(grep -n '<style' "$FILE" 2>/dev/null | grep -v 'scoped' | grep -v '<!--' | head -3)
    if [ -n "$UNSCOPED" ]; then
      ERRORS="${ERRORS}\n  [SCOPE] <style> without 'scoped'. Use <style scoped>:\n${UNSCOPED}\n"
    fi
  fi
fi

# ── ERROR 6: Hardcoded font-size in px ──
if [[ "$FILE" == *.vue ]]; then
  HARDCODED_FONT=$(grep -n 'font-size:' "$FILE" 2>/dev/null | grep -v 'var(--' | grep -v '\/\/' | grep -v '\/\*' | head -3)
  if [ -n "$HARDCODED_FONT" ]; then
    ERRORS="${ERRORS}\n  [TYPOGRAPHY] Hardcoded font-size. Use var(--text-xs/sm/base/md/lg/xl):\n${HARDCODED_FONT}\n"
  fi
fi

# ── ERROR 7: Options API ──
if [[ "$FILE" == *.vue ]]; then
  OPTIONS_API=$(grep -n 'export default {' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | head -1)
  if [ -n "$OPTIONS_API" ]; then
    ERRORS="${ERRORS}\n  [VUE] Options API (export default {}). Use <script setup lang=\"ts\">:\n${OPTIONS_API}\n"
  fi
fi

# ════════════════════════════════════════
# WARNINGS — inform but DON'T block
# ════════════════════════════════════════

# ── WARN 8: Inline styles ──
if [[ "$FILE" == *.vue ]]; then
  INLINE=$(grep -n 'style="' "$FILE" 2>/dev/null | grep -v ':style' | grep -v '<!--' | head -3)
  if [ -n "$INLINE" ]; then
    WARNINGS="${WARNINGS}\n  [STYLE] Inline style=\"\" found. Prefer CSS classes:\n${INLINE}\n"
  fi
fi

# ── WARN 9: Direct axios import ──
if [[ "$FILE" == *"components/"* ]] || [[ "$FILE" == *"views/"* ]] || [[ "$FILE" == *"stores/"* ]]; then
  DIRECT_AXIOS=$(grep -n "from 'axios'\|from \"axios\"\|import axios" "$FILE" 2>/dev/null | head -3)
  if [ -n "$DIRECT_AXIOS" ]; then
    WARNINGS="${WARNINGS}\n  [API] Direct axios import. Use api/ modules instead:\n${DIRECT_AXIOS}\n"
  fi
fi

# ── WARN 10: Raw rgb/rgba/hsl colors ──
if [[ "$FILE" == *.vue ]]; then
  # Allow known design system rgba patterns: black overlays, white overlays, brand, error
  RAW_COLORS=$(grep -n 'rgb(\|rgba(\|hsl(' "$FILE" 2>/dev/null \
    | grep -v '\/\/' | grep -v '\/\*' | grep -v 'var(--' \
    | grep -v 'rgba(0,' | grep -v 'rgba(255,' \
    | grep -v 'rgba(153, 27, 27' | grep -v 'rgba(239, 68, 68' \
    | head -3)
  if [ -n "$RAW_COLORS" ]; then
    WARNINGS="${WARNINGS}\n  [DESIGN] Non-standard rgba/rgb color. Consider using a CSS variable:\n${RAW_COLORS}\n"
  fi
fi

# ── WARN 11: Direct lucide import ──
if [[ "$FILE" == *"components/"* ]]; then
  DIRECT_LUCIDE=$(grep -n "from 'lucide-vue-next'" "$FILE" 2>/dev/null | head -1)
  if [ -n "$DIRECT_LUCIDE" ]; then
    WARNINGS="${WARNINGS}\n  [ICONS] Direct lucide-vue-next import. Prefer @/config/icons:\n${DIRECT_LUCIDE}\n"
  fi
fi

# ── WARN 12: Business logic calculations in frontend ──
if [[ "$FILE" == *.vue ]] || [[ "$FILE" == *"stores/"* ]] || [[ "$FILE" == *"composables/"* ]]; then
  # Catch price/cost/margin calculations that belong in backend
  # Skip formatters (utils/formatters.ts) and display-only math (pagination)
  if [[ ! "$FILE" == *"utils/"* ]] && [[ ! "$FILE" == *"useDashboardInsights"* ]]; then
    BIZ_CALC=$(grep -n 'price.*\*\|cost.*\*\|margin.*\*\|\* hourly\|\* quantity\|_rate \*\|_cost \*\|_price \*' "$FILE" 2>/dev/null | grep -v '\/\/' | grep -v '\/\*' | grep -v 'formatCurrency\|formatNumber\|formatPrice' | head -3)
    if [ -n "$BIZ_CALC" ]; then
      WARNINGS="${WARNINGS}\n  [DATA] Possible business calculation in frontend. Prices/costs/margins must be calculated in backend (services/):\n${BIZ_CALC}\n"
    fi
  fi
fi

# ════════════════════════════════════════
# REPORT
# ════════════════════════════════════════

if [ -n "$ERRORS" ] || [ -n "$WARNINGS" ]; then
  echo "========================================="
  echo "FRONTEND VALIDATION: $(basename "$FILE")"
  echo "========================================="

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

  echo "Reference: frontend/template.html (visual) + design-system.css (tokens)"
  echo "========================================="

  # Only block on ERRORS, not warnings
  if [ -n "$ERRORS" ]; then
    exit 1
  fi
fi

exit 0
