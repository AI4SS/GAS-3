from app.services.config import load_settings


def test_load_settings_has_model():
    settings = load_settings()
    assert settings.llm.model
    assert settings.llm.base_url
