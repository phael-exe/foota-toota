"""Integridade dos DAGs: roda dentro da imagem do Airflow (testar_dags.sh)."""

from __future__ import annotations

from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import DagBag


DAGS = Path(__file__).resolve().parent.parent / "dags"
ESPERADOS = {
    "coleta_ao_vivo",
    "coleta_noticias",
    "disparar_eventos",
    "saude",
    "dataflow_liga_desliga",
}


@pytest.fixture(scope="module")
def bag() -> DagBag:
    return DagBag(dag_folder=str(DAGS))


def test_dags_carregam_sem_erro(bag):
    assert bag.import_errors == {}
    assert set(bag.dag_ids) == ESPERADOS


def test_todo_dag_alerta_na_falha(bag):
    for dag in bag.dags.values():
        for t in dag.tasks:
            assert t.on_failure_callback, f"{dag.dag_id}.{t.task_id}"


def test_saude_checa_o_atraso_depois_do_dataflow(bag):
    dag = bag.dags["saude"]
    assert dag.get_task("atraso_predicao").upstream_task_ids == {"dataflow"}


def test_nenhum_dag_recupera_execucoes_passadas(bag):
    for dag in bag.dags.values():
        assert dag.catchup is False, dag.dag_id
