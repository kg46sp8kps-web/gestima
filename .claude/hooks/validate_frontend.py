#!/usr/bin/env python3
"""
Hook: PreToolUse/PostToolUse for Edit/Write on frontend files
Works in BOTH main chat (PostToolUse) and subagent frontmatter (PreToolUse)
Reads JSON from stdin (official Claude Code hook protocol)
Exit 0 = OK, Exit 2 = block with message (stderr)

RULES ENFORCED (BLOCKING = exit 2):
L-011: No hardcoded colors → use CSS variables
L-033: No duplicate CSS utilities → use design-system.css
L-036: Component max 300 LOC
L-036: No hardcoded font-size
L-037: No mixing directives with event handlers
L-038: No emoji in production UI
L-044: No console.log/debug in production code
L-049: No 'any' type in TypeScript
UI:    No new Views (deprecated)
DS4-001: No filled/solid buttons (background-color on btn)
DS4-002: No chromatic colors except brand #991b1b (no green/blue/yellow in UI)
DS4-003: No font-size below 11px

RULES ENFORCED (WARNING):
CSS:   No hardcoded padding/margin → use design tokens
L-046: TODO/FIXME/HACK tracking
"""
import sys
import json
import re
import os

# Emoji ranges for detection
EMOJI_PATTERN = re.compile(
    '[\U0001F300-\U0001F9FF'   # Miscellaneous Symbols and Pictographs + Supplemental
    '\U00002600-\U000026FF'    # Misc symbols
    '\U00002700-\U000027BF'    # Dingbats
    '\U0001F600-\U0001F64F'    # Emoticons
    '\U0001F680-\U0001F6FF'    # Transport and Map
    ']'
)

# Protected CSS classes that must not be redefined
PROTECTED_CLASSES = ['.btn', '.btn-primary', '.btn-secondary', '.btn-danger',
                     '.badge', '.part-badge', '.time-badge']

def main():
    # ─── Read JSON from stdin ────────────────────────────
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    hook_event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")

    if not file_path:
        file_path = os.environ.get("TOOL_INPUT_FILE_PATH", "")
    if not file_path:
        sys.exit(0)

    is_test_file = '/__tests__/' in file_path or '.spec.' in file_path or '.test.' in file_path

    # ─── Get content to check ────────────────────────────
    # PreToolUse+Write: content from JSON (file not on disk yet)
    # PreToolUse+Edit: check new_string (what's about to be written)
    # PostToolUse: read file from disk (safety net - check final result)
    if hook_event == "PreToolUse" and tool_name == "Write":
        content = tool_input.get("content", "")
    elif hook_event == "PreToolUse" and tool_name == "Edit":
        new_string = tool_input.get("new_string", "")
        if new_string:
            content = new_string
        else:
            sys.exit(0)
    else:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except (FileNotFoundError, PermissionError):
            sys.exit(0)

    if not content:
        sys.exit(0)

    lines = content.split('\n')

    # ═══ Vue files ═══════════════════════════════════════
    if file_path.endswith('.vue'):

        # L-036: Component LOC (max 300)
        loc = len(lines)
        if loc > 300:
            print(f"L-036 VIOLATION: {file_path} has {loc} lines (max 300)", file=sys.stderr)
            print("Split into smaller components. Generic-first principle.", file=sys.stderr)
            sys.exit(2)

        # L-038: No emoji in production UI (BLOCKING)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('<!--'):
                continue
            if EMOJI_PATTERN.search(line):
                print(f"L-038 VIOLATION: Emoji found in {file_path} (line {i+1})", file=sys.stderr)
                print("Use Lucide Vue icons instead: import { IconName } from 'lucide-vue-next'", file=sys.stderr)
                print("See: docs/reference/DESIGN-SYSTEM.md -> Icons section", file=sys.stderr)
                sys.exit(2)

        # L-011: Hardcoded colors (BLOCKING)
        hex_color = re.compile(r'#[0-9a-fA-F]{3,8}')
        for i, line in enumerate(lines):
            if hex_color.search(line):
                if 'var(--' not in line and '//' not in line and '<!--' not in line and 'eslint' not in line:
                    print(f"L-011 VIOLATION: Hardcoded color in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {line.strip()}", file=sys.stderr)
                    print("Use CSS variables: var(--color-primary), var(--color-danger), etc.", file=sys.stderr)
                    sys.exit(2)

        # L-036 (CSS): Hardcoded font-size (BLOCKING)
        for i, line in enumerate(lines):
            if re.search(r'font-size:\s*\d', line):
                if 'var(--' not in line and '//' not in line:
                    print(f"L-036 VIOLATION: Hardcoded font-size in {file_path} (line {i+1})", file=sys.stderr)
                    print("Use design tokens: var(--text-xs), var(--text-sm), var(--text-base)", file=sys.stderr)
                    sys.exit(2)

        # L-044: No console.log in production Vue (BLOCKING)
        if not is_test_file:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('<!--'):
                    continue
                if re.search(r'console\.(log|debug|warn|error|trace|info)\s*\(', stripped):
                    # Allow in error handlers (catch blocks)
                    context_before = '\n'.join(lines[max(0, i-3):i+1])
                    if 'catch' in context_before or 'onError' in context_before:
                        continue
                    print(f"L-044 VIOLATION: console.{re.search(r'console[.](log|debug|warn|error|trace|info)', stripped).group(1)}() in {file_path} (line {i+1})", file=sys.stderr)
                    print("Remove debug statements before committing.", file=sys.stderr)
                    print("For error handling, use a proper error reporting mechanism.", file=sys.stderr)
                    sys.exit(2)

        # L-049: No 'any' type in TypeScript section (BLOCKING)
        if not is_test_file:
            in_script = False
            for i, line in enumerate(lines):
                if '<script' in line:
                    in_script = True
                elif '</script>' in line:
                    in_script = False
                if in_script:
                    stripped = line.strip()
                    if stripped.startswith('//'):
                        continue
                    # Detect `: any`, `as any`, `<any>`, but not in comments or strings
                    if re.search(r':\s*any\b|as\s+any\b|<any>', line):
                        # Skip eslint-disable comments
                        if 'eslint-disable' in line or 'type-ignore' in line:
                            continue
                        print(f"L-049 VIOLATION: 'any' type used in {file_path} (line {i+1})", file=sys.stderr)
                        print(f"  {stripped[:80]}", file=sys.stderr)
                        print("Use proper TypeScript types instead of 'any'.", file=sys.stderr)
                        print("Options: unknown, Record<string, unknown>, specific interface, generic", file=sys.stderr)
                        sys.exit(2)

        # DS4-001: No filled/solid buttons (BLOCKING)
        # Track <style> section for DS4-001 and DS4-002
        ds_in_style = False
        in_btn_rule = False
        for i, line in enumerate(lines):
            if '<style' in line:
                ds_in_style = True
            elif '</style>' in line:
                ds_in_style = False
                in_btn_rule = False
            if not ds_in_style:
                in_btn_rule = False
                continue
            stripped = line.strip()
            if stripped.startswith('/*') or stripped.startswith('//'):
                continue
            # Track if we're inside a .btn rule block
            if re.search(r'\.btn[^{]*\{', stripped):
                in_btn_rule = True
            if '}' in stripped:
                in_btn_rule = False
            # Check background inside btn rules
            if in_btn_rule and re.search(r'background(-color)?\s*:', stripped):
                bg_value = re.sub(r'background(-color)?\s*:\s*', '', stripped).rstrip(';').strip()
                if bg_value not in ('transparent', 'none', 'inherit', 'unset') and not bg_value.startswith('var(--bg'):
                    print(f"DS4-001 VIOLATION: Filled/solid button in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {stripped}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("DS v4.0: Buttons MUST be ghost style (transparent background).", file=sys.stderr)
                    print("Allowed: background: transparent; or background: var(--bg-*);", file=sys.stderr)
                    print("See: skill gestima-design-system or frontend/template.html", file=sys.stderr)
                    sys.exit(2)

        # DS4-002: No chromatic colors except brand (BLOCKING)
        ds_in_style2 = False
        chromatic_names = ['green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'cyan', 'teal', 'indigo', 'violet', 'lime', 'fuchsia']
        for i, line in enumerate(lines):
            if '<style' in line:
                ds_in_style2 = True
            elif '</style>' in line:
                ds_in_style2 = False
            if not ds_in_style2:
                continue
            stripped = line.strip()
            if stripped.startswith('/*') or stripped.startswith('//'):
                continue
            line_lower = line.lower()
            # Skip var() references and comments
            if 'var(--' in line or 'lucide' in line_lower:
                continue
            # Allow in dataviz contexts
            if any(dv in line_lower for dv in ['chart', 'graph', 'dataviz', 'price-bar', 'progress']):
                continue
            for color_name in chromatic_names:
                if re.search(rf'\b{color_name}\b', line_lower):
                    print(f"DS4-002 VIOLATION: Chromatic color '{color_name}' in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {stripped[:80]}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("DS v4.0: Only 3 colors allowed: black + red (#991b1b) + gray.", file=sys.stderr)
                    print("Chromatic colors ONLY in dataviz (charts, graphs, price bars).", file=sys.stderr)
                    print("See: skill gestima-design-system", file=sys.stderr)
                    sys.exit(2)

        # DS4-003: No font-size below 11px (BLOCKING)
        for i, line in enumerate(lines):
            match = re.search(r'font-size:\s*(\d+)px', line)
            if match:
                size = int(match.group(1))
                if size < 11 and 'var(--' not in line:
                    print(f"DS4-003 VIOLATION: Font-size {size}px is below minimum 11px in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {line.strip()}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("DS v4.0: Minimum font-size is 11px.", file=sys.stderr)
                    print("Use design tokens: var(--text-xs)=11px, var(--text-sm)=12px, var(--text-base)=13px", file=sys.stderr)
                    sys.exit(2)

        # L-036 (CSS): Hardcoded padding/margin with px (WARNING only)
        for i, line in enumerate(lines):
            if re.search(r'(padding|margin):\s*\d+px', line):
                if 'var(--' not in line and '//' not in line:
                    print(f"L-036 WARNING: Hardcoded padding/margin in {file_path} (line {i+1})", file=sys.stderr)
                    print("Consider using design tokens: var(--space-1) through var(--space-8)", file=sys.stderr)
                    break  # Only warn once

        # L-033: Duplicate CSS class definitions (BLOCKING)
        for cls in PROTECTED_CLASSES:
            escaped = re.escape(cls)
            if re.search(rf'^\s*{escaped}\s*\{{', content, re.MULTILINE):
                print(f"L-033 VIOLATION: Redefining global CSS class '{cls}' in {file_path}", file=sys.stderr)
                print("Use the class from design-system.css, don't redefine in <style scoped>", file=sys.stderr)
                sys.exit(2)

        # L-037: Mixing v-directive + @event for same function (BLOCKING)
        if 'v-select-on-focus' in content:
            if re.search(r'@focus=".*select', content):
                print(f"L-037 VIOLATION: Mixing v-select-on-focus directive with @focus handler in {file_path}", file=sys.stderr)
                print("Use ONLY the directive OR the event handler, NEVER both!", file=sys.stderr)
                sys.exit(2)

        # UI Pattern: No new Views (DEPRECATED)
        if '/views/' in file_path:
            allowed_views = ['Login', 'MasterData', 'Settings', 'Windows', 'Dashboard', 'Quote', 'Partner']
            if not any(v in file_path for v in allowed_views):
                print(f"UI PATTERN VIOLATION: New View created at {file_path}", file=sys.stderr)
                print("Views are DEPRECATED. Use frontend/src/components/modules/*Module.vue", file=sys.stderr)
                sys.exit(2)

        # L-046: TODO/FIXME tracking (WARNING)
        todo_count = 0
        for i, line in enumerate(lines):
            if re.search(r'(?://|<!--|/\*)\s*(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
                todo_count += 1
                if todo_count == 1:
                    print(f"L-046 WARNING: Found TODO/FIXME markers in {file_path}:", file=sys.stderr)
                if todo_count <= 3:
                    print(f"  Line {i+1}: {line.strip()[:80]}", file=sys.stderr)
        if todo_count > 0:
            print(f"  Total: {todo_count}. Track and resolve before release.", file=sys.stderr)

    # ═══ TypeScript files ════════════════════════════════
    elif re.search(r'\.(ts|tsx)$', file_path) and 'frontend/' in file_path:
        # L-038: No emoji
        for i, line in enumerate(lines):
            if line.strip().startswith('//'):
                continue
            if EMOJI_PATTERN.search(line):
                print(f"L-038 VIOLATION: Emoji found in {file_path} (line {i+1})", file=sys.stderr)
                print("Use Lucide Vue icons or plain text constants instead.", file=sys.stderr)
                sys.exit(2)

        # L-049: No 'any' type in TypeScript (BLOCKING)
        if not is_test_file:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('//'):
                    continue
                if re.search(r':\s*any\b|as\s+any\b|<any>', line):
                    if 'eslint-disable' in line or 'type-ignore' in line:
                        continue
                    print(f"L-049 VIOLATION: 'any' type used in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {stripped[:80]}", file=sys.stderr)
                    print("Use proper TypeScript types. Options: unknown, Record<string, unknown>, specific interface", file=sys.stderr)
                    sys.exit(2)

        # L-044: No console.log in production TS (BLOCKING)
        if not is_test_file:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('//'):
                    continue
                if re.search(r'console\.(log|debug)\s*\(', stripped):
                    print(f"L-044 VIOLATION: console.log/debug in {file_path} (line {i+1})", file=sys.stderr)
                    print("Remove debug statements. Use proper logging mechanism.", file=sys.stderr)
                    sys.exit(2)

    # ═══ CSS files ═══════════════════════════════════════
    elif file_path.endswith('.css') and 'frontend/' in file_path:
        if 'design-system.css' not in file_path:
            hex_color = re.compile(r'#[0-9a-fA-F]{3,8}')
            for i, line in enumerate(lines):
                if hex_color.search(line) and 'var(--' not in line and '/*' not in line:
                    print(f"L-011 WARNING: Hardcoded color in {file_path} (line {i+1})", file=sys.stderr)
                    print("Colors should be defined ONLY in design-system.css", file=sys.stderr)
                    break  # Only warn once

    sys.exit(0)

if __name__ == '__main__':
    main()
