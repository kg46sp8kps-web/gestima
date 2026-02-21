"""GESTIMA - Drawings router

Multiple drawings per part support via FileRecord + FileLink architecture.
RESTful API for managing part drawings (PDF/STEP files).

Endpoints:
- GET    /api/parts/{part_number}/drawings       - List all drawings
- POST   /api/parts/{part_number}/drawings       - Upload new drawing
- PUT    /api/parts/{part_number}/drawings/{id}/primary - Set as primary
- DELETE /api/parts/{part_number}/drawings/{id}  - Soft delete drawing
- GET    /api/parts/{part_number}/drawings/{id}  - Download drawing file

Security:
- PDF/STEP validation via magic bytes
- File size limits (10MB PDF, 100MB STEP)
- Path traversal prevention
- Transaction handling (L-008)

Architecture:
- FileRecord: Physical file on disk
- FileLink: Part-file relationship with business metadata (is_primary, revision)
- FileService: Centralized file operations (ADR-044)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.file_record import FileRecord, FileLink
from app.models.part import Part
from app.models.user import User, UserRole
from app.dependencies import get_current_user, require_role
from app.schemas.drawing import DrawingListResponse, DrawingResponse
from app.services.file_service import FileService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/parts/{part_number}/drawings", response_model=DrawingListResponse)
async def list_part_drawings(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí seznam všech výkresů pro díl.

    Načte FileLinks pro part (entity_type='part', link_type='drawing')
    + JOIN FileRecord pro metadata.

    Seřazeno: primární první, pak podle data vytvoření (nejnovější první).

    Returns:
        DrawingListResponse: Seznam výkresů + ID primárního výkresu

    Raises:
        HTTPException 404: Díl nebyl nalezen
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get FileLinks for part (join FileRecord for file metadata)
    result = await db.execute(
        select(FileLink, FileRecord)
        .join(FileRecord, FileLink.file_id == FileRecord.id)
        .where(
            and_(
                FileLink.entity_type == "part",
                FileLink.entity_id == part.id,
                FileLink.link_type == "drawing",
                FileLink.deleted_at.is_(None),
                FileRecord.deleted_at.is_(None)
            )
        )
        .order_by(FileLink.is_primary.desc(), FileLink.created_at.desc())
    )
    links_and_files = result.all()

    # Build response
    primary_id = None
    response_drawings = []

    file_service = FileService()

    for link, file_record in links_and_files:
        if link.is_primary:
            primary_id = file_record.id

        # Check if file physically exists on disk
        file_path = file_service.UPLOADS_DIR / file_record.file_path
        file_exists = file_path.exists()

        if not file_exists:
            logger.warning(
                f"Orphan file record: id={file_record.id}, "
                f"file_path={file_record.file_path} (part={part_number})"
            )

        # Build DrawingResponse from FileRecord + FileLink
        resp = DrawingResponse(
            id=file_record.id,
            part_id=part.id,
            drawing_number=link.drawing_number,
            filename=file_record.original_filename,
            original_filename=file_record.original_filename,
            file_path=file_record.file_path,
            file_type=file_record.file_type,
            file_size=file_record.file_size,
            revision=link.revision,
            is_primary=link.is_primary,
            created_at=link.created_at,
            file_exists=file_exists
        )
        response_drawings.append(resp)

    logger.debug(
        f"Listed {len(response_drawings)} drawings for part {part_number} "
        f"(primary_id={primary_id})"
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

    Uses FileService to store file + create FileLink.
    Auto-nastaví is_primary=True pokud je to první výkres dílu.

    Security:
    - PDF/STEP validation via FileService (magic bytes)
    - File size limits (10MB PDF, 100MB STEP)
    - Path traversal prevention

    Args:
        part_number: Číslo dílu (8 znaků)
        file: PDF nebo STEP soubor
        revision: Revize výkresu (A-Z, default A)

    Returns:
        DrawingResponse: Vytvořený záznam výkresu

    Raises:
        HTTPException 404: Díl nenalezen
        HTTPException 400: Neplatný soubor nebo revize
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

    # Transaction handling (L-008)
    try:
        file_service = FileService()

        # 1. Store file via FileService
        file_record = await file_service.store(
            file=file,
            directory=f"parts/{part_number}",
            db=db,
            allowed_types=["pdf", "step", "stp"],
            created_by=current_user.username
        )

        # 2. Check if this is first drawing (auto-primary)
        result = await db.execute(
            select(FileLink)
            .where(
                and_(
                    FileLink.entity_type == "part",
                    FileLink.entity_id == part.id,
                    FileLink.link_type == "drawing",
                    FileLink.deleted_at.is_(None)
                )
            )
        )
        existing_links = result.scalars().all()
        is_first = len(existing_links) == 0

        # 3. Create FileLink
        file_link = await file_service.link(
            file_id=file_record.id,
            entity_type="part",
            entity_id=part.id,
            db=db,
            is_primary=is_first,
            revision=revision,
            link_type="drawing",
            created_by=current_user.username
        )

        # 4. Update Part.file_id if primary PDF
        if is_first and file_record.file_type == "pdf":
            part.file_id = file_record.id
            part.updated_by = current_user.username

        await db.commit()
        await db.refresh(file_record)
        await db.refresh(file_link)

        logger.info(
            f"Uploaded drawing: part={part_number}, file='{file.filename}', "
            f"size={file_record.file_size}, type={file_record.file_type}, "
            f"primary={is_first}, revision={revision}, user={current_user.username}"
        )

        # Build response
        return DrawingResponse(
            id=file_record.id,
            part_id=part.id,
            drawing_number=part.drawing_number,
            filename=file_record.original_filename,
            original_filename=file_record.original_filename,
            file_path=file_record.file_path,
            file_type=file_record.file_type,
            file_size=file_record.file_size,
            revision=file_link.revision,
            is_primary=file_link.is_primary,
            created_at=file_link.created_at,
            file_exists=True
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
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

    drawing_id = FileRecord.id
    Updates FileLink.is_primary=True for this file,
    sets is_primary=False for all other drawings.

    Transaction handling (L-008):
    - Unset is_primary pro všechny ostatní FileLinks
    - Set is_primary=True pro tento FileLink
    - Update Part.file_id pokud je to PDF
    - Commit

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu (FileRecord.id)

    Returns:
        DrawingResponse: Aktualizovaný výkres

    Raises:
        HTTPException 404: Díl nebo výkres nenalezen
        HTTPException 400: Výkres nepatří k dílu
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get FileRecord
    file_service = FileService()
    file_record = await file_service.get_async(drawing_id, db)

    # Get FileLink for this file + part
    result = await db.execute(
        select(FileLink)
        .where(
            and_(
                FileLink.file_id == drawing_id,
                FileLink.entity_type == "part",
                FileLink.entity_id == part.id,
                FileLink.link_type == "drawing",
                FileLink.deleted_at.is_(None)
            )
        )
    )
    file_link = result.scalar_one_or_none()

    if not file_link:
        raise HTTPException(
            status_code=400,
            detail=f"Výkres {drawing_id} nepatří k dílu {part_number}"
        )

    # Transaction handling (L-008)
    try:
        # 1. Unset is_primary for all other links
        result = await db.execute(
            select(FileLink)
            .where(
                and_(
                    FileLink.entity_type == "part",
                    FileLink.entity_id == part.id,
                    FileLink.link_type == "drawing",
                    FileLink.id != file_link.id,
                    FileLink.deleted_at.is_(None)
                )
            )
        )
        other_links = result.scalars().all()
        for link in other_links:
            link.is_primary = False
            link.updated_at = datetime.utcnow()
            link.updated_by = current_user.username

        # 2. Set is_primary=True for this link
        file_link.is_primary = True
        file_link.updated_at = datetime.utcnow()
        file_link.updated_by = current_user.username

        # 3. Update Part.file_id if PDF
        if file_record.file_type == "pdf":
            part.file_id = file_record.id
            part.updated_by = current_user.username

        await db.commit()
        await db.refresh(file_link)
        await db.refresh(file_record)

        logger.info(
            f"Set primary drawing: part={part_number}, drawing_id={drawing_id}, "
            f"user={current_user.username}"
        )

        # Build response
        return DrawingResponse(
            id=file_record.id,
            part_id=part.id,
            drawing_number=file_link.drawing_number,
            filename=file_record.original_filename,
            original_filename=file_record.original_filename,
            file_path=file_record.file_path,
            file_type=file_record.file_type,
            file_size=file_record.file_size,
            revision=file_link.revision,
            is_primary=file_link.is_primary,
            created_at=file_link.created_at,
            file_exists=True
        )

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

    drawing_id = FileRecord.id
    Soft deletes FileLink (deleted_at = now).
    Pokud byl výkres primární, automaticky povýší první zbývající PDF drawing.

    Transaction handling (L-008):
    - Soft delete FileLink
    - If was primary, auto-promote next PDF drawing
    - Update Part.file_id
    - Commit

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu (FileRecord.id)

    Raises:
        HTTPException 404: Díl nebo výkres nenalezen
        HTTPException 400: Výkres již smazán
    """
    # Find part
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Get FileLink for this file + part
    result = await db.execute(
        select(FileLink, FileRecord)
        .join(FileRecord, FileLink.file_id == FileRecord.id)
        .where(
            and_(
                FileLink.file_id == drawing_id,
                FileLink.entity_type == "part",
                FileLink.entity_id == part.id,
                FileLink.link_type == "drawing",
                FileLink.deleted_at.is_(None)
            )
        )
    )
    link_and_file = result.one_or_none()

    if not link_and_file:
        raise HTTPException(
            status_code=404,
            detail=f"Výkres {drawing_id} nenalezen nebo již smazán"
        )

    file_link, file_record = link_and_file

    # Transaction handling (L-008)
    try:
        was_primary = file_link.is_primary
        was_pdf = file_record.file_type == "pdf"

        # Soft delete FileLink
        file_link.deleted_at = datetime.utcnow()
        file_link.deleted_by = current_user.username
        file_link.updated_at = datetime.utcnow()

        # If was primary, auto-promote next PDF drawing
        if was_primary:
            # Find next PDF drawing
            result = await db.execute(
                select(FileLink, FileRecord)
                .join(FileRecord, FileLink.file_id == FileRecord.id)
                .where(
                    and_(
                        FileLink.entity_type == "part",
                        FileLink.entity_id == part.id,
                        FileLink.link_type == "drawing",
                        FileLink.id != file_link.id,
                        FileLink.deleted_at.is_(None),
                        FileRecord.file_type == "pdf",
                        FileRecord.deleted_at.is_(None)
                    )
                )
                .order_by(FileLink.created_at.desc())
                .limit(1)
            )
            next_link_and_file = result.one_or_none()

            if next_link_and_file:
                next_link, next_file = next_link_and_file
                next_link.is_primary = True
                next_link.updated_at = datetime.utcnow()
                next_link.updated_by = current_user.username

                # Update Part.file_id
                part.file_id = next_file.id
                part.updated_by = current_user.username

                logger.info(
                    f"Auto-promoted drawing {next_file.id} to primary after delete "
                    f"(part={part_number})"
                )
            else:
                # No more PDF drawings
                part.file_id = None
                part.updated_by = current_user.username
                logger.info(
                    f"No more PDF drawings for part {part_number}, cleared part.file_id"
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


@router.get("/api/parts/{part_number}/drawings/{drawing_id}")
async def get_drawing_file(
    part_number: str,
    drawing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stáhne soubor výkresu (PDF nebo STEP).

    drawing_id = FileRecord.id
    Uses FileService.serve_file() for proper file serving.

    Args:
        part_number: Číslo dílu
        drawing_id: ID výkresu (FileRecord.id)

    Returns:
        FileResponse: File s proper Content-Type

    Raises:
        HTTPException 404: Díl, výkres nebo soubor nenalezen
    """
    # Find part (verify ownership)
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nebyl nalezen")

    # Verify FileLink exists for this part
    result = await db.execute(
        select(FileLink)
        .where(
            and_(
                FileLink.file_id == drawing_id,
                FileLink.entity_type == "part",
                FileLink.entity_id == part.id,
                FileLink.link_type == "drawing",
                FileLink.deleted_at.is_(None)
            )
        )
    )
    file_link = result.scalar_one_or_none()

    if not file_link:
        raise HTTPException(
            status_code=404,
            detail=f"Výkres {drawing_id} nepatří k dílu {part_number}"
        )

    # Serve file via FileService
    file_service = FileService()
    return await file_service.serve_file(drawing_id, db)


# ============================================================================
# LEGACY PHASE A ENDPOINTS (backwards compatibility)
# ============================================================================

@router.get("/api/parts/{part_number}/drawing")
async def get_primary_drawing_legacy(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    LEGACY endpoint: Vrátí primární výkres dílu.

    Uses Part.file_id FK to FileRecord.
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

    # Check if part has primary drawing
    if not part.file_id:
        raise HTTPException(
            status_code=404,
            detail=f"Drawing not found for part: {part_number}"
        )

    # Serve file via FileService
    file_service = FileService()
    return await file_service.serve_file(part.file_id, db)
