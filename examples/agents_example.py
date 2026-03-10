import os

from dotenv import load_dotenv

from src.agents.orchestrator import process_user_input_strands
from src.features.location_service import get_device_location

load_dotenv()


def main():
    print("RefugeeReach - Amazon Nova Agents Demo")
    print("Using Nova Orchestrator Agent:", os.getenv("NOVA_ORCHESTRATOR_AGENT_ID", "Not configured"))
    print("Using Nova SOS Agent:", os.getenv("NOVA_SOS_AGENT_ID", "Not configured"))
    print("Using Nova General Agent:", os.getenv("NOVA_GENERAL_AGENT_ID", "Not configured"))
    print("=" * 80)

    device_location = get_device_location()
    if device_location:
        print(f"Device Location Detected: {device_location[0]:.4f}, {device_location[1]:.4f}")
    else:
        print("Device Location: Not available (using hardcoded locations for demo)")
    print("=" * 80)

    scenarios = [
        {
            "input": "Help! 3 people are injured and bleeding",
            "location": (33.8938, 35.5018),
            "description": "Emergency SOS scenario"
        },
        {
            "input": "Where can I find a hospital nearby?",
            "location": (33.8938, 35.5018),
            "description": "Aid locator scenario"
        },
        {
            "input": "I need food and water for my family",
            "location": (33.8938, 35.5018),
            "description": "Aid locator for basic needs"
        },
        {
            "input": "Hello, what can you help me with?",
            "location": None,
            "description": "General chat scenario"
        },
        {
            "input": "Someone is unconscious",
            "location": (33.8938, 35.5018),
            "description": "Critical emergency"
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}: {scenario['description']}")
        print(f"User Input: {scenario['input']}")
        if scenario['location']:
            print(f"User Location: {scenario['location']}")
        print("-" * 80)

        result = process_user_input_strands(scenario['input'], location=scenario['location'])
        print()


def interactive_mode():
    print("\nRefugeeReach Interactive Chat (Amazon Nova Agents)")
    print("Using Nova Orchestrator Agent:", os.getenv("NOVA_ORCHESTRATOR_AGENT_ID", "Not configured"))
    print("=" * 80)

    user_location = get_device_location()
    if user_location:
        print(f"Device Location Detected: {user_location[0]:.4f}, {user_location[1]:.4f}")
    else:
        print("Device Location: Not available")

    print("Type 'quit' to exit, 'location <lat> <lon>' to set/override location, 'location auto' to auto-detect")
    print("=" * 80)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == 'quit':
            print("Goodbye!")
            break

        if user_input.lower().startswith('location '):
            parts = user_input.split()
            if len(parts) == 2 and parts[1].lower() == 'auto':
                user_location = get_device_location()
                if user_location:
                    print(f"Location auto-detected: {user_location[0]:.4f}, {user_location[1]:.4f}")
                else:
                    print("Failed to auto-detect location")
                continue
            try:
                lat, lon = float(parts[1]), float(parts[2])
                user_location = (lat, lon)
                print(f"Location set to: {lat}, {lon}")
                continue
            except:
                print("Invalid location format. Use: location <latitude> <longitude> or location auto")
                continue

        result = process_user_input_strands(user_input, location=user_location)


if __name__ == "__main__":
    print("1. Run demo conversation")
    print("2. Interactive mode")
    choice = input("Choose mode (1 or 2): ").strip()

    if choice == "2":
        interactive_mode()
    else:
        main()
