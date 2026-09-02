import httpx
import pytest
import respx
from pitchside import AsyncPitchside, FileCache, Pitchside, Settings

from footatoota import create_async_client, create_client, load_settings


SPORTS_BODY = {
    "data": [{"slug": "football", "name": "Soccer", "aliases": ["soccer"]}],
    "meta": {"source": "catalogue", "cached": False, "request_id": "req_test"},
    "error": None,
}


def test_settings_come_from_the_config_file(settings):
    assert settings.base_url == "https://api.bigballsdata.com"
    assert settings.max_retries == 3
    assert settings.timeout.connect == 10.0
    assert settings.timeout.read == 60.0
    assert settings.cache.backend == "disk"
    assert settings.cache.max_entries == 512


def test_load_settings_finds_the_project_files():
    assert load_settings().base_url == "https://api.bigballsdata.com"


def test_disk_cache_is_built_from_the_file(settings):
    assert isinstance(settings.cache.build(), FileCache)


def test_factories_return_both_flavours(settings):
    with create_client(settings) as sync_client:
        assert isinstance(sync_client, Pitchside)

    assert isinstance(create_async_client(settings), AsyncPitchside)


@respx.mock
def test_request_carries_the_key_and_the_configured_timeouts(api_settings):
    route = respx.get("https://api.bigballsdata.com/v1/sports").mock(
        return_value=httpx.Response(200, json=SPORTS_BODY)
    )

    with create_client(api_settings) as client:
        sports = client.sports.list()
        timeout = client._http.timeout

    assert route.called
    assert (
        route.calls.last.request.headers["authorization"]
        == "Bearer bbs_live_test"
    )
    assert [sport.slug for sport in sports] == ["football"]
    assert (timeout.connect, timeout.read) == (10.0, 60.0)


@respx.mock
def test_a_custom_base_url_is_honoured():
    settings = Settings.load(
        path=False,
        use_env=False,
        api_key="bbs_live_test",
        base_url="https://mock.local",
    )
    route = respx.get("https://mock.local/v1/sports").mock(
        return_value=httpx.Response(200, json=SPORTS_BODY)
    )

    with create_client(settings) as client:
        client.sports.list()

    assert route.called


@pytest.mark.asyncio
async def test_async_factory_shares_the_settings(settings):
    client = create_async_client(settings)

    assert client.base_url == "https://api.bigballsdata.com"
    await client.aclose()


@respx.mock
def test_the_cache_spares_the_second_request(cached_settings):
    route = respx.get("https://api.bigballsdata.com/v1/sports").mock(
        return_value=httpx.Response(200, json=SPORTS_BODY)
    )

    with create_client(cached_settings) as client:
        client.sports.list()
        client.sports.list()

    assert route.call_count == 1
