"""Ramo de predição do pipeline, com o Beam (roda no venv do streaming:
streaming/.venv/bin/python -m pytest tests/test_streaming_beam.py)."""

import pytest


beam = pytest.importorskip("apache_beam")

from apache_beam.testing.test_pipeline import TestPipeline  # noqa: E402
from apache_beam.testing.util import assert_that, equal_to  # noqa: E402

from test_streaming import (  # noqa: E402
    item,
    linha_agendada,
    pipeline,
    predicao_api,
)


def enviar_de(_url):
    def enviar(pedidos):
        return 200, {
            "resultados": [
                item(200, p["event_id"], predicao_api(p["event_id"]))
                if p["event_id"] == "e1"
                else item(409, p["event_id"], motivo="sem_campeao")
                for p in pedidos
            ]
        }

    return enviar


def test_ramo_preve_agendadas_e_deixa_as_outras_passarem():
    linhas = [
        linha_agendada(event_id="e1"),
        linha_agendada(event_id="e2"),
        linha_agendada(event_id="e3", status="finished"),
    ]
    with TestPipeline() as p:
        partidas, falhas = pipeline.ramo_predicao(
            p | beam.Create(linhas), "https://api", enviar_de
        )
        assert_that(
            partidas
            | "ids" >> beam.Map(lambda x: (x["event_id"], x["prediction_id"])),
            equal_to([("e1", "p-e1"), ("e2", None), ("e3", None)]),
            label="partidas",
        )
        assert_that(
            falhas
            | "motivos" >> beam.Map(lambda f: (f["event_id"], f["motivo"])),
            equal_to([("e2", "sem_campeao")]),
            label="falhas",
        )


def test_sem_url_nao_chama_a_api():
    linhas = [linha_agendada(event_id="e1")]
    with TestPipeline() as p:
        partidas, falhas = pipeline.ramo_predicao(p | beam.Create(linhas), "")
        assert_that(
            partidas | "ids" >> beam.Map(lambda x: x["event_id"]),
            equal_to(["e1"]),
            label="partidas",
        )
        assert_that(falhas, equal_to([]), label="falhas")
