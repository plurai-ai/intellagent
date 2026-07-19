import pytest

FAKE_LLM_ENV = {
    'openai': {'OPENAI_API_KEY': '', 'OPENAI_ORGANIZATION': '', 'OPENAI_API_BASE': ''},
    'azure': {'AZURE_OPENAI_API_KEY': '', 'AZURE_OPENAI_ENDPOINT': '', 'OPENAI_API_VERSION': ''},
    'google': {'GOOGLE_API_KEY': ''},
    'anthropic_vertex': {'PROJECT_ID': '', 'REGION': ''},
    'anthropic': {'ANTHROPIC_KEY': ''},
    'oracle': {'SERVICE_ENDPOINT': '', 'COMPARTMENT_ID': ''},
    'ollama': {'HOST': 'http://localhost:11434'},
    'groq': {'GROQ_API_KEY': 'test-key-from-env'},
}

@pytest.fixture(autouse=True)
def patch_llm_env(monkeypatch):
    import simulator.utils.llm_utils as lu
    monkeypatch.setattr(lu, 'LLM_ENV', FAKE_LLM_ENV)


def test_groq_returns_chatgroq():
    from simulator.utils.llm_utils import get_llm
    from langchain_groq import ChatGroq

    config = {'type': 'groq', 'name': 'llama-3.3-70b-versatile'}
    llm = get_llm(config)

    assert isinstance(llm, ChatGroq)


def test_groq_uses_env_api_key():
    from simulator.utils.llm_utils import get_llm
    from langchain_groq import ChatGroq

    config = {'type': 'groq', 'name': 'llama-3.3-70b-versatile'}
    llm = get_llm(config)

    assert isinstance(llm, ChatGroq)
    assert llm.groq_api_key.get_secret_value() == 'test-key-from-env'


def test_groq_uses_config_api_key_override():
    from simulator.utils.llm_utils import get_llm
    from langchain_groq import ChatGroq

    config = {'type': 'groq', 'name': 'llama-3.1-70b-versatile', 'api_key': 'override-from-config'}
    llm = get_llm(config)

    assert isinstance(llm, ChatGroq)
    assert llm.groq_api_key.get_secret_value() == 'override-from-config'


def test_groq_case_insensitive():
    from simulator.utils.llm_utils import get_llm
    from langchain_groq import ChatGroq

    config = {'type': 'Groq', 'name': 'mixtral-8x7b-32768'}
    llm = get_llm(config)

    assert isinstance(llm, ChatGroq)


def test_llm_env_has_groq_section():
    import yaml
    with open('config/llm_env.yml') as f:
        env = yaml.safe_load(f)
    assert 'groq' in env
    assert 'GROQ_API_KEY' in env['groq']
