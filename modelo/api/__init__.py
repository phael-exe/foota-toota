"""API do modelo: prevê o resultado das partidas.

Um serviço Cloud Run com as rotas da seção 4 de docs/arquitetura/contratos.md:

  POST /predict  {"match_id": "fdorg_555047"}: devolve a predição no formato
                 da seção 3. Quem chama, no streaming, é o Dataflow
  GET  /health   versão do modelo e partidas carregadas de cada liga

Features: a gold pública de cada liga (gs://foota-toota-505511/gold/), relida
a cada RECARREGAR_SEGUNDOS. A partida é achada pelo match_id e, se não estiver
lá, pelo confronto (temporada, mandante, visitante): o replay do Brasileirão
traz ids `fdorg_` de jogos que a gold guarda com o id de outra fonte, e o
de-para de clubes sai do bronze público do Football-Data.org.

Modelos: um por liga no Vertex AI Model Registry de MODELO_PROJECT_ID, com o
display_name da tabela LIGAS. Vale a versão com o alias `campeao` (ou a
padrão), conferida a cada RECARREGAR_SEGUNDOS. O artefato é o `model.joblib`
do diretório da versão:

  - um estimador scikit-learn com predict_proba e classes_ iguais a
    {"home", "draw", "away"} (os rótulos de silver.matches.outcome);
  - entrada = array posicional na ordem do `features.json` da versão (sem
    ele, a de FEATURES), NaN onde falta dado; toda feature da lista precisa
    existir na gold;
  - treinado com o scikit-learn de modelo/requirements.txt.

Sem o Registry, MODELOS_DIR aponta uma pasta com <display_name>/model.joblib.

  cd modelo && uvicorn api.main:app --port 8080
"""

from __future__ import annotations

from .config import (
    CLASSES,
    DADOS,
    FEATURES,
    LIGAS,
    PIPELINE,
    RAIZ,
    Config,
    Liga,
    agora,
    ambiente,
)
from .features import (
    Features,
    baixar_publico,
    ler_parquet,
)
from .modelos import (
    Fonte,
    Modelo,
    Modelos,
    PastaLocal,
    Registry,
    SemModeloError,
    fonte_padrao,
    validar,
)
from .predicao import (
    predicao,
    prediction_id,
    probabilidades,
    vetor,
)
from .rotas import (
    Pedido,
    criar_app,
)


__all__ = [
    "CLASSES",
    "DADOS",
    "FEATURES",
    "LIGAS",
    "PIPELINE",
    "RAIZ",
    "Config",
    "Features",
    "Fonte",
    "Liga",
    "Modelo",
    "Modelos",
    "PastaLocal",
    "Pedido",
    "Registry",
    "SemModeloError",
    "agora",
    "ambiente",
    "baixar_publico",
    "criar_app",
    "fonte_padrao",
    "ler_parquet",
    "predicao",
    "prediction_id",
    "probabilidades",
    "validar",
    "vetor",
]
