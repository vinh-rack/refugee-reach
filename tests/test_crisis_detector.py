import pytest

from src.agents.crisis_detector import (CrisisReport, detect_crisis,
                                        detect_injury_type, detect_needs,
                                        detect_urgency_level,
                                        extract_coordinates, extract_numbers,
                                        generate_summary, should_escalate)


def test_extract_numbers():
    text = "There are 5 people injured and 3 children"
    numbers = extract_numbers(text)
    assert numbers == [5, 3]


def test_extract_numbers_no_numbers():
    text = "No numbers here"
    numbers = extract_numbers(text)
    assert numbers == []


def test_extract_coordinates_valid():
    text = "Location is 40.7128, -74.0060"
    coords = extract_coordinates(text)
    assert coords == (40.7128, -74.0060)


def test_extract_coordinates_invalid():
    text = "No coordinates here"
    coords = extract_coordinates(text)
    assert coords is None


def test_extract_coordinates_out_of_range():
    text = "Location is 200.0, 300.0"
    coords = extract_coordinates(text)
    assert coords is None


def test_detect_urgency_level_critical():
    text = "Someone is dying here, bleeding heavily"
    level, keywords = detect_urgency_level(text)
    assert level == "critical"
    assert "dying" in keywords
    assert "bleeding" in keywords


def test_detect_urgency_level_high():
    text = "We are injured and need urgent help"
    level, keywords = detect_urgency_level(text)
    assert level == "high"
    assert "injured" in keywords
    assert "urgent" in keywords


def test_detect_urgency_level_medium():
    text = "I am lost and scared"
    level, keywords = detect_urgency_level(text)
    assert level == "medium"
    assert "lost" in keywords
    assert "scared" in keywords


def test_detect_urgency_level_low():
    text = "Where can I find food?"
    level, keywords = detect_urgency_level(text)
    assert level == "low"
    assert "where" in keywords


def test_detect_injury_type_bleeding():
    text = "There is heavy bleeding"
    injury = detect_injury_type(text)
    assert injury == "severe_bleeding"


def test_detect_injury_type_fracture():
    text = "My arm is broken"
    injury = detect_injury_type(text)
    assert injury == "fracture"


def test_detect_injury_type_none():
    text = "I need water"
    injury = detect_injury_type(text)
    assert injury is None


def test_detect_needs_multiple():
    text = "We need water, food, and medical help"
    needs = detect_needs(text)
    assert "water" in needs
    assert "food" in needs
    assert "medical" in needs


def test_detect_needs_single():
    text = "Looking for shelter"
    needs = detect_needs(text)
    assert needs == ["shelter"]


def test_detect_needs_none():
    text = "Just checking in"
    needs = detect_needs(text)
    assert needs == []


def test_generate_summary_full():
    summary = generate_summary(
        urgency_level="critical",
        keywords=["bleeding", "dying"],
        num_people=5,
        injury_type="severe_bleeding",
        needs=["medical", "water"],
        location=(40.7128, -74.0060)
    )

    assert "URGENCY: CRITICAL" in summary
    assert "5 person(s)" in summary
    assert "severe bleeding" in summary
    assert "medical, water" in summary
    assert "40.712800, -74.006000" in summary


def test_generate_summary_minimal():
    summary = generate_summary(
        urgency_level="low",
        keywords=[],
        num_people=None,
        injury_type=None,
        needs=[],
        location=None
    )

    assert "URGENCY: LOW" in summary


def test_detect_crisis_critical():
    user_input = "5 people are bleeding at 40.7128, -74.0060, we need medical help urgently"

    report = detect_crisis(user_input)

    assert report.urgency_level == "critical"
    assert "bleeding" in report.detected_keywords
    assert report.num_people == 5
    assert report.injury_type == "severe_bleeding"
    assert "medical" in report.needs
    assert report.location == (40.7128, -74.0060)
    assert report.raw_input == user_input


def test_detect_crisis_with_provided_location():
    user_input = "I am injured and need help"
    location = (34.0522, -118.2437)

    report = detect_crisis(user_input, location=location)

    assert report.urgency_level == "high"
    assert report.location == location


def test_detect_crisis_extracted_location_priority():
    user_input = "Help at 40.7128, -74.0060"
    provided_location = (34.0522, -118.2437)

    report = detect_crisis(user_input, location=provided_location)

    assert report.location == (40.7128, -74.0060)


def test_should_escalate_critical():
    report = CrisisReport(
        urgency_level="critical",
        detected_keywords=["dying"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="",
        timestamp="",
        raw_input=""
    )

    assert should_escalate(report) is True


def test_should_escalate_high():
    report = CrisisReport(
        urgency_level="high",
        detected_keywords=["injured"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="",
        timestamp="",
        raw_input=""
    )

    assert should_escalate(report) is True


def test_should_escalate_medium():
    report = CrisisReport(
        urgency_level="medium",
        detected_keywords=["lost"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="",
        timestamp="",
        raw_input=""
    )

    assert should_escalate(report) is False


def test_crisis_report_dataclass():
    report = CrisisReport(
        urgency_level="high",
        detected_keywords=["injured", "help"],
        location=(40.7128, -74.0060),
        num_people=3,
        injury_type="fracture",
        needs=["medical"],
        summary="Test summary",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test input"
    )

    assert report.urgency_level == "high"
    assert len(report.detected_keywords) == 2
    assert report.num_people == 3
