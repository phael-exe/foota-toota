import pytest
from pydantic import ValidationError

from footatoota import AppConfig


def test_reads_the_footatoota_table():
    config = AppConfig(_env_file=None)

    assert config.log_level == "INFO"
    assert config.api_log_level == "INFO"
    assert config.json_logs is False
    assert config.default_sport == "football"
    assert config.default_page_size == 200


def test_environment_overrides_the_file(monkeypatch):
    monkeypatch.setenv("FOOTATOOTA_LOG_LEVEL", "DEBUG")

    assert AppConfig(_env_file=None).log_level == "DEBUG"


def test_arguments_override_everything(monkeypatch):
    monkeypatch.setenv("FOOTATOOTA_LOG_LEVEL", "DEBUG")

    assert AppConfig(_env_file=None, log_level="ERROR").log_level == "ERROR"


def test_holds_no_credentials():
    assert "api_key" not in AppConfig.model_fields


@pytest.mark.parametrize(
    "overrides",
    [
        {"log_level": "LOUD"},
        {"api_log_level": "LOUD"},
        {"default_page_size": 0},
        {"default_page_size": 201},
    ],
)
def test_rejects_invalid_values(overrides):
    with pytest.raises(ValidationError):
        AppConfig(_env_file=None, **overrides)
