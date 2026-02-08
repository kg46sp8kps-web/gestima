#!/usr/bin/env python3
"""
Hook: PreToolUse/PostToolUse for Edit/Write on documentation files
Works in BOTH main chat and subagent frontmatter
Reads JSON from stdin (official Claude Code hook protocol)
Exit 0 = OK, Exit 2 = block with message (stderr)

RULES ENFORCED:
L-040: Doc files ONLY in docs/ (not root!)
"""
import sys
import json
import os

ALLOWED_ROOT_FILES = {'README.md', 'CLAUDE.md', 'CHANGELOG.md', 'CLAUDE.local.md'}

def main():
    # ─── Read JSON from stdin ────────────────────────────
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        file_path = os.environ.get("TOOL_INPUT_FILE_PATH", "")
    if not file_path:
        sys.exit(0)

    # Only check .md files
    if not file_path.endswith('.md'):
        sys.exit(0)

    # ─── L-040: No .md files in project root ─────────────
    basename = os.path.basename(file_path)
    dirname = os.path.dirname(file_path)

    # Check if file is in project root
    # Handle: "NOTES.md", "./NOTES.md", "/Users/.../Gestima/NOTES.md"
    is_root = False
    if dirname in ('', '.', '/'):
        is_root = True
    elif dirname.endswith('/Gestima') or dirname.endswith('Gestima'):
        is_root = True
    elif basename == file_path:  # bare filename, no path
        is_root = True

    if is_root and basename not in ALLOWED_ROOT_FILES:
        print(f"L-040 VIOLATION: Documentation file '{basename}' in project root!", file=sys.stderr)
        print("", file=sys.stderr)
        print("ONLY these .md files are allowed in root:", file=sys.stderr)
        for f in sorted(ALLOWED_ROOT_FILES):
            print(f"  - {f}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Move to appropriate location:", file=sys.stderr)
        print("  docs/ADR/NNN-name.md          # Architecture decisions", file=sys.stderr)
        print("  docs/guides/NAME.md            # How-to guides", file=sys.stderr)
        print("  docs/audits/YYYY-MM-DD-name.md # Audit notes", file=sys.stderr)
        print("  docs/reference/NAME.md         # Reference docs", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == '__main__':
    main()
