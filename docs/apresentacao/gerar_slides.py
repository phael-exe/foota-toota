# ruff: noqa: E501, RUF001
"""Gera o deck do Trabalho 2 (Ingestão em Tempo Real e Deploy de Modelo) em .pptx.

O arquivo sobe para o Google Drive e vira Google Slides. Cada print que falta
é uma caixa tracejada com nome `PRINT: <id>`, o projeto e a URL exata do
console do GCP, para trocar pela imagem depois.

    uv run --no-project --with python-pptx python docs/apresentacao/gerar_slides.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


REPO = "https://github.com/phael-exe/foota-toota"
CODIGO = f"{REPO}/blob/main/"
PRINTS = "https://raw.githubusercontent.com/phael-exe/foota-toota/main/docs/apresentacao/prints/"
API = "https://modelo-api-3gvoh2dyuq-uc.a.run.app"
COLETA = "pdm-bia-505511"
MODELO = "pdm-andre-2026"
CONSOLE = "https://console.cloud.google.com/"
PASTA_PRINTS = Path(__file__).with_name("prints")

FONTE = "Inter"
MONO = "Roboto Mono"
TINTA = RGBColor(0x1F, 0x23, 0x28)
CINZA = RGBColor(0x57, 0x60, 0x6A)
VERDE = RGBColor(0x14, 0x6C, 0x43)
VERDE_CLARO = RGBColor(0xE8, 0xF5, 0xEC)
AZUL = RGBColor(0x09, 0x69, 0xDA)
AREIA = RGBColor(0xF6, 0xF8, 0xFA)
BORDA = RGBColor(0x9C, 0xA3, 0xAF)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BRANCO_LAYOUT = prs.slide_layouts[6]


def novo(titulo: str, kicker: str = "") -> object:
    s = prs.slides.add_slide(BRANCO_LAYOUT)
    faixa = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12)
    )
    faixa.fill.solid()
    faixa.fill.fore_color.rgb = VERDE
    faixa.line.fill.background()
    if kicker:
        texto(
            s, kicker.upper(), 0.55, 0.32, 12, 0.3, 11, cor=VERDE, negrito=True
        )
    texto(s, titulo, 0.55, 0.55, 12.2, 0.7, 26, negrito=True)
    rodape = (
        f"Foota Toota · Trabalho 2 · PDM 2026/2   {len(prs.slides._sldIdLst)}"
    )
    texto(s, rodape, 9.0, 7.08, 3.8, 0.3, 9, cor=CINZA, alinhar=PP_ALIGN.RIGHT)
    return s


def texto(
    s,
    conteudo,
    x,
    y,
    w,
    h,
    tam=14,
    cor=TINTA,
    negrito=False,
    alinhar=None,
    fonte=FONTE,
    link=None,
):
    caixa = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = caixa.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, linha in enumerate(conteudo.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if alinhar is not None:
            p.alignment = alinhar
        r = p.add_run()
        r.text = linha
        r.font.size = Pt(tam)
        r.font.name = fonte
        r.font.bold = negrito
        r.font.color.rgb = AZUL if link else cor
        if link:
            r.hyperlink.address = link
    return caixa


def topicos(s, itens, x, y, w, h, tam=15):
    """Itens: str ou (str, [subitens]). `texto|url` vira link."""
    caixa = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = caixa.text_frame
    tf.word_wrap = True
    primeiro = True
    for item in itens:
        sub = []
        if isinstance(item, tuple):
            item, sub = item
        for nivel, linha in [(0, item)] + [(1, t) for t in sub]:
            p = tf.paragraphs[0] if primeiro else tf.add_paragraph()
            primeiro = False
            p.space_after = Pt(6)
            marcador = "•  " if nivel == 0 else "–  "
            r = p.add_run()
            r.text = ("      " * nivel) + marcador
            r.font.size = Pt(tam - nivel * 2)
            r.font.color.rgb = VERDE
            r.font.name = FONTE
            partes = linha.split("`")
            for k, parte in enumerate(partes):
                if not parte:
                    continue
                r = p.add_run()
                r.text = parte
                r.font.size = Pt(tam - nivel * 2)
                r.font.name = MONO if k % 2 else FONTE
                r.font.color.rgb = TINTA
    return caixa


def links(s, pares, x, y, w=6.0):
    """Linha 'Código:' com links clicáveis para o GitHub."""
    caixa = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.35))
    tf = caixa.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "Código:  "
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.name = FONTE
    r.font.color.rgb = CINZA
    for i, (rotulo, caminho) in enumerate(pares):
        if i:
            r = p.add_run()
            r.text = "  ·  "
            r.font.size = Pt(12)
            r.font.color.rgb = CINZA
        r = p.add_run()
        r.text = rotulo
        r.font.size = Pt(12)
        r.font.name = MONO
        r.font.color.rgb = AZUL
        r.hyperlink.address = (
            caminho if caminho.startswith("http") else CODIGO + caminho
        )
    return caixa


def imagem(s, arquivo, nome, url, x, y, w, h):
    """Print encaixado na área (x, y, w, h), sem distorcer, centralizado e clicável."""
    with Image.open(arquivo) as im:
        proporcao = im.width / im.height
    if proporcao >= w / h:
        largura, altura = w, w / proporcao
    else:
        largura, altura = h * proporcao, h
    foto = s.shapes.add_picture(
        str(arquivo),
        Inches(x + (w - largura) / 2),
        Inches(y + (h - altura) / 2),
        Inches(largura),
        Inches(altura),
    )
    foto.name = nome
    foto.line.color.rgb = BORDA
    foto.line.width = Pt(0.75)
    foto.click_action.hyperlink.address = url
    return foto


def print_gcp(s, ident, titulo, projeto, url, x, y, w, h):
    """Print do console do GCP (prints/<ident>.png) ou, se ainda não existir,
    uma caixa tracejada com o que mostrar e o link do console."""
    arquivo = PASTA_PRINTS / f"{ident}.png"
    if arquivo.exists():
        return imagem(s, arquivo, f"PRINT: {ident}", url, x, y, w, h)
    caixa = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    caixa.name = f"PRINT: {ident}"
    caixa.fill.solid()
    caixa.fill.fore_color.rgb = AREIA
    caixa.line.color.rgb = BORDA
    caixa.line.width = Pt(1.5)
    caixa.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    tf = caixa.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, (t, tam, cor, neg, href) in enumerate(
        [
            (f"PRINT DO GCP  ·  {ident}", 11, CINZA, True, None),
            (titulo, 15, TINTA, True, None),
            (f"projeto {projeto}", 11, CINZA, False, None),
            ("abrir no console", 11, AZUL, False, url),
        ]
    ):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = t
        r.font.size = Pt(tam)
        r.font.bold = neg
        r.font.name = FONTE
        r.font.color.rgb = cor
        if href:
            r.hyperlink.address = href
    return caixa


def print_repo(s, ident, titulo, arquivo, x, y, w, h):
    """Print que já está no repositório (docs/apresentacao/prints)."""
    if (PASTA_PRINTS / arquivo).exists():
        return imagem(
            s,
            PASTA_PRINTS / arquivo,
            f"PRINT_REPO: {arquivo}",
            PRINTS + arquivo,
            x,
            y,
            w,
            h,
        )
    caixa = print_gcp(
        s, ident, titulo, "evidência local", PRINTS + arquivo, x, y, w, h
    )
    caixa.name = f"PRINT_REPO: {arquivo}"
    caixa.fill.fore_color.rgb = VERDE_CLARO
    caixa.text_frame.paragraphs[0].runs[
        0
    ].text = f"PRINT DO REPOSITÓRIO  ·  {arquivo}"
    caixa.text_frame.paragraphs[2].runs[0].text = "docs/apresentacao/prints"
    caixa.text_frame.paragraphs[3].runs[0].text = "abrir imagem"
    return caixa


def tabela(s, linhas, x, y, w, larguras, tam=12, alt=0.36):
    t = s.shapes.add_table(
        len(linhas),
        len(linhas[0]),
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(alt * len(linhas)),
    ).table
    for j, lw in enumerate(larguras):
        t.columns[j].width = Inches(lw)
    for i, linha in enumerate(linhas):
        for j, valor in enumerate(linha):
            c = t.cell(i, j)
            c.text = ""
            p = c.text_frame.paragraphs[0]
            partes = str(valor).split("`")
            for k, parte in enumerate(partes):
                if not parte:
                    continue
                r = p.add_run()
                r.text = parte
                r.font.size = Pt(tam)
                r.font.name = MONO if k % 2 else FONTE
                r.font.bold = i == 0
                r.font.color.rgb = BRANCO if i == 0 else TINTA
            c.fill.solid()
            c.fill.fore_color.rgb = (
                VERDE if i == 0 else (AREIA if i % 2 else BRANCO)
            )
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.04)
    return t


def bloco(s, conteudo, x, y, w, h, tam=11):
    """Saída de terminal real, em fonte mono."""
    fundo = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    fundo.fill.solid()
    fundo.fill.fore_color.rgb = RGBColor(0x1E, 0x1F, 0x24)
    fundo.line.fill.background()
    tf = fundo.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.1)
    for i, linha in enumerate(conteudo.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = linha
        r.font.size = Pt(tam)
        r.font.name = MONO
        if linha.startswith("$"):
            r.font.color.rgb = RGBColor(0x79, 0xC0, 0xFF)
        elif "REJEITADA" in linha:
            r.font.color.rgb = RGBColor(0xFF, 0x7B, 0x72)
        elif "LIMPA" in linha or "aprovado" in linha:
            r.font.color.rgb = RGBColor(0x7E, 0xE7, 0x87)
        else:
            r.font.color.rgb = RGBColor(0xE6, 0xE6, 0xE6)
    return fundo


def seta(s, a, b, de=3, para=1, tipo=MSO_CONNECTOR.ELBOW):
    c = s.shapes.add_connector(tipo, 0, 0, 0, 0)
    c.begin_connect(a, de)
    c.end_connect(b, para)
    c.line.color.rgb = CINZA
    c.line.width = Pt(1.25)
    ln = c.line._get_or_add_ln()
    ponta = etree.SubElement(
        ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd"
    )
    ponta.set("type", "triangle")
    return c


# ---------------------------------------------------------------- 1. capa
s = prs.slides.add_slide(BRANCO_LAYOUT)
fundo = s.shapes.add_shape(
    MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
)
fundo.fill.solid()
fundo.fill.fore_color.rgb = RGBColor(0x0B, 0x3D, 0x2E)
fundo.line.fill.background()
texto(
    s,
    "PROCESSAMENTO DE DADOS MASSIVOS · 2026/2 (BIA) · INF/UFG",
    0.8,
    1.5,
    11,
    0.4,
    13,
    cor=RGBColor(0x9F, 0xE0, 0xB5),
    negrito=True,
)
texto(s, "Foota Toota", 0.8, 2.0, 11, 1.1, 54, cor=BRANCO, negrito=True)
texto(
    s,
    "Trabalho 2: Ingestão em Tempo Real e Deploy de Modelo",
    0.8,
    3.15,
    11.5,
    0.7,
    28,
    cor=BRANCO,
)
texto(
    s,
    "Brasileirão ao vivo no Pub/Sub e Dataflow, batch e stream juntos no BigQuery,\n"
    "e um modelo por liga no Vertex AI servido por uma API no Cloud Run.",
    0.8,
    4.0,
    11.5,
    0.9,
    16,
    cor=RGBColor(0xD0, 0xE8, 0xDA),
)
texto(
    s,
    "Raphael Alves de Lima Soares  ·  André Vinicius Moura Koraleski\n"
    "Victor Gabriel Ribeiro Jacome  ·  Wagner Victor Alves de Menezes",
    0.8,
    5.05,
    11.5,
    0.7,
    15,
    cor=BRANCO,
    negrito=True,
)
base = s.shapes.add_shape(
    MSO_SHAPE.ROUNDED_RECTANGLE,
    Inches(0.8),
    Inches(5.85),
    Inches(7.6),
    Inches(0.85),
)
base.adjustments[0] = 0.15
base.fill.solid()
base.fill.fore_color.rgb = BRANCO
base.line.fill.background()
for i, (rotulo, url) in enumerate(
    [
        ("Repositório: github.com/phael-exe/foota-toota", REPO),
        (f"API em produção: {API}", f"{API}/docs"),
    ]
):
    texto(s, rotulo, 1.0, 5.92 + i * 0.35, 7.3, 0.35, 13, link=url)

# ---------------------------------------------------------------- 2. entregas
s = novo("O que entregamos", "visão geral")
cartoes = [
    (
        "1  Ingestão em tempo real",
        "Coletor no Cloud Run Job, disparado a cada 5 min pelo Cloud Scheduler, publica no "
        "Pub/Sub só as partidas do Brasileirão que mudaram.",
        "streaming/producer.py",
    ),
    (
        "2  Processamento em streaming",
        "Dataflow (Apache Beam) valida e limpa cada evento. O que for inválido vai para a "
        "quarentena com o motivo.",
        "streaming/pipeline.py",
    ),
    (
        "3  Batch + stream no BigQuery",
        "Tabelas do stream particionadas por dia; views da gold juntam o histórico do "
        "Trabalho 1 com o que chega ao vivo.",
        "sql/10_stream/06_create_view_partidas_unificadas.sql",
    ),
    (
        "4  Deploy do modelo",
        "Um modelo por liga no Vertex AI Model Registry, servido por uma API FastAPI no Cloud "
        "Run, por HTTP e pelo push do Pub/Sub.",
        "modelo/api.py",
    ),
]
for i, (t, d, cam) in enumerate(cartoes):
    x = 0.55 + (i % 2) * 6.2
    y = 1.55 + (i // 2) * 2.65
    card = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(5.95),
        Inches(2.4),
    )
    card.adjustments[0] = 0.06
    card.fill.solid()
    card.fill.fore_color.rgb = VERDE_CLARO
    card.line.fill.background()
    texto(s, t, x + 0.3, y + 0.25, 5.4, 0.45, 19, cor=VERDE, negrito=True)
    texto(s, d, x + 0.3, y + 0.8, 5.4, 1.1, 15)
    texto(
        s, cam, x + 0.3, y + 1.85, 5.4, 0.35, 12, fonte=MONO, link=CODIGO + cam
    )

# ---------------------------------------------------------------- 3. evolução
s = novo("Do Trabalho 1 ao Trabalho 2", "evolução da arquitetura")
tabela(
    s,
    [
        ["", "Trabalho 1: batch", "Trabalho 2: + tempo real e deploy"],
        [
            "Ingestão",
            "scripts baixam as fontes para o GCS (bronze)",
            "+ coletor a cada 5 min publica eventos JSON no Pub/Sub",
        ],
        [
            "Processamento",
            "SQL em camadas: bronze → silver → gold, com `ASSERT` bloqueantes",
            "+ Dataflow valida e limpa cada evento; inválidos vão para a quarentena",
        ],
        [
            "BigQuery",
            "histórico de todas as fontes em bronze, silver e gold",
            "+ dataset `stream` e views da gold que juntam batch e stream",
        ],
        [
            "Modelo",
            "referência em BigQuery ML: regressão logística e boosted trees",
            "um modelo por liga no Vertex AI Model Registry, alias `campeao`",
        ],
        [
            "Serviço",
            "previsões gravadas em tabela",
            "API REST em Docker no Cloud Run: `POST /predict` e push do Pub/Sub",
        ],
    ],
    0.55,
    1.5,
    12.25,
    [1.95, 4.6, 5.7],
    13,
    0.68,
)
topicos(
    s,
    [
        "O batch continua igual: a gold dele é a base do treino e o histórico que o stream "
        "completa."
    ],
    0.55,
    5.85,
    12.2,
    0.6,
    15,
)

# ---------------------------------------------------------------- 4. arquitetura
s = novo("Arquitetura", "como os dados andam")
COL = [0.55 + i * 2.1 for i in range(6)]
BW, BH = 1.85, 0.62


def faixa(y, h, rotulo, cor):
    r = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.4),
        Inches(y),
        Inches(12.55),
        Inches(h),
    )
    r.adjustments[0] = 0.04
    r.fill.solid()
    r.fill.fore_color.rgb = cor
    r.line.fill.background()
    texto(s, rotulo, 0.55, y + 0.04, 6, 0.28, 10, cor=CINZA, negrito=True)


faixa(1.3, 2.5, f"STREAMING · projeto {COLETA}", RGBColor(0xEE, 0xF6, 0xFF))
faixa(3.95, 1.15, f"MODELO · projeto {MODELO}", RGBColor(0xF3, 0xEE, 0xFF))
faixa(
    5.3,
    1.2,
    "BATCH · Trabalho 1 (bronze, silver, gold)",
    RGBColor(0xFF, 0xF8, 0xE7),
)


def caixa(c, y, nome, sub, caminho=None, cor=BRANCO):
    b = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(COL[c]),
        Inches(y),
        Inches(BW),
        Inches(BH),
    )
    b.adjustments[0] = 0.12
    b.fill.solid()
    b.fill.fore_color.rgb = cor
    b.line.color.rgb = BORDA
    b.line.width = Pt(1)
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    grande = 11 if len(nome) <= 18 else 9
    for i, (t, tam, neg) in enumerate(
        [(nome, grande, True), (sub, 8.5, False)]
    ):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = t
        r.font.size = Pt(tam)
        r.font.bold = neg
        r.font.name = FONTE
        r.font.color.rgb = TINTA if neg else CINZA
    if caminho:
        b.click_action.hyperlink.address = CODIGO + caminho
    return b


fdo = caixa(0, 1.95, "Football-Data.org", "API do Brasileirão")
col = caixa(
    1, 1.95, "Coletor", "Cloud Run Job · 5 min", "streaming/producer.py"
)
evt = caixa(2, 1.95, "Pub/Sub: eventos", "tópico", "streaming/infra.sh")
ebr = caixa(
    3,
    1.42,
    "stream.eventos_brutos",
    "assinatura BigQuery",
    "sql/10_stream/02_create_table_eventos_brutos.sql",
)
dfl = caixa(3, 2.5, "Dataflow", "Apache Beam · pull", "streaming/pipeline.py")
spa = caixa(
    4,
    2.12,
    "stream.partidas",
    "eventos limpos",
    "sql/10_stream/03_create_table_partidas.sql",
)
srj = caixa(
    4,
    3.0,
    "stream.partidas_rejeitadas",
    "quarentena + motivo",
    "sql/10_stream/04_create_table_partidas_rejeitadas.sql",
)
uni = caixa(
    5,
    1.6,
    "gold.partidas_unificadas",
    "silver + stream · partidas_atual",
    "sql/10_stream/06_create_view_partidas_unificadas.sql",
)
ava = caixa(
    5,
    3.0,
    "gold.predicoes_avaliadas",
    "predição x resultado real",
    "sql/10_stream/08_create_view_predicoes_avaliadas.sql",
)
trn = caixa(1, 4.28, "treinar.py", "1 modelo por liga", "modelo/treinar.py")
reg = caixa(
    2,
    4.28,
    "Vertex AI Registry",
    "alias campeao · Experiments",
    "modelo/treinar.py",
)
api = caixa(3, 4.28, "API no Cloud Run", "/predict · /pubsub", "modelo/api.py")
prd = caixa(4, 4.28, "Pub/Sub: predicoes", "tópico", "streaming/infra.sh")
spr = caixa(
    5,
    4.28,
    "stream.predicoes",
    "assinatura BigQuery",
    "sql/10_stream/05_create_table_predicoes.sql",
)
fon = caixa(
    0, 5.68, "Fontes", "FD.co.uk, FD.org, Big Balls…", "scripts/fetch_bronze.py"
)
brz = caixa(1, 5.68, "bronze", "GCS + BigQuery", "sql/01_bronze")
sil = caixa(2, 5.68, "silver", "modelo canônico", "sql/02_silver")
gld = caixa(3, 5.68, "gold", "features por partida", "sql/04_gold")
pub = caixa(
    4, 5.68, "bucket público", "Parquet", "scripts/exportar_tabelas_publicas.sh"
)
for a, b in [
    (fdo, col),
    (col, evt),
    (evt, ebr),
    (evt, dfl),
    (dfl, spa),
    (dfl, srj),
    (spa, uni),
    (spa, ava),
    (trn, reg),
    (reg, api),
    (api, prd),
    (prd, spr),
    (fon, brz),
    (brz, sil),
    (sil, gld),
    (gld, pub),
]:
    seta(s, a, b)
seta(s, evt, api, 2, 0)
seta(s, spr, ava, 0, 2)
seta(s, pub, trn, 0, 2)
seta(s, pub, api, 0, 2)
texto(s, "push", 4.6, 3.55, 0.6, 0.25, 9, cor=CINZA)
texto(
    s,
    "Clique numa caixa para abrir o código.",
    0.55,
    6.62,
    6,
    0.3,
    10,
    cor=CINZA,
)

# ---------------------------------------------------------------- 4. coletor
s = novo("Ingestão: o coletor do Football-Data.org", "streaming · 1/5")
topicos(
    s,
    [
        "Roda como Cloud Run Job (`foota-toota-coletor`), disparado pelo Cloud Scheduler a cada "
        "5 minutos (`foota-toota-coletor-5min`).",
        "Consulta o Brasileirão e publica no tópico `eventos` só as partidas que mudaram: status, "
        "placar ou horário.",
        "O `event_id` identifica aquela versão da partida: `match_id:status:placar:horário`.",
        "Partida encerrada não volta a agendada: protege do cache antigo da API.",
        "Modo `replay` reproduz rodadas já jogadas, para demonstrar a qualquer hora.",
    ],
    0.55,
    1.45,
    5.9,
    4.6,
    15,
)
links(
    s,
    [
        ("producer.py", "streaming/producer.py#L122-L141"),
        ("deploy_coletor.sh", "streaming/deploy_coletor.sh"),
    ],
    0.55,
    6.55,
)
print_gcp(
    s,
    "coletor-execucoes",
    "Cloud Run › Jobs › foota-toota-coletor (histórico de execuções)",
    COLETA,
    f"{CONSOLE}run/jobs?project={COLETA}",
    6.75,
    1.45,
    6.05,
    2.5,
)
print_gcp(
    s,
    "scheduler",
    "Cloud Scheduler › foota-toota-coletor-5min",
    COLETA,
    f"{CONSOLE}cloudscheduler?project={COLETA}",
    6.75,
    4.1,
    6.05,
    2.35,
)

# ---------------------------------------------------------------- 5. pubsub
s = novo("Pub/Sub: um tópico, três consumidores", "streaming · 2/5")
tabela(
    s,
    [
        ["Assinatura", "Tipo", "Destino"],
        [
            "`eventos-bigquery`",
            "BigQuery",
            "`stream.eventos_brutos`: cada mensagem como chegou",
        ],
        [
            "`eventos-dataflow`",
            "Pull (guarda 7 dias)",
            "Dataflow → `stream.partidas`",
        ],
        [
            "`eventos-api`",
            "Push com token OIDC",
            "API do modelo, `POST /pubsub`",
        ],
        [
            "`predicoes-bigquery`",
            "BigQuery",
            "`stream.predicoes` (falhas → `predicoes-dlq`)",
        ],
    ],
    0.55,
    1.5,
    6.1,
    [1.9, 1.55, 2.65],
    11,
    0.5,
)
topicos(
    s,
    [
        "O bronze do stream não tem código: a assinatura BigQuery grava tudo, mesmo com o "
        "Dataflow desligado.",
        "Ao religar o Dataflow, ele processa o acumulado da assinatura sem perder nada.",
    ],
    0.55,
    4.25,
    6.1,
    1.8,
    14,
)
links(s, [("infra.sh", "streaming/infra.sh#L60-L110")], 0.55, 6.55)
print_gcp(
    s,
    "pubsub-topicos",
    "Pub/Sub › Tópicos (eventos, predicoes, predicoes-dlq)",
    COLETA,
    f"{CONSOLE}cloudpubsub/topic/list?project={COLETA}",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_gcp(
    s,
    "pubsub-assinaturas",
    "Pub/Sub › Assinaturas",
    COLETA,
    f"{CONSOLE}cloudpubsub/subscription/list?project={COLETA}",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 6. dataflow
s = novo("Dataflow: validação e quarentena", "streaming · 3/5")
topicos(
    s,
    [
        (
            "Recusa o evento",
            [
                "sem campo obrigatório",
                "competição ou status desconhecido",
                "mandante igual ao visitante",
                "placar negativo",
                "partida encerrada sem placar",
            ],
        ),
        "`league_id` e `status` saem no formato da silver.",
        "O recusado (e o que o próprio BigQuery recusa) vai para `stream.partidas_rejeitadas` "
        "com o motivo e a mensagem original.",
    ],
    0.55,
    1.45,
    5.4,
    3.6,
    14,
)
bloco(
    s,
    "$ limpar() sobre o replay da rodada 30 + 5 eventos quebrados\n"
    "LIMPA     fdorg_555039 scheduled brasileirao_serie_a\n"
    "LIMPA     fdorg_555039 finished  placar 0-0\n"
    "LIMPA     fdorg_555038 finished  placar 2-1\n"
    "REJEITADA mandante e visitante são o mesmo time\n"
    "REJEITADA placar negativo: -1\n"
    "REJEITADA partida encerrada sem placar\n"
    "REJEITADA status desconhecido: ADIADO??\n"
    "REJEITADA campos ausentes: match_id",
    0.55,
    4.6,
    5.4,
    1.85,
    10,
)
links(
    s,
    [
        ("pipeline.py", "streaming/pipeline.py#L73-L130"),
        ("dataflow.sh", "streaming/dataflow.sh"),
    ],
    0.55,
    6.55,
)
print_gcp(
    s,
    "dataflow-grafo",
    "Dataflow › Jobs › foota-toota-partidas (grafo do job rodando)",
    COLETA,
    f"{CONSOLE}dataflow/jobs?project={COLETA}",
    6.2,
    1.45,
    6.6,
    5.0,
)

# ---------------------------------------------------------------- 7. bigquery stream
s = novo("BigQuery: as tabelas do stream", "streaming · 4/5")
tabela(
    s,
    [
        ["Tabela", "Partição", "Cluster", "Conteúdo"],
        [
            "`eventos_brutos`",
            "dia de publicação",
            "—",
            "cada mensagem como chegou",
        ],
        ["`partidas`", "dia de publicação", "liga, partida", "eventos limpos"],
        [
            "`partidas_rejeitadas`",
            "dia de processamento",
            "—",
            "recusados + motivo",
        ],
        ["`predicoes`", "dia da predição", "partida", "predições do modelo"],
    ],
    0.55,
    1.5,
    6.1,
    [1.75, 1.5, 1.15, 1.7],
    11,
    0.5,
)
topicos(
    s,
    [
        "O stream só escreve na partição do dia; consultas por período leem só as partições do "
        "intervalo.",
        "A página de um jogo lê poucos blocos, por causa da clusterização por liga e partida.",
    ],
    0.55,
    4.25,
    6.1,
    1.8,
    14,
)
links(s, [("sql/10_stream", f"{REPO}/tree/main/sql/10_stream")], 0.55, 6.55)
print_gcp(
    s,
    "bq-stream-detalhes",
    "BigQuery › stream.partidas › Detalhes (partição e cluster)",
    COLETA,
    f"{CONSOLE}bigquery?project={COLETA}&p={COLETA}&d=stream&t=partidas&page=table",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_gcp(
    s,
    "bq-stream-preview",
    "BigQuery › stream.partidas_rejeitadas › Visualização",
    COLETA,
    f"{CONSOLE}bigquery?project={COLETA}&p={COLETA}&d=stream&page=dataset",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 8. batch + stream
s = novo("Batch e stream juntos", "streaming · 5/5")
tabela(
    s,
    [
        ["View", "O que mostra"],
        [
            "`gold.partidas_unificadas`",
            "partidas da silver (`batch`) + último estado de cada partida "
            "do stream, com os mesmos ids de clube",
        ],
        [
            "`gold.partidas_atual`",
            "o estado mais recente de cada partida: o que a plataforma lê",
        ],
        [
            "`gold.predicoes_avaliadas`",
            "cada predição ao lado do resultado real, e se acertou",
        ],
    ],
    0.55,
    1.5,
    6.1,
    [2.3, 3.8],
    11,
    0.62,
)
topicos(
    s,
    [
        "A versão encerrada vence uma mais nova: a API às vezes devolve uma rodada jogada como "
        "agendada.",
        "Silver e gold também vão em Parquet para um bucket público (31 arquivos, 29.655 "
        "partidas): a API e a plataforma leem sem conta no GCP.",
    ],
    0.55,
    4.25,
    6.1,
    2.1,
    14,
)
links(
    s,
    [
        (
            "06_partidas_unificadas.sql",
            "sql/10_stream/06_create_view_partidas_unificadas.sql",
        ),
        (
            "exportar_tabelas_publicas.sh",
            "scripts/exportar_tabelas_publicas.sh",
        ),
    ],
    0.55,
    6.55,
    6.3,
)
print_gcp(
    s,
    "bq-unificadas",
    "BigQuery › SELECT origem, mode, COUNT(*) FROM "
    "gold.partidas_unificadas GROUP BY 1, 2",
    COLETA,
    f"{CONSOLE}bigquery?project={COLETA}",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_gcp(
    s,
    "gcs-publico",
    "Cloud Storage › bucket foota-toota-505511 (silver/ e gold/)",
    COLETA,
    f"{CONSOLE}storage/browser/foota-toota-505511?project={COLETA}",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 9. treino
s = novo("Modelo: treino e regra de promoção", "modelo · 1/4")
topicos(
    s,
    [
        "Um `HistGradientBoostingClassifier` por liga (Brasileirão e Premier League), sobre a "
        "gold pública: casa, empate ou fora.",
        "Hiperparâmetros pela log loss em EVAL, retreino em TRAIN + EVAL, medida em TEST, que não "
        "entra em nenhuma escolha.",
        (
            "Só é promovido se, em TEST, bater",
            [
                'o "sempre mandante" em acurácia',
                "as frequências do treino em log loss",
                "o campeão atual nas mesmas partidas",
            ],
        ),
    ],
    0.55,
    1.45,
    6.1,
    4.8,
    15,
)
tabela(
    s,
    [
        ["TEST, versão 1", "Brasileirão", "Premier League"],
        ["Partidas", "669", "407"],
        [
            "Acurácia: modelo / sempre mandante",
            "50,1% / 49,3%",
            "45,0% / 41,5%",
        ],
        ["Log loss: modelo / frequências", "1,012 / 1,044", "1,060 / 1,093"],
    ],
    6.9,
    4.25,
    5.9,
    [2.7, 1.6, 1.6],
    11,
    0.42,
)
links(s, [("treinar.py", "modelo/treinar.py#L148-L222")], 0.55, 6.55)
print_gcp(
    s,
    "vertex-experiments",
    "Vertex AI › Experiments › foota-toota-resultado "
    "(runs aprovados e reprovados)",
    MODELO,
    f"{CONSOLE}vertex-ai/experiments?project={MODELO}",
    6.9,
    1.45,
    5.9,
    2.55,
)

# ---------------------------------------------------------------- 10. registry
s = novo("Vertex AI Model Registry", "modelo · 2/4")
topicos(
    s,
    [
        "`boosted_tree_brasileirao` e `boosted_tree_epl`, versão 1 com o alias `campeao`.",
        "A API serve a versão que tem o alias e confere a cada 10 minutos: promover outra versão "
        "é mover o alias, sem novo deploy.",
        "Cada execução do treino, aprovada ou não, vira um run no Vertex AI Experiments.",
        "Um retreino nos mesmos dados empatou com o campeão e foi reprovado: empate não promove.",
    ],
    0.55,
    1.45,
    5.6,
    4.8,
    15,
)
links(
    s,
    [
        ("treinar.py: registrar", "modelo/treinar.py#L276-L337"),
        ("api.py: Registry", "modelo/api.py#L316-L387"),
    ],
    0.55,
    6.55,
)
print_gcp(
    s,
    "vertex-registry",
    "Vertex AI › Model Registry (os dois modelos)",
    MODELO,
    f"{CONSOLE}vertex-ai/models?project={MODELO}",
    6.4,
    1.45,
    6.4,
    2.45,
)
print_gcp(
    s,
    "vertex-versoes",
    "Vertex AI › Model Registry › boosted_tree_brasileirao "
    "(versões e alias campeao)",
    MODELO,
    f"{CONSOLE}vertex-ai/models?project={MODELO}",
    6.4,
    4.05,
    6.4,
    2.4,
)

# ---------------------------------------------------------------- 11. api
s = novo("API do modelo no Cloud Run", "modelo · 3/4")
tabela(
    s,
    [
        ["Rota", "O que faz"],
        [
            "`POST /predict`",
            "recebe o `match_id` (ou as features, para simular) e devolve as "
            "probabilidades de casa, empate e fora",
        ],
        [
            "`POST /pubsub`",
            "recebe o push de `eventos-api`, prevê as partidas agendadas e publica "
            "em `predicoes`",
        ],
        [
            "`GET /health`",
            "versão do modelo e partidas carregadas de cada liga",
        ],
    ],
    0.55,
    1.5,
    6.1,
    [1.5, 4.6],
    11,
    0.58,
)
topicos(
    s,
    [
        "FastAPI; imagem pelo Cloud Build e Artifact Registry; deploy com `deploy_api.sh`.",
        "Escala a zero: a 1ª chamada leva ~25 s, as seguintes menos de meio segundo.",
        "`/pubsub` valida o token OIDC do Pub/Sub: sem token, 401.",
    ],
    0.55,
    4.05,
    6.1,
    2.3,
    14,
)
links(
    s,
    [
        ("api.py", "modelo/api.py#L856-L955"),
        ("Dockerfile", "modelo/Dockerfile"),
        ("deploy_api.sh", "modelo/deploy_api.sh"),
        ("Swagger", f"{API}/docs"),
    ],
    0.55,
    6.55,
    6.3,
)
print_gcp(
    s,
    "cloudrun-api",
    "Cloud Run › modelo-api › Métricas (requisições, latência, instâncias)",
    MODELO,
    f"{CONSOLE}run/detail/us-central1/modelo-api/metrics?project={MODELO}",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_gcp(
    s,
    "cloudrun-logs",
    "Cloud Run › modelo-api › Registros (fdorg_… -> home)",
    MODELO,
    f"{CONSOLE}run/detail/us-central1/modelo-api/logs?project={MODELO}",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 12. ao vivo
s = novo("A API respondendo ao vivo (03/11/2026)", "modelo · 4/4")
bloco(
    s,
    f"$ curl -s -X POST {API}/predict \\\n"
    '    -d \'{"match_id": "fdorg_555052", "publicar": false}\'\n'
    "{\n"
    '  "match_id": "fdorg_555052",\n'
    '  "league_id": "brasileirao_serie_a",\n'
    '  "model_name": "boosted_tree_brasileirao",\n'
    '  "model_version": "1",\n'
    '  "prob_home": 0.6325,\n'
    '  "prob_draw": 0.1909,\n'
    '  "prob_away": 0.1766,\n'
    '  "predicted_outcome": "home"\n'
    "}\n"
    '$ curl -s -X POST .../predict -d \'{"match_id": "2aa61d11-…"}\'   # EPL\n'
    "  boosted_tree_epl v1: home 0.6502 · draw 0.2074 · away 0.1424\n"
    "$ curl -s -X POST .../pubsub -d '{}'   # sem token OIDC\n"
    "  401",
    0.55,
    1.45,
    6.3,
    5.0,
    11,
)
print_repo(
    s,
    "swagger",
    "Swagger da API: /predict executado",
    "api_docs_predict.jpg",
    6.95,
    1.45,
    5.85,
    2.45,
)
print_repo(
    s,
    "health",
    "GET /health: as duas ligas carregadas",
    "term_api1.jpg",
    6.95,
    4.05,
    5.85,
    2.4,
)

# ---------------------------------------------------------------- 13. evento -> avaliacao
s = novo("Do evento à avaliação da predição", "integração")
passos = [
    (
        "1",
        "Evento agendado",
        "o coletor publica em `eventos`; o push entrega em `/pubsub`",
    ),
    (
        "2",
        "Predição",
        "a API prevê com a versão `campeao` e publica em `predicoes`",
    ),
    ("3", "Gravação", "a assinatura BigQuery grava em `stream.predicoes`"),
    (
        "4",
        "Resultado",
        "o placar chega pelo stream e `predicoes_avaliadas` marca o acerto",
    ),
]
for i, (n, t, d) in enumerate(passos):
    y = 1.5 + i * 1.22
    bola = s.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(0.55), Inches(y), Inches(0.55), Inches(0.55)
    )
    bola.fill.solid()
    bola.fill.fore_color.rgb = VERDE
    bola.line.fill.background()
    bola.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    r = bola.text_frame.paragraphs[0].add_run()
    r.text = n
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = BRANCO
    texto(s, t, 1.3, y - 0.02, 5, 0.35, 16, negrito=True)
    topicos(s, [d], 1.25, y + 0.34, 5.3, 0.7, 12)
texto(
    s,
    "O Pub/Sub entrega pelo menos uma vez: o prediction_id é o mesmo para o mesmo evento "
    "e a mesma versão do modelo, então reentrega não duplica.",
    0.55,
    6.05,
    6.1,
    0.5,
    12,
    cor=CINZA,
)
links(
    s,
    [
        ("api.py: /pubsub", "modelo/api.py#L935-L955"),
        (
            "08_predicoes_avaliadas.sql",
            "sql/10_stream/08_create_view_predicoes_avaliadas.sql",
        ),
    ],
    0.55,
    6.6,
    6.3,
)
print_gcp(
    s,
    "bq-predicoes-vs-real",
    "BigQuery › modelo.predicoes_vs_real (replay: predição, placar e hit)",
    MODELO,
    f"{CONSOLE}bigquery?project={MODELO}&p={MODELO}&d=modelo&page=dataset",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_gcp(
    s,
    "bq-acerto-por-versao",
    "BigQuery › modelo.acerto_por_versao",
    MODELO,
    f"{CONSOLE}bigquery?project={MODELO}&p={MODELO}&d=modelo&page=dataset",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 14. escolhas
s = novo("Escolhas técnicas", "por quê")
escolhas = [
    ("Particionamento por dia", "o stream só escreve na partição do dia"),
    (
        "Cluster pela chave de leitura",
        "liga e partida: a página de um jogo lê poucos blocos",
    ),
    (
        "Bronze do stream sem código",
        "assinatura BigQuery grava mesmo com o Dataflow desligado",
    ),
    (
        "Quarentena, não descarte",
        "inválidos ficam com motivo e mensagem original",
    ),
    ("Reentrega sem duplicar", "event_id e prediction_id determinísticos"),
    (
        "Serverless e barato",
        "job que roda e termina; API escala a zero; Dataflow desligável",
    ),
]
for i, (t, d) in enumerate(escolhas):
    x = 0.55 + (i % 3) * 4.15
    y = 1.55 + (i // 3) * 2.55
    card = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(3.9),
        Inches(2.25),
    )
    card.adjustments[0] = 0.06
    card.fill.solid()
    card.fill.fore_color.rgb = VERDE_CLARO
    card.line.fill.background()
    texto(s, t, x + 0.25, y + 0.3, 3.4, 0.8, 18, cor=VERDE, negrito=True)
    texto(s, d, x + 0.25, y + 1.15, 3.4, 0.9, 14)

# ---------------------------------------------------------------- 15. qualidade
s = novo("Qualidade e reprodutibilidade", "engenharia")
topicos(
    s,
    [
        "106 testes automatizados (coletor, pipeline, API e treino), com o HTTP simulado: "
        "`uv run pytest`.",
        "CI no GitHub Actions: lint (`ruff`), tipos (`ty`) e testes a cada push na `main`.",
        "No batch, regras S1–S23 e G1–G8 como `ASSERT` bloqueantes, incluindo a prova de zero "
        "vazamento temporal.",
        "Treino reproduzível sem registrar nada: `treinar.py --sem-registrar` aprovou os dois "
        "modelos de novo hoje.",
    ],
    0.55,
    1.45,
    6.1,
    4.8,
    15,
)
links(
    s,
    [
        ("tests/", f"{REPO}/tree/main/tests"),
        ("ci.yml", ".github/workflows/ci.yml"),
    ],
    0.55,
    6.55,
)
print_repo(
    s,
    "pytest",
    "uv run pytest: 106 passed",
    "term_pytest.jpg",
    6.9,
    1.45,
    5.9,
    2.45,
)
print_repo(
    s,
    "treino",
    "treinar.py --sem-registrar: aprovado nas duas ligas",
    "term_treino_log.jpg",
    6.9,
    4.05,
    5.9,
    2.4,
)

# ---------------------------------------------------------------- 16. reproduzir
s = novo("Como reproduzir", "comandos")
bloco(
    s,
    "# streaming (projeto pdm-bia-505511)\n"
    "streaming/infra.sh               # tópicos, assinaturas, dataset stream, views\n"
    "streaming/deploy_coletor.sh      # Cloud Run Job + Scheduler (5 min)\n"
    "streaming/dataflow.sh iniciar    # pipeline no Dataflow\n"
    "uv run python streaming/producer.py replay --rodadas 28-30 --intervalo 1\n"
    "\n"
    "# modelo (projeto pdm-andre-2026)\n"
    "uv run --no-project --with-requirements modelo/requirements-treino.txt \\\n"
    "    python modelo/treinar.py      # treina, avalia, registra no Vertex AI\n"
    "modelo/deploy_api.sh             # imagem + deploy no Cloud Run\n"
    "\n"
    f"curl -s {API}/health",
    0.55,
    1.45,
    8.0,
    4.6,
    12,
)
caixa_links = topicos(
    s,
    [
        "Repositório",
        "Contratos do pipeline",
        "Roteiro da demo do modelo",
        "API: Swagger",
    ],
    8.85,
    1.45,
    4.0,
    2.5,
    14,
).text_frame.paragraphs
for p, url in zip(
    caixa_links,
    [
        REPO,
        CODIGO + "docs/arquitetura/contratos.md",
        CODIGO + "docs/arquitetura/demo-modelo.md",
        f"{API}/docs",
    ],
    strict=True,
):
    r = p.runs[-1]
    r.font.color.rgb = AZUL
    r.hyperlink.address = url

saida = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).with_name("trabalho2.pptx")
)
# Arquivo menor para subir pelo conector do Drive: só o layout em branco.
for layout in list(prs.slide_layouts):
    if layout is not BRANCO_LAYOUT:
        prs.slide_layouts.remove(layout)
prs.save(saida)
print(
    saida, saida.stat().st_size, "bytes,", len(prs.slides._sldIdLst), "slides"
)
