"""GESTIMA - HTML Pages router (Vue SPA Redirects)

ARCHIVED: 2026-01-31
All Jinja2/Alpine.js templates moved to: archive/legacy-alpinejs-v1.6.1/

This router now redirects legacy URLs to Vue SPA equivalents.
Vue SPA is served from: frontend/dist/ via FastAPI static files.
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


# ============================================================================
# LEGACY URL REDIRECTS → VUE SPA
# ============================================================================
# These redirects ensure old bookmarks/links continue to work.
# Vue SPA handles all routing via Vue Router.

@router.get("/login")
async def login_redirect():
    """Redirect to Vue SPA login"""
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/parts")
async def parts_list_redirect():
    """Redirect to Vue SPA parts list"""
    return RedirectResponse(url="/parts", status_code=302)


@router.get("/parts/new")
async def parts_new_redirect():
    """Redirect to Vue SPA create part"""
    return RedirectResponse(url="/parts/new", status_code=302)


@router.get("/parts/{part_number}/edit")
async def parts_edit_redirect(part_number: str):
    """Redirect to Vue SPA part detail"""
    return RedirectResponse(url=f"/parts/{part_number}", status_code=302)


@router.get("/parts/{part_number}/pricing")
async def parts_pricing_redirect(part_number: str):
    """Redirect to Vue SPA part detail (pricing tab)"""
    return RedirectResponse(url=f"/parts/{part_number}?tab=pricing", status_code=302)


@router.get("/workspace")
async def workspace_redirect():
    """Redirect to Vue SPA windows view"""
    return RedirectResponse(url="/windows", status_code=302)


@router.get("/pricing/batch-sets")
async def batch_sets_redirect():
    """Redirect to Vue SPA batch sets"""
    return RedirectResponse(url="/pricing/batch-sets", status_code=302)


@router.get("/pricing/batch-sets/{set_id}")
async def batch_set_detail_redirect(set_id: int):
    """Redirect to Vue SPA batch set detail"""
    return RedirectResponse(url=f"/pricing/batch-sets/{set_id}", status_code=302)


@router.get("/settings")
async def settings_redirect():
    """Redirect to Vue SPA settings"""
    return RedirectResponse(url="/settings", status_code=302)


# ============================================================================
# REMOVED ROUTES (Alpine.js era)
# ============================================================================
# The following routes were removed as they served Jinja2 templates:
#
# GET /              → Vue SPA serves index.html at root
# GET /login         → Redirected above
# GET /parts         → Redirected above
# GET /parts/new     → Redirected above
# GET /parts/{id}/edit    → Redirected above
# GET /parts/{id}/pricing → Redirected above
# GET /workspace     → Redirected above
# GET /pricing/*     → Redirected above
# GET /settings      → Redirected above
# GET /machines/*    → Removed (ADR-021: WorkCenters)
#
# All templates archived in: archive/legacy-alpinejs-v1.6.1/templates/
# ============================================================================
