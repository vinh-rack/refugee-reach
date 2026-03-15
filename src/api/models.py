from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    latitude: Optional[float] = Field(None, description="Client device latitude")
    longitude: Optional[float] = Field(None, description="Client device longitude")


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict
    result: Optional[str] = None  # Changed from dict to str since we're passing text results


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_used: Optional[str] = None
    location: Optional[Tuple[float, float]] = None
    error: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    resources: Optional[List['AidResourceResponse']] = None
    sos_alert: Optional[dict] = None
    news_events: Optional[List['NewsEventResponse']] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    agents_configured: bool



class RouteStepResponse(BaseModel):
    instruction: str
    distance_m: float
    duration_s: float
    latitude: float
    longitude: float


class RouteResponse(BaseModel):
    total_distance_km: float
    total_duration_min: float
    steps: List[RouteStepResponse]
    polyline: List[Tuple[float, float]]


class AidResourceResponse(BaseModel):
    name: str
    type: str
    latitude: float
    longitude: float
    distance_km: float
    address: Optional[str] = None
    contact: Optional[str] = None
    hours: Optional[str] = None
    source: str


class SOSRequest(BaseModel):
    latitude: float = Field(..., description="Device latitude")
    longitude: float = Field(..., description="Device longitude")


class SOSResponse(BaseModel):
    success: bool
    alert_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class RouteToResourceRequest(BaseModel):
    user_latitude: float
    user_longitude: float
    resource_latitude: float
    resource_longitude: float


class RouteToResourceResponse(BaseModel):
    success: bool
    route: Optional[RouteResponse] = None
    resource: Optional[AidResourceResponse] = None
    error: Optional[str] = None


class NewsArticleResponse(BaseModel):
    id: str
    title: Optional[str] = None
    url: str
    source_name: Optional[str] = None
    published_at: Optional[str] = None
    summary_hint: Optional[str] = None


class NewsEventResponse(BaseModel):
    id: str
    canonical_title: str
    topic: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None
    severity_score: Optional[float] = None
    confidence_score: Optional[float] = None
    summary: Optional[str] = None
    article_count: int
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    articles: List[NewsArticleResponse] = []


class NewsResponse(BaseModel):
    success: bool
    count: int = 0
    events: List[NewsEventResponse] = []
    error: Optional[str] = None
