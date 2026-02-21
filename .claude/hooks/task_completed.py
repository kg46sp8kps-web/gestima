#!/usr/bin/env python3
"""
Hook: TaskCompleted — Quality gate when a task is marked complete.
Prevents premature task completion if basic quality criteria aren't met.

Exit 0 = allow task completion
Exit 2 + stderr message = prevent completion, send feedback
"""
import sys
import json
import os
import subprocess


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    task_name = data.get("task_name", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    issues = []

    # Check for syntax errors in changed Python files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir
        )
        changed_py = [
            f for f in result.stdout.strip().split('\n')
            if f.endswith('.py') and f.startswith('app/') and f
        ]
        for f in changed_py:
            filepath = os.path.join(project_dir, f)
            if os.path.exists(filepath):
                check = subprocess.run(
                    ["python3", "-m", "py_compile", filepath],
                    capture_output=True, text=True, timeout=5
                )
                if check.returncode != 0:
                    issues.append(f"Syntax error v {f}: {check.stderr.strip()[:200]}")
    except Exception:
        pass

    # Check for TypeScript/Vue build errors in changed frontend files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=project_dir
        )
        changed_fe = [
            f for f in result.stdout.strip().split('\n')
            if f.startswith('frontend/') and f.endswith(('.vue', '.ts', '.tsx')) and f
        ]
        if changed_fe:
            # Quick type check
            check = subprocess.run(
                ["npx", "vue-tsc", "--noEmit"],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.join(project_dir, "frontend")
            )
            if check.returncode != 0:
                error_lines = check.stdout.strip().split('\n')[:5]
                issues.append(f"TypeScript errors:\n" + "\n".join(error_lines))
    except Exception:
        pass

    if issues:
        feedback = "TASK COMPLETION BLOCKED — Problémy:\n" + "\n".join(f"- {i}" for i in issues)
        print(feedback, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
