"""Pydantic schemas for SGI restoration protocols."""

import uuid

from pydantic import BaseModel, Field


class ProtocolBase(BaseModel):
    """Common fields for a restoration protocol."""

    name: str = Field(..., description="Human‑readable name of the protocol")
    description: str | None = Field(None, description="Detailed description of the protocol steps")
    version: str = Field(..., description="Semantic version of the protocol, e.g. '1.0.0'")


class ProtocolCreate(ProtocolBase):
    """Fields required when creating a new protocol."""

    pass


class ProtocolUpdate(BaseModel):
    """Fields that can be updated on an existing protocol."""

    name: str | None = None
    description: str | None = None
    version: str | None = None


class Protocol(ProtocolBase):
    """Schema returned from the API, includes the database identifier."""

    id: uuid.UUID = Field(..., description="Primary key of the protocol record")

    class Config:
        from_attributes = True
