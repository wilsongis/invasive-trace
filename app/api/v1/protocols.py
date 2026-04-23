"""API routes for managing restoration protocols (SGI Standardized pillar)."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas.protocol import Protocol, ProtocolCreate, ProtocolUpdate
from app.services import protocol_service

router = APIRouter(prefix="/protocols", tags=["Protocols"])


@router.post("/", response_model=Protocol)
async def create_protocol(protocol: ProtocolCreate, db: AsyncSession = Depends(get_db)):
    return await protocol_service.create_protocol(db, protocol)


@router.get("/{protocol_id}", response_model=Protocol)
async def get_protocol(protocol_id: int, db: AsyncSession = Depends(get_db)):
    result = await protocol_service.get_protocol(db, protocol_id)
    if not result:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return result


@router.put("/{protocol_id}", response_model=Protocol)
async def update_protocol(protocol_id: int, payload: ProtocolUpdate, db: AsyncSession = Depends(get_db)):
    result = await protocol_service.update_protocol(db, protocol_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return result


@router.delete("/{protocol_id}", response_model=dict)
async def delete_protocol(protocol_id: int, db: AsyncSession = Depends(get_db)):
    await protocol_service.delete_protocol(db, protocol_id)
    return {"detail": "deleted"}
