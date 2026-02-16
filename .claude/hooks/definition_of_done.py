#!/usr/bin/env python3
"""
Hook: Stop / SubagentStop — Definition of Done (DoD) verification
Runs when an agent is about to finish. Checks that the professional
software development workflow was followed for CHANGED files only.

Checks:
1. Changed service/router files have corresponding test files
2. Schema/model changes have alembic migrations
3. Frontend changes → build freshness
4. Changed router files have response_model on new endpoints

IMPORTANT: Only checks files in `git diff --name-only` (uncommitted changes).
Does NOT audit the entire codebase — only the agent's work.

Exit 0 + JSON {"decision":"block","reason":"..."} = prevent agent from stopping
Exit 0 + no output = allow stop
"""
import sys
import json
import os
import subprocess
import re

def get_changed_files(project_dir):
    """Get list of files changed (uncommitted) in git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir
        )
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        # Also check untracked new files
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir
        )
        new_files = result2.stdout.strip().split('\n') if result2.stdout.strip() else []
        return list(set(files + new_files))
    except Exception:
        return []

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Prevent infinite loop
    if data.get("stop_hook_active", False):
        sys.exit(0)

    agent_type = data.get("agent_type", "")

    # Only apply to coding agents
    coding_agents = ["backend", "frontend", "cartman"]
    if agent_type and agent_type not in coding_agents:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    changed_files = get_changed_files(project_dir)

    # Filter out hook/config files — those are meta, not production code
    production_changes = [
        f for f in changed_files
        if not f.startswith('.claude/')
        and not f.startswith('docs/')
        and f  # skip empty strings
    ]

    if not production_changes:
        sys.exit(0)

    # Categorize changes
    changed_app_py = [f for f in production_changes if f.endswith('.py') and f.startswith('app/')]
    changed_services = [f for f in changed_app_py if '/services/' in f]
    changed_routers = [f for f in changed_app_py if '/routers/' in f]
    changed_models = [f for f in changed_app_py if '/models/' in f]
    changed_schemas = [f for f in changed_app_py if '/schemas/' in f]
    changed_frontend = [f for f in production_changes if 'frontend/' in f and f.endswith(('.vue', '.ts', '.tsx', '.css'))]
    changed_tests = [f for f in production_changes if 'test' in f.lower()]
    changed_migrations = [f for f in production_changes if 'alembic' in f or 'migration' in f]

    violations = []

    # ─── DoD-TEST: Service/Router code without test files ─
    if (changed_services or changed_routers) and not changed_tests:
        missing_tests = []
        for f in changed_services + changed_routers:
            # Convert app/services/item_service.py → tests/test_item_service.py
            basename = os.path.basename(f)
            test_name = f"tests/test_{basename}"
            test_path = os.path.join(project_dir, test_name)
            if not os.path.exists(test_path):
                missing_tests.append(f"  {f} → no {test_name}")

        if missing_tests:
            violations.append(
                "DoD-TEST: Service/router code changed but no tests updated!\n"
                "Missing test files:\n" +
                "\n".join(missing_tests[:5]) +
                "\nWrite tests for changed services/routers, or run existing tests."
            )

    # ─── DoD-MIGRATION: Model changes without migration ──
    if changed_models and not changed_migrations:
        # Only warn if actual Column/relationship changes detected
        has_schema_change = False
        for f in changed_models:
            try:
                filepath = os.path.join(project_dir, f)
                result = subprocess.run(
                    ["git", "diff", filepath],
                    capture_output=True, text=True, timeout=5,
                    cwd=project_dir
                )
                diff = result.stdout
                # Look for actual schema changes (not just imports or docstrings)
                if re.search(r'^\+.*Column\(|^\+.*relationship\(|^\+.*ForeignKey\(', diff, re.MULTILINE):
                    has_schema_change = True
                    break
            except Exception:
                pass

        if has_schema_change:
            violations.append(
                "DoD-MIGRATION: Model schema changed (Column/relationship) but no migration!\n"
                "Run: alembic revision --autogenerate -m 'description'\n"
                "     alembic upgrade head"
            )

    # ─── DoD-BUILD: Frontend changes → check build age ───
    if changed_frontend:
        dist_dir = os.path.join(project_dir, "frontend", "dist")
        if os.path.exists(dist_dir):
            import time
            dist_mtime = os.path.getmtime(dist_dir)
            age_minutes = (time.time() - dist_mtime) / 60
            if age_minutes > 30:
                violations.append(
                    "DoD-BUILD: Frontend files changed but last build is >30 min old!\n"
                    "Run: cd frontend && npm run build\n"
                    "Verify the build passes before finishing."
                )

    # ─── DoD-API: Changed routers missing response_model ──
    for f in changed_routers:
        try:
            filepath = os.path.join(project_dir, f)
            # Check ONLY the diff (new/changed lines), not entire file
            result = subprocess.run(
                ["git", "diff", filepath],
                capture_output=True, text=True, timeout=5,
                cwd=project_dir
            )
            diff = result.stdout
            # Count new endpoints in diff
            new_endpoints = len(re.findall(r'^\+.*@router\.(get|post|put|patch|delete)\s*\(', diff, re.MULTILINE))
            new_response_models = len(re.findall(r'^\+.*response_model', diff, re.MULTILINE))
            if new_endpoints > 0 and new_response_models == 0:
                violations.append(
                    f"DoD-API: New endpoints in {f} without response_model!\n"
                    "Add response_model=SchemaName to every endpoint for API consistency."
                )
        except Exception:
            pass

    # ─── Output ──────────────────────────────────────────
    if violations:
        reason = "DEFINITION OF DONE — Issues found:\n\n" + "\n\n".join(violations)
        reason += "\n\nAddress these before completing. (If already handled, explain why.)"
        output = {"decision": "block", "reason": reason}
        print(json.dumps(output))

    sys.exit(0)

if __name__ == '__main__':
    main()
