import httpx
import respx
from pitchside import Settings

from footatoota.__main__ import main


HEALTH_BODY = {
    "status": "ok",
    "sha": "abc123",
    "deployed_at": "2026-09-02T00:00:00.000Z",
    "uptime_seconds": 120,
}

ME_BODY = {
    "data": {
        "key_id": "...test",
        "plan": "free",
        "github_connected": False,
        "paused": False,
        "limits": {"per_minute": 100, "per_day": 1000},
    },
    "meta": {"request_id": "req_test"},
    "error": None,
}


@respx.mock
def test_reports_account_and_health(monkeypatch, capsys):
    monkeypatch.setattr(
        "footatoota.__main__.load_settings",
        lambda: Settings.load(path=False, use_env=False, api_key="bbs_test"),
    )
    respx.get("https://api.bigballsdata.com/v1/user/me").mock(
        return_value=httpx.Response(200, json=ME_BODY)
    )
    respx.get("https://api.bigballsdata.com/v1/health").mock(
        return_value=httpx.Response(200, json=HEALTH_BODY)
    )

    assert main() == 0

    out = capsys.readouterr().out
    assert "plano free" in out
    assert "1000/dia" in out


@respx.mock
def test_reports_a_failure_without_raising(monkeypatch, capsys):
    monkeypatch.setattr(
        "footatoota.__main__.load_settings",
        lambda: Settings.load(path=False, use_env=False, api_key="bbs_test"),
    )
    respx.get("https://api.bigballsdata.com/v1/user/me").mock(
        return_value=httpx.Response(
            401, json={"error": {"code": "unauthorized", "message": "no"}}
        )
    )

    assert main() == 1
    assert "Falha ao contatar a API" in capsys.readouterr().err
