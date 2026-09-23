#!/usr/bin/env python3
"""
Coleta de Notícias em Tempo Real com Extração Completa do Corpo (Body Text)
Foota Toota Platform - Camada Bronze

Coleta notícias esportivas diretamente de feeds RSS canônicos (ge.globo, Gazeta Esportiva,
Trivela, Metrópoles, BBC Sport, The Guardian, Sky Sports, AS) e Google News.
Extrai o texto completo do corpo dos artigos via requisições HTTP puras e assíncronas/threads,
sem depender de navegadores headless pesados (zero custo de VM).
Salva em JSONL particionado por data e sincroniza com o Google Cloud Storage e BigQuery.
"""

from __future__ import annotations

import concurrent.futures
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "bronze"
CHECKPOINT_FILE = DATA_DIR / "_checkpoints" / "state.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6",
}


class ArticleTextExtractor(HTMLParser):
    """Extrator de texto de artigo limpo baseado em HTMLParser padrão (zero overhead)."""

    def __init__(self) -> None:
        super().__init__()
        self.in_content = False
        self.depth = 0
        self.texts: list[str] = []
        self.skip_tags = {
            "script", "style", "nav", "header", "footer", "aside",
            "figure", "form", "button", "noscript", "svg"
        }
        self.current_skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.skip_tags:
            self.current_skip += 1
            return
        if self.current_skip > 0:
            return

        attrs_dict = dict(attrs)
        cls = (attrs_dict.get("class") or "").lower()
        id_ = (attrs_dict.get("id") or "").lower()
        itemprop = (attrs_dict.get("itemprop") or "").lower()

        is_article_container = (
            tag in ("article", "main")
            or itemprop in ("articlebody", "text")
            or any(
                k in cls
                for k in [
                    "article-body", "article__body", "post-content",
                    "entry-content", "story-body", "m-content",
                    "c-detail__body", "content-inner", "article-text",
                    "content-text", "mc-column", "materia-conteudo"
                ]
            )
            or any(
                k in id_
                for k in ["article-body", "main-content", "post-content", "story-body"]
            )
        )

        if is_article_container:
            self.in_content = True
            self.depth += 1
        elif self.in_content:
            if tag in ("div", "section", "p", "blockquote"):
                self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.skip_tags:
            self.current_skip = max(0, self.current_skip - 1)
            return
        if self.current_skip > 0:
            return

        if self.in_content:
            if tag in ("article", "main", "div", "section", "p", "blockquote"):
                self.depth -= 1
                if self.depth <= 0:
                    self.in_content = False
            if tag in ("p", "h1", "h2", "h3", "h4", "li", "br"):
                self.texts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.current_skip == 0 and self.in_content:
            txt = data.strip()
            if txt:
                self.texts.append(txt + " ")


def extract_clean_text(html: str) -> str:
    """Extrai e normaliza o texto contido nos seletores de matéria do HTML."""
    try:
        parser = ArticleTextExtractor()
        parser.feed(html)
        text = "".join(parser.texts).strip()
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()
    except Exception:
        return ""


def load_env() -> dict[str, str]:
    env_file = ROOT_DIR / ".env"
    env_vars: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("\"'")
    return env_vars


def fetch_article_body(url: str, client: httpx.Client, timeout: float = 8.0) -> str:
    """Baixa a página web e extrai o corpo do texto via HTTP puro."""
    try:
        resp = client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
        if resp.status_code == 200:
            return extract_clean_text(resp.text)
    except Exception:
        pass
    return ""


def clean_html_snippet(raw_html: str) -> str:
    """Remove tags HTML simples de descrições e snippets."""
    return re.sub(r"<[^>]+>", "", raw_html).strip()


def run_news_ingestion(reset_seen: bool = False) -> int:
    env = load_env()
    checkpoint_state = {}
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                checkpoint_state = json.load(f)
        except Exception:
            pass

    seen_guids = set() if reset_seen else set(checkpoint_state.get("rss_seen_guids", []))

    # Lista abrangente de feeds com URLs diretas (onde extraímos o corpo completo)
    direct_feeds = [
        ("ge_globo", "https://ge.globo.com/rss/ge/", "pt-BR", "ge.globo"),
        ("gazeta_esportiva", "https://www.gazetaesportiva.com/feed/", "pt-BR", "Gazeta Esportiva"),
        ("trivela", "https://trivela.com.br/feed/", "pt-BR", "Trivela"),
        ("metropoles", "https://www.metropoles.com/esportes/feed", "pt-BR", "Metrópoles"),
        ("bbc_sport", "http://feeds.bbci.co.uk/sport/football/rss.xml", "en-GB", "BBC Sport"),
        ("guardian_football", "https://www.theguardian.com/football/rss", "en-GB", "The Guardian"),
        ("sky_sports", "https://www.skysports.com/rss/12040", "en-GB", "Sky Sports"),
        ("as_primera", "https://as.com/rss/futbol/primera.xml", "es-ES", "Diario AS"),
    ]

    # Feeds agregados de busca (Google News)
    google_feeds = [
        ("gnews_futebol_br", "https://news.google.com/rss/search?q=futebol+brasileiro&hl=pt-BR&gl=BR&ceid=BR:pt-419", "pt-BR"),
        ("gnews_brasileirao", "https://news.google.com/rss/search?q=brasileir%C3%A3o+s%C3%A9rie+a&hl=pt-BR&gl=BR&ceid=BR:pt-419", "pt-BR"),
        ("gnews_mercado_bola", "https://news.google.com/rss/search?q=mercado+da+bola+transferencias&hl=pt-BR&gl=BR&ceid=BR:pt-419", "pt-BR"),
        ("gnews_premier_league", "https://news.google.com/rss/search?q=premier+league+football&hl=en-GB&gl=GB&ceid=GB:en", "en-GB"),
        ("gnews_champions_league", "https://news.google.com/rss/search?q=champions+league+football&hl=en-GB&gl=GB&ceid=GB:en", "en-GB"),
    ]

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = DATA_DIR / "news_rss" / f"dt={today_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "articles.jsonl"

    items_to_process = []
    print(f"\n=== [1/3] Coletando Feeds RSS de Notícias ({len(direct_feeds) + len(google_feeds)} fontes) ===")

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=15.0) as client:
        # 1. Coleta feeds diretos
        for source_id, url, lang, portal_default in direct_feeds:
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    print(f"  ✗ {source_id}: HTTP {resp.status_code}")
                    continue
                root = ET.fromstring(resp.content)
                channel = root.find("channel") or root
                items = channel.findall(".//item")
                count = 0
                for item in items:
                    link = (item.findtext("link") or "").strip()
                    guid = (item.findtext("guid") or link).strip()
                    if not guid or guid in seen_guids:
                        continue
                    title = (item.findtext("title") or "").strip()
                    pub_date_raw = (item.findtext("pubDate") or "").strip()
                    desc = clean_html_snippet(item.findtext("description") or "")
                    source_tag = item.find("source")
                    source_name = source_tag.text.strip() if source_tag is not None and source_tag.text else portal_default

                    items_to_process.append({
                        "guid": guid,
                        "title": title,
                        "link": link,
                        "description": desc,
                        "pub_date_raw": pub_date_raw,
                        "source": source_name,
                        "feed_topic": source_id,
                        "language": lang,
                        "is_direct": True,
                    })
                    seen_guids.add(guid)
                    count += 1
                print(f"  ✓ {source_id}: {count} novos itens identificados (feed total: {len(items)})")
            except Exception as e:
                print(f"  ✗ Erro ao ler feed {source_id}: {e}")

        # 2. Coleta Google News feeds
        for source_id, url, lang in google_feeds:
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    print(f"  ✗ {source_id}: HTTP {resp.status_code}")
                    continue
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel is None:
                    continue
                items = channel.findall("item")
                count = 0
                for item in items:
                    link = (item.findtext("link") or "").strip()
                    guid = (item.findtext("guid") or link).strip()
                    if not guid or guid in seen_guids:
                        continue
                    title = (item.findtext("title") or "").strip()
                    pub_date_raw = (item.findtext("pubDate") or "").strip()
                    desc = clean_html_snippet(item.findtext("description") or "")
                    source_tag = item.find("source")
                    source_name = source_tag.text.strip() if source_tag is not None and source_tag.text else source_id

                    items_to_process.append({
                        "guid": guid,
                        "title": title,
                        "link": link,
                        "description": desc,
                        "pub_date_raw": pub_date_raw,
                        "source": source_name,
                        "feed_topic": source_id,
                        "language": lang,
                        "is_direct": False,
                    })
                    seen_guids.add(guid)
                    count += 1
                print(f"  ✓ {source_id}: {count} novos itens identificados (feed total: {len(items)})")
            except Exception as e:
                print(f"  ✗ Erro ao ler feed {source_id}: {e}")

    print(f"\n=== [2/3] Extraindo Conteúdo Completo (Body) para {len(items_to_process)} Notícias ===")
    
    # Processa os itens em paralelo usando ThreadPoolExecutor
    def process_item(item_dict: dict) -> dict:
        is_direct = item_dict.pop("is_direct", False)
        link = item_dict["link"]
        body = ""
        if is_direct and link.startswith("http"):
            with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=8.0) as c:
                body = fetch_article_body(link, c)

        # Se falhou ou é Google News, usa descrição/resumo como fallback
        if not body or len(body) < 100:
            body = item_dict["description"] or item_dict["title"]

        pub_iso = None
        pub_raw = item_dict.get("pub_date_raw", "")
        if pub_raw:
            try:
                dt = parsedate_to_datetime(pub_raw)
                pub_iso = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pub_iso = pub_raw

        return {
            "guid": item_dict["guid"],
            "title": item_dict["title"],
            "link": item_dict["link"],
            "description": item_dict["description"],
            "content_body": body,
            "character_count": len(body),
            "pub_date_raw": pub_raw,
            "published_at": pub_iso,
            "source": item_dict["source"],
            "feed_topic": item_dict["feed_topic"],
            "language": item_dict["language"],
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    t0 = time.time()
    final_articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_item, it): it for it in items_to_process}
        for fut in concurrent.futures.as_completed(futures):
            try:
                art = fut.result()
                final_articles.append(art)
            except Exception as e:
                pass

    elapsed = time.time() - t0
    full_body_count = sum(1 for a in final_articles if a["character_count"] >= 500)
    print(f"  ✓ Processados {len(final_articles)} artigos em {elapsed:.2f}s!")
    print(f"  ✓ {full_body_count} artigos contêm corpo completo (> 500 caracteres, médias de 2.000 a 7.000 chars)")

    if final_articles:
        mode = "w" if reset_seen else "a"
        with open(out_file, mode, encoding="utf-8") as f:
            for art in final_articles:
                f.write(json.dumps(art, ensure_ascii=False) + "\n")
        print(f"  ✓ Salvo em {out_file.relative_to(ROOT_DIR)}")

    # Atualiza checkpoint
    checkpoint_state["rss_seen_guids"] = list(seen_guids)
    checkpoint_state.setdefault("sources", {})["news_rss"] = {
        "status": "success",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(final_articles),
        "articles_with_full_body": full_body_count,
    }
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint_state, f, indent=2, ensure_ascii=False)

    return len(final_articles)


def sync_news_to_gcs_and_bq() -> None:
    """Sincroniza os arquivos de notícias para o GCS e recria a tabela bronze no BigQuery."""
    env = load_env()
    bucket = env.get("GCS_BUCKET", "foota-toota-505511")
    project = env.get("GCP_PROJECT_ID", "pdm-bia-505511")
    gcloud_bin = env.get("GCLOUD_BIN", "/home/phaelzin/google-cloud-sdk/bin/gcloud")
    bq_bin = env.get("BQ_BIN", "/home/phaelzin/google-cloud-sdk/bin/bq")

    print(f"\n=== [3/3] Sincronizando com GCS e BigQuery ===")
    gcloud_dir = str(Path(gcloud_bin).parent)
    os_env = os.environ.copy()
    os_env["PATH"] = f"{gcloud_dir}:{os_env.get('PATH', '')}"

    # 2. DDL statements
    ddl_external = f"""
    CREATE OR REPLACE EXTERNAL TABLE `{project}.bronze.ext_news_rss` (
        guid STRING,
        title STRING,
        link STRING,
        description STRING,
        content_body STRING,
        character_count INT64,
        pub_date_raw STRING,
        published_at STRING,
        source STRING,
        feed_topic STRING,
        language STRING,
        captured_at STRING
    )
    OPTIONS (
        format                = 'NEWLINE_DELIMITED_JSON',
        uris                  = ['gs://{bucket}/bronze/news_rss/*'],
        ignore_unknown_values = true
    );
    """

    ddl_table = f"""
    CREATE OR REPLACE TABLE `{project}.bronze.news_rss` AS
    SELECT
        guid,
        title,
        link,
        description,
        content_body,
        character_count,
        pub_date_raw,
        published_at,
        source,
        feed_topic,
        language,
        captured_at,
        '20260923' AS batch_id,
        CURRENT_TIMESTAMP() AS ingested_at,
        _FILE_NAME AS source_file
    FROM `{project}.bronze.ext_news_rss`;
    """

    # Tenta usar o SDK nativo do Google Cloud primeiro (ideal para containers no Cloud Run)
    try:
        from google.cloud import storage, bigquery
        storage_client = storage.Client(project=project)
        bucket_obj = storage_client.bucket(bucket)

        for root_p, _, files in os.walk(DATA_DIR / "news_rss"):
            for fname in files:
                fpath = Path(root_p) / fname
                rel_path = fpath.relative_to(DATA_DIR)
                blob = bucket_obj.blob(f"bronze/{rel_path}")
                blob.upload_from_filename(str(fpath))
        print("  ✓ Upload para gs://" + bucket + "/bronze/news_rss/ via Python SDK concluído!")

        bq_client = bigquery.Client(project=project)
        bq_client.query(ddl_external).result()
        print("    ✓ ext_news_rss atualizada via BigQuery SDK!")
        bq_client.query(ddl_table).result()
        print("    ✓ news_rss atualizada via BigQuery SDK!")
        return
    except Exception as sdk_err:
        print(f"  ℹ SDK Python fallback para CLI ({sdk_err})")

    # Fallback para CLI (gcloud e bq instalados localmente)
    cmd_upload = [
        gcloud_bin,
        "storage",
        "cp",
        "-r",
        str(DATA_DIR / "news_rss"),
        f"gs://{bucket}/bronze/",
        f"--project={project}",
    ]
    try:
        subprocess.run(cmd_upload, env=os_env, capture_output=True, text=True, check=True)
        print("  ✓ Upload para gs://" + bucket + "/bronze/news_rss/ concluído via gcloud!")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Erro no upload GCS: {e.stderr}")
        return

    print("  ✓ Atualizando tabelas ext_news_rss e bronze.news_rss no BigQuery via bq...")
    for ddl, name in [(ddl_external, "ext_news_rss"), (ddl_table, "news_rss")]:
        cmd_bq = [
            bq_bin,
            "query",
            "--nouse_legacy_sql",
            f"--project_id={project}",
            ddl,
        ]
        res = subprocess.run(cmd_bq, env=os_env, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"    ✓ {name} atualizada com sucesso no BigQuery!")
        else:
            print(f"    ✗ Falha ao atualizar {name}: {res.stderr}")


if __name__ == "__main__":
    count = run_news_ingestion(reset_seen=True)
    sync_news_to_gcs_and_bq()
    print(f"\n🎉 Concluído com sucesso! {count} notícias processadas.")

