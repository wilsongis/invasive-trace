"""Service layer for SGI restoration protocols.

This is a minimal implementation that provides the expected async CRUD
functions.  The actual persistence logic would use SQLAlchemy models and
Alembic migrations, but for the purpose of getting the codebase to pass
type‑checking and linting we provide simple stubs that raise a clear
exception.  Implementations can be added later without changing the API.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.protocol import ProtocolCreate, ProtocolUpdate, Protocol


async def create_protocol(db: AsyncSession, payload: ProtocolCreate) -> Protocol:
    """Create a new protocol record.

    A real implementation would add a SQLAlchemy model instance to the
    session and commit.  Here we raise ``NotImplementedError`` to make the
    missing behaviour explicit.
    """
    raise NotImplementedError("Protocol creation not implemented yet")


async def get_protocol(db: AsyncSession, protocol_id: int) -> Optional[Protocol]:
    """Retrieve a protocol by its primary key.

    Returns ``None`` if the protocol does not exist.
    """
    raise NotImplementedError("Protocol retrieval not implemented yet")


async def update_protocol(db: AsyncSession, protocol_id: int, payload: ProtocolUpdate) -> Optional[Protocol]:
    """Update an existing protocol.

    Returns the updated ``Protocol`` or ``None`` if not found.
    """
    raise NotImplementedError("Protocol update not implemented yet")


async def delete_protocol(db: AsyncSession, protocol_id: int) -> None:
    """Delete a protocol record.

    Raises ``NotImplementedError`` until a concrete implementation is added.
    """
    raise NotImplementedError("Protocol deletion not implemented yet")
