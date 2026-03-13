import asyncio
import base64 as b64
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.agents.orchestrator import process_user_input_strands
from src.agents.voice_agent import NovaVoiceBridge
from src.api.models import ChatRequest, ChatResponse, HealthResponse
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
