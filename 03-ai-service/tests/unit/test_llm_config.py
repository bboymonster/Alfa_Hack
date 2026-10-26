import pytest
from pydantic import ValidationError

from ai_service.config import ALLOWED_LLM_MODELS, Settings
from ai_service.llm.provider import build_model_slots


def test_no_key_never_builds_online_models() -> None:
    settings = Settings(llm_api_key="", _env_file=None)
    assert build_model_slots(settings) is None


@pytest.mark.parametrize("model", sorted(ALLOWED_LLM_MODELS))
def test_organizer_models_can_be_selected(model: str) -> None:
    settings = Settings(llm_api_key="", llm_model_main=model, _env_file=None)
    assert settings.llm_model_main == model


@pytest.mark.parametrize("slot", ["llm_model_main", "llm_model_fast", "llm_model_checker"])
def test_unapproved_model_is_rejected_before_any_request(slot: str) -> None:
    with pytest.raises(ValidationError, match="Приложения 3"):
        Settings(**{slot: "unapproved/model"}, _env_file=None)


def test_key_hidden_and_reasoning_disabled_in_provider() -> None:
    settings = Settings(llm_api_key="test-secret-value", _env_file=None)
    assert "test-secret-value" not in repr(settings)
    slots = build_model_slots(settings)
    assert slots is not None
    assert slots.main.extra_body == {"reasoning": {"enabled": False}}
    assert slots.checker.extra_body == {"reasoning": {"enabled": False}}
    assert slots.fast.extra_body is None
