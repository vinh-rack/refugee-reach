import os

from src.agents.crisis_detector import (detect_crisis, detect_crisis_with_llm,
                                        send_sos_alert, should_escalate)


def example_keyword_detection_with_sos():
    print("Example 1: Keyword Detection with Mock SOS")
    print("=" * 80)

    user_input = "5 people bleeding at 33.8938, 35.5018, need urgent medical help"

    report = detect_crisis(user_input)

    print(f"Input: {user_input}")
    print(f"Urgency: {report.urgency_level}")
    print(f"Summary: {report.summary}")
    print(f"Detection Mode: {report.detection_mode}")

    if should_escalate(report):
        emergency_contacts = ["+1234567890", "+9876543210"]

        alert = send_sos_alert(
            crisis_report=report,
            emergency_contacts=emergency_contacts,
            use_sns=False
        )

        print(f"\nAlert ID: {alert.alert_id}")
        print(f"Status: {alert.status}")
        print(f"Sent at: {alert.sent_at}")

    print("\n")


def example_llm_detection_with_sos():
    print("Example 2: LLM Detection with Mock SOS")
    print("=" * 80)

    user_input = "There's been an explosion near the market. Multiple casualties, children crying, we desperately need ambulances"
    location = (33.8938, 35.5018)

    report = detect_crisis_with_llm(user_input, location=location)

    print(f"Input: {user_input}")
    print(f"Urgency: {report.urgency_level}")
    print(f"Summary: {report.summary}")
    print(f"Detection Mode: {report.detection_mode}")

    if should_escalate(report):
        emergency_contacts = ["+1234567890", "emergency@ngo.org"]

        alert = send_sos_alert(
            crisis_report=report,
            emergency_contacts=emergency_contacts,
            use_sns=False
        )

        print(f"\nAlert ID: {alert.alert_id}")
        print(f"Status: {alert.status}")

    print("\n")


def example_sns_integration():
    print("Example 3: AWS SNS Integration (requires AWS credentials)")
    print("=" * 80)

    if not os.getenv('SNS_SOS_TOPIC_ARN'):
        print("⚠️  SNS_SOS_TOPIC_ARN not configured, using mock mode")
        print("To use real SNS, set SNS_SOS_TOPIC_ARN in your environment")
        use_sns = False
    else:
        use_sns = True

    user_input = "Critical: Person unconscious, not breathing at 33.8938, 35.5018"

    report = detect_crisis(user_input)

    if should_escalate(report):
        emergency_contacts = ["+1234567890"]

        alert = send_sos_alert(
            crisis_report=report,
            emergency_contacts=emergency_contacts,
            use_sns=use_sns
        )

        print(f"Alert Status: {alert.status}")
        if alert.status == "sent_sns":
            print("✅ SOS alert sent via AWS SNS")
        elif alert.status == "mock_sent":
            print("✅ Mock SOS alert sent (SNS not configured)")
        else:
            print(f"⚠️  Alert status: {alert.status}")

    print("\n")


def main():
    example_keyword_detection_with_sos()
    example_llm_detection_with_sos()
    example_sns_integration()


if __name__ == "__main__":
    main()
