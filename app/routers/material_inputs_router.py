"""GESTIMA - Material Inputs Router

ADR-024: MaterialInput refactor (v1.8.0)

Endpoints:
- CRUD operations for MaterialInput
- Link/unlink MaterialInput ↔ Operation (M:N relationship)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.material_input import (
    MaterialInput,
    MaterialInputCreate,
    MaterialInputUpdate,
    MaterialInputResponse,
    MaterialInputWithOperationsResponse,
    MaterialOperationLinkRequest,
    material_operation_link,
)
from app.models.operation import Operation
from app.models.part import Part
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/api/material-inputs", tags=["material-inputs"])


# ═══════════════════════════════════════════════════════════════
# CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════

@router.get("/parts/{part_id}", response_model=List[MaterialInputWithOperationsResponse])
async def list_material_inputs(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Seznam materiálových vstupů pro díl (seřazeno podle seq)"""

    result = await db.execute(
        select(MaterialInput)
        .options(selectinload(MaterialInput.operations))
        .where(
            and_(
                MaterialInput.part_id == part_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .order_by(MaterialInput.seq)
    )

    return result.scalars().all()


@router.get("/{material_id}", response_model=MaterialInputWithOperationsResponse)
async def get_material_input(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Detail materiálového vstupu"""

    result = await db.execute(
        select(MaterialInput)
        .options(selectinload(MaterialInput.operations))
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )

    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    return material


@router.post("", response_model=MaterialInputResponse, status_code=status.HTTP_201_CREATED)
async def create_material_input(
    data: MaterialInputCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Vytvoření nového materiálového vstupu"""

    # Verify part exists
    part_result = await db.execute(
        select(Part).where(
            and_(
                Part.id == data.part_id,
                Part.deleted_at.is_(None)
            )
        )
    )
    if not part_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Part {data.part_id} not found"
        )

    # Create MaterialInput
    material = MaterialInput(
        **data.model_dump(),
        created_by=current_user.username,
        updated_by=current_user.username
    )

    db.add(material)
    await db.commit()
    await db.refresh(material)

    return material


@router.put("/{material_id}", response_model=MaterialInputResponse)
async def update_material_input(
    material_id: int,
    data: MaterialInputUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Aktualizace materiálového vstupu (optimistic locking)"""

    # Get current material
    result = await db.execute(
        select(MaterialInput).where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    # Optimistic locking check
    if material.version != data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data změněna jiným uživatelem. Načtěte znovu."
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={"version"})
    update_data["updated_by"] = current_user.username
    update_data["version"] = material.version + 1

    result = await db.execute(
        update(MaterialInput)
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.version == data.version
            )
        )
        .values(**update_data)
        .returning(MaterialInput)
    )

    updated_material = result.scalar_one_or_none()
    if not updated_material:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Optimistic lock failed"
        )

    await db.commit()
    await db.refresh(updated_material)

    return updated_material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_input(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Smazání materiálového vstupu (soft delete)"""

    from datetime import datetime as dt

    result = await db.execute(
        update(MaterialInput)
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .values(
            deleted_at=dt.utcnow(),
            deleted_by=current_user.username
        )
        .returning(MaterialInput.id)
    )

    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    await db.commit()


# ═══════════════════════════════════════════════════════════════
# M:N LINKING (MaterialInput ↔ Operation)
# ═══════════════════════════════════════════════════════════════

@router.post("/{material_id}/link-operation/{operation_id}", status_code=status.HTTP_201_CREATED)
async def link_material_to_operation(
    material_id: int,
    operation_id: int,
    request: Optional[MaterialOperationLinkRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Přiřadit materiál k operaci (M:N vztah)"""

    # Verify MaterialInput exists
    mat_result = await db.execute(
        select(MaterialInput).where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )
    if not mat_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    # Verify Operation exists
    op_result = await db.execute(
        select(Operation).where(
            and_(
                Operation.id == operation_id,
                Operation.deleted_at.is_(None)
            )
        )
    )
    if not op_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found"
        )

    # Check if link already exists
    existing = await db.execute(
        select(material_operation_link).where(
            and_(
                material_operation_link.c.material_input_id == material_id,
                material_operation_link.c.operation_id == operation_id
            )
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link already exists"
        )

    # Create link
    consumed_quantity = request.consumed_quantity if request else None
    await db.execute(
        material_operation_link.insert().values(
            material_input_id=material_id,
            operation_id=operation_id,
            consumed_quantity=consumed_quantity
        )
    )

    await db.commit()

    return {"message": "Link created successfully"}


@router.delete("/{material_id}/unlink-operation/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_material_from_operation(
    material_id: int,
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Odebrat vazbu materiál → operace"""

    result = await db.execute(
        delete(material_operation_link).where(
            and_(
                material_operation_link.c.material_input_id == material_id,
                material_operation_link.c.operation_id == operation_id
            )
        )
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )

    await db.commit()


@router.get("/operations/{operation_id}/materials", response_model=List[MaterialInputResponse])
async def get_operation_materials(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Materiály spotřebované v operaci"""

    result = await db.execute(
        select(MaterialInput)
        .join(
            material_operation_link,
            MaterialInput.id == material_operation_link.c.material_input_id
        )
        .where(
            and_(
                material_operation_link.c.operation_id == operation_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .order_by(MaterialInput.seq)
    )

    return result.scalars().all()
