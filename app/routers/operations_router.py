"""GESTIMA - Operations API router"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.operation import Operation, OperationCreate, OperationUpdate, OperationResponse

router = APIRouter()


@router.get("/part/{part_id}", response_model=List[OperationResponse])
async def get_operations(part_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Operation).where(Operation.part_id == part_id).order_by(Operation.seq)
    )
    return result.scalars().all()


@router.get("/{operation_id}", response_model=OperationResponse)
async def get_operation(operation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")
    return operation


@router.post("/", response_model=OperationResponse)
async def create_operation(data: OperationCreate, db: AsyncSession = Depends(get_db)):
    operation = Operation(**data.model_dump())
    db.add(operation)
    await db.commit()
    await db.refresh(operation)
    return operation


@router.put("/{operation_id}", response_model=OperationResponse)
async def update_operation(operation_id: int, data: OperationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(operation, key, value)
    
    await db.commit()
    await db.refresh(operation)
    return operation


@router.delete("/{operation_id}")
async def delete_operation(operation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")
    
    await db.delete(operation)
    await db.commit()
    return {"message": "Operace smazána"}


@router.post("/{operation_id}/change-mode", response_model=OperationResponse)
async def change_mode(operation_id: int, cutting_mode: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")
    
    if cutting_mode not in ["low", "mid", "high"]:
        raise HTTPException(status_code=400, detail="Neplatný režim")
    
    operation.cutting_mode = cutting_mode
    await db.commit()
    await db.refresh(operation)
    return operation
