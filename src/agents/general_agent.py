from strands import Agent

from src.agents.nova_client import get_general_model


def create_general_chat_agent(model=None) -> Agent:
    """Create and configure the General Chat agent."""

    if model is None:
        model = get_general_model()

    agent = Agent(model=model)

    return agent
