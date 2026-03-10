import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agents.orchestrator import process_user_input_strands
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
