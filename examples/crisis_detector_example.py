from src.features.crisis_detector import (detect_crisis,
                                          detect_crisis_with_llm,
                                          should_escalate)


def main():
    scenarios = [
        {
            "input": "5 people are bleeding heavily at 33.8938, 35.5018, we need urgent medical help",
            "location": None,
            "mode": "keyword"
        },
        {
            "input": "My child is injured and we need a doctor immediately",
            "location": (33.8938, 35.5018),
            "mode": "keyword"
        },
        {
            "input": "We are lost and looking for shelter, 3 of us including children",
            "location": (33.8938, 35.5018),
            "mode": "llm"
        },
        {
            "input": "Where can I find food and water?",
            "location": (33.8938, 35.5018),
            "mode": "keyword"
        },
        {
            "input": "Explosion nearby, multiple people unconscious, need ambulance now",
            "location": (33.8938, 35.5018),
            "mode": "llm"
        }
    ]

    print("Crisis Detection Examples (Keyword vs LLM)")
    print("=" * 80)

    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i} (Detection Mode: {scenario['mode'].upper()}):")
        print(f"Input: {scenario['input']}")
        if scenario['location']:
            print(f"Provided Location: {scenario['location']}")
        print("-" * 80)

        if scenario['mode'] == 'llm':
            report = detect_crisis_with_llm(scenario['input'], location=scenario['location'])
        else:
            report = detect_crisis(scenario['input'], location=scenario['location'])

        print(f"Urgency Level: {report.urgency_level.upper()}")
        print(f"Detected Keywords: {', '.join(report.detected_keywords)}")
        print(f"Detection Mode Used: {report.detection_mode}")

        if report.location:
            print(f"Location: {report.location[0]:.6f}, {report.location[1]:.6f}")

        if report.num_people:
            print(f"Number of People: {report.num_people}")

        if report.injury_type:
            print(f"Injury Type: {report.injury_type.replace('_', ' ').title()}")

        if report.needs:
            print(f"Needs: {', '.join(report.needs)}")

        print(f"\nSummary: {report.summary}")
        print(f"Timestamp: {report.timestamp}")

        escalate = should_escalate(report)
        print(f"Should Escalate: {'YES - SEND SOS ALERT' if escalate else 'No'}")
        print()


if __name__ == "__main__":
    main()
