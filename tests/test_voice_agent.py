import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.voice_agent import (_voice_agent, create_voice_agent,
                                    get_voice_agent, get_voice_model,
                                    run_voice_assistant)


@pytest.fixture
def mock_boto_session():
    """Mock boto3 session."""
    with patch('boto3.Session') as mock_session:
        mock_instance = MagicMock()
        mock_session.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_bidi_nova_sonic_model():
    """Mock BidiNovaSonicModel."""
    with patch('src.agents.voice_agent.BidiNovaSonicModel') as mock_model:
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_bidi_agent():
    """Mock BidiAgent."""
    with patch('src.agents.voice_agent.BidiAgent') as mock_agent:
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock()
        mock_instance.stop = AsyncMock()
        mock_agent.return_value = mock_instance
        yield mock_instance


def test_get_voice_model_initialization(mock_boto_session, mock_bidi_nova_sonic_model):
    """Test voice model initialization with correct configuration."""
    os.environ['AWS_REGION'] = 'us-east-1'

    model = get_voice_model()

    assert model is not None


def test_create_voice_agent(mock_bidi_nova_sonic_model, mock_bidi_agent):
    """Test voice agent creation with proper configuration."""
    mock_model = MagicMock()

    agent = create_voice_agent(model=mock_model)

    assert agent is not None


def test_get_voice_agent_lazy_initialization(mock_boto_session, mock_bidi_nova_sonic_model, mock_bidi_agent):
    """Test lazy initialization of voice agent."""

    agent1 = get_voice_agent()
    agent2 = get_voice_agent()

    assert agent1 is agent2


@pytest.mark.asyncio
async def test_run_voice_assistant(mock_boto_session, mock_bidi_nova_sonic_model, mock_bidi_agent):
    """Test running voice assistant with audio I/O."""
    with patch('src.agents.voice_agent.BidiAudioIO') as mock_audio_io, \
         patch('src.agents.voice_agent.BidiTextIO') as mock_text_io, \
         patch('src.agents.voice_agent.get_voice_agent') as mock_get_agent:

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock()
        mock_agent_instance.stop = AsyncMock()
        mock_get_agent.return_value = mock_agent_instance

        mock_audio_instance = MagicMock()
        mock_audio_instance.input = MagicMock()
        mock_audio_instance.output = MagicMock()
        mock_audio_io.return_value = mock_audio_instance

        mock_text_instance = MagicMock()
        mock_text_instance.output = MagicMock()
        mock_text_io.return_value = mock_text_instance


        await run_voice_assistant()

        mock_agent_instance.run.assert_called_once()
        mock_agent_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_voice_agent_tools_configuration(mock_bidi_nova_sonic_model):
    """Test that voice agent has correct tools configured."""
    with patch('src.agents.voice_agent.BidiAgent') as mock_agent_class:
        mock_model = MagicMock()

        create_voice_agent(model=mock_model)

        call_kwargs = mock_agent_class.call_args[1]
        tools = call_kwargs['tools']

        assert len(tools) >= 5
        assert call_kwargs['system_prompt'] is not None
        assert call_kwargs['agent_id'] == "refugee_reach_voice"
        assert call_kwargs['name'] == "RefugeeReach Voice Assistant"


def test_voice_model_configuration(mock_boto_session):
    """Test voice model has correct Nova Sonic configuration."""
    with patch('src.agents.voice_agent.BidiNovaSonicModel') as mock_model_class:
        os.environ['AWS_REGION'] = 'us-east-1'

        get_voice_model()

        call_kwargs = mock_model_class.call_args[1]

        assert call_kwargs['model_id'] == "amazon.nova-sonic-v1:0"
        assert 'audio' in call_kwargs['provider_config']
        assert call_kwargs['provider_config']['audio']['voice'] == "matthew"
        assert call_kwargs['provider_config']['audio']['input_rate'] == 16000
        assert call_kwargs['provider_config']['audio']['output_rate'] == 16000
        assert 'inference' in call_kwargs['provider_config']
        assert call_kwargs['client_config']['region'] == 'us-east-1'
