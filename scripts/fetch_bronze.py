#!/usr/bin/env python3
"""fetch_bronze.py - Coleta multi-liga para a camada Bronze do Foota Toota.

Fontes e Ligas Cobertas:
1. Football-Data.co.uk:
   - 10 ligas (Premier League, Championship, La Liga, Serie A, Bundesliga,
     Ligue 1, Eredivisie, Primeira Liga, Bélgica, Escócia)
   - Temporadas: 2022-2023 até a atual (2026-2027) com dados de partidas,
     estatísticas e odds.
   - Cada CSV é regravado com as colunas de bronze.ext_football_data_uk,
     escolhidas pelo nome do cabeçalho: o BigQuery lê CSV pela posição e os
     arquivos mudam por liga e temporada (Referee só nas ligas britânicas,
     HxG/AxG desde 2026-2027).
   - Brasileirão Série A (new/BRA.csv): 2012 até a atualidade, com odds de
     fechamento.
2. Brasileirão Dataset (adaoduque):
   - Histórico completo de 2003 até a atualidade (>8.700 partidas com placar,
     técnicos, formação, arena).
3. Football-Data.org API (Tier One Free):
   - Premier League (PL), Brasileirão (BSA), La Liga (PD), Bundesliga (BL1),
     Serie A (SA), Ligue 1 (FL1), Champions League (CL), Championship (ELC).
   - Rate limit controlado com intervalo de segurança (10 req/min).
4. Feeds RSS de Notícias:
   - Trivela (pt-BR), BBC Sport (en-GB), Sky Sports (en-GB) com controle de
     novidades via GUID.

Armazena em data/bronze/ e envia para gs://{GCS_BUCKET}/bronze/.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "bronze"
CHECKPOINT_FILE = DATA_DIR / "_checkpoints" / "state.json"

# Colunas de bronze.ext_football_data_uk, na ordem da tabela externa
FOOTBALL_DATA_UK_COLUMNS = [
    "Div",
    "Date",
    "Time",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "Referee",
    "HS",
    "AS",
    "HST",
    "AST",
    "HF",
    "AF",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
    "B365H",
    "B365D",
    "B365A",
]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with env_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    for k, v in os.environ.items():
        env.setdefault(k, v)
    return env


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with CHECKPOINT_FILE.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_run": None, "rss_seen_guids": [], "sources": {}}


def save_checkpoint(state: dict) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(UTC).isoformat()
    if len(state.get("rss_seen_guids", [])) > 2000:
        state["rss_seen_guids"] = state["rss_seen_guids"][-2000:]
    with CHECKPOINT_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def normalize_football_data_uk(content: str) -> str:
    """Regrava o CSV com FOOTBALL_DATA_UK_COLUMNS, lidas pelo nome.

    Coluna ausente no arquivo sai vazia.
    """
    out = io.StringIO()
    writer = csv.DictWriter(
        out, fieldnames=FOOTBALL_DATA_UK_COLUMNS, lineterminator="\n"
    )
    writer.writeheader()
    for row in csv.DictReader(io.StringIO(content)):
        if row.get("Div"):
            writer.writerow(
                {col: row.get(col) or "" for col in FOOTBALL_DATA_UK_COLUMNS}
            )
    return out.getvalue()


def fetch_football_data_uk(client: httpx.Client, state: dict) -> int:
    """Baixa CSVs de 10 ligas europeias, de 2022-2023 até a temporada atual."""
    print("\n=== [1/4] Coletando Football-Data.co.uk (10 Ligas Européias) ===")
    leagues = [
        ("E0", "Premier_League"),
        ("E1", "Championship"),
        ("SP1", "La_Liga"),
        ("I1", "Serie_A"),
        ("D1", "Bundesliga"),
        ("F1", "Ligue_1"),
        ("N1", "Eredivisie"),
        ("P1", "Primeira_Liga"),
        ("B1", "Belgian_Pro_League"),
        ("SC0", "Scottish_Premiership"),
    ]
    seasons = [
        ("2627", "2026-2027"),
        ("2526", "2025-2026"),
        ("2425", "2024-2025"),
        ("2324", "2023-2024"),
        ("2223", "2022-2023"),
    ]
    total_saved = 0
    headers = {"User-Agent": "Mozilla/5.0 (FootaToota MultiLeague/0.1)"}

    for s_code, s_name in seasons:
        for l_code, l_name in leagues:
            out_dir = (
                DATA_DIR
                / "football_data_uk"
                / f"season={s_name}"
                / f"league={l_name}"
            )
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "matches.csv"

            url = f"https://football-data.co.uk/mmz4281/{s_code}/{l_code}.csv"
            content = None
            for attempt in range(3):
                try:
                    resp = client.get(
                        url,
                        headers=headers,
                        follow_redirects=True,
                        timeout=60.0,
                    )
                    if resp.status_code == 200 and len(resp.text.strip()) > 0:
                        content = resp.text.lstrip("\ufeff")
                        break
                    print(f"  ✗ {l_name} ({s_name}): status {resp.status_code}")
                except Exception as e:
                    print(
                        f"  ✗ Falha ao baixar {l_name} ({s_name}), "
                        f"tentativa {attempt + 1}: {e}"
                    )
                time.sleep(5)
            if content is None and out_file.exists():
                # o arquivo de uma coleta anterior pode estar na ordem do
                # site; normalizar um arquivo já normalizado não o altera
                print(
                    f"  ↺ {l_name} ({s_name}): "
                    "mantendo o arquivo anterior, normalizado"
                )
                content = out_file.read_text(encoding="utf-8").lstrip("\ufeff")
            if content is None:
                continue
            content = normalize_football_data_uk(content)
            lines = content.strip().splitlines()
            out_file.write_text(content, encoding="utf-8")
            total_saved += len(lines) - 1
            print(f"  ✓ {l_name} ({s_name}): {len(lines) - 1} partidas")

    state.setdefault("sources", {})["football_data_uk"] = {
        "status": "success",
        "last_updated": datetime.now(UTC).isoformat(),
        "total_records": total_saved,
    }
    return total_saved


def fetch_football_data_uk_brazil(client: httpx.Client, state: dict) -> int:
    """Baixa o Brasileirão Série A do Football-Data.co.uk.

    Cobre de 2012 até hoje, com odds.
    """
    print(
        "\n=== [1b/4] Coletando Brasileirão do Football-Data.co.uk "
        "(2012-presente) ==="
    )
    out_dir = DATA_DIR / "football_data_uk_bra"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "BRA.csv"

    url = "https://www.football-data.co.uk/new/BRA.csv"
    headers = {"User-Agent": "Mozilla/5.0 (FootaToota MultiLeague/0.1)"}
    try:
        resp = client.get(
            url, headers=headers, follow_redirects=True, timeout=30.0
        )
        if resp.status_code == 200 and len(resp.text.strip()) > 0:
            content = resp.text.lstrip("﻿")
            out_file.write_text(content, encoding="utf-8")
            total_matches = len(content.strip().splitlines()) - 1
            print(
                f"  ✓ Brasileirão (Football-Data.co.uk): "
                f"{total_matches} partidas"
            )
            state.setdefault("sources", {})["football_data_uk_bra"] = {
                "status": "success",
                "last_updated": datetime.now(UTC).isoformat(),
                "total_records": total_matches,
            }
            return total_matches
        print(f"  ✗ Erro ao baixar BRA.csv: status {resp.status_code}")
    except Exception as e:
        print(f"  ✗ Falha no download do BRA.csv: {e}")
    return 0


def fetch_brasileirao_dataset(client: httpx.Client, state: dict) -> int:
    """Baixa o histórico completo do Brasileirão Série A (2003-presente)."""
    print(
        "\n=== [2/4] Coletando Histórico Completo do Brasileirão Série A "
        "(adaoduque) ==="
    )
    out_dir = DATA_DIR / "brasileirao_historico"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "campeonato_brasileiro_full.csv"

    url = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/campeonato-brasileiro-full.csv"
    headers = {"User-Agent": "Mozilla/5.0 (FootaToota/0.1)"}
    try:
        resp = client.get(
            url, headers=headers, follow_redirects=True, timeout=30.0
        )
        if resp.status_code == 200:
            content = resp.text.strip()
            out_file.write_text(content, encoding="utf-8")
            lines = content.splitlines()
            total_matches = len(lines) - 1
            print(
                f"  ✓ Brasileirão Série A (2003-2026): {total_matches} "
                f"partidas salvas em {out_file.relative_to(ROOT_DIR)}"
            )
            state.setdefault("sources", {})["brasileirao_dataset"] = {
                "status": "success",
                "last_updated": datetime.now(UTC).isoformat(),
                "total_records": total_matches,
            }
            return total_matches
        else:
            print(
                f"  ✗ Erro ao baixar Brasileirão Dataset: "
                f"status {resp.status_code}"
            )
    except Exception as e:
        print(f"  ✗ Falha no download do Brasileirão: {e}")
    return 0


def fetch_football_data_org(
    client: httpx.Client, api_key: str, state: dict
) -> int:
    """Coleta as ligas Tier One do plano free da API football-data.org."""
    print("\n=== [3/4] Coletando football-data.org API (Multi-Liga) ===")
    if not api_key:
        print("  ✗ FOOTBALLDATA_API_KEY ausente.")
        return 0

    competitions = [
        ("PL", "Premier League"),
        ("BSA", "Campeonato Brasileiro Série A"),
        ("PD", "La Liga"),
        ("BL1", "Bundesliga"),
        ("SA", "Serie A"),
        ("FL1", "Ligue 1"),
        ("DED", "Eredivisie"),
        ("PPL", "Primeira Liga"),
        ("ELC", "Championship"),
        ("CL", "UEFA Champions League"),
    ]
    headers = {"X-Auth-Token": api_key, "User-Agent": "FootaToota/0.1"}
    total_matches = 0

    for i, (code, name) in enumerate(competitions):
        out_dir = DATA_DIR / "football_data_org" / f"competition={code}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "matches.jsonl"

        url = f"https://api.football-data.org/v4/competitions/{code}/matches"
        try:
            resp = client.get(url, headers=headers, timeout=25.0)
            if resp.status_code == 200:
                payload = resp.json()
                matches = payload.get("matches", [])
                with out_file.open("w", encoding="utf-8") as f:
                    for m in matches:
                        m["_competition_code"] = code
                        m["_competition_name"] = name
                        f.write(json.dumps(m, ensure_ascii=False) + "\n")
                total_matches += len(matches)
                print(f"  ✓ {name} ({code}): {len(matches)} partidas")
            elif resp.status_code == 429:
                print(f"  ⚠ Rate limit atingido em {code}. Aguardando 15s...")
                time.sleep(15)
            else:
                print(f"  ✗ {name} ({code}): status {resp.status_code}")
        except Exception as e:
            print(f"  ✗ Erro em {code}: {e}")

        # Respeita o teto de 10 requisições por minuto (intervalo de 6.5s)
        if i < len(competitions) - 1:
            time.sleep(6.5)

    state.setdefault("sources", {})["football_data_org"] = {
        "status": "success",
        "last_updated": datetime.now(UTC).isoformat(),
        "total_records": total_matches,
    }
    return total_matches


def fetch_news_rss(client: httpx.Client, state: dict) -> int:
    """Coleta notícias de vários portais via Google News RSS e redações."""
    print(
        "\n=== [4/4] Coletando Notícias em Tempo Real "
        "(Google News + Redações) ==="
    )
    feeds = [
        (
            "gnews_futebol_br",
            "https://news.google.com/rss/search?q=futebol+brasileiro&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "pt-BR",
        ),
        (
            "gnews_brasileirao",
            "https://news.google.com/rss/search?q=brasileir%C3%A3o+s%C3%A9rie+a&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "pt-BR",
        ),
        (
            "gnews_mercado_bola",
            "https://news.google.com/rss/search?q=mercado+da+bola+transferencias&hl=pt-BR&gl=BR&ceid=BR:pt-419",
            "pt-BR",
        ),
        (
            "gnews_premier_league",
            "https://news.google.com/rss/search?q=premier+league+football&hl=en-GB&gl=GB&ceid=GB:en",
            "en-GB",
        ),
        (
            "gnews_champions_league",
            "https://news.google.com/rss/search?q=champions+league+football&hl=en-GB&gl=GB&ceid=GB:en",
            "en-GB",
        ),
        ("trivela", "https://trivela.com.br/feed/", "pt-BR"),
        (
            "bbc_sport",
            "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "en-GB",
        ),
        ("sky_sports", "https://www.skysports.com/rss/12040", "en-GB"),
    ]
    seen_guids = set(state.get("rss_seen_guids", []))
    new_articles = []
    headers = {"User-Agent": "Mozilla/5.0 (FootaToota RSS/0.1)"}
    # Coleta notícias com extração do corpo completo (full article body)
    try:
        from fetch_news import run_news_ingestion

        return run_news_ingestion(reset_seen=False)
    except Exception as e:
        print(f"  ✗ Erro ao coletar notícias: {e}")
        return 0

    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = DATA_DIR / "news_rss" / f"dt={today_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "articles.jsonl"

    for source_id, url, lang in feeds:
        try:
            resp = client.get(
                url, headers=headers, follow_redirects=True, timeout=20.0
            )
            if resp.status_code != 200:
                print(f"  ✗ {source_id}: status {resp.status_code}")
                continue

            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                continue

            items = channel.findall("item")
            count_new = 0

            for item in items:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                guid = (item.findtext("guid") or link).strip()
                pub_date_raw = (item.findtext("pubDate") or "").strip()
                desc = (item.findtext("description") or "").strip()

                # Extrai nome do portal de publicação (ex: ge, UOL, ESPN, BBC)
                source_tag = item.find("source")
                portal_name = (
                    source_tag.text.strip()
                    if source_tag is not None and source_tag.text
                    else source_id
                )

                if not guid or guid in seen_guids:
                    continue

                pub_iso = None
                if pub_date_raw:
                    try:
                        dt = parsedate_to_datetime(pub_date_raw)
                        pub_iso = dt.astimezone(UTC).isoformat()
                    except Exception:
                        pub_iso = pub_date_raw

                article = {
                    "guid": guid,
                    "title": title,
                    "link": link,
                    "description": desc,
                    "pub_date_raw": pub_date_raw,
                    "published_at": pub_iso,
                    "source": portal_name,
                    "feed_topic": source_id,
                    "language": lang,
                    "captured_at": datetime.now(UTC).isoformat(),
                }
                new_articles.append(article)
                seen_guids.add(guid)
                count_new += 1

            print(
                f"  ✓ {source_id}: {count_new} novos artigos adicionados "
                f"(feed total: {len(items)})"
            )
        except Exception as e:
            print(f"  ✗ Erro em {source_id}: {e}")

    if new_articles:
        with out_file.open("a", encoding="utf-8") as f:
            for art in new_articles:
                f.write(json.dumps(art, ensure_ascii=False) + "\n")
        print(
            f"  ✓ {len(new_articles)} novos artigos anexados em "
            f"{out_file.relative_to(ROOT_DIR)}"
        )
    else:
        print("  • Sem novos artigos nos feeds.")

    state["rss_seen_guids"] = list(seen_guids)
    state.setdefault("sources", {})["news_rss"] = {
        "status": "success",
        "last_updated": datetime.now(UTC).isoformat(),
        "new_articles_count": len(new_articles),
    }
    return len(new_articles)


def sync_to_gcs(env: dict[str, str]) -> bool:
    bucket = env.get("GCS_BUCKET")
    project = env.get("GCP_PROJECT_ID")
    gcloud_bin = env.get("GCLOUD_BIN", "gcloud")

    if not bucket or not project:
        print("[warn] GCS_BUCKET ou GCP_PROJECT_ID não definidos.")
        return False

    print(f"\n=== Sincronizando data/bronze para gs://{bucket}/bronze/ ===")
    gcloud_dir = str(Path(gcloud_bin).parent)
    os_env = os.environ.copy()
    os_env["PATH"] = f"{gcloud_dir}:{os_env.get('PATH', '')}"

    cmd = [
        gcloud_bin,
        "storage",
        "cp",
        "-r",
        str(DATA_DIR),
        f"gs://{bucket}/",
        f"--project={project}",
    ]
    try:
        subprocess.run(
            cmd, env=os_env, capture_output=True, text=True, check=True
        )
        print("  ✓ Upload para o Cloud Storage concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Erro no upload GCS: {e.stderr}")
        return False


def main() -> None:
    env = load_env()
    state = load_checkpoint()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        fetch_football_data_uk(client, state)
        fetch_football_data_uk_brazil(client, state)
        fetch_brasileirao_dataset(client, state)
        api_key = env.get("FOOTBALLDATA_API_KEY", "")
        fetch_football_data_org(client, api_key, state)
        fetch_news_rss(client, state)

    save_checkpoint(state)
    sync_to_gcs(env)
    print("\n✓ Coleta multi-liga e sincronização concluídas!")


if __name__ == "__main__":
    main()
