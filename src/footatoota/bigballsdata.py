from pitchside import AsyncPitchside, Pitchside, Settings

from .config import CONFIG_FILE, ENV_FILE


def load_settings() -> Settings:
    return Settings.load(
        path=CONFIG_FILE if CONFIG_FILE.is_file() else None,
        dotenv=ENV_FILE if ENV_FILE.is_file() else None,
    )


def create_client(settings: Settings | None = None) -> Pitchside:
    return (settings or load_settings()).build()


def create_async_client(settings: Settings | None = None) -> AsyncPitchside:
    return AsyncPitchside(**(settings or load_settings()).client_kwargs())
