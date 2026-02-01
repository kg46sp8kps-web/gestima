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

    # Find primary ID
    primary_id = None
    for drawing in drawings:
        if drawing.is_primary:
            primary_id = drawing.id
            break

    logger.debug(
        f"Listed {len(drawings)} drawings for part {part_number} "
        f"(primary_id={primary_id})"
    )

    return DrawingListResponse(
        drawings=[DrawingResponse.model_validate(d) for d in drawings],
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

    # SECURITY: Validate PDF
    try:
        await drawing_service.validate_pdf(file)
        file_size = await drawing_service.validate_file_size(file)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF validation failed for {part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Chyba při validaci PDF souboru")

    # Generate filename: {part_number}_{timestamp}_{revision}.pdf
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_part_number = drawing_service.sanitize_part_number(part_number)
    new_filename = f"{safe_part_number}_{timestamp}_{revision}.pdf"
    file_path_abs = drawing_service.DRAWINGS_DIR / new_filename
    file_path_rel = f"drawings/{new_filename}"

    # Transaction handling (L-008)
    try:
        # Save file to disk
        with file_path_abs.open("wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)

        # Calculate hash
        file_hash = await drawing_service.calculate_file_hash(file_path_abs)

        # Check if this is first drawing (auto-primary)
        result = await db.execute(
            select(Drawing)
            .where(
                Drawing.part_id == part.id,
                Drawing.deleted_at.is_(None)
            )
        )
        existing_drawings = result.scalars().all()
        is_first_drawing = len(existing_drawings) == 0

        # Create drawing record
        drawing = await drawing_service.save_drawing_record(
            part_id=part.id,
            file_path=file_path_rel,
            filename=file.filename or new_filename,
            file_size=file_size,
            file_hash=file_hash,
            is_primary=is_first_drawing,  # Auto-primary if first
            revision=revision,
            created_by=current_user.username,
            db=db
        )

        await db.commit()
        await db.refresh(drawing)

        logger.info(
            f"Uploaded drawing: part={part_number}, file='{file.filename}', "
            f"size={file_size}, hash={file_hash[:8]}..., primary={is_first_drawing}, "
            f"revision={revision}, user={current_user.username}"
        )

        return DrawingResponse.model_validate(drawing)

    except HTTPException:
        # Rollback file on DB error
        if file_path_abs.exists():
            file_path_abs.unlink()
        await db.rollback()
        raise
    except Exception as e:
        # Rollback file on any error
        if file_path_abs.exists():
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

        # If was primary, auto-promote next oldest
        if was_primary:
            promoted = await drawing_service.auto_promote_primary(part.id, db)
            if promoted:
                promoted.updated_by = current_user.username
                logger.info(
                    f"Auto-promoted drawing {promoted.id} to primary after delete "
                    f"(part={part_number})"
                )

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

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=drawing.filename
    )
