"""GESTIMA - Files router (ADR-044: Centralized File Manager)

"Dumb" file storage API - ONLY physical file operations.
NO business logic (primary drawing, TimeVision matching, etc.).

Endpoints:
- POST   /api/files/upload                                   - Upload souboru (FormData)
- GET    /api/files/{file_id}                                - Metadata souboru (s links)
- GET    /api/files/{file_id}/preview                        - Náhled PDF (inline, bez auth — pro iframe/pdf.js)
- GET    /api/files/{file_id}/download                       - Stáhni/zobraz soubor (FileResponse, s auth)
- DELETE /api/files/{file_id}                                - Soft delete

- POST   /api/files/{file_id}/link                           - Propoj s entitou (JSON)
- DELETE /api/files/{file_id}/link/{entity_type}/{entity_id} - Odpoj
- PUT    /api/files/{file_id}/primary/{entity_type}/{entity_id} - Nastav jako primary

- GET    /api/files                                           - List (query filters)
- GET    /api/files/orphans                                   - Osiřelé soubory (admin)

Security:
- Magic bytes validation (security-critical)
- File size limits
- Path traversal prevention
- Transaction handling (L-008)

Business logic STAYS in respective routers/services.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.file_record import FileRecord, FileLink
from app.models.user import User
from app.dependencies import get_current_user
from app.schemas.file_record import (
    FileRecordResponse,
    FileLinkResponse,
    FileWithLinksResponse,
    FileListResponse,
    FileLinkRequest,
    FileUploadResponse
)
from app.services.file_service import file_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Form(default="loose", description="Podadresář (parts/10900635, loose, temp)"),
    entity_type: Optional[str] = Form(None, description="Volitelně: entity_type pro okamžité propojení"),
    entity_id: Optional[int] = Form(None, description="Volitelně: entity_id pro okamžité propojení"),
    is_primary: bool = Form(default=False, description="Nastav jako primary (pokud se linkuje)"),
    revision: Optional[str] = Form(None, description="Revize (A, B, C...)"),
    link_type: str = Form(default="drawing", description="Typ vazby (drawing, step_model, nc_program)"),
    allowed_types: Optional[str] = Form(None, description="Povolené typy oddělené čárkou (pdf,step)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Nahraje soubor na disk a vytvoří DB záznam.
    Volitelně hned propojí s entitou (pokud entity_type + entity_id).

    Steps:
    1. FileService.store() - fyzické uložení + DB záznam
    2. Pokud entity_type + entity_id → FileService.link()
    3. Commit

    Args:
        file: Soubor (FormData)
        directory: Podadresář (např. "parts/10900635", "loose", "temp")
        entity_type: Volitelně - entity type pro okamžité propojení
        entity_id: Volitelně - entity ID pro okamžité propojení
        is_primary: Nastav jako primary (pokud se linkuje)
        revision: Revize (A, B, C...)
        link_type: Typ vazby (drawing, step_model, nc_program)
        allowed_types: Comma-separated povolené typy (např. "pdf,step")

    Returns:
        FileUploadResponse: FileRecord + optional link

    Raises:
        HTTPException 400: Invalid file type
        HTTPException 413: File too large
        HTTPException 500: Storage failed
    """
    # Parse allowed_types
    allowed_types_list = None
    if allowed_types:
        allowed_types_list = [t.strip().lower() for t in allowed_types.split(',') if t.strip()]

    # Transaction handling (L-008)
    try:
        # 1. Store file to disk + create DB record
        record = await file_service.store(
            file=file,
            directory=directory,
            db=db,
            allowed_types=allowed_types_list,
            created_by=current_user.username
        )

        # 2. Optional: Link to entity
        link = None
        if entity_type and entity_id:
            link = await file_service.link(
                file_id=record.id,
                entity_type=entity_type,
                entity_id=entity_id,
                db=db,
                is_primary=is_primary,
                revision=revision,
                link_type=link_type,
                created_by=current_user.username
            )

        # 3. Commit
        await db.commit()
        await db.refresh(record)

        logger.info(
            f"Uploaded file: id={record.id}, path='{record.file_path}', "
            f"type={record.file_type}, size={record.file_size}, "
            f"linked={link is not None}, user={current_user.username}"
        )

        # Build response
        response = FileUploadResponse.model_validate(record)
        if link:
            response.link = FileLinkResponse.model_validate(link)

        return response

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při nahrávání souboru")


@router.get("/{file_id}", response_model=FileWithLinksResponse)
async def get_file_metadata(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí metadata souboru včetně všech vazeb na entity.

    Args:
        file_id: ID souboru

    Returns:
        FileWithLinksResponse: Metadata + seznam vazeb

    Raises:
        HTTPException 404: Soubor nenalezen nebo smazán
    """
    try:
        # Get file with links (eager loading)
        result = await db.execute(
            select(FileRecord)
            .options(selectinload(FileRecord.links))
            .where(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.deleted_at.is_(None)
                )
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail=f"Soubor nenalezen: ID {file_id}")

        # Filter out soft-deleted links
        active_links = [link for link in record.links if link.deleted_at is None]

        # Build response
        response = FileWithLinksResponse.model_validate(record)
        response.links = [FileLinkResponse.model_validate(link) for link in active_links]

        logger.debug(
            f"Retrieved file metadata: id={file_id}, links={len(active_links)}, "
            f"user={current_user.username}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání souboru")


@router.get("/{file_id}/preview", response_class=FileResponse)
async def preview_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Náhled souboru (inline Content-Disposition, bez auth).

    Iframe a pdf.js nemohou poslat Authorization header,
    proto tento endpoint NEMÁ auth dependency.
    Omezeno na PDF soubory — ostatní typy vrací 400.

    Args:
        file_id: ID souboru

    Returns:
        FileResponse: PDF s Content-Disposition: inline

    Raises:
        HTTPException 400: Soubor není PDF
        HTTPException 404: Soubor nenalezen (DB nebo disk)
    """
    try:
        # Validate file exists and is PDF
        result = await db.execute(
            select(FileRecord).where(
                FileRecord.id == file_id,
                FileRecord.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=f"Soubor nenalezen: ID {file_id}")
        if record.file_type != "pdf":
            raise HTTPException(status_code=400, detail="Preview je dostupný pouze pro PDF soubory")

        # Serve file inline (no download)
        return await file_service.serve_file(file_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání náhledu")


@router.get("/{file_id}/download", response_class=FileResponse)
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stáhne/zobrazí soubor (FileResponse s Content-Disposition).

    Args:
        file_id: ID souboru

    Returns:
        FileResponse: Soubor s proper MIME type a filename

    Raises:
        HTTPException 404: Soubor nenalezen (DB nebo disk)
    """
    try:
        # Serve file (validates existence on disk)
        return await file_service.serve_file(file_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání souboru")


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete souboru (set deleted_at).
    Fyzický soubor na disku ZŮSTÁVÁ (bezpečnost).

    Transaction handling (L-008):
    - Soft delete FileRecord (deleted_at, deleted_by)
    - FileLinks remain (cascade in query filters)
    - Commit

    Args:
        file_id: ID souboru

    Raises:
        HTTPException 404: Soubor nenalezen
    """
    try:
        await file_service.delete(file_id, db, deleted_by=current_user.username)
        await db.commit()

        logger.info(f"Deleted file: id={file_id}, user={current_user.username}")

        return None  # 204 No Content

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při mazání souboru")


@router.post("/{file_id}/link", response_model=FileLinkResponse, status_code=201)
async def link_file_to_entity(
    file_id: int,
    data: FileLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Propojí soubor s entitou (UPSERT: update if exists, insert if not).
    Pokud is_primary=True, automaticky unset ostatní primary vazby.

    Transaction handling (L-008):
    - FileService.link() (UPSERT)
    - Commit

    Args:
        file_id: ID souboru
        data: FileLinkRequest (entity_type, entity_id, is_primary, revision, link_type)

    Returns:
        FileLinkResponse: Vytvořená nebo aktualizovaná vazba

    Raises:
        HTTPException 404: Soubor nenalezen
        HTTPException 500: Database error
    """
    try:
        link = await file_service.link(
            file_id=file_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            db=db,
            is_primary=data.is_primary,
            revision=data.revision,
            link_type=data.link_type,
            created_by=current_user.username
        )

        await db.commit()
        await db.refresh(link)

        logger.info(
            f"Linked file to entity: file_id={file_id}, "
            f"entity={data.entity_type}:{data.entity_id}, "
            f"primary={data.is_primary}, user={current_user.username}"
        )

        return FileLinkResponse.model_validate(link)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to link file {file_id} to {data.entity_type}:{data.entity_id}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Chyba při propojování souboru")


@router.delete("/{file_id}/link/{entity_type}/{entity_id}", status_code=204)
async def unlink_file_from_entity(
    file_id: int,
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Odpojí soubor od entity (soft delete FileLink).

    Transaction handling (L-008):
    - FileService.unlink()
    - Commit

    Args:
        file_id: ID souboru
        entity_type: Typ entity (part, quote_item, timevision)
        entity_id: ID entity

    Raises:
        HTTPException 404: Link nenalezen
    """
    try:
        await file_service.unlink(file_id, entity_type, entity_id, db)
        await db.commit()

        logger.info(
            f"Unlinked file from entity: file_id={file_id}, "
            f"entity={entity_type}:{entity_id}, user={current_user.username}"
        )

        return None  # 204 No Content

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to unlink file {file_id} from {entity_type}:{entity_id}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Chyba při odpojování souboru")


@router.put("/{file_id}/primary/{entity_type}/{entity_id}", response_model=FileLinkResponse)
async def set_file_as_primary(
    file_id: int,
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Nastaví soubor jako primární pro entitu.
    Automaticky unset is_primary u ostatních vazeb stejného link_type.

    Transaction handling (L-008):
    - FileService.set_primary()
    - Commit

    Args:
        file_id: ID souboru
        entity_type: Typ entity (part, quote_item, timevision)
        entity_id: ID entity

    Returns:
        FileLinkResponse: Aktualizovaná vazba

    Raises:
        HTTPException 404: Link nenalezen
    """
    try:
        await file_service.set_primary(file_id, entity_type, entity_id, db)
        await db.commit()

        # Re-fetch link to get updated is_primary
        result = await db.execute(
            select(FileLink).where(
                and_(
                    FileLink.file_id == file_id,
                    FileLink.entity_type == entity_type,
                    FileLink.entity_id == entity_id,
                    FileLink.deleted_at.is_(None)
                )
            )
        )
        link = result.scalar_one()

        logger.info(
            f"Set file as primary: file_id={file_id}, "
            f"entity={entity_type}:{entity_id}, user={current_user.username}"
        )

        return FileLinkResponse.model_validate(link)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to set file {file_id} as primary for {entity_type}:{entity_id}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Chyba při nastavování primárního souboru")


@router.get("", response_model=FileListResponse)
async def list_files(
    entity_type: Optional[str] = Query(None, description="Filtr: entity_type (part, quote_item, timevision)"),
    entity_id: Optional[int] = Query(None, description="Filtr: entity_id"),
    file_type: Optional[str] = Query(None, description="Filtr: file_type (pdf, step, nc)"),
    status: Optional[str] = Query(None, description="Filtr: status (temp, active, archived)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí seznam souborů s volitelnými filtry.

    Query parametry:
    - entity_type + entity_id: Soubory pro konkrétní entitu
    - file_type: Typ souboru (pdf, step, nc, xlsx)
    - status: Status souboru (temp, active, archived)

    Returns:
        FileListResponse: Seznam souborů + total count
    """
    try:
        # Build query
        query = (
            select(FileRecord)
            .options(selectinload(FileRecord.links))
            .where(FileRecord.deleted_at.is_(None))
        )

        # Apply filters
        if file_type:
            query = query.where(FileRecord.file_type == file_type)
        if status:
            query = query.where(FileRecord.status == status)

        # Entity filter requires JOIN
        if entity_type and entity_id:
            query = (
                query
                .join(FileLink, FileRecord.id == FileLink.file_id)
                .where(
                    and_(
                        FileLink.entity_type == entity_type,
                        FileLink.entity_id == entity_id,
                        FileLink.deleted_at.is_(None)
                    )
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get files
        result = await db.execute(query.order_by(FileRecord.created_at.desc()))
        records = result.scalars().all()

        # Build response
        files = []
        for record in records:
            # Filter out soft-deleted links
            active_links = [link for link in record.links if link.deleted_at is None]

            file_resp = FileWithLinksResponse.model_validate(record)
            file_resp.links = [FileLinkResponse.model_validate(link) for link in active_links]
            files.append(file_resp)

        logger.debug(
            f"Listed {len(files)} files (total={total}, "
            f"entity={entity_type}:{entity_id if entity_id else 'all'}, "
            f"file_type={file_type or 'all'}, status={status or 'all'}, "
            f"user={current_user.username})"
        )

        return FileListResponse(files=files, total=total)

    except Exception as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání seznamu souborů")


@router.get("/orphans", response_model=FileListResponse)
async def list_orphaned_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí seznam osiřelých souborů (bez aktivní vazby, kromě temp).
    Admin endpoint pro cleanup.

    Returns:
        FileListResponse: Seznam osiřelých souborů
    """
    try:
        orphans = await file_service.find_orphans(db)

        # Build response
        files = [
            FileWithLinksResponse.model_validate(record)
            for record in orphans
        ]

        logger.info(
            f"Found {len(orphans)} orphaned files, user={current_user.username}"
        )

        return FileListResponse(files=files, total=len(orphans))

    except Exception as e:
        logger.error(f"Failed to list orphans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání osiřelých souborů")
