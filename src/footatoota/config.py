from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


CONFIG_FILE = Path("config/bigballsdata.toml")
ENV_FILE = Path(".env")

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


class AppConfig(BaseSettings):
    log_level: LogLevel = "INFO"
    api_log_level: LogLevel = "INFO"
    json_logs: bool = False

    default_sport: str = "football"
    default_page_size: int = Field(default=200, ge=1, le=200)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_prefix="FOOTATOOTA_",
        toml_file=CONFIG_FILE,
        toml_table_header=("footatoota",),
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
