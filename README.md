# RefugeeReach

> anh Tường nhớ đọc khúc đầu nhé

AI-powered crisis response and aid location system for refugees using Amazon Nova agents.

See `examples/` directory for usage demonstrations.

First Install Dependencies
```bash
pip install -r src/requirements.txt
```

Then configure Environment by copying `.env.example` to `.env` and add your credentials:
```
NOVA_API_KEY=your_nova_api_key
NOVA_ORCHESTRATOR_AGENT_ID=
NOVA_SOS_AGENT_ID=
NOVA_GENERAL_AGENT_ID=
NOVA_VOICE_AGENT_ID=
```

Run docker...
```bash
docker compose up --build -d
```

Access the API thru:
```
http://localhost:8000/docs
```

---

## **1. Aid Resource Finder**
Discovers verified aid services near a user's location using OpenStreetMap and UNHCR data sources.

### *1.1. Main Function*
```python
find_aid_resources(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    max_results: int = 20
) -> List[AidResource]
```

*Parameters:*
- `latitude`: User's GPS latitude coordinate
- `longitude`: User's GPS longitude coordinate
- `radius_km`: Search radius in kilometers (default: 10km)
- `max_results`: Maximum number of results to return (default: 20)

*Returns:*
List of `AidResource` objects sorted by distance, each containing:
- `name`: Facility name
- `type`: Resource type (hospital, clinic, shelter, refugee_camp, etc.)
- `latitude`, `longitude`: GPS coordinates
- `distance_km`: Distance from user location
- `address`: Street address (if available)
- `contact`: Phone number (if available)
- `hours`: Opening hours (if available)
- `source`: Data source (OpenStreetMap or UNHCR)

### *1.2. Data Sources*
- *OpenStreetMap Overpass API*: Queries hospitals, clinics, pharmacies, water sources, and shelters
- *UNHCR API*: Retrieves registered refugee camp locations and displacement statistics

### *1.3. Distance Calculation*
Uses Haversine formula to calculate great-circle distance between coordinates, accounting for Earth's curvature with 6371km radius.

## **2. Crisis Detection**
Analyzes user messages to detect emergency situations and extract structured crisis information. Supports both keyword-based and LLM-based detection modes.

### *2.1. Keyword-Based Detection*
```python
detect_crisis(
    user_input: str,
    location: Optional[Tuple[float, float]] = None
) -> CrisisReport
```

*Parameters:*
- `user_input`: User's crisis message text
- `location`: Optional GPS coordinates (latitude, longitude)

*Returns:*
`CrisisReport` object containing:
- `urgency_level`: Classification (critical, high, medium, low)
- `detected_keywords`: List of crisis keywords found
- `location`: GPS coordinates (extracted or provided)
- `num_people`: Number of people affected
- `injury_type`: Injury classification (severe_bleeding, fracture, burn, gunshot, unconscious, general_injury)
- `needs`: List of required resources (medical, water, food, shelter, safety)
- `summary`: Human-readable crisis summary
- `timestamp`: ISO 8601 timestamp
- `raw_input`: Original user message
- `detection_mode`: Detection method used (keyword, llm, keyword_fallback)

### *2.2. LLM-Based Detection*

> hiện chưa dùng vì chưa có env của AWS


```python
detect_crisis_with_llm(
    user_input: str,
    location: Optional[Tuple[float, float]] = None,
    model_id: str = "amazon.nova-lite-v1:0"
) -> CrisisReport
```
Uses Amazon Nova Lite via AWS Bedrock for intelligent urgency detection. Automatically falls back to keyword detection if AWS Bedrock is unavailable.

*Parameters:*
- `user_input`: User's crisis message text
- `location`: Optional GPS coordinates
- `model_id`: Bedrock model identifier (default: Nova Lite)

*Returns:* Same `CrisisReport` structure as keyword-based detection, with `detection_mode` set to "llm" or "keyword_fallback".

### *2.3. Urgency Classification*
- *Critical*: Life-threatening situations (dying, bleeding, unconscious, explosion, shooting)
- *High*: Injuries and immediate danger (injured, violence, urgent, emergency)
- *Medium*: Distress without immediate danger (lost, missing, scared, hungry)
- *Low*: General inquiries and non-urgent needs

## **3. SOS Alert System**
Sends emergency alerts to designated contacts when critical or high urgency situations are detected.

### *3.1. Alert Function*

```python
send_sos_alert(
    crisis_report: CrisisReport,
    emergency_contacts: List[str],
    use_sns: bool = True
) -> SOSAlert
```

*Parameters:*
- `crisis_report`: Crisis report from detection functions
- `emergency_contacts`: List of phone numbers or email addresses
- `use_sns`: Use AWS SNS (True) or mock mode (False)

*Returns:*

`SOSAlert` object containing:
- `report`: Original crisis report
- `alert_id`: Unique UUID for tracking
- `recipients`: List of emergency contacts
- `status`: Delivery status (sent_sns, mock_sent, no_topic_configured, sns_failed)
- `sent_at`: ISO 8601 timestamp

### *3.2. Escalation Logic*

```python
should_escalate(crisis_report: CrisisReport) -> bool
```

Returns `True` if urgency level is critical or high, triggering SOS alert workflow.

### *3.3. Alert Delivery Modes*

- *AWS SNS Mode*: Publishes to configured SNS topic for SMS, email, and push notifications
- *Mock Mode*: Prints alert to console for testing without AWS credentials


## **4. Agent Orchestration**
Intelligent routing system using Amazon Nova agents to analyze user intent and delegate to specialized agents for crisis response, aid location, or general assistance.

### *4.1. Main Orchestrator Function*
```python
process_user_input_strands(
    user_input: str,
    location: Optional[Tuple[float, float]] = None
) -> Dict
```

*Parameters:*
- `user_input`: User's message text
- `location`: Optional GPS coordinates (latitude, longitude)

*Returns:*
Dictionary containing:
- `success`: Boolean indicating processing status
- `response`: Agent's response message
- `agent_used`: Agent that handled the request (orchestrator, sos, aid_locator, general)
- `user_input`: Original user message
- `location`: GPS coordinates used
- `error`: Error message if processing failed

### *4.2. Agent Architecture*

#### 4.2.1. Orchestrator Agent
- *Model*: Amazon Nova agent (configured in Nova console)
- *Purpose*: Analyzes user intent and routes to appropriate specialized agent
- *Tools*: `route_to_sos_agent`, `route_to_aid_locator_agent`, `route_to_general_chat_agent`
- *Configuration*: `NOVA_ORCHESTRATOR_AGENT_ID` environment variable

#### 4.2.2. SOS Agent
- *Model*: Amazon Nova agent with crisis response system prompt
- *Purpose*: Handles emergency situations and crisis detection
- *Tools*: `analyze_crisis`, `trigger_sos_alert`
- *Configuration*: `NOVA_SOS_AGENT_ID` environment variable
- *Capabilities*: Urgency classification, injury detection, emergency contact alerting

#### 4.2.3. Aid Locator Agent
- *Model*: Amazon Nova agent with resource finding capabilities
- *Purpose*: Finds nearby aid resources (hospitals, shelters, food, water)
- *Tools*: `search_nearby_resources`, `filter_resources_by_type`
- *Configuration*: Uses `NOVA_SOS_AGENT_ID` (shares model with SOS agent)
- *Data Sources*: OpenStreetMap, UNHCR refugee camp database

## **5. API**

REST API providing HTTP endpoints for the RefugeeReach agent system with automatic location detection and CORS support.

### *5.1. Endpoints*

#### 5.1.1. Health Check
```http
GET /
```

*Response:*
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "agents_configured": true
}
```

Returns API health status and agent configuration state.

#### 5.1.2. Chat
```http
POST /chat
Content-Type: application/json
```

*Request Body:*
```json
{
  "message": "Help! I need medical assistance"
}
```

*Parameters:*
- `message`: User's message text (required)
- `location`: GPS coordinates as [latitude, longitude] (optional, overrides auto-detection)
- `auto_detect_location`: Enable automatic IP-based location detection (optional, default: true)

*Response:*
```json
{
  "success": true,
  "response": "I've detected a critical situation and triggered an SOS alert...",
  "agent_used": "orchestrator",
  "location": [33.8938, 35.5018],
  "error": null
}
```

Processes user messages through the orchestrator agent and returns AI-generated responses.

#### 5.1.3. Get Location
```http
GET /location
```

*Response:*
```json
{
  "success": true,
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

Auto-detects device location from IP address using geocoder library.

### *5.2. Running the API*

#### 5.2.1. Development Mode*
```bash
python src/api/run.py
```

Server starts at http://localhost:8000 with auto-reload enabled.

#### 5.2.2. Production Mode
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 5.2.3. Docker
```bash
docker-compose up -d
```

Builds and runs containerized API with environment variables from `.env` file.



## **6. Voice Agent**

Real-time bidirectional voice assistant using Amazon Nova Sonic for natural speech-to-speech interaction in crisis situations.

### *6.1. Voice Agent Function*
```python
async def run_voice_assistant():
    """Run the voice assistant with audio I/O."""
```

Starts a persistent bidirectional streaming session with Nova Sonic, enabling:
- Real-time speech recognition and synthesis
- Natural conversation with interruption handling
- Concurrent tool execution (crisis detection, aid finding)
- Multilingual support (English, Arabic, Farsi, Hebrew)

### *6.2. Configuration*

#### 6.2.1. Environment Variables
```bash
NOVA_VOICE_AGENT_ID=your_voice_agent_id
AWS_REGION=us-east-1  # or eu-north-1, ap-northeast-1
```

#### 6.2.2. Model Configuration
- *Model*: `amazon.nova-sonic-v1:0`
- *Voice*: matthew (masculine-sounding English)
- *Audio Format*: PCM, 16kHz, mono
- *Temperature*: 0.5 (balanced creativity)
- *Max Tokens*: 1000 (concise responses)

### *6.3. Capabilities*

#### 6.3.1. Emergency Detection
Voice agent automatically detects crisis keywords and routes to SOS agent:
```
User: "I'm bleeding and need help"
Agent: "I've detected an emergency. Analyzing your situation..."
```

#### 6.3.2. Aid Resource Finding
Finds nearby resources through voice commands:
```
User: "Where is the nearest hospital?"
Agent: "I found 3 hospitals within 5km. The closest is..."
```

#### 6.3.3. General Assistance
Answers questions about safety, procedures, and guidance:
```
User: "What should I do if I cross the border?"
Agent: "When crossing the border, you should..."
```

### *6.4. Running the Voice Agent*

#### 6.4.1. Basic Usage
```python
import asyncio
from src.agents.voice_agent import run_voice_assistant

asyncio.run(run_voice_assistant())
```

#### 6.4.2. Example Script
```bash
python examples/voice_agent_example.py
```

#### 6.4.3. With Context Manager
```python
from src.agents.voice_agent import run_voice_assistant_with_context

async def main():
    await run_voice_assistant_with_context()

asyncio.run(main())
```

### *6.5. Voice Commands*

- *Stop Session*: "stop conversation"
- *Emergency*: "help", "emergency", "injured", "bleeding"
- *Find Resources*: "hospital", "shelter", "food", "water"
- *General*: Any question about safety, procedures, or guidance

### *6.6. Requirements*

- Python 3.12+ (required for BidiNovaSonicModel)
- `strands-agents[bidi]` package installed
- AWS credentials configured (boto3 session or environment variables)
- Microphone and speakers available
- AWS region: us-east-1, eu-north-1, or ap-northeast-1

### *6.7. API Endpoint*
```http
GET /voice/status
```

*Response:*
```json
{
  "voice_agent_configured": true,
  "aws_region": "us-east-1",
  "model": "amazon.nova-sonic-v1:0",
  "note": "Voice agent requires bidirectional streaming. Use WebSocket or dedicated client."
}
```

Checks voice agent configuration status. Note: Voice streaming requires WebSocket connection, not standard HTTP REST.
