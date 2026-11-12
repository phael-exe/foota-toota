"""SQL da gold: as colunas que a API do modelo devolve existem na gold."""

import re
from pathlib import Path


SQL = Path(__file__).resolve().parent.parent / "sql"


def test_gold_de_features_tem_features_ate():
    texto = (SQL / "04_gold" / "03_create_table_match_features.sql").read_text()
    assert "features_ate" in re.findall(r"\bAS (\w+)", texto)


def test_regra_g9_confere_features_ate():
    regra = (
        SQL / "05_gold_checks" / "10_assert_g9_features_ate_before_kickoff.sql"
    )
    assert "features_ate >= kickoff_utc" in regra.read_text()
