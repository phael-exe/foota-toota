import sys

from pitchside.errors import PitchsideError

from . import AppConfig, configure_logging, create_client, load_settings


def main() -> int:
    configure_logging(AppConfig())

    settings = load_settings()
    print(settings.explain())

    try:
        with create_client(settings) as client:
            account = client.platform.me()
            health = client.platform.health()
    except PitchsideError as error:
        print(f"\nFalha ao contatar a API: {error}", file=sys.stderr)
        return 1

    limits = account.limits
    quota = (
        f"{limits.per_minute}/min, {limits.per_day}/dia"
        if limits
        else "sem limites declarados"
    )
    print(f"\nConta   plano {account.plan}, {quota}")
    print(f"Serviço {health.status}, no ar há {health.uptime_seconds}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
