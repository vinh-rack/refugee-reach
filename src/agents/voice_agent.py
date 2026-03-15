import asyncio
import base64
import json
import os
import ssl
import struct
from typing import Optional, Tuple

import pyaudio
import websockets
from dotenv import load_dotenv

from src.features.aid_locator import find_aid_resources
from src.features.crisis_detector import (detect_crisis, send_sos_alert,
                                          should_escalate)
from src.features.location_service import get_device_location

load_dotenv()

NOVA_API_KEY = os.environ.get("NOVA_API_KEY", "")
NOVA_VOICE_AGENT_ID = os.environ.get("NOVA_VOICE_AGENT_ID", "")

if not NOVA_API_KEY:
    raise EnvironmentError("NOVA_API_KEY is not set.")

SAMPLE_RATE = 24000
INPUT_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
CHUNK = 2048

TOOLS = [
    {
        "type": "function",
        "name": "detect_emergency",
        "description": "Analyze if user is in emergency situation requiring immediate help. Use for: injuries, bleeding, danger, violence, life-threatening situations.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_message": {
                    "type": "string",
                    "description": "The user's message describing their situation"
                }
            },
            "required": ["user_message"]
        }
    },
    {
        "type": "function",
        "name": "find_nearby_aid",
        "description": "Find nearby aid resources like hospitals, shelters, food, water, refugee camps.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": "string",
                    "enum": ["hospital", "shelter", "food", "water", "refugee_camp"],
                    "description": "Type of resource to find"
                }
            },
            "required": ["resource_type"]
        }
    }
]

SESSION_INSTRUCTIONS = """
    You are RefugeeReach Voice Assistant, a compassionate AI companion helping displaced people in crisis situations.

    Your role:
    - Provide clear, concise voice responses optimized for real-time conversation
    - Detect emergencies and analyze crisis situations
    - Help users find nearby aid resources (hospitals, shelters, food, water, refugee camps)
    - Answer general questions about safety, procedures, and assistance
    - Support multilingual conversations when needed

    Communication style:
    - Speak naturally and calmly, especially during emergencies
    - Use simple, clear language accessible to non-native speakers
    - Be empathetic and supportive without being patronizing
    - Keep responses brief (2-3 sentences) for voice interaction
    - Prioritize actionable information over explanations

    Available tools:
    1. detect_emergency(user_message)
    - Use when user mentions: injuries, bleeding, danger, violence, life-threatening situations
    - Analyzes crisis severity and provides immediate action steps

    2. find_nearby_aid(resource_type)
    - Use when user needs: hospital, shelter, food, water, refugee_camp
    - Finds resources within 10km sorted by distance
    - Location is retrieved automatically — never ask the user for it

    For greetings, general questions, and unclear requests — respond directly without calling a tool.

    Critical rules:
    - For emergencies, ALWAYS call detect_emergency first, then suggest calling local emergency services
    - If user mentions multiple needs, prioritize medical emergencies over other resources
    - Never make up resource locations - only use data from find_nearby_aid tool
    - If tools fail, provide general guidance and suggest contacting local authorities

    Always prioritize user safety and provide actionable information.
"""


def build_ws_url() -> str:
    url = "wss://api.nova.amazon.com/v1/realtime?model=nova-2-sonic-v1"
    if NOVA_VOICE_AGENT_ID:
        url += f"&agent_id={NOVA_VOICE_AGENT_ID}"
    return url


def pcm_to_base64(pcm_bytes: bytes) -> str:
    return base64.b64encode(pcm_bytes).decode("utf-8")


def float32_to_pcm16(float32_array) -> bytes:
    clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
    return b"".join(struct.pack("<h", int(x * 32767)) for x in clipped)

# Tool implementations
async def detect_emergency_tool(user_message: str, location: Optional[Tuple[float, float]] = None) -> dict:
    """Returns {"text": str, "sos_alert": dict|None}"""
    from datetime import datetime

    from src.features.crisis_detector import CrisisReport

    crisis_report = detect_crisis(user_message, location)

    response = f"Crisis Level: {crisis_report.urgency_level.upper()}\n"

    if crisis_report.injury_type:
        response += f"Injury Type: {crisis_report.injury_type.replace('_', ' ')}\n"

    if crisis_report.needs:
        response += f"Immediate Needs: {', '.join(crisis_report.needs)}\n"

    sos_alert = None

    if crisis_report.urgency_level in ['critical', 'high']:
        response += "\n🚨 EMERGENCY DETECTED\n"
        response += "Recommended actions:\n"
        response += "- Call local emergency services immediately\n"
        response += "- Share your location with authorities\n"
        if location:
            response += f"- Your coordinates: {location[0]}, {location[1]}\n"

        # Trigger SOS alert like the orchestrator does
        if should_escalate(crisis_report):
            alert = send_sos_alert(crisis_report, ["+1234567890"], use_sns=False)
            sos_alert = {
                "alert_sent": True,
                "alert_id": alert.alert_id,
                "status": alert.status,
                "sent_at": alert.sent_at,
                "urgency_level": crisis_report.urgency_level,
                "summary": crisis_report.summary,
                "location": location
            }
            response += "- SOS alert has been sent to emergency contacts\n"

    return {"text": response, "sos_alert": sos_alert}


async def find_nearby_aid_tool(resource_type: str, location: Tuple[float, float]) -> dict:
    """Returns {"text": str, "resources": list[dict]}"""
    all_resources = find_aid_resources(
        latitude=location[0],
        longitude=location[1],
        radius_km=10,
        max_results=20
    )

    type_mapping = {
        'hospital': ['hospital', 'clinic', 'doctors'],
        'shelter': ['shelter'],
        'food': ['food'],
        'water': ['drinking_water'],
        'refugee_camp': ['refugee_camp']
    }

    valid_types = type_mapping.get(resource_type, [resource_type])
    filtered = [r for r in all_resources if r.type in valid_types]

    if not filtered:
        return {
            "text": f"No {resource_type} facilities found within 10km. Try expanding search radius or contact local authorities.",
            "resources": []
        }

    # Build structured resource list for the UI
    resources_data = [
        {
            "name": r.name,
            "type": r.type,
            "distance_km": round(r.distance_km, 2),
            "latitude": r.latitude,
            "longitude": r.longitude,
            "address": r.address,
            "contact": r.contact,
            "hours": r.hours,
            "source": r.source
        }
        for r in filtered[:5]
    ]

    response = f"Found {len(filtered)} {resource_type} locations nearby:\n\n"
    for i, resource in enumerate(filtered[:5], 1):
        response += f"{i}. {resource.name}\n"
        response += f"   Distance: {resource.distance_km:.1f}km\n"
        if resource.address:
            response += f"   Address: {resource.address}\n"
        if resource.contact:
            response += f"   Phone: {resource.contact}\n"
        response += "\n"

    return {"text": response, "resources": resources_data}


# Headless bridge (shared by CLI and API)
class NovaVoiceBridge:
    """
    Manages the Nova Sonic WebSocket connection and all tool execution.

    Audio/event I/O is handled via overridable hooks:
      on_audio_output(pcm_bytes) — called for each audio chunk from Nova
      on_event(event_dict)       — called for transcripts, errors, status

    location may be set at any point before a tool call runs.
    """

    def __init__(self, location: Optional[Tuple[float, float]] = None):
        self.nova_ws = None
        self.is_active = False
        self.session_id = None
        self.location = location

    async def connect(self):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        self.nova_ws = await websockets.connect(
            build_ws_url(),
            ssl=ssl_ctx,
            additional_headers={
                "Authorization": f"Bearer {NOVA_API_KEY}",
                "Origin": "https://api.nova.amazon.com",
            },
        )
        self.is_active = True

    async def handshake(self):
        event = json.loads(await self.nova_ws.recv())
        assert event["type"] == "session.created"
        self.session_id = event["session"]["id"]

        await self.nova_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_output_tokens": 3000,
                "instructions": SESSION_INSTRUCTIONS,
                "audio": {
                    "input": {"turn_detection": {"threshold": 0.5}},
                    "output": {"voice": "matthew"},
                },
            },
            "extra_body": {"temperature": 0.7, "top_p": 0.9},
        }))

        event = json.loads(await self.nova_ws.recv())
        assert event["type"] == "session.updated"

    async def send_audio(self, pcm_bytes: bytes):
        """Forward a PCM chunk from the caller to Nova."""
        if not self.is_active:
            return
        await self.nova_ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": pcm_to_base64(pcm_bytes),
        }))

    # Override these in subclasses
    async def on_audio_output(self, pcm_bytes: bytes):
        pass

    async def on_event(self, event: dict):
        pass

    # Nova receive loop
    async def receive_loop(self):
        try:
            async for raw in self.nova_ws:
                event = json.loads(raw)
                t = event.get("type", "")

                if t == "response.output_audio.delta":
                    await self.on_audio_output(base64.b64decode(event["delta"]))

                elif t == "response.function_call_arguments.done":
                    await self._handle_function_call(event)

                elif t in (
                    "error",
                    "response.done",
                    "response.output_audio_transcript.done",
                    "conversation.item.input_audio_transcription.completed",
                ):
                    await self.on_event(event)

        except websockets.ConnectionClosed:
            pass
        finally:
            self.is_active = False

    async def _handle_function_call(self, event: dict):
        call_id = event.get("call_id", "")
        name = event.get("name", "")

        try:
            args = json.loads(event.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        await self.on_event({"type": "tool.call", "name": name, "args": args})

        result_text = "Tool not implemented."
        try:
            location = self.location or get_device_location()

            if name == "detect_emergency":
                tool_result = await detect_emergency_tool(
                    user_message=args.get("user_message", ""),
                    location=location,
                )
                result_text = tool_result["text"]
                if tool_result.get("sos_alert"):
                    await self.on_event({
                        "type": "tool.sos_alert",
                        "sos_alert": tool_result["sos_alert"]
                    })

            elif name == "find_nearby_aid":
                if not location:
                    result_text = "Unable to determine your location. Please ensure location access is enabled."
                else:
                    tool_result = await find_nearby_aid_tool(
                        resource_type=args.get("resource_type", "hospital"),
                        location=location,
                    )
                    result_text = tool_result["text"]
                    if tool_result.get("resources"):
                        await self.on_event({
                            "type": "tool.resources",
                            "resources": tool_result["resources"]
                        })
            else:
                result_text = f"Unknown tool '{name}'."

        except Exception as e:
            result_text = f"Error executing tool: {str(e)}"
            await self.on_event({"type": "tool.error", "name": name, "error": str(e)})

        await self.nova_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps({"result": result_text}),
            },
        }))

    async def close(self):
        self.is_active = False
        if self.nova_ws:
            try:
                await self.nova_ws.close()
            except Exception:
                pass

# CLI subclass (PyAudio I/O)
class NovaVoiceAgent(NovaVoiceBridge):
    def __init__(self):
        super().__init__(location=None)
        self.audio_queue = asyncio.Queue()
        self.pa = None

    async def on_audio_output(self, pcm_bytes: bytes):
        await self.audio_queue.put(pcm_bytes)

    async def on_event(self, event: dict):
        t = event.get("type", "")
        if t == "error":
            err = event.get("error", event)
            print(f"❌ Error [{err.get('code')}]: {err.get('message')}")
        elif t == "conversation.item.input_audio_transcription.completed":
            if transcript := event.get("transcript", ""):
                print(f"You:   {transcript}")
        elif t == "response.output_audio_transcript.done":
            print(f"Agent: {event.get('transcript', '')}")
        elif t == "tool.call":
            print(f"Tool:  {event['name']}({event['args']})")
        elif t == "tool.error":
            print(f"Tool error [{event['name']}]: {event['error']}")

    async def _stream_microphone(self):
        self.pa = pyaudio.PyAudio()
        mic = self.pa.open(
            format=pyaudio.paInt16, channels=CHANNELS,
            rate=INPUT_RATE, input=True, frames_per_buffer=CHUNK,
        )
        print("\nListening — speak now. Press Ctrl+C to stop.\n")
        try:
            while self.is_active:
                pcm = mic.read(CHUNK, exception_on_overflow=False)
                await self.send_audio(pcm)
                await asyncio.sleep(0)
        except Exception as e:
            if self.is_active:
                print(f"[Mic error] {e}")
        finally:
            mic.stop_stream()
            mic.close()

    async def _play_audio(self):
        self.pa = self.pa or pyaudio.PyAudio()
        speaker = self.pa.open(
            format=pyaudio.paInt16, channels=CHANNELS,
            rate=SAMPLE_RATE, output=True,
        )
        try:
            while self.is_active or not self.audio_queue.empty():
                try:
                    chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=0.05)
                    speaker.write(chunk)
                except asyncio.TimeoutError:
                    pass
        finally:
            speaker.stop_stream()
            speaker.close()

    async def close(self):
        await super().close()
        if self.pa:
            self.pa.terminate()
        print("\n[Session] Closed.")

    async def run(self):
        await self.connect()
        await self.handshake()
        print(f"Connected (session={self.session_id})")
        try:
            await asyncio.gather(
                self.receive_loop(),
                self._stream_microphone(),
                self._play_audio(),
            )
        except KeyboardInterrupt:
            print("\nStopping…")
        finally:
            await self.close()


async def run_voice_assistant():
    agent = NovaVoiceAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(run_voice_assistant())
