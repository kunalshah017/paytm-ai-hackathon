"""Shared dependencies for API routes (e.g., DB sessions, auth)."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db

DBSession = Annotated[AsyncSession, Depends(get_db)]
