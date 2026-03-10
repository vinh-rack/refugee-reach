from typing import Optional, Tuple

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_used: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    agents_configured: bool
