"""Service layer for SGI restoration protocols."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocol import RestorationProtocol
from app.schemas.protocol import Protocol, ProtocolCreate, ProtocolUpdate


async def create_protocol(db: AsyncSession, payload: ProtocolCreate) -> Protocol:
    """Create a new protocol record."""
    db_protocol = RestorationProtocol(
        name=payload.name, description=payload.description, version=payload.version
    )
    db.add(db_protocol)
    await db.commit()
    await db.refresh(db_protocol)
    return Protocol.model_validate(db_protocol)


async def get_protocol(db: AsyncSession, protocol_id: uuid.UUID) -> Protocol | None:
    """Retrieve a protocol by its primary key."""
    result = await db.execute(
        select(RestorationProtocol).where(RestorationProtocol.id == protocol_id)
    )
    db_protocol = result.scalar_one_or_none()
    if db_protocol:
        return Protocol.model_validate(db_protocol)
    return None


async def update_protocol(
    db: AsyncSession, protocol_id: uuid.UUID, payload: ProtocolUpdate
) -> Protocol | None:
    """Update an existing protocol."""
    result = await db.execute(
        select(RestorationProtocol).where(RestorationProtocol.id == protocol_id)
    )
    db_protocol = result.scalar_one_or_none()

    if db_protocol:
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_protocol, key, value)

        await db.commit()
        await db.refresh(db_protocol)
        return Protocol.model_validate(db_protocol)

    return None


async def delete_protocol(db: AsyncSession, protocol_id: uuid.UUID) -> None:
    """Delete a protocol record."""
    result = await db.execute(
        select(RestorationProtocol).where(RestorationProtocol.id == protocol_id)
    )
    db_protocol = result.scalar_one_or_none()
    if db_protocol:
        await db.delete(db_protocol)
        await db.commit()
