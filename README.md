# Anh Tường đọc nha

Dưới đây sẽ là instructions để dùng từng feat.

See `examples/` directory for usage demonstrations.

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

## **4. Installation and Usage**

### *4.1. Dependencies*

```bash
pip install -r src/agents/requirements.txt
```

### *4.2. Environment Configuration*
Copy `.env.example` to `.env` and configure:
- AWS credentials and region
- SNS topic ARN for SOS alerts
- Bedrock model access for LLM detection

*4.3. Example Usage*

```python
from src.agents.aid_locator import find_aid_resources
from src.agents.crisis_detector import detect_crisis, send_sos_alert, should_escalate

resources = find_aid_resources(latitude=33.8938, longitude=35.5018, radius_km=15)

report = detect_crisis("5 people bleeding, need urgent medical help", location=(33.8938, 35.5018))

if should_escalate(report):
    alert = send_sos_alert(report, ["+1234567890"], use_sns=False)
```

