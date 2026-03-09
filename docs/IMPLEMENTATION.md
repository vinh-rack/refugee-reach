# Implementation Doc

## **1. Features**
### *1.1. Aid Resource Finder (`aid_locator.py`)*
- Distance Calculation (`calculate_distance`)
	- Uses the Haversine formula to calculate the great-circle distance between two GPS coordinates
	- Takes two lat/lon pairs and returns distance in kilometers
	- Accounts for Earth's curvature (radius = 6371 km)
- UNHCR Camp Query (`query_unhcr_camps`)
	- Calls UNHCR's public API to get refugee camp locations
	- Filters camps within the specified radius (default 50km)
	- Calculates distance from user's location to each camp
	- Returns camp data with coordinates and distance
- OpenStreetMap Query (`query_openstreetmap`)
	- Uses Overpass API to query OpenStreetMap data
	- Searches for amenities: hospitals, clinics, doctors, pharmacies, water sources, shelters
	- Builds an Overpass QL query with a radius search around user coordinates
	- Extracts location data from both nodes (points) and ways (areas)
	- Parses contact info, addresses, and opening hours from OSM tags
- Main Function (`find_aid_resources`)
	- Combines results from both UNHCR and OpenStreetMap
	- Sorts all resources by distance (closest first)
	- Limits results to `max_results` (default 20)
	- Returns structured `AidResource` objects with all metadata

> Example flow: User at (33.8938, 35.5018) $\rightarrow$ Query OSM for hospitals within 10km $\rightarrow$ Query UNHCR for camps within 50km $\rightarrow$ Combine & sort by distance $\rightarrow$ Return top 20 closest resources
### *1.2. Crisis Detection & Escalation (`crisis_detector.py`)*
#### 1.2.1 Keyword-Based Detection (`detect_crisis`)
- Urgency Detection (`detect_urgency_level`)
	- Scans text for predefined keywords in 4 urgency tiers
	- Critical: dying, bleeding, unconscious, explosion, shooting
	- High: injured, danger, urgent, emergency
	- Medium: lost, missing, scared, hungry
	- Low: general questions (where, how, need)
	- Returns first matching tier (critical takes priority)
- Information Extraction
	- `extract_numbers`: Finds all numbers in text (for people count)
	- `extract_coordinates`: Regex pattern to find lat/lon pairs
	- `detect_injury_type`: Matches injury keywords to categories
	- `detect_needs`: Identifies required resources (medical, water, food, shelter, safety)
- Report Generation
	- Combines all extracted data into a `CrisisReport` object
	- Generates human-readable summary
	- Timestamps the report

- Example:
	- Input: "5 people bleeding at 33.8938, 35.5018, need medical help"
	- Output:
		- Urgency: `critical` (keyword: bleeding)
		- People: `5`
		- Location: `(33.8938, 35.5018)`
		- Injury: `severe_bleeding`
		- Needs: `[medical]`

#### 1.2.2. LLM-Based Detection (`detect_crisis_with_llm`)
- Advantages over keyword detection:
	- Understands context and nuance ("my child won't wake up" $\rightarrow$ critical, even without keyword "unconscious")
	- Handles multiple languages better
	- Can infer urgency from tone and phrasing
	- More flexible with varied expressions
- AWS Bedrock Integration
	- Connects to Amazon Bedrock using boto3
	- Uses Nova Lite model (fast, cost-effective)
	- Structured Prompt
- Sends user message with strict JSON schema instructions
	- Asks LLM to classify urgency, extract keywords, count people, identify injuries, and list needs
	- Uses low temperature (0.1) for consistent, deterministic output
- Response Parsing
	- Extracts JSON from LLM response (handles both pure JSON and text with embedded JSON)
	- Validates and structures data into `CrisisReport`
- Fallback Mechanism
	- If LLM call fails (no AWS credentials, network error, etc.), automatically falls back to keyword detection
	- Sets `detection_mode` to "`keyword_fallback`" for transparency

#### 1.2.3. SOS Alert System (`send_sos_alert`)
- Alert Preparation
	- Generates unique alert ID (UUID)
	- Formats emergency message with all crisis details
	- Includes Google Maps link if location available
	- Dual Mode Operation
- Mock Mode (`use_sns=False`)
	- Prints alert to console
	- Useful for testing without AWS
	- Returns status "`mock_sent`"
	- AWS SNS Mode (`use_sns=True`):
- Connects to AWS SNS service
	- Publishes message to configured SNS topic
	- SNS topic can have multiple subscribers (SMS, email, mobile push, webhooks)
	- Returns status: "`sent_sns`", "`no_topic_configured`", or "`sns_failed`"
- Status Tracking
	- Returns `SOSAlert` object with delivery status
	- Tracks recipients, timestamp, and alert ID
	- Enables audit trail for emergency responses
