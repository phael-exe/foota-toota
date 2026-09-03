import logging

import structlog

from footatoota import configure_logging


def test_configures_levels_from_the_configuration(config):
    configure_logging(
        config.model_copy(
            update={"log_level": "WARNING", "api_log_level": "DEBUG"}
        )
    )

    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger("pitchside").level == logging.DEBUG


def test_quiets_the_http_libraries(config):
    configure_logging(config)

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_installs_a_single_handler(config):
    configure_logging(config)
    configure_logging(config)

    assert len(logging.getLogger().handlers) == 1


def test_api_log_fields_reach_the_output(config, capsys):
    configure_logging(
        config.model_copy(
            update={"log_level": "DEBUG", "api_log_level": "DEBUG"}
        )
    )

    logging.getLogger("pitchside._transport").debug(
        "<-- GET /v1/sports 200",
        extra={
            "method": "GET",
            "status": 200,
            "request_id": "req_test",
            "elapsed_ms": 12,
        },
    )

    err = capsys.readouterr().err
    assert "request_id" in err
    assert "req_test" in err
    assert "elapsed_ms" in err


def test_json_logs_render_as_json(config, capsys):
    configure_logging(
        config.model_copy(update={"json_logs": True, "log_level": "INFO"})
    )
    structlog.get_logger("footatoota").info("ingest.started", league="epl")

    assert '"league": "epl"' in capsys.readouterr().err
