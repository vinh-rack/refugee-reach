import os

from strands_amazon_nova import NovaAPIModel

_orchestrator_model = None
_sos_model = None
_general_model = None
_voice_model = None


def get_orchestrator_model():
    """Get Nova orchestrator agent model (lazy initialization)."""
    global _orchestrator_model

    if _orchestrator_model is None:
        api_key = os.getenv("NOVA_API_KEY")
        if not api_key:
            raise ValueError(
                "NOVA_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )

        _orchestrator_model = NovaAPIModel(
            api_key=api_key,
            model_id=os.getenv("NOVA_ORCHESTRATOR_AGENT_ID", "AGENT-bb3df26469be4bfa8e53095d8b84c5c0"),
            params={
                "max_tokens": 2000,
                "temperature": 0.3,
            }
        )

    return _orchestrator_model


def get_sos_model():
    """Get Nova SOS agent model (lazy initialization)."""
    global _sos_model

    if _sos_model is None:
        api_key = os.getenv("NOVA_API_KEY")
        if not api_key:
            raise ValueError(
                "NOVA_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )

        _sos_model = NovaAPIModel(
            api_key=api_key,
            model_id=os.getenv("NOVA_SOS_AGENT_ID", "AGENT-3037eeb067a94302991f90918364b42d"),
            params={
                "max_tokens": 1500,
                "temperature": 0.2,
            }
        )

    return _sos_model


def get_general_model():
    """Get Nova general chat agent model (lazy initialization)."""
    global _general_model

    if _general_model is None:
        api_key = os.getenv("NOVA_API_KEY")
        if not api_key:
            raise ValueError(
                "NOVA_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )

        _general_model = NovaAPIModel(
            api_key=api_key,
            model_id=os.getenv("NOVA_GENERAL_AGENT_ID", "AGENT-62e5c56e06ec43949222e212eead0870"),
            params={
                "max_tokens": 1000,
                "temperature": 0.7,
            }
        )

    return _general_model


def get_voice_model():
    """Get Nova voice agent model (lazy initialization)."""
    global _voice_model

    if _voice_model is None:
        api_key = os.getenv("NOVA_API_KEY")
        if not api_key:
            raise ValueError(
                "NOVA_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )

        _voice_model = NovaAPIModel(
            api_key=api_key,
            model_id=os.getenv("NOVA_VOICE_AGENT_ID", "AGENT-77337257c7ea4017b700cad9949614f9"),
            params={
                "max_tokens": 1000,
                "temperature": 0.5,
            }
        )

    return _voice_model
