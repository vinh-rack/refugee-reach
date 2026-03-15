import asyncio
import base64 as b64
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.agents.orchestrator import process_user_input_strands
from src.agents.voice_agent import NovaVoiceBridge
from src.api.models import (AidResourceResponse, ChatRequest, ChatResponse,
                            HealthResponse, RouteResponse, RouteStepResponse,
                            RouteToResourceRequest, RouteToResourceResponse)
from src.features.aid_locator import find_aid_resources, get_route_to_resource
from src.features.location_service import get_device_location

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting RefugeeReach API...")
    print(f"Nova API Key: {'Configured' if os.getenv('NOVA_API_KEY') else 'Not configured'}")
    yield
    print("Shutting down RefugeeReach API...")


app = FastAPI(
    title="RefugeeReach API",
    description="AI-powered crisis response and aid location system for refugees",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        agents_configured=bool(os.getenv("NOVA_API_KEY"))
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process user message through the orchestrator agent
    """
    try:
        location = get_device_location()

        result = process_user_input_strands(
            user_input=request.message,
            location=location
        )

        return ChatResponse(
            success=result.get("success", True),
            response=result.get("response", ""),
            agent_used=result.get("agent_used"),
            location=result.get("location"),
            resources=[
                AidResourceResponse(**r) for r in result["resources"]
            ] if result.get("resources") else None,
            sos_alert=result.get("sos_alert"),
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/location")
async def get_location():
    """Get device location from IP"""
    location = get_device_location()

    if location:
        return {
            "success": True,
            "latitude": location[0],
            "longitude": location[1]
        }

    return {
        "success": False,
        "message": "Could not determine location"
    }


@app.get("/aid/nearby")
async def get_nearby_aid(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    max_results: int = 20
):
    """Find nearby aid resources"""
    try:
        resources = find_aid_resources(latitude, longitude, radius_km, max_results)

        return {
            "success": True,
            "count": len(resources),
            "resources": [
                AidResourceResponse(
                    name=r.name,
                    type=r.type,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    distance_km=r.distance_km,
                    address=r.address,
                    contact=r.contact,
                    hours=r.hours,
                    source=r.source
                ) for r in resources
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/route/to-resource", response_model=RouteToResourceResponse)
async def calculate_route_endpoint(request: RouteToResourceRequest):
    """Get route from user location to aid resource"""
    try:
        api_key = os.getenv("OPENROUTESERVICE_API_KEY")

        route = get_route_to_resource(
            request.user_latitude,
            request.user_longitude,
            request.resource_latitude,
            request.resource_longitude,
            api_key
        )

        if route:
            return RouteToResourceResponse(
                success=True,
                route=RouteResponse(
                    total_distance_km=route.total_distance_km,
                    total_duration_min=route.total_duration_min,
                    steps=[
                        RouteStepResponse(
                            instruction=step.instruction,
                            distance_m=step.distance_m,
                            duration_s=step.duration_s,
                            latitude=step.latitude,
                            longitude=step.longitude
                        ) for step in route.steps
                    ],
                    polyline=route.polyline
                )
            )

        return RouteToResourceResponse(
            success=False,
            error="Could not calculate route"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WebSocketVoiceBridge(NovaVoiceBridge):
    """Subclass that relays Nova audio/events back to the client WebSocket."""

    def __init__(self, client_ws: WebSocket):
        super().__init__(location=None)
        self.client_ws = client_ws

    async def on_audio_output(self, pcm_bytes: bytes):
        await self.client_ws.send_json({
            "type": "response.output_audio.delta",
            "delta": b64.b64encode(pcm_bytes).decode(),
        })

    async def on_event(self, event: dict):
        await self.client_ws.send_json(event)


@app.get("/voice/status")
async def voice_status():
    """Check voice agent configuration status"""
    return {
        "voice_agent_configured": bool(os.getenv("NOVA_API_KEY")),
        "nova_voice_agent_id": os.getenv("NOVA_VOICE_AGENT_ID", "not set"),
        "model": "nova-2-sonic-v1",
        "endpoint": "/voice/stream (WebSocket)"
    }


@app.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional voice streaming.

    Protocol (client → server):
        {"type": "input_audio_buffer.append", "audio": "<base64 PCM16 @ 16kHz>"}
        {"type": "session.location", "latitude": 10.76, "longitude": 106.66}

    Protocol (server → client):
        {"type": "session.created",  "session_id": "..."}
        {"type": "session.ready"}
        {"type": "response.output_audio.delta",                    "delta": "<base64 PCM16>"}
        {"type": "response.output_audio_transcript.done",          "transcript": "..."}
        {"type": "conversation.item.input_audio_transcription.completed", "transcript": "..."}
        {"type": "tool.call",  "name": "...", "args": {...}}
        {"type": "error",      "error": {...}}
        {"type": "session.closed"}
    """
    await websocket.accept()

    bridge = WebSocketVoiceBridge(client_ws=websocket)

    try:
        await bridge.connect()
        await bridge.handshake()

        await websocket.send_json({
            "type": "session.created",
            "session_id": bridge.session_id,
        })
        await websocket.send_json({"type": "session.ready"})

        nova_task = asyncio.create_task(bridge.receive_loop())

        try:
            while bridge.is_active:
                msg = await websocket.receive_json()
                t = msg.get("type", "")

                if t == "input_audio_buffer.append":
                    import base64
                    await bridge.send_audio(base64.b64decode(msg["audio"]))

                elif t == "session.location":
                    lat = msg.get("latitude")
                    lon = msg.get("longitude")
                    if lat is not None and lon is not None:
                        bridge.location = (float(lat), float(lon))

        except WebSocketDisconnect:
            pass
        finally:
            nova_task.cancel()
            await bridge.close()

    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": {"message": str(e)}})
        except Exception:
            pass
    finally:
        try:
            await websocket.send_json({"type": "session.closed"})
        except Exception:
            pass
