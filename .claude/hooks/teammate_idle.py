#!/usr/bin/env python3
"""
Hook: TeammateIdle — Quality gate when a teammate finishes work.
Runs when a teammate is about to go idle. Checks that the teammate
completed their work properly before allowing idle state.

Exit 0 + no output = allow idle
Exit 2 + stderr message = send feedback, keep teammate working
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

    agent_name = data.get("agent_name", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    changed_files = get_changed_files(project_dir)

    issues = []

    # Backend teammate checks
    if agent_name == "backend":
        changed_py = [f for f in changed_files if f.endswith('.py') and f.startswith('app/')]
        changed_services = [f for f in changed_py if '/services/' in f]
        changed_routers = [f for f in changed_py if '/routers/' in f]
        changed_tests = [f for f in changed_files if f.startswith('tests/')]

        if (changed_services or changed_routers) and not changed_tests:
            issues.append("Backend: napsal jsi services/routers ale žádné testy. Napiš testy.")

    # Frontend teammate checks
    elif agent_name == "frontend":
        changed_vue = [f for f in changed_files if f.endswith('.vue')]
        for f in changed_vue:
            try:
                filepath = os.path.join(project_dir, f)
                with open(filepath, 'r') as fh:
                    loc = sum(1 for _ in fh)
                if loc > 300:
                    issues.append(f"Frontend: {f} má {loc} LOC (limit 300). Rozděl komponentu.")
            except Exception:
                pass

    # QA teammate checks
    elif agent_name == "qa":
        # QA should have run tests — check if output was provided
        # This is a lightweight check; the real verification is in the task output
        pass

    # Auditor checks — auditor should always produce a verdict
    elif agent_name == "auditor":
        pass

    if issues:
        feedback = "TEAMMATE IDLE CHECK — Problémy:\n" + "\n".join(f"- {i}" for i in issues)
        print(feedback, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
