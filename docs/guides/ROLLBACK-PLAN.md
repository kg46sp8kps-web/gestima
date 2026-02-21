# Rollback Plan — Gestima Production Deployment

**Version:** 1.0
**Last Updated:** 2026-02-20
**Target Release:** v2.0.1
**Current Stable:** v2.0.0

---

## Overview

This document describes the rollback procedure for Gestima production deployments. Follow these steps if a deployment fails or introduces critical issues.

**Stack:**
- Backend: FastAPI + SQLAlchemy + SQLite (WAL mode)
- Frontend: Vue 3 (built static assets)
- Database: Single `gestima.db` file
- Migrations: Alembic (47 linear migrations as of v2.0.0)

---

## Pre-Deployment Checklist

**CRITICAL: Execute BEFORE deploying new version.**

```bash
# 1. Backup database
cp gestima.db gestima.db.bak.$(date +%Y%m%d_%H%M%S)

# 2. Note current state
git tag                           # Note current tag (e.g., v2.0.0)
git rev-parse HEAD                # Note current commit hash
alembic current                   # Note current migration revision

# 3. Export current alembic version (for reference)
alembic current > alembic_version_pre_deploy.txt

# 4. Test rollback procedure (optional, recommended for major releases)
# Run through steps 1-6 in "Rollback Procedure" below on staging
```

**Store these values:**
- Previous tag: `v2.0.0`
- Previous commit: `<hash>`
- Previous alembic revision: `<revision>`
- Backup file: `gestima.db.bak.YYYYMMDD_HHMMSS`

---

## Rollback Procedure

### Step 1: Stop Application

```bash
# If running as systemd service
sudo systemctl stop gestima

# If running manually (find process, then kill)
ps aux | grep "python gestima.py run"
kill <PID>

# Verify stopped
curl http://localhost:8000/health
# Should fail with connection error
```

### Step 2: Restore Database

```bash
# List available backups
ls -lh gestima.db.bak.*

# Restore from backup (choose appropriate backup file)
cp gestima.db.bak.YYYYMMDD_HHMMSS gestima.db

# Verify restoration
sqlite3 gestima.db "SELECT COUNT(*) FROM parts;"
# Should return expected count
```

**CRITICAL:** If database schema changed between versions, you MUST also rollback migrations (see Step 4).

### Step 3: Rollback Code

```bash
# Checkout previous stable tag
git checkout v2.0.0

# Alternatively, checkout specific commit
git checkout <commit-hash>

# Verify code version
git describe --tags
git log -1 --oneline
```

### Step 4: Rollback Migrations (if schema changed)

```bash
# Check current migration
alembic current

# Rollback single migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <target-revision>

# Example: rollback to v2.0.0 baseline
alembic downgrade aa001_add_drawing_number_drop_drawings

# Verify migration state
alembic current
```

**WARNING:** Some migrations may have stub `downgrade()` functions. Test rollback on staging first.

**Common migration issues:**
- **Data loss:** Downgrade may drop columns → data lost permanently
- **Stub downgrade:** Migration has `pass` in downgrade() → manual SQL required
- **FK constraints:** May fail if child records exist

### Step 5: Rebuild Frontend

```bash
# Install dependencies (if package.json changed)
cd frontend
npm ci

# Build static assets for previous version
npm run build

# Verify build
ls -lh dist/
# Should contain index.html, assets/, etc.

cd ..
```

### Step 6: Restart Application

```bash
# If using systemd
sudo systemctl start gestima
sudo systemctl status gestima

# If running manually
python gestima.py run &

# Check logs
tail -f logs/gestima.log
```

### Step 7: Verify Rollback

```bash
# 1. Health endpoint
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# 2. Database connection
curl http://localhost:8000/api/parts/items?limit=1
# Expected: {"items": [...], "total": <count>}

# 3. Frontend
curl http://localhost:8000/
# Expected: HTML with correct version in <title> or meta tags

# 4. Check logs for errors
tail -n 100 logs/gestima.log | grep ERROR
# Expected: No critical errors

# 5. Smoke test critical workflows
# - Login
# - List parts
# - Create quote
# - View FileManager
```

---

## Alembic Rollback Reference

### Single Migration Rollback

```bash
alembic downgrade -1
```

### Multi-Step Rollback

```bash
# Rollback 3 migrations
alembic downgrade -3

# Rollback to specific revision
alembic downgrade aa001
```

### View Migration History

```bash
# Show all migrations
alembic history

# Show current state
alembic current

# Show pending migrations
alembic history --verbose
```

### Stub Downgrade Handling

If migration has stub downgrade:

```python
def downgrade() -> None:
    # TODO: Implement rollback
    pass
```

**Manual rollback required:**

1. Identify changes in `upgrade()`
2. Write reverse SQL manually
3. Execute via `sqlite3 gestima.db < rollback.sql`

**Example:**

```sql
-- Reverse of "ALTER TABLE parts ADD COLUMN file_id"
ALTER TABLE parts DROP COLUMN file_id;
```

---

## Monitoring After Rollback

### Health Checks (first 30 minutes)

```bash
# Every 5 minutes
watch -n 300 'curl -s http://localhost:8000/health'

# Monitor logs
tail -f logs/gestima.log

# Monitor database locks (SQLite WAL mode)
sqlite3 gestima.db "PRAGMA wal_checkpoint(FULL);"
```

### Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `no such column` | Migration rollback incomplete | Run additional `alembic downgrade` |
| `database is locked` | WAL checkpoint stuck | `PRAGMA wal_checkpoint(RESTART)` |
| `404 on /api/*` | Frontend build mismatch | Re-run `npm run build` |
| `500 on parts/items` | Data integrity issue | Restore older backup |

### Critical Workflows to Test

1. **Authentication:** Login with test user
2. **Parts List:** Load `/windows?module=parts-list` → verify data
3. **Quote Creation:** Create new quote → verify DB write
4. **File Upload:** Upload PDF → verify FileManager
5. **Infor Import:** Test material import (if applicable)

---

## Point of No Return

### When Rollback is Safe

- **Within 1 hour of deployment** (no user activity)
- **Database backup exists** (pre-deployment)
- **No production data created** (no new parts/quotes/files)

### When Rollback is Risky

- **Users have created data** (new parts, quotes, production records)
- **File uploads** (new PDFs in `uploads/` not in backup)
- **Migration added columns with data** (rollback drops data permanently)

### Partial Rollback Strategies

**Scenario 1: Backend broken, frontend OK**

```bash
# Keep frontend build, rollback backend only
git checkout v2.0.0 -- app/ alembic/
python gestima.py run
```

**Scenario 2: Schema change with user data**

```bash
# Export user data created after deployment
sqlite3 gestima.db ".dump parts" > new_parts.sql

# Rollback
cp gestima.db.bak gestima.db
alembic downgrade <revision>

# Re-import user data (manual merge required)
# Edit new_parts.sql to match old schema
sqlite3 gestima.db < new_parts.sql
```

**Scenario 3: File uploads after deployment**

```bash
# Files stored in uploads/ are NOT in database backup
# Compare file_records table before/after
sqlite3 gestima.db "SELECT id, filename, created_at FROM file_records WHERE created_at > '<deployment_time>';"

# Copy new files to safe location
rsync -av uploads/ uploads_backup/

# After rollback, manually re-link files if needed
```

---

## Emergency Contacts

| Issue | Contact | Action |
|-------|---------|--------|
| Database corruption | DBA / DevOps | Restore from offsite backup |
| Critical security issue | Security team | Immediate shutdown + rollback |
| Data loss | Product owner | Assess impact, decide rollback vs forward fix |

---

## Rollback Decision Tree

```
Deployment failed?
├─ Yes → Health endpoint fails
│  ├─ Backend crash → Check logs → Rollback code (Step 3)
│  ├─ DB schema mismatch → Rollback migrations (Step 4)
│  └─ Frontend 404 → Rebuild frontend (Step 5)
│
├─ Partial → Some features broken
│  ├─ Critical feature (quotes, parts) → ROLLBACK
│  ├─ Non-critical (admin panel) → Forward fix or rollback
│  └─ Performance issue → Monitor, decide in 1 hour
│
└─ No, but bugs reported
   ├─ Data integrity issue → ROLLBACK IMMEDIATELY
   ├─ UI bug (cosmetic) → Forward fix
   └─ Performance degradation → Monitor, rollback if >30% slower
```

**Rule of thumb:** If in doubt, ROLLBACK. Forward fixes can wait.

---

## Post-Rollback Actions

1. **Root cause analysis:** Why did deployment fail?
2. **Update deployment checklist:** Add missing validation step
3. **Test rollback on staging:** Verify procedure works
4. **Document incident:** `docs/incidents/YYYY-MM-DD-rollback.md`
5. **Plan forward fix:** Schedule re-deployment with fix

---

## Testing Rollback Procedure (Staging)

**RECOMMENDED before major releases (e.g., v2.0.0 → v3.0.0).**

```bash
# 1. Deploy to staging
git checkout v2.0.1
alembic upgrade head
npm run build
python gestima.py run

# 2. Create test data
curl -X POST http://localhost:8000/api/parts/items -d '{...}'

# 3. Execute rollback procedure (Steps 1-6)
# ...

# 4. Verify test data handling
# - Is test data lost? (expected if schema changed)
# - Are old records intact? (expected)
# - Does app start? (expected)

# 5. Document results
echo "Rollback test: PASS/FAIL" > rollback_test_results.txt
```

---

## Automation (Future Enhancement)

**Candidate for scripting:**

```bash
#!/bin/bash
# rollback.sh — Automated rollback to previous tag

set -e

BACKUP_FILE="gestima.db.bak.$(date +%Y%m%d_%H%M%S)"
PREV_TAG="${1:-v2.0.0}"

echo "Stopping application..."
systemctl stop gestima

echo "Backing up current state..."
cp gestima.db "$BACKUP_FILE"

echo "Rolling back to $PREV_TAG..."
git checkout "$PREV_TAG"

echo "Rebuilding frontend..."
cd frontend && npm ci && npm run build && cd ..

echo "Starting application..."
systemctl start gestima

echo "Rollback complete. Verify: curl http://localhost:8000/health"
```

**Usage:**

```bash
./rollback.sh v2.0.0
```

---

**Version:** 1.0 (2026-02-20)
**Owner:** DevOps / Backend Architect
**Review:** Quarterly or after major release
