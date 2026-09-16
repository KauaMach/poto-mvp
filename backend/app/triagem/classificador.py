"""Classificador de triagem — TF-IDF + Regressão Logística.

O motor real da triagem. Medido no held-out: 83% de acurácia de tipo e 86% de
gravidade em poucos milissegundos, 100% offline. Os LLMs que cabem na Pi dão
29–45% em ~6 s — a comparação está em ARCHITECTURE.md D3.

Dois classificadores separados, um para `tipo` e outro para `gravidade`. São
decisões diferentes: "é caso de saúde?" e "é urgente agora?" não se determinam
mutuamente — alguém pode relatar mal-estar leve (saúde, orientação) ou parada
respiratória (saúde, risco imediato). Um classificador único sobre o par
tipo×gravidade teria 12 classes com poucos exemplos cada.

Degradação graciosa: sem o artefato treinado, `classificar()` devolve `None` e
quem chama cai na heurística. Nunca levanta exceção — um acionamento de
emergência não pode falhar porque o `make setup` não rodou.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import config

# Cache em memória, indexado pelo caminho de onde veio. Carregar o artefato do
# disco a cada acionamento desperdiçaria o ganho de latência que justifica esta
# abordagem; indexar pelo caminho faz o cache se refazer sozinho quando a
# configuração muda (útil em teste, e correto em produção).
_cache: dict[str, Any] = {"caminho": None, "modelo": None, "tentado": False}


def _construir_pipeline():
    """TF-IDF de palavra **e** de caractere, unidos, sobre Regressão Logística.

    Os n-gramas de caractere não são detalhe: com pouco dado rotulado, são eles
    que dão robustez a erro de digitação e variação morfológica. "socorroo",
    "tão me seguindo" e "passando maal" continuam caindo no lugar certo porque o
    modelo vê pedaços de palavra, não só a palavra inteira.

    `class_weight="balanced"` compensa o desequilíbrio entre trilhas — sem ele,
    a classe mais frequente no treino seria favorecida.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "palavra",
                            TfidfVectorizer(
                                analyzer="word",
                                ngram_range=(1, 2),
                                sublinear_tf=True,
                                min_df=1,
                            ),
                        ),
                        (
                            "caractere",
                            TfidfVectorizer(
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                sublinear_tf=True,
                                min_df=1,
                            ),
                        ),
                    ]
                ),
            ),
            (
                "clf",
                LogisticRegression(max_iter=1000, C=4.0, class_weight="balanced"),
            ),
        ]
    )


def treinar(dados: list[dict], caminho: str | None = None) -> dict:
    """Treina os dois classificadores e salva o artefato.

    `dados` são dicionários com `texto`, `tipo` e `gravidade` — o formato de
    `scripts/triagem_dataset.json`.
    """
    import joblib

    destino = Path(caminho or config.CLF_PATH)
    destino.parent.mkdir(parents=True, exist_ok=True)

    textos = [d["texto"] for d in dados]

    modelo_tipo = _construir_pipeline()
    modelo_tipo.fit(textos, [d["tipo"] for d in dados])

    modelo_gravidade = _construir_pipeline()
    modelo_gravidade.fit(textos, [d["gravidade"] for d in dados])

    artefato = {
        "tipo": modelo_tipo,
        "gravidade": modelo_gravidade,
        "meta": {
            "amostras": len(dados),
            "treinado_em": datetime.now(UTC).isoformat(),
        },
    }
    joblib.dump(artefato, destino)

    # Invalida o cache para que a próxima classificação use o modelo novo.
    _cache.update(caminho=None, modelo=None, tentado=False)

    return {
        "amostras": len(dados),
        "caminho": str(destino),
        "tamanho_kb": round(destino.stat().st_size / 1024),
    }


def _carregar() -> dict | None:
    """Carrega o artefato uma vez e mantém em memória.

    Só tenta o disco uma vez por caminho: se o arquivo não existe, insistir a
    cada acionamento custaria I/O à toa no caminho crítico.
    """
    caminho = config.CLF_PATH
    if _cache["tentado"] and _cache["caminho"] == caminho:
        return _cache["modelo"]

    modelo = None
    try:
        import joblib

        if Path(caminho).is_file():
            modelo = joblib.load(caminho)
    except Exception:
        # Artefato corrompido, incompatível com a versão do sklearn, ou
        # qualquer outra surpresa. Cair na heurística é degradação; levantar
        # exceção aqui derrubaria o acionamento.
        modelo = None

    _cache.update(caminho=caminho, modelo=modelo, tentado=True)
    return modelo


def disponivel() -> bool:
    """Se o classificador pode ser usado. `False` significa heurística."""
    return _carregar() is not None


def classificar(texto: str | None) -> dict | None:
    """Classifica um texto. Devolve `None` quando não há o que ou como classificar.

    `None` não é erro: é o sinal para quem chama usar a heurística.
    """
    if not texto or not texto.strip():
        return None

    modelo = _carregar()
    if modelo is None:
        return None

    try:
        entrada = [texto]
        tipo = modelo["tipo"].predict(entrada)[0]
        gravidade = modelo["gravidade"].predict(entrada)[0]
        return {
            "tipo": str(tipo),
            "gravidade": str(gravidade),
            "confianca": _confianca(modelo["tipo"], entrada),
            "confianca_gravidade": _confianca(modelo["gravidade"], entrada),
        }
    except Exception:
        return None


def _confianca(pipeline, entrada: list[str]) -> float:
    """Probabilidade da classe escolhida, arredondada."""
    return round(float(max(pipeline.predict_proba(entrada)[0])), 3)


def status() -> dict:
    """Diagnóstico para o `/health` (MVP-036).

    Reporta o que **de fato** está carregado, não o que deveria estar. O projeto
    de referência dizia estar usando IA sem estar, e não havia como perceber.
    """
    modelo = _carregar()
    info: dict[str, Any] = {
        "disponivel": modelo is not None,
        "caminho": config.CLF_PATH,
        "artefato_existe": Path(config.CLF_PATH).is_file(),
    }
    if modelo is not None:
        info["meta"] = modelo.get("meta", {})
    return info


def _resumo_json() -> str:
    """Usado pelo script de treino para imprimir o resultado."""
    return json.dumps(status(), ensure_ascii=False, indent=2)
