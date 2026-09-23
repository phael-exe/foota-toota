#!/usr/bin/env python3
"""fetch_transfers_and_fantasy.py - Coleta dados de Transferências, Valores de Mercado e Fantasy (FPL).

Fontes integradas:
1. Transfermarkt Datasets (Cloudflare R2):
   - transfers (histórico de transferências mundiais e taxas)
   - player_valuations (série histórica de valor de mercado dos jogadores)
   - players (perfil de atletas: nacionalidade, posição, altura, pé, clube)
   - clubs (clubes: valor de elenco, estádio, capacidade, treinador)
2. Fantasy Premier League (vaastav/Fantasy-Premier-League):
   - Estatísticas detalhadas jogador por rodada (xG, xA, xGI, pontos, minutos, assistências)
   - Temporadas 2021-2022 até 2024-2025.
3. Football-Data.org Standings:
   - Tabelas e classificações atualizadas das 10 principais competições.

Sincroniza com gs://{GCS_BUCKET}/bronze/.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

import httpx


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "bronze"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    for k, v in os.environ.items():
        env.setdefault(k, v)
    return env


def fetch_transfermarkt_files() -> None:
    """Baixa os datasets do Transfermarkt e salva em data/bronze/transfermarkt/."""
    print("\n=== [1/3] Coletando Transfermarkt Datasets (Mercado & Atletas) ===")
    out_dir = DATA_DIR / "transfermarkt"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("transfers", "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz"),
        ("player_valuations", "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz"),
        ("players", "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz"),
        ("clubs", "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/clubs.csv.gz"),
    ]

    for name, url in files:
        out_file = out_dir / f"{name}.csv.gz"
        print(f"  -> Baixando {name}.csv.gz...")
        try:
            with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
                if resp.status_code == 200:
                    with open(out_file, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                    mb = out_file.stat().st_size / (1024 * 1024)
                    print(f"  ✓ {name}.csv.gz salvo ({mb:.2f} MB)")
                else:
                    print(f"  ✗ Erro em {name}: status {resp.status_code}")
        except Exception as e:
            print(f"  ✗ Falha ao baixar {name}: {e}")


def fetch_fantasy_premier_league() -> None:
    """Baixa dados de gameweeks detalhados do Fantasy Premier League."""
    print("\n=== [2/3] Coletando Fantasy Premier League (Estatísticas & xG/xA) ===")
    seasons = ["2024-25", "2023-24", "2022-23", "2021-22"]
    headers = {"User-Agent": "Mozilla/5.0"}

    with httpx.Client(headers=headers, timeout=60.0) as client:
        for s in seasons:
            out_dir = DATA_DIR / "fpl_gameweeks" / f"season={s}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "merged_gw.csv"

            url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{s}/gws/merged_gw.csv"
            try:
                resp = client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    content = resp.text.strip()
                    lines = content.splitlines()
                    out_file.write_text(content, encoding="utf-8")
                    print(f"  ✓ FPL {s}: {len(lines) - 1} registros jogador-rodada salvos")
                else:
                    print(f"  ✗ FPL {s}: status {resp.status_code}")
            except Exception as e:
                print(f"  ✗ Erro em FPL {s}: {e}")


def fetch_football_data_org_standings(env: dict[str, str]) -> None:
    """Coleta tabelas de classificação oficiais da API football-data.org."""
    print("\n=== [3/3] Coletando Classificação Oficial (Standings) das 10 Ligas ===")
    api_key = env.get("FOOTBALLDATA_API_KEY", "")
    if not api_key:
        print("  ✗ FOOTBALLDATA_API_KEY ausente.")
        return

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

    with httpx.Client(headers=headers, timeout=30.0) as client:
        for i, (code, name) in enumerate(competitions):
            out_dir = DATA_DIR / "football_data_org_standings" / f"competition={code}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "standings.jsonl"

            url = f"https://api.football-data.org/v4/competitions/{code}/standings"
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    payload = resp.json()
                    standings = payload.get("standings", [])
                    with open(out_file, "w", encoding="utf-8") as f:
                        for st in standings:
                            st["_competition_code"] = code
                            st["_competition_name"] = name
                            st["_season"] = payload.get("season", {})
                            f.write(json.dumps(st, ensure_ascii=False) + "\n")
                    print(f"  ✓ Classificação {name} ({code}) salva")
                elif resp.status_code == 429:
                    print(f"  ⚠ Rate limit em {code}. Aguardando 15s...")
                    time.sleep(15)
                else:
                    print(f"  ✗ {name} ({code}): status {resp.status_code}")
            except Exception as e:
                print(f"  ✗ Erro em {code}: {e}")

            if i < len(competitions) - 1:
                time.sleep(6.5)


def sync_to_gcs(env: dict[str, str]) -> bool:
    bucket = env.get("GCS_BUCKET")
    project = env.get("GCP_PROJECT_ID")
    gcloud_bin = env.get("GCLOUD_BIN", "gcloud")

    if not bucket or not project:
        print("[warn] GCS_BUCKET ou GCP_PROJECT_ID não definidos.")
        return False

    print(f"\n=== Sincronizando novos dados para gs://{bucket}/bronze/ ===")
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
        subprocess.run(cmd, env=os_env, capture_output=True, text=True, check=True)
        print("  ✓ Upload para gs://foota-toota-505511 concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Erro no upload: {e.stderr}")
        return False


def main() -> None:
    env = load_env()
    fetch_transfermarkt_files()
    fetch_fantasy_premier_league()
    fetch_football_data_org_standings(env)
    sync_to_gcs(env)
    print("\n✓ Coleta de transferências, mercado e fantasy concluída com sucesso!")


if __name__ == "__main__":
    main()
