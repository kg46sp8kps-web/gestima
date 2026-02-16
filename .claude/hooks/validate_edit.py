#!/usr/bin/env python3
"""
Hook: PreToolUse/PostToolUse for Edit/Write on Python files
Works in BOTH main chat (PostToolUse) and subagent frontmatter (PreToolUse)
Reads JSON from stdin (official Claude Code hook protocol)
Exit 0 = OK, Exit 2 = block with message (stderr)

RULES ENFORCED (BLOCKING = exit 2):
L-008: Transaction handling (try/except/rollback) — BLOCKING
L-009: Pydantic Field() validation — BLOCKING
L-042: No secrets/credentials in code — BLOCKING
L-043: No bare except / except pass — BLOCKING
L-044: No debug statements in production code — BLOCKING

RULES ENFORCED (WARNING = stderr only):
L-007: Audit fields on mutable models
L-015: No weakening of validation constraints
L-028: SQLite Enum handling
L-001: No business calculations in routers
L-045: Missing type hints on functions
L-046: TODO/FIXME/HACK tracking
L-047: Missing response_model on endpoints
L-048: Missing docstring on public functions
"""
import sys
import json
import re
import os

# ─── Patterns for secret detection (L-042) ─────────────
SECRET_PATTERNS = [
    (re.compile(r'''(?:password|passwd|pwd|secret|api_key|apikey|api_secret|token|auth_token|access_token|private_key)\s*=\s*["\'][^"\']{4,}["\']''', re.IGNORECASE), "hardcoded credential"),
    (re.compile(r'''(?:sk-|pk-|ak-|rk_live_|sk_live_|sk_test_|pk_test_)[a-zA-Z0-9]{10,}'''), "API key pattern"),
    (re.compile(r'''(?:ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]{30,}'''), "GitHub token"),
    (re.compile(r'''-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'''), "private key"),
    (re.compile(r'''(?:AKIA|ASIA)[A-Z0-9]{16}'''), "AWS access key"),
]

# Lines/contexts to skip in secret detection
SECRET_SKIP_PATTERNS = [
    'os.environ', 'os.getenv', 'settings.', 'config.', 'Config.',
    'SECRET_KEY', '# example', '# test', 'test_', 'fixture',
    'def test_', 'mock', 'Mock', 'placeholder', 'example.com',
    'localhost', '= Field(', 'description='
]

def main():
    # ─── Read JSON from stdin ────────────────────────────
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # Can't parse → skip

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    hook_event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")

    # Fallback: env var (legacy)
    if not file_path:
        file_path = os.environ.get("TOOL_INPUT_FILE_PATH", "")
    if not file_path:
        sys.exit(0)

    # Only check Python files in app/ or tests/
    if not re.search(r'(app|tests)/.*\.py$', file_path):
        sys.exit(0)

    is_test_file = '/tests/' in file_path or file_path.startswith('tests/')

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

    # ═══════════════════════════════════════════════════════
    # BLOCKING RULES (exit 2)
    # ═══════════════════════════════════════════════════════

    # ─── L-008: Transaction handling (BLOCKING) ──────────
    if 'db.commit()' in content and not is_test_file:
        # Check that every db.commit() has try: within 10 lines before it
        for i, line in enumerate(lines):
            if 'db.commit()' in line:
                context_before = '\n'.join(lines[max(0, i-10):i+1])
                if 'try:' not in context_before:
                    print(f"L-008 VIOLATION: db.commit() without try/except/rollback in {file_path}", file=sys.stderr)
                    print("Every db.commit() MUST be wrapped in:", file=sys.stderr)
                    print("  try:", file=sys.stderr)
                    print("      await db.commit()", file=sys.stderr)
                    print("  except Exception:", file=sys.stderr)
                    print("      await db.rollback()", file=sys.stderr)
                    print("      raise", file=sys.stderr)
                    sys.exit(2)

        # Verify rollback exists somewhere
        if 'db.rollback()' not in content:
            print(f"L-008 VIOLATION: db.commit() found but no db.rollback() in {file_path}", file=sys.stderr)
            print("Every try/commit block MUST have except/rollback", file=sys.stderr)
            sys.exit(2)

    # ─── L-009: Pydantic Field() validation (BLOCKING) ──
    if '/schemas/' in file_path or 'schemas/' in file_path:
        bare_types = []
        for line in lines:
            if re.match(r'^\s+\w+:\s+(str|int|float|bool|Optional\[)', line):
                if '= Field(' not in line and '= field(' not in line and '=' not in line:
                    bare_types.append(line.rstrip())
        if bare_types:
            print(f"L-009 VIOLATION: Bare type without Field() in {file_path}", file=sys.stderr)
            print("Found:", file=sys.stderr)
            for bt in bare_types[:5]:
                print(f"  {bt}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Use Field() with constraints:", file=sys.stderr)
            print("  name: str = Field(..., min_length=1, max_length=200)", file=sys.stderr)
            print("  quantity: int = Field(..., gt=0)", file=sys.stderr)
            print("  price: float = Field(..., ge=0)", file=sys.stderr)
            sys.exit(2)

    # ─── L-042: No secrets/credentials in code (BLOCKING) ─
    if not is_test_file:
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip comments and known safe patterns
            if stripped.startswith('#'):
                continue
            if any(skip in line for skip in SECRET_SKIP_PATTERNS):
                continue
            for pattern, desc in SECRET_PATTERNS:
                if pattern.search(line):
                    print(f"L-042 VIOLATION: Possible {desc} in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {stripped[:80]}...", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("NEVER hardcode secrets! Use:", file=sys.stderr)
                    print("  os.environ.get('SECRET_NAME')", file=sys.stderr)
                    print("  settings.SECRET_NAME  (from config.py)", file=sys.stderr)
                    sys.exit(2)

    # ─── L-043: No bare except / except pass (BLOCKING) ──
    if not is_test_file:
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Bare except (catches everything including SystemExit, KeyboardInterrupt)
            if re.match(r'^except\s*:', stripped):
                print(f"L-043 VIOLATION: Bare 'except:' in {file_path} (line {i+1})", file=sys.stderr)
                print("Always specify exception type:", file=sys.stderr)
                print("  except Exception:     # catches runtime errors", file=sys.stderr)
                print("  except ValueError:    # catches specific error", file=sys.stderr)
                print("  except (TypeError, KeyError):  # multiple types", file=sys.stderr)
                print("NEVER use bare 'except:' — it catches SystemExit, KeyboardInterrupt!", file=sys.stderr)
                sys.exit(2)
            # except with pass = silently swallowing errors
            if stripped == 'pass' and i > 0:
                prev_line = lines[i-1].strip()
                if re.match(r'^except\s', prev_line):
                    print(f"L-043 VIOLATION: 'except ... pass' (silent error swallowing) in {file_path} (line {i})", file=sys.stderr)
                    print("NEVER silently swallow exceptions! At minimum:", file=sys.stderr)
                    print("  except Exception as e:", file=sys.stderr)
                    print("      logger.warning(f'Operation failed: {e}')", file=sys.stderr)
                    print("Or re-raise if in transaction context.", file=sys.stderr)
                    sys.exit(2)

    # ─── L-044: No debug statements in production (BLOCKING)
    if not is_test_file and ('/services/' in file_path or '/routers/' in file_path or '/models/' in file_path):
        debug_patterns = [
            (re.compile(r'^\s*print\s*\('), 'print()'),
            (re.compile(r'^\s*breakpoint\s*\('), 'breakpoint()'),
            (re.compile(r'^\s*import\s+pdb'), 'import pdb'),
            (re.compile(r'^\s*pdb\.set_trace'), 'pdb.set_trace()'),
            (re.compile(r'^\s*import\s+ipdb'), 'import ipdb'),
        ]
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                continue
            for pattern, name in debug_patterns:
                if pattern.search(line):
                    # Allow print in __main__ blocks and logging setup
                    context_before = '\n'.join(lines[max(0, i-5):i+1])
                    if "__main__" in context_before or "if __name__" in context_before:
                        continue
                    # Allow print in CLI/scripts
                    if 'gestima.py' in file_path or 'cli' in file_path:
                        continue
                    print(f"L-044 VIOLATION: Debug statement '{name}' in {file_path} (line {i+1})", file=sys.stderr)
                    print(f"  {line.strip()}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("Use proper logging instead:", file=sys.stderr)
                    print("  import logging", file=sys.stderr)
                    print("  logger = logging.getLogger(__name__)", file=sys.stderr)
                    print("  logger.debug('message')  # for debug info", file=sys.stderr)
                    print("  logger.info('message')   # for info", file=sys.stderr)
                    sys.exit(2)

    # ═══════════════════════════════════════════════════════
    # WARNING RULES (stderr only, no block)
    # ═══════════════════════════════════════════════════════

    # ─── L-007: Audit fields on models (WARNING) ─────────
    if '/models/' in file_path or 'models/' in file_path:
        if re.search(r'class\s+\w+.*Base\)', content):
            if not any(x in content for x in ['AuditMixin', 'created_at', 'created_by']):
                print(f"L-007 WARNING: Model in {file_path} missing audit fields", file=sys.stderr)
                print("Add AuditMixin or manual created_at/updated_at/created_by/updated_by", file=sys.stderr)

    # ─── L-015: Validation weakening detection (WARNING) ─
    if '/schemas/' in file_path or 'schemas/' in file_path:
        weakening_patterns = ['# removed', '# disabled', '# relaxed', '# was gt=', '# was min_length=']
        if any(p in content for p in weakening_patterns):
            print(f"L-015 WARNING: Possible validation weakening in {file_path}", file=sys.stderr)
            print("NEVER weaken validation to fit bad data! Fix the DATA, not the schema.", file=sys.stderr)

    # ─── L-028: SQLite Enum handling (WARNING) ────────────
    if '/models/' in file_path or 'models/' in file_path:
        if 'Enum(' in content and 'String(' not in content:
            print(f"L-028 WARNING: Using Enum() without String() wrapper in {file_path}", file=sys.stderr)
            print("SQLite requires: Column(String(X)) with Python-side Enum validation", file=sys.stderr)

    # ─── L-001: No business calculations in routers ──────
    if '/routers/' in file_path or 'routers/' in file_path:
        calc_pattern = re.compile(r'(\*\s*\d|\d\s*\*|price\s*=|cost\s*=|total\s*=).*[+\-*/]')
        skip_words = ['page', 'offset', 'limit', 'skip', 'count']
        for line in lines[:200]:
            if calc_pattern.search(line):
                if not any(w in line.lower() for w in skip_words):
                    print(f"L-001 WARNING: Possible business calculation in router {file_path}", file=sys.stderr)
                    print("Business logic belongs in app/services/*.py, NOT in routers!", file=sys.stderr)
                    break

    # ─── L-045: Missing type hints on functions (WARNING) ─
    if not is_test_file:
        for i, line in enumerate(lines):
            # Match function definitions without return type
            match = re.match(r'^(?:async\s+)?def\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                # Skip private/magic methods and simple ones
                if func_name.startswith('_') and func_name != '__init__':
                    continue
                if '->' not in line and ':' in line:
                    # Check if the line or next line has ->
                    next_lines = '\n'.join(lines[i:min(i+3, len(lines))])
                    if '->' not in next_lines:
                        print(f"L-045 WARNING: Function '{func_name}' missing return type hint in {file_path} (line {i+1})", file=sys.stderr)
                        print("Add return type: def func() -> ReturnType:", file=sys.stderr)
                        break  # Only warn once per file

    # ─── L-046: TODO/FIXME/HACK tracking (WARNING) ───────
    todo_count = 0
    for i, line in enumerate(lines):
        if re.search(r'#\s*(TODO|FIXME|HACK|XXX|WORKAROUND)\b', line, re.IGNORECASE):
            todo_count += 1
            if todo_count == 1:
                print(f"L-046 WARNING: Found TODO/FIXME markers in {file_path}:", file=sys.stderr)
            if todo_count <= 3:
                print(f"  Line {i+1}: {line.strip()[:80]}", file=sys.stderr)
    if todo_count > 0:
        print(f"  Total: {todo_count} marker(s). Track and resolve before release.", file=sys.stderr)

    # ─── L-047: Missing response_model on endpoints (WARNING)
    if '/routers/' in file_path or 'routers/' in file_path:
        for i, line in enumerate(lines):
            if re.search(r'@router\.(get|post|put|patch|delete)\s*\(', line):
                # Check this line and next for response_model
                context = '\n'.join(lines[i:min(i+3, len(lines))])
                if 'response_model' not in context:
                    print(f"L-047 WARNING: Endpoint without response_model in {file_path} (line {i+1})", file=sys.stderr)
                    print("Add response_model=SchemaName for consistent API responses", file=sys.stderr)
                    break  # Only warn once

    # ─── L-048: Missing docstring on public functions (WARNING)
    if not is_test_file:
        func_count = 0
        missing_docstring = 0
        for i, line in enumerate(lines):
            match = re.match(r'^(?:async\s+)?def\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                if func_name.startswith('_'):
                    continue
                func_count += 1
                # Check next non-empty line for docstring
                for j in range(i+1, min(i+4, len(lines))):
                    next_stripped = lines[j].strip()
                    if next_stripped:
                        if not (next_stripped.startswith('"""') or next_stripped.startswith("'''")):
                            missing_docstring += 1
                        break
        if missing_docstring > 0 and func_count > 0:
            ratio = missing_docstring / func_count
            if ratio > 0.5:  # Only warn if more than half are missing
                print(f"L-048 WARNING: {missing_docstring}/{func_count} public functions lack docstrings in {file_path}", file=sys.stderr)
                print("Add docstrings to public functions for maintainability.", file=sys.stderr)

    sys.exit(0)

if __name__ == '__main__':
    main()
