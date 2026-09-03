import pytest
from pitchside import Settings

from footatoota import AppConfig


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(_env_file=None)


@pytest.fixture
def settings() -> Settings:
    return Settings.load(
        path="config/bigballsdata.toml",
        use_env=False,
        api_key="bbs_live_test",
    )


@pytest.fixture
def api_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={"cache": settings.cache.model_copy(update={"backend": "none"})}
    )


@pytest.fixture
def cached_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "cache": settings.cache.model_copy(update={"backend": "memory"})
        }
    )
