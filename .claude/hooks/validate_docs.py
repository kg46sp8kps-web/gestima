#!/usr/bin/env python3
"""
Hook: PreToolUse/PostToolUse for Edit/Write on documentation files
Works in BOTH main chat and subagent frontmatter
Reads JSON from stdin (official Claude Code hook protocol)
Exit 0 = OK, Exit 2 = block with message (stderr)

RULES ENFORCED:
L-040: Doc files ONLY in docs/ (not root!)
DOC-001: CLAUDE.local.md max 40 lines (prevent context pollution)
"""
import sys
import json
import os

ALLOWED_ROOT_FILES = {'README.md', 'CLAUDE.md', 'CHANGELOG.md', 'CLAUDE.local.md'}
CLAUDE_LOCAL_MAX_LINES = 40

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

    # Only check .md files
    if not file_path.endswith('.md'):
        sys.exit(0)

    basename = os.path.basename(file_path)
    dirname = os.path.dirname(file_path)

    # ─── DOC-001: CLAUDE.local.md size guard ─────────────
    if basename == 'CLAUDE.local.md':
        # Get the content that will be written
        if hook_event == "PreToolUse" and tool_name == "Write":
            content = tool_input.get("content", "")
        elif hook_event == "PreToolUse" and tool_name == "Edit":
            new_string = tool_input.get("new_string", "")
            # For Edit, estimate: read current file + new content
            try:
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
                for path in [file_path, os.path.join(project_dir, file_path)]:
                    try:
                        with open(path, 'r') as f:
                            current = f.read()
                            break
                    except FileNotFoundError:
                        current = ""
                        continue
                old_string = tool_input.get("old_string", "")
                if old_string and new_string:
                    content = current.replace(old_string, new_string, 1)
                else:
                    content = current
            except Exception:
                content = ""
        elif hook_event == "PostToolUse":
            try:
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
                for path in [file_path, os.path.join(project_dir, file_path)]:
                    try:
                        with open(path, 'r') as f:
                            content = f.read()
                            break
                    except FileNotFoundError:
                        continue
                else:
                    content = ""
            except Exception:
                content = ""
        else:
            content = ""

        if content:
            line_count = len(content.strip().split('\n'))
            if line_count > CLAUDE_LOCAL_MAX_LINES:
                print(f"DOC-001 VIOLATION: CLAUDE.local.md has {line_count} lines (max {CLAUDE_LOCAL_MAX_LINES})!", file=sys.stderr)
                print("", file=sys.stderr)
                print("CLAUDE.local.md is injected into EVERY prompt = context pollution!", file=sys.stderr)
                print("", file=sys.stderr)
                print("WHAT BELONGS IN CLAUDE.local.md (max 1-3 lines each):", file=sys.stderr)
                print("  - ACTIVE WARNINGS: smazane services, deprecated APIs", file=sys.stderr)
                print("  - CURRENT VERSION: tag + commit hash", file=sys.stderr)
                print("  - KEY LEARNINGS: L-0XX one-liner pouceni", file=sys.stderr)
                print("  - TECH DEBT: kratky seznam", file=sys.stderr)
                print("", file=sys.stderr)
                print("WHAT DOES NOT BELONG (move elsewhere!):", file=sys.stderr)
                print("  - Design system pravidla  → skill gestima-design-system", file=sys.stderr)
                print("  - Backend/frontend vzory  → skill gestima-backend-patterns", file=sys.stderr)
                print("  - Detailni popisy         → docs/ADR/NNN-name.md", file=sys.stderr)
                print("  - Session logy            → docs/audits/ nebo SMAZAT", file=sys.stderr)
                print("  - Implementacni detaily   → docs/reference/", file=sys.stderr)
                print("", file=sys.stderr)
                print("HOW TO FIX:", file=sys.stderr)
                print("  1. Move detailed content to the correct location (see above)", file=sys.stderr)
                print("  2. Keep only a 1-line pointer in CLAUDE.local.md", file=sys.stderr)
                print("     Example: '- L-063: DS v4.0 schvalen → viz skill gestima-design-system'", file=sys.stderr)
                print("  3. Delete old session notes (git preserves history)", file=sys.stderr)
                sys.exit(2)

    # ─── L-040: No .md files in project root ─────────────
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
