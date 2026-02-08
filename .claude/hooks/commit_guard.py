#!/usr/bin/env python3
"""
Hook: PreToolUse for Bash — Git commit quality gate
Intercepts 'git commit' commands and verifies:
1. No .env / secrets files being committed
2. No debug statements in staged files
3. Commit message format is correct
4. CHANGELOG.md updated if feature commit

Exit 0 = allow, Exit 2 = block
"""
import sys
import json
import os
import subprocess
import re

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only intercept git commit commands
    if "git commit" not in command:
        sys.exit(0)

    # Skip if it's just git commit --amend or similar status checks
    if "git commit --dry-run" in command:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

    # ─── Check 1: Dangerous files in staging ─────────────
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception:
        staged_files = []

    if not staged_files:
        sys.exit(0)

    # Check for sensitive files
    dangerous_patterns = [
        '.env', '.env.local', '.env.production',
        'credentials', 'secret', 'private_key',
        '.pem', '.key', '.p12', '.pfx',
        'id_rsa', 'id_ed25519'
    ]
    dangerous_staged = []
    for f in staged_files:
        basename = os.path.basename(f).lower()
        if any(p in basename for p in dangerous_patterns):
            dangerous_staged.append(f)

    if dangerous_staged:
        print(f"COMMIT GUARD VIOLATION: Sensitive files staged for commit!", file=sys.stderr)
        for f in dangerous_staged:
            print(f"  ❌ {f}", file=sys.stderr)
        print("", file=sys.stderr)
        print("NEVER commit secrets! Remove with: git reset HEAD <file>", file=sys.stderr)
        sys.exit(2)

    # ─── Check 2: Debug statements in staged Python files ─
    for f in staged_files:
        if f.endswith('.py') and ('app/' in f) and 'test' not in f:
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached", f],
                    capture_output=True, text=True, timeout=5,
                    cwd=project_dir
                )
                diff_content = result.stdout
                # Check added lines only (lines starting with +)
                added_lines = [l for l in diff_content.split('\n') if l.startswith('+') and not l.startswith('+++')]
                for line in added_lines:
                    if re.search(r'^\+\s*(print\s*\(|breakpoint\s*\(|import\s+pdb)', line):
                        print(f"COMMIT GUARD VIOLATION: Debug statement in staged file {f}!", file=sys.stderr)
                        print(f"  {line.strip()}", file=sys.stderr)
                        print("Remove debug statements before committing.", file=sys.stderr)
                        sys.exit(2)
            except Exception:
                pass

    # ─── Check 3: Commit message format ──────────────────
    # Extract commit message from command (after -m)
    msg_match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
    if not msg_match:
        # Try heredoc format
        msg_match = re.search(r'-m\s+"\$\(cat <<', command)
        if msg_match:
            # Heredoc — extract the first line
            lines = command.split('\n')
            for line in lines[1:]:
                line = line.strip()
                if line and not line.startswith('EOF') and not line.startswith('Co-Authored'):
                    msg_match = re.match(r'^(feat|fix|refactor|docs|test|chore|build|ci|perf|style)[\(:]', line)
                    break

    if msg_match and isinstance(msg_match, re.Match):
        msg = msg_match.group(1) if msg_match.lastindex else ""
        # Check format: type: description
        if msg and not re.match(r'^(feat|fix|refactor|docs|test|chore|build|ci|perf|style)[\(:]', msg):
            print(f"COMMIT GUARD WARNING: Commit message doesn't follow conventional format", file=sys.stderr)
            print("Expected: feat: description, fix: description, etc.", file=sys.stderr)
            print(f"Got: {msg[:60]}", file=sys.stderr)
            # WARNING only, don't block

    # ─── Check 4: Feature commit without CHANGELOG ───────
    has_feature_code = any(
        f.startswith(('app/services/', 'app/routers/', 'frontend/src/components/'))
        for f in staged_files
    )
    has_changelog = 'CHANGELOG.md' in staged_files

    if has_feature_code and not has_changelog:
        # Check if commit message starts with feat:
        if 'feat' in command.lower():
            print("COMMIT GUARD WARNING: Feature commit without CHANGELOG.md update!", file=sys.stderr)
            print("Consider adding a CHANGELOG entry for new features.", file=sys.stderr)
            # WARNING only, don't block

    # ─── Check 5: Co-Authored-By present ─────────────────
    if 'Co-Authored-By' not in command and 'co-authored-by' not in command.lower():
        print("COMMIT GUARD WARNING: Missing Co-Authored-By in commit message.", file=sys.stderr)
        print("Add: Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>", file=sys.stderr)
        # WARNING only

    sys.exit(0)

if __name__ == '__main__':
    main()
