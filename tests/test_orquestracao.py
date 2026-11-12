"""Regras de decisão dos DAGs (orquestracao/dags/foota/), sem Airflow."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


DAGS = Path(__file__).resolve().parent.parent / "orquestracao" / "dags"
sys.path.insert(0, str(DAGS))

from foota import alerta, replay, saude  # noqa: E402


AGORA = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
JANELA = timedelta(minutes=30)


# --- replay -----------------------------------------------------------------


def test_argumentos_do_replay_apontam_o_arquivo_da_competicao():
    assert replay.argumentos_replay("PL", 2026, "10-11", 0.5) == [
        "python",
        "producer.py",
        "replay",
        "--arquivo",
        "gs://foota-toota-505511/bronze/football_data_org/"
        "competition=PL/matches.jsonl",
        "--temporada",
        "2026",
        "--rodadas",
        "10-11",
        "--intervalo",
        "0.5",
    ]


def test_rodadas_validas_saem_sem_espacos():
    assert replay.validar_rodadas(" 28-30,32 ") == "28-30,32"


@pytest.mark.parametrize("texto", ["31;rm", "", "a-b", "31-", "-3", "1,,2"])
def test_rodadas_malformadas_sao_recusadas(texto):
    with pytest.raises(ValueError, match="rodadas"):
        replay.validar_rodadas(texto)


def test_competicao_desconhecida_e_recusada():
    with pytest.raises(ValueError, match="XYZ"):
        replay.consulta_primeira_test("XYZ")
    with pytest.raises(ValueError, match="XYZ"):
        replay.argumentos_replay("XYZ", 2026, "1", 0.5)


def test_consulta_da_primeira_temporada_de_test():
    sql = replay.consulta_primeira_test("BSA")
    assert "`pdm-bia-505511.gold.match_training_brasileirao`" in sql
    assert "split_set = 'TEST'" in sql


def test_temporada_de_treino_e_recusada():
    with pytest.raises(ValueError, match="TEST começa em 2025"):
        replay.checar_fora_da_amostra("BSA", 2024, 2025)
    replay.checar_fora_da_amostra("BSA", 2025, 2025)
    replay.checar_fora_da_amostra("BSA", 2026, 2025)


def test_sem_test_recusa():
    with pytest.raises(ValueError, match="sem TEST"):
        replay.checar_fora_da_amostra("PL", 2026, None)


def test_overrides_no_formato_do_cloud_run():
    assert replay.overrides(["a", "b"]) == {
        "container_overrides": [{"args": ["a", "b"]}]
    }


# --- saúde ------------------------------------------------------------------


def test_api_lenta_mas_ok_nao_e_problema():
    corpo = {
        "ligas": {"BSA": {"motivo": None}, "PL": {"motivo": "sem_campeao"}}
    }
    assert saude.problema_api(200, corpo) is None


def test_api_fora_ou_vazia_e_problema():
    assert saude.problema_api(503, None) == "/health respondeu 503"
    assert saude.problema_api(200, {"ligas": {}}) == (
        "a API não carregou nenhuma liga"
    )
    assert saude.problema_api(200, None) == "a API não carregou nenhuma liga"


def _execucao(nome, minutos_atras, falhou, job="foota-toota-coletor"):
    fim = AGORA - timedelta(minutes=minutos_atras)
    return {"job": job, "nome": nome, "fim": fim, "falhou": falhou}


def test_falha_recente_conta_mesmo_com_sucesso_depois():
    execucoes = [_execucao("c-1", 10, True), _execucao("c-2", 5, False)]
    assert saude.falhas_de_execucao(execucoes, AGORA, JANELA) == [
        "foota-toota-coletor: execução c-1 falhou às 14:50 UTC"
    ]


def test_falha_fora_da_janela_nao_conta():
    execucoes = [_execucao("c-1", 31, True), _execucao("c-2", 5, False)]
    assert saude.falhas_de_execucao(execucoes, AGORA, JANELA) == []


def test_execucao_em_andamento_nao_conta():
    execucoes = [{"job": "j", "nome": "c-3", "fim": None, "falhou": False}]
    assert saude.falhas_de_execucao(execucoes, AGORA, JANELA) == []


def _job(estado, horas_inicio, horas_fim=None):
    fim = None if horas_fim is None else AGORA - timedelta(hours=horas_fim)
    return {
        "estado": estado,
        "inicio": AGORA - timedelta(hours=horas_inicio),
        "fim": fim,
    }


def test_dataflow_drenado_nao_e_problema():
    jobs = [_job("JOB_STATE_DRAINED", 3, 2)]
    assert saude.estado_dataflow(jobs, AGORA, JANELA) == (None, None)
    assert saude.estado_dataflow([], AGORA, JANELA) == (None, None)


def test_dataflow_rodando_devolve_o_inicio():
    jobs = [_job("JOB_STATE_DRAINED", 30, 29), _job("JOB_STATE_RUNNING", 1)]
    inicio = AGORA - timedelta(hours=1)
    assert saude.estado_dataflow(jobs, AGORA, JANELA) == (inicio, None)


def test_dataflow_que_falhou_agora_e_problema():
    jobs = [_job("JOB_STATE_RUNNING", 5), _job("JOB_STATE_FAILED", 1, 0.1)]
    inicio, problema = saude.estado_dataflow(jobs, AGORA, JANELA)
    assert inicio is None
    assert problema == "o job do Dataflow falhou às 14:54 UTC"


def test_dataflow_que_falhou_ha_tempo_nao_e_problema():
    jobs = [_job("JOB_STATE_FAILED", 5, 4)]
    assert saude.estado_dataflow(jobs, AGORA, JANELA) == (None, None)


def test_atraso_so_com_pendentes():
    assert saude.problema_atraso(0, None, 10) is None
    assert saude.problema_atraso(3, AGORA, 10) == (
        "3 eventos de jogo agendado sem predição há mais de 10 min "
        "(o mais antigo publicado às 15:00 UTC)"
    )


def test_consulta_de_atraso_usa_o_projeto():
    sql = saude.consulta_atraso()
    assert "PROJECT" not in sql
    assert "`pdm-bia-505511.stream.eventos_brutos`" in sql
    assert "@desde" in sql
    assert "@limite_min" in sql


# --- alerta -----------------------------------------------------------------


def test_entrada_do_alerta():
    entrada = alerta.entrada_alerta("saude", "api_modelo", "r1", 2, "boom")
    assert entrada == {
        "dag_id": "saude",
        "task_id": "api_modelo",
        "run_id": "r1",
        "tentativa": 2,
        "erro": "boom",
        "mensagem": "saude.api_modelo falhou: boom",
    }
