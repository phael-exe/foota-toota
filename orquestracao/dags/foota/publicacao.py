"""Publicação dos dados para a plataforma: a versão do bucket público, a que
a plataforma carregou e o aviso para o time. Sem Airflow: o DAG lê, aqui
decide."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from foota.config import MANIFESTO_URL, TABELAS_PLATAFORMA, TIMEOUT_HTTP_S


BRASILIA = ZoneInfo("America/Sao_Paulo")


def ler_manifesto() -> dict:
    """O _manifest.json público, por HTTPS, como a plataforma lê."""
    import time

    import requests

    # o parâmetro fura qualquer cache no caminho; o objeto já sai com no-cache
    resposta = requests.get(
        MANIFESTO_URL, params={"t": int(time.time())}, timeout=TIMEOUT_HTTP_S
    )
    resposta.raise_for_status()
    return resposta.json()


def versao_do_manifesto(manifesto: object) -> str:
    versao = manifesto.get("version") if isinstance(manifesto, dict) else None
    if not versao:
        raise ValueError(f"_manifest.json sem version: {manifesto!r:.200}")
    return versao


def versao_da_plataforma(corpo: object) -> str | None:
    """O /api/futebol/versao da plataforma. Na amostra congelada (o ambiente
    local dela) a versão não é a do bucket, então não conta."""
    if not isinstance(corpo, dict) or corpo.get("amostra"):
        return None
    return corpo.get("versao") or None


def problema_exportacao(
    exportada_em: datetime, agora: datetime, maximo: timedelta
) -> str | None:
    idade = agora - exportada_em
    if idade <= maximo:
        return None
    return (
        f"o bucket público não é exportado há {idade.days} dias "
        f"(última exportação em {exportada_em.astimezone(BRASILIA):%d/%m %H:%M}"
        " de Brasília): a plataforma está mostrando dados velhos"
    )


def _linhas(manifesto: dict | None) -> dict[str, int]:
    """Linhas por tabela que a plataforma lê, do Parquet (o CSV repete)."""
    linhas = {}
    for arquivo in (manifesto or {}).get("files", []):
        tabela, _, ext = arquivo["path"].rpartition(".")
        if ext == "parquet" and tabela in TABELAS_PLATAFORMA:
            linhas[tabela] = arquivo.get("rows")
    return linhas


def _num(n: int | None) -> str:
    return "?" if n is None else f"{n:,}".replace(",", ".")


def resumo_aviso(antigo: dict | None, novo: dict, url_plataforma: str) -> str:
    exportada = datetime.fromisoformat(novo["exported_at"]).astimezone(BRASILIA)
    antes, depois = _linhas(antigo), _linhas(novo)
    mudancas = []
    for tabela in TABELAS_PLATAFORMA:
        if tabela not in depois or antes.get(tabela) == depois[tabela]:
            continue
        if tabela not in antes:
            mudancas.append(f"- {tabela}: {_num(depois[tabela])}")
            continue
        delta = (depois[tabela] or 0) - (antes[tabela] or 0)
        mudancas.append(
            f"- {tabela}: {_num(antes[tabela])} → {_num(depois[tabela])}"
            f" ({'+' if delta >= 0 else '-'}{_num(abs(delta))})"
        )
    anterior = f" desde a versão {antigo['version']}" if antigo else ""
    corpo = (
        "\n".join(mudancas) if mudancas else "- nenhuma tabela mudou de tamanho"
    )
    return (
        f"Dados de {exportada:%d/%m/%Y %H:%M} (Brasília) no ar na plataforma "
        f"(versão {novo['version']}).\n"
        f"O que mudou{anterior}:\n{corpo}\n"
        f"{url_plataforma}"
    )
