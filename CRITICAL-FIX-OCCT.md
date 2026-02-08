# 🚨 CRITICAL FIX NEEDED - OCCT Installation

## Problem

**Backend běží s `venv/` Python který NEMÁ pythonocc-core!**

**Důsledek:** Všechny STEP soubory se parsují REGEX parserem místo OCCT → accuracy 30% místo 90%+

## Root Cause

```
Backend process: /Users/lofas/Documents/__App_Claude/Gestima/venv/bin/python
OCCT installed in: /Users/lofas/miniforge3/bin/python

→ Backend nevidí OCCT!
```

## Solution (Pick ONE)

### Option A: Install OCCT in venv (RECOMMENDED - 5 min)

```bash
cd /Users/lofas/Documents/__App_Claude/Gestima

# 1. Stop backend
pkill -f "gestima.py run"

# 2. Create conda environment from venv requirements
conda create -n gestima-prod python=3.9 --yes
conda activate gestima-prod

# 3. Install requirements
pip install -r requirements.txt

# 4. Install OCCT
conda install -c conda-forge pythonocc-core --yes

# 5. Verify
python -c "from OCC.Core.STEPControl import STEPControl_Reader; print('OCCT OK')"

# 6. Update gestima.py to use conda env:
# Edit shebang or use: conda run -n gestima-prod python gestima.py run

# 7. Restart backend
python gestima.py run
```

### Option B: Symlink miniforge as system Python (QUICK but hacky - 1 min)

```bash
# Use miniforge Python globally
export PATH="/Users/lofas/miniforge3/bin:$PATH"

# Install all venv requirements into miniforge
pip install -r requirements.txt

# Start backend with miniforge Python
python gestima.py run
```

### Option C: Use Docker (BEST for production - 30 min)

```bash
# Create Dockerfile with OCCT included
# Deploy as container
```

## Verification

After fix, run:

```bash
python batch_reprocess_step_files.py

# Expected output:
# Source: step_deterministic (or step_occt)
# part_type: rotational (for 29+ files)
```

## Current Status

- ❌ Backend uses venv Python (NO OCCT)
- ✅ OCCT installed in miniforge
- ❌ 37 files processed with REGEX (not OCCT)
- ❌ 8 files FAILED (insufficient data)
- ❌ 26 files have WRONG diameter (Ø8745mm bug)

## After Fix Expected

- ✅ Backend uses Python WITH OCCT
- ✅ All 37 files reprocessed with OCCT
- ✅ 0 files should fail (OCCT handles complex geometry)
- ✅ Correct diameter values
- ✅ Accuracy 90%+

## Time Estimate

- Option A: 5 minutes
- Option B: 1 minute (but dependencies may break)
- Option C: 30 minutes (cleanest solution)

**User: Pick which option and I'll implement it!**
