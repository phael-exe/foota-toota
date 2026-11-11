"""SQL do stream: as colunas que o pipeline grava existem nas tabelas."""

import importlib.util
import re
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql" / "10_stream"

_spec = importlib.util.spec_from_file_location(
    "pipeline_sql", RAIZ / "streaming" / "pipeline.py"
)
assert _spec is not None and _spec.loader is not None
pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pipeline)


def colunas(arquivo: str) -> set[str]:
    texto = (SQL / arquivo).read_text()
    return set(
        re.findall(
            r"^\s+(\w+)\s+(?:STRING|INT64|FLOAT64|TIMESTAMP)", texto, re.M
        )
    )


def test_partidas_tem_as_colunas_de_predicao():
    assert set(pipeline.COLUNAS_PREDICAO) <= colunas(
        "03_create_table_partidas.sql"
    )


def test_alter_acrescenta_as_mesmas_colunas():
    texto = (SQL / "03a_alter_table_partidas_predicao.sql").read_text()
    achadas = set(re.findall(r"ADD COLUMN IF NOT EXISTS (\w+)", texto))
    assert achadas == set(pipeline.COLUNAS_PREDICAO)


def test_falhas_tem_as_colunas_que_o_pipeline_grava():
    linha = pipeline.falha(
        {"event_id": "e", "match_id": "m", "league_id": "l"}, 409, "x", 1, "t"
    )
    assert set(linha) == colunas("09_create_table_predicoes_falhas.sql")


def test_views_criadas_depois_do_que_leem():
    nomes = sorted(p.name for p in SQL.glob("*.sql"))
    alter = nomes.index("03a_alter_table_partidas_predicao.sql")
    predicoes = nomes.index("10_create_view_predicoes.sql")
    avaliadas = nomes.index("11_create_view_predicoes_avaliadas.sql")
    assert alter < predicoes < avaliadas
    assert "08_create_view_predicoes_avaliadas.sql" not in nomes
    texto = (SQL / "10_create_view_predicoes.sql").read_text()
    assert "prevista_antes_do_jogo" in texto
    assert "features_antes_do_jogo" in texto
    avaliadas_sql = (SQL / "11_create_view_predicoes_avaliadas.sql").read_text()
    assert "gold.predicoes`" in avaliadas_sql


def test_run_sh_cria_a_tabela_antes_do_alter_em_qualquer_locale(tmp_path):
    import os
    import subprocess

    bq = tmp_path / "bq"
    bq.write_text("#!/bin/sh\ncat >/dev/null\n")
    bq.chmod(0o755)
    env = {
        **os.environ,
        "LANG": "en_US.UTF-8",
        "LC_ALL": "",
        "GCP_PROJECT_ID": "p",
        "GCS_BUCKET": "b",
        "BQ_BIN": str(bq),
    }
    saida = subprocess.run(
        [str(RAIZ / "sql" / "run.sh"), str(SQL)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    ordem = [
        linha[4:] for linha in saida.splitlines() if linha.startswith("=== ")
    ]
    criar = next(
        i for i, n in enumerate(ordem) if "03_create_table_partidas" in n
    )
    alterar = next(i for i, n in enumerate(ordem) if "03a_alter" in n)
    assert criar < alterar
