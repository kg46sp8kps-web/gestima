"""GESTIMA - Drawings router

Multiple drawings per part support.
RESTful API for managing part drawings (PDF files).

Endpoints:
- GET    /api/parts/{part_number}/drawings       - List all drawings
- POST   /api/parts/{part_number}/drawings       - Upload new drawing
- PUT    /api/parts/{part_number}/drawings/{id}/primary - Set as primary
- DELETE /api/parts/{part_number}/drawings/{id}  - Soft delete drawing
- GET    /api/parts/{part_number}/drawings/{id}  - Download drawing file

Security:
- PDF validation via magic bytes
- File size limits (10MB)
- Path traversal prevention
- Transaction handling (L-008)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.drawing import Drawing
from app.models.part import Part
from app.models.user import User, UserRole
from app.dependencies import get_current_user, require_role
from app.schemas.drawing import DrawingListResponse, DrawingResponse
from app.services.drawing_service import DrawingService

logger = logging.getLogger(__name__)
router = APIRouter()

# Drawing service (security-focused file operations)
drawing_service = DrawingService()


@router.get("/api/parts/{part_number}/drawings", response_model=DrawingListResponse)
async def list_part_drawings(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí seznam všech výkresů pro díl.
    Seřazeno: primární první, pak podle data vytvoření (nejnovější první).

    Returns:
        DrawingListResponse: Seznam výkresů + ID primárního výkresu
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get non-deleted drawings
    result = await db.execute(
        select(Drawing)
        .where(
            Drawing.part_id == part.id,
            Drawing.deleted_at.is_(None)
        )
        .order_by(Drawing.is_primary.desc(), Drawing.created_at.desc())
    )
    drawings = result.scalars().all()

    # Build response with file_exists check + auto-cleanup orphans
    primary_id = None
    response_drawings = []
    orphan_count = 0

    for drawing in drawings:
        if drawing.is_primary:
            primary_id = drawing.id

        # Check if file physically exists on disk
        file_exists = Path(drawing.file_path).exists() if drawing.file_path else False

        if not file_exists:
            orphan_count += 1
            logger.warning(
                f"Orphan drawing record: id={drawing.id}, "
                f"file_path={drawing.file_path} (part={part_number})"
            )

        resp = DrawingResponse.model_validate(drawing)
        resp.file_exists = file_exists
        response_drawings.append(resp)

    # Auto-cleanup: if primary drawing is orphan, promote next valid one
    if primary_id and orphan_count > 0:
        primary_orphan = any(
            d.id == primary_id and not d.file_exists for d in response_drawings
        )
        if primary_orphan:
            # Find first non-orphan drawing of same file_type to promote
            orphan_drawing = next(d for d in response_drawings if d.id == primary_id)
            for d in response_drawings:
                if d.id != primary_id and d.file_exists and d.file_type == orphan_drawing.file_type:
                    # Promote in DB
                    try:
                        new_primary = await drawing_service.set_primary_drawing(d.id, db)
                        if orphan_drawing.file_type == "pdf":
                            part.drawing_path = new_primary.file_path
                        await db.commit()
                        primary_id = d.id
                        d.is_primary = True
                        orphan_drawing.is_primary = False
                        logger.info(
                            f"Auto-promoted drawing {d.id} (orphan primary {orphan_drawing.id} "
                            f"had missing file, part={part_number})"
                        )
                    except Exception as e:
                        logger.error(f"Failed to auto-promote drawing: {e}")
                    break

    logger.debug(
        f"Listed {len(drawings)} drawings for part {part_number} "
        f"(primary_id={primary_id}, orphans={orphan_count})"
    )

    return DrawingListResponse(
        drawings=response_drawings,
        primary_id=primary_id
    )


@router.post("/api/parts/{part_number}/drawings", response_model=DrawingResponse, status_code=201)
async def upload_drawing(
    part_number: str,
    file: UploadFile = File(...),
    revision: str = Form(default="A"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Nahraje nový výkres pro díl.
    Auto-nastaví is_primary=True pokud je to první výkres dílu.

    Security:
    - PDF validation (magic bytes)
    - File size limit (10MB)
    - Path traversal prevention
    - Deduplication via SHA-256 hash

    Args:
        part_number: Číslo dílu (8 znaků)
        file: PDF soubor
        revision: Revize výkresu (A-Z, default A)

    Returns:
        DrawingResponse: Vytvořený záznam výkresu

    Raises:
        HTTPException 404: Díl nenalezen
        HTTPException 400: Neplatný PDF soubor
        HTTPException 409: Duplicitní soubor (stejný hash)
        HTTPException 413: Soubor příliš velký
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Validate revision format
    if not revision or len(revision) > 2 or not revision.isalpha() or not revision.isupper():
        raise HTTPException(
            status_code=400,
            detail="Neplatná revize. Použijte formát A-Z (1-2 znaky)."
        )

    # SECURITY: Auto-detect and validate file type (PDF or STEP)
    try:
        file_type = drawing_service.detect_file_type(file.filename or "unknown")
        if file_type == "pdf":
            await drawing_service.validate_pdf(file)
            file_size = await drawing_service.validate_file_size(file)
        elif file_type == "step":
            await drawing_service.validate_step(file)
            file_size = await drawing_service.validate_file_size(file, max_size=drawing_service.MAX_STEP_FILE_SIZE)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File validation failed for {part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Chyba při validaci souboru")

    # Generate filename: {part_number}_{timestamp}_{revision}.{ext}
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_part_number = drawing_service.sanitize_part_number(part_number)
    ext = Path(file.filename).suffix.lower() if file.filename else '.pdf'
    new_filename = f"{safe_part_number}_{timestamp}_{revision}{ext}"
    file_path_abs = drawing_service.DRAWINGS_DIR / new_filename
    file_path_rel = f"drawings/{new_filename}"

    # Transaction handling (L-008)
    committed = False
    try:
        # Save file to disk
        with file_path_abs.open("wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)

        # Calculate hash
        file_hash = await drawing_service.calculate_file_hash(file_path_abs)

        # Check if this is first drawing of this file_type (auto-primary per type)
        result = await db.execute(
            select(Drawing)
            .where(
                Drawing.part_id == part.id,
                Drawing.file_type == file_type,
                Drawing.deleted_at.is_(None)
            )
        )
        existing_of_type = result.scalars().all()
        is_first_of_type = len(existing_of_type) == 0

        # Create drawing record
        drawing = await drawing_service.save_drawing_record(
            part_id=part.id,
            file_path=file_path_rel,
            filename=file.filename or new_filename,
            file_size=file_size,
            file_hash=file_hash,
            is_primary=is_first_of_type,  # Auto-primary if first of this type
            revision=revision,
            created_by=current_user.username,
            db=db,
            file_type=file_type
        )

        await db.commit()
        committed = True
        await db.refresh(drawing)

        # Sync Part.drawing_path with primary PDF drawing only (Phase A compatibility)
        if is_first_of_type and file_type == "pdf":
            part.drawing_path = file_path_rel
            part.updated_by = current_user.username
            await db.commit()

        logger.info(
            f"Uploaded drawing: part={part_number}, file='{file.filename}', "
            f"size={file_size}, hash={file_hash[:8]}..., primary={is_first_of_type}, "
            f"revision={revision}, user={current_user.username}"
        )

        return DrawingResponse.model_validate(drawing)

    except HTTPException:
        # Rollback file only if DB was NOT committed (prevents orphaned DB records)
        if not committed and file_path_abs.exists():
            file_path_abs.unlink()
        await db.rollback()
        raise
    except Exception as e:
        # Rollback file only if DB was NOT committed (prevents orphaned DB records)
        if not committed and file_path_abs.exists():
            file_path_abs.unlink()
        await db.rollback()
        logger.error(f"Failed to upload drawing for {part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při nahrávání výkresu")
    finally:
        await file.close()


@router.put("/api/parts/{part_number}/drawings/{drawing_id}/primary", response_model=DrawingResponse)
async def set_primary_drawing(
    part_number: str,
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Nastaví výkres jako primární.
    Automaticky odebere is_primary flag z ostatních výkresů dílu.

    Transaction handling (L-008):
    - Unset is_primary pro všechny výkresy dílu
    - Set is_primary=True pro tento výkres
    - Commit

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu

    Returns:
        DrawingResponse: Aktualizovaný výkres

    Raises:
        HTTPException 404: Díl nebo výkres nenalezen
        HTTPException 400: Výkres je smazaný
    """
    # Find part (verify ownership)
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get drawing
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="Výkres nebyl nalezen")

    # Verify drawing belongs to this part
    if drawing.part_id != part.id:
        raise HTTPException(
            status_code=400,
            detail=f"Výkres {drawing_id} nepatří k dílu {part_number}"
        )

    # Transaction handling (L-008)
    try:
        drawing = await drawing_service.set_primary_drawing(drawing_id, db)
        drawing.updated_by = current_user.username

        # Sync Part.drawing_path only for PDF primary (Phase A compatibility)
        if drawing.file_type == "pdf":
            part.drawing_path = drawing.file_path
            part.updated_by = current_user.username

        await db.commit()
        await db.refresh(drawing)

        logger.info(
            f"Set primary drawing: part={part_number}, drawing_id={drawing_id}, "
            f"user={current_user.username}"
        )

        return DrawingResponse.model_validate(drawing)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to set primary drawing {drawing_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při nastavování primárního výkresu")


@router.delete("/api/parts/{part_number}/drawings/{drawing_id}", status_code=204)
async def delete_drawing(
    part_number: str,
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Soft delete výkresu.
    Pokud byl výkres primární, automaticky povýší nejstarší zbývající výkres.

    Transaction handling (L-008):
    - Soft delete (set deleted_at, deleted_by)
    - If was primary, auto-promote next oldest
    - Commit

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu

    Raises:
        HTTPException 404: Díl nebo výkres nenalezen
        HTTPException 400: Výkres již smazán
    """
    # Find part (verify ownership)
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get drawing
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="Výkres nebyl nalezen")

    # Verify drawing belongs to this part
    if drawing.part_id != part.id:
        raise HTTPException(
            status_code=400,
            detail=f"Výkres {drawing_id} nepatří k dílu {part_number}"
        )

    # Already deleted?
    if drawing.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Výkres je již smazaný")

    # Transaction handling (L-008)
    try:
        was_primary = drawing.is_primary

        # Soft delete
        drawing.deleted_at = datetime.utcnow()
        drawing.deleted_by = current_user.username
        drawing.version += 1

        # If was primary, auto-promote next oldest of same file_type
        deleted_file_type = drawing.file_type or "pdf"
        if was_primary:
            promoted = await drawing_service.auto_promote_primary(part.id, db, file_type=deleted_file_type)
            if promoted:
                promoted.updated_by = current_user.username
                # Sync Part.drawing_path only for PDF primary (Phase A compatibility)
                if deleted_file_type == "pdf":
                    part.drawing_path = promoted.file_path
                    part.updated_by = current_user.username
                logger.info(
                    f"Auto-promoted drawing {promoted.id} to primary after delete "
                    f"(part={part_number}, type={deleted_file_type})"
                )
            else:
                # No more drawings of this type
                if deleted_file_type == "pdf":
                    part.drawing_path = None
                    part.updated_by = current_user.username

        await db.commit()

        logger.info(
            f"Deleted drawing: part={part_number}, drawing_id={drawing_id}, "
            f"was_primary={was_primary}, user={current_user.username}"
        )

        return None  # 204 No Content

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete drawing {drawing_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při mazání výkresu")


@router.get("/api/parts/{part_number}/drawings/{drawing_id}", response_class=FileResponse)
async def get_drawing_file(
    part_number: str,
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stáhne PDF soubor výkresu.
    Returns FileResponse s proper Content-Type a filename.

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu

    Returns:
        FileResponse: PDF soubor

    Raises:
        HTTPException 404: Díl, výkres nebo soubor nenalezen
        HTTPException 400: Výkres je smazaný
    """
    # Find part (verify ownership)
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get drawing
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="Výkres nebyl nalezen")

    # Verify drawing belongs to this part
    if drawing.part_id != part.id:
        raise HTTPException(
            status_code=400,
            detail=f"Výkres {drawing_id} nepatří k dílu {part_number}"
        )

    # Check if deleted
    if drawing.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Výkres je smazaný")

    # Check file exists
    file_path = Path(drawing.file_path)
    if not file_path.exists():
        logger.error(f"Drawing file not found on disk: {drawing.file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Soubor výkresu nebyl nalezen na disku"
        )

    logger.debug(f"Serving drawing file: {drawing.filename} (part={part_number})")

    # Determine media type based on file_type
    media_type = "application/pdf" if drawing.file_type == "pdf" else "application/step"

    # RFC 5987: Encode filename for Unicode support in Content-Disposition header
    # Use ASCII fallback + UTF-8 encoded version for Czech characters (háčky, čárky)
    encoded_filename = quote(drawing.filename, safe='')
    ascii_fallback = drawing.filename.encode('ascii', 'ignore').decode('ascii') or f'drawing{Path(drawing.filename).suffix}'

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=drawing.filename,
        headers={
            "Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}"
        }
    )


# ============================================================================
# LEGACY PHASE A ENDPOINTS (backwards compatibility)
# ============================================================================

@router.get("/api/parts/{part_number}/drawing", response_class=FileResponse)
async def get_primary_drawing_legacy(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    LEGACY Phase A endpoint: Vrátí primární výkres dílu.
    Pro backwards compatibility s Phase A kódem.

    Args:
        part_number: Číslo dílu

    Returns:
        FileResponse: PDF soubor primárního výkresu

    Raises:
        HTTPException 404: Díl nenalezen nebo nemá primární výkres
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Find primary drawing
    primary_drawing = await drawing_service.get_primary_drawing(part.id, db)
    if not primary_drawing:
        raise HTTPException(
            status_code=404,
            detail=f"Drawing not found for part: {part_number}"
        )

    # Check if deleted
    if primary_drawing.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Výkres byl smazán")

    # Get file path
    file_path = Path(primary_drawing.file_path)
    if not file_path.exists():
        logger.error(
            f"Drawing file not found on disk: {primary_drawing.file_path} "
            f"(part={part_number}, drawing_id={primary_drawing.id})"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Soubor výkresu nebyl nalezen na disku"
        )

    logger.debug(f"Serving primary drawing: {primary_drawing.filename} (part={part_number})")

    # Determine media type based on file_type
    media_type = "application/pdf" if primary_drawing.file_type == "pdf" else "application/step"

    # RFC 5987: Encode filename for Unicode support
    encoded_filename = quote(primary_drawing.filename, safe='')
    ascii_fallback = primary_drawing.filename.encode('ascii', 'ignore').decode('ascii') or f'drawing{Path(primary_drawing.filename).suffix}'

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=primary_drawing.filename,
        headers={
            "Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}"
        }
    )
