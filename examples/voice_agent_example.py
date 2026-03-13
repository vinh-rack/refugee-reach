import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.voice_agent import run_voice_assistant


async def main():
    """
    Example: Running the RefugeeReach Voice Assistant.

    This demonstrates real-time bidirectional voice streaming with Nova Sonic.
    The assistant can:
    - Detect emergencies and trigger SOS alerts
    - Find nearby aid resources (hospitals, shelters, food)
    - Answer general questions
    - Support multilingual conversations

    Requirements:
    - NOVA_API_KEY from nova.amazon.com
    - NOVA_VOICE_AGENT_ID (optional, for pre-configured agent)
    - Microphone and speakers available
    - websockets and pyaudio installed

    Usage:
    1. Speak naturally into your microphone
    2. The assistant will respond via audio
    3. Press Ctrl+C to stop
    """

    print("=" * 60)
    print("RefugeeReach Voice Assistant Example")
    print("=" * 60)
    print()
    print("This example demonstrates bidirectional voice streaming")
    print("with Amazon Nova Sonic for crisis assistance.")
    print()
    print("Available commands:")
    print("- Ask for help: 'I need to find a hospital'")
    print("- Emergency: 'I'm injured and need help'")
    print("- General: 'What should I do if I cross the border?'")
    print()
    print("Starting voice assistant...")
    print("-" * 60)

    await run_voice_assistant()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nVoice assistant stopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nMake sure:")
        print("1. NOVA_API_KEY is set in .env")
        print("2. NOVA_VOICE_AGENT_ID is set (optional)")
        print("3. websockets and pyaudio are installed")
        print("4. Microphone and speakers are available")
