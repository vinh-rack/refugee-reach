import requests

API_URL = "http://localhost:8000"


def test_health():
    print("Testing health endpoint...")
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_location():
    print("Testing location endpoint...")
    response = requests.get(f"{API_URL}/location")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_chat(message, location=None, auto_detect=True):
    print(f"Testing chat with message: '{message}'")

    payload = {"message": message}

    if location:
        payload["location"] = location

    if not auto_detect:
        payload["auto_detect_location"] = False

    response = requests.post(f"{API_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"Response: {data['response']}")
        print(f"Agent: {data.get('agent_used', 'N/A')}")
        if data.get('location'):
            print(f"Location: {data['location']}")
    else:
        print(f"Error: {response.text}")
    print()


def main():
    print("RefugeeReach API Client Demo")
    print("=" * 80)
    print()

    test_health()
    test_location()

    test_chat("Hello, what can you help me with?")

    test_chat(
        "Help! 3 people are injured and bleeding",
        location=(33.8938, 35.5018)
    )

    test_chat("Where can I find a hospital nearby?")

    test_chat("I need food and water")


if __name__ == "__main__":
    main()
