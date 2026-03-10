import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import boto3


class DetectionMode(Enum):
    KEYWORD = "keyword"
    LLM = "llm"


@dataclass
class CrisisReport:
    urgency_level: str
    detected_keywords: List[str]
    location: Optional[Tuple[float, float]]
    num_people: Optional[int]
    injury_type: Optional[str]
    needs: List[str]
    summary: str
    timestamp: str
    raw_input: str
    detection_mode: str = "keyword"


@dataclass
class SOSAlert:
    report: CrisisReport
    alert_id: str
    recipients: List[str]
    status: str
    sent_at: str


URGENCY_KEYWORDS = {
    "critical": ["dying", "dead", "bleeding", "unconscious", "attack", "shooting", "explosion", "fire"],
    "high": ["injured", "hurt", "pain", "sick", "violence", "danger", "urgent", "emergency", "help"],
    "medium": ["lost", "missing", "separated", "alone", "scared", "hungry", "thirsty"],
    "low": ["need", "looking for", "where", "how"]
}

INJURY_KEYWORDS = {
    "severe_bleeding": ["bleeding", "blood", "hemorrhage"],
    "fracture": ["broken", "fracture", "bone"],
    "burn": ["burn", "burned", "fire"],
    "gunshot": ["shot", "bullet", "gunshot"],
    "unconscious": ["unconscious", "passed out", "not breathing"],
    "general_injury": ["injured", "hurt", "pain", "wound"]
}

NEEDS_KEYWORDS = {
    "medical": ["doctor", "hospital", "medicine", "medical", "clinic", "ambulance"],
    "water": ["water", "thirsty", "dehydrated"],
    "food": ["food", "hungry", "eat"],
    "shelter": ["shelter", "place to stay", "homeless", "cold"],
    "safety": ["safe", "danger", "violence", "protect"]
}


def extract_numbers(text: str) -> List[int]:
    numbers = re.findall(r'\b\d+\b', text)
    return [int(n) for n in numbers]


def extract_coordinates(text: str) -> Optional[Tuple[float, float]]:
    coord_pattern = r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)'
    match = re.search(coord_pattern, text)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except ValueError:
            pass
    return None


def detect_urgency_level(text: str) -> Tuple[str, List[str]]:
    text_lower = text.lower()
    detected = []

    for keyword in URGENCY_KEYWORDS["critical"]:
        if keyword in text_lower:
            detected.append(keyword)
    if detected:
        return ("critical", detected)

    for keyword in URGENCY_KEYWORDS["high"]:
        if keyword in text_lower:
            detected.append(keyword)
    if detected:
        return ("high", detected)

    for keyword in URGENCY_KEYWORDS["medium"]:
        if keyword in text_lower:
            detected.append(keyword)
    if detected:
        return ("medium", detected)

    for keyword in URGENCY_KEYWORDS["low"]:
        if keyword in text_lower:
            detected.append(keyword)
    if detected:
        return ("low", detected)

    return ("low", [])


def detect_injury_type(text: str) -> Optional[str]:
    text_lower = text.lower()

    for injury_type, keywords in INJURY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return injury_type

    return None


def detect_needs(text: str) -> List[str]:
    text_lower = text.lower()
    needs = []

    for need_type, keywords in NEEDS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                if need_type not in needs:
                    needs.append(need_type)
                break

    return needs


def generate_summary(
    urgency_level: str,
    keywords: List[str],
    num_people: Optional[int],
    injury_type: Optional[str],
    needs: List[str],
    location: Optional[Tuple[float, float]]
) -> str:
    summary_parts = []

    summary_parts.append(f"URGENCY: {urgency_level.upper()}")

    if num_people:
        summary_parts.append(f"{num_people} person(s) affected")

    if injury_type:
        summary_parts.append(f"Injury: {injury_type.replace('_', ' ')}")

    if needs:
        summary_parts.append(f"Needs: {', '.join(needs)}")

    if location:
        summary_parts.append(f"Location: {location[0]:.6f}, {location[1]:.6f}")

    if keywords:
        summary_parts.append(f"Keywords: {', '.join(keywords[:3])}")

    return " | ".join(summary_parts)


def detect_crisis(
    user_input: str,
    location: Optional[Tuple[float, float]] = None
) -> CrisisReport:
    urgency_level, detected_keywords = detect_urgency_level(user_input)

    extracted_location = extract_coordinates(user_input)
    final_location = extracted_location or location

    numbers = extract_numbers(user_input)
    num_people = numbers[0] if numbers and numbers[0] < 1000 else None

    injury_type = detect_injury_type(user_input)

    needs = detect_needs(user_input)

    summary = generate_summary(
        urgency_level,
        detected_keywords,
        num_people,
        injury_type,
        needs,
        final_location
    )

    return CrisisReport(
        urgency_level=urgency_level,
        detected_keywords=detected_keywords,
        location=final_location,
        num_people=num_people,
        injury_type=injury_type,
        needs=needs,
        summary=summary,
        timestamp=datetime.utcnow().isoformat(),
        raw_input=user_input
    )


def detect_crisis_with_llm(
    user_input: str,
    location: Optional[Tuple[float, float]] = None,
    model_id: str = "amazon.nova-lite-v1:0"
) -> CrisisReport:
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))

        prompt = f"""Analyze this crisis message and extract structured information.

        Message: "{user_input}"

        Respond ONLY with valid JSON in this exact format:
        {{
            "urgency_level": "critical|high|medium|low",
            "detected_keywords": ["keyword1", "keyword2"],
            "num_people": number or null,
            "injury_type": "severe_bleeding|fracture|burn|gunshot|unconscious|general_injury" or null,
            "needs": ["medical", "water", "food", "shelter", "safety"]
        }}

        Rules:
        - urgency_level: "critical" for life-threatening (dying, bleeding, unconscious), "high" for injuries/danger, "medium" for lost/scared, "low" for general questions
        - detected_keywords: key crisis words from the message
        - num_people: extract number of people mentioned, null if not specified
        - injury_type: classify injury if mentioned, null otherwise
        - needs: list applicable needs from the message"""

        request_body = {
            "messages": [{"role": "user", "content": prompt}],
            "inferenceConfig": {
                "temperature": 0.1,
                "maxTokens": 500
            }
        }

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        content = response_body['output']['message']['content'][0]['text']

        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            llm_data = json.loads(json_match.group())
        else:
            llm_data = json.loads(content)

        extracted_location = extract_coordinates(user_input)
        final_location = extracted_location or location

        summary = generate_summary(
            llm_data.get("urgency_level", "low"),
            llm_data.get("detected_keywords", []),
            llm_data.get("num_people"),
            llm_data.get("injury_type"),
            llm_data.get("needs", []),
            final_location
        )

        return CrisisReport(
            urgency_level=llm_data.get("urgency_level", "low"),
            detected_keywords=llm_data.get("detected_keywords", []),
            location=final_location,
            num_people=llm_data.get("num_people"),
            injury_type=llm_data.get("injury_type"),
            needs=llm_data.get("needs", []),
            summary=summary,
            timestamp=datetime.utcnow().isoformat(),
            raw_input=user_input,
            detection_mode="llm"
        )
    except Exception as e:
        print(f"LLM detection failed: {e}, falling back to keyword detection")
        report = detect_crisis(user_input, location)
        report.detection_mode = "keyword_fallback"
        return report


def should_escalate(crisis_report: CrisisReport) -> bool:
    return crisis_report.urgency_level in ["critical", "high"]


def send_sos_alert(
    crisis_report: CrisisReport,
    emergency_contacts: List[str],
    use_sns: bool = True
) -> SOSAlert:
    import uuid

    alert_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    message = f"""🚨 EMERGENCY SOS ALERT 🚨

    Alert ID: {alert_id}
    Urgency: {crisis_report.urgency_level.upper()}
    Time: {timestamp}

    {crisis_report.summary}

    Raw Message: {crisis_report.raw_input}

    Detection Method: {crisis_report.detection_mode}
    """

    if crisis_report.location:
        lat, lon = crisis_report.location
        message += f"\n📍 Location: https://www.google.com/maps?q={lat},{lon}"

    status = "pending"

    if use_sns:
        try:
            sns = boto3.client('sns', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            topic_arn = os.getenv('SNS_SOS_TOPIC_ARN')

            if topic_arn:
                sns.publish(
                    TopicArn=topic_arn,
                    Subject=f"🚨 SOS Alert - {crisis_report.urgency_level.upper()}",
                    Message=message
                )
                status = "sent_sns"
            else:
                status = "no_topic_configured"
        except Exception as e:
            print(f"SNS send failed: {e}")
            status = "sns_failed"
    else:
        print("\n" + "="*80)
        print("MOCK SOS ALERT - Would send to:", ", ".join(emergency_contacts))
        print("="*80)
        print(message)
        print("="*80)
        status = "mock_sent"

    return SOSAlert(
        report=crisis_report,
        alert_id=alert_id,
        recipients=emergency_contacts,
        status=status,
        sent_at=timestamp
    )
