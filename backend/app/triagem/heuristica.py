"""Heurística de palavras-chave — a rede de segurança final.

Roda quando o classificador não está disponível: artefato ausente, corrompido,
ou `make setup` que nunca rodou. Não tem dependência externa nenhuma — só a
biblioteca padrão — então funciona em qualquer circunstância em que o processo
esteja de pé.

Não é bom quanto o classificador, e não precisa ser. Precisa ser **protetiva**:
na dúvida, escolhe a interpretação que encaminha para um canal 24h em vez de
deixar um pedido de socorro na Ouvidoria.

Duas correções em relação ao projeto de referência:

1. **Fronteira de palavra.** Lá o casamento era substring crua, e `"arma"` está
   na lista de sinais críticos — então *"o armário do laboratório está quebrado"*
   disparava emergência. Aqui `arma` só casa a palavra inteira.
2. **Radicais explícitos.** Lá a lista tinha `desmaio` e `desmaiou`, mas não
   `desmaiando`, e "estou desmaiando" caía na Ouvidoria. Aqui `desmai*` cobre
   toda a família.
"""

from __future__ import annotations

import re
import unicodedata

from ..models import Gravidade, TipoOcorrencia

# `termo`  → casa a palavra inteira ("arma" não casa "armário")
# `termo*` → casa o radical    ("desmai*" casa desmaio, desmaiou, desmaiando)
PALAVRAS: dict[TipoOcorrencia, list[str]] = {
    TipoOcorrencia.mulher: [
        "assedi*", "estupr*", "ex-namorado", "ex namorado", "marido",
        "persegu*", "me segue", "me seguindo", "me seguiu", "seguindo",
        "me bateu", "me bate", "violencia", "importuna*", "abus*", "cantada",
        "sala lilas",
    ],
    TipoOcorrencia.seguranca: [
        "roubo", "roubaram", "assalt*", "ladra*", "arma", "armado", "armada",
        "briga", "agress*", "invas*", "perigo", "suspeit*", "furt*",
        "ameac*", "socorro*", "me ajuda", "fogo", "fumaca", "incendio",
        "vazamento de gas", "cheiro de gas",
    ],
    TipoOcorrencia.saude: [
        "passando mal", "passar mal", "desmai*", "convuls*", "dor no peito",
        "sangrando", "sangramento", "falta de ar", "nao respira",
        "ansiedade", "panico", "depress*", "suicid*", "me matar",
        "tirar minha vida", "remedi*", "enfermaria", "ambulancia",
    ],
    TipoOcorrencia.ouvidoria: [
        "reclama*", "denunci*", "sugest*", "sugerir", "elogi*",
        "informacao", "informacoes", "onde fica", "horario", "secretaria",
        "carteirinha", "atestado",
    ],
}

# Emergência inequívoca: qualquer um destes leva a gravidade ao topo,
# independente do tipo que a contagem de palavras tiver escolhido.
SINAIS_CRITICOS = [
    "suicid*", "me matar", "tirar minha vida", "arma", "armado", "armada",
    "sangrando", "nao respira", "desmai*", "convuls*", "estupr*",
    "dor no peito", "falta de ar", "passando mal", "passar mal",
    "fogo", "incendio", "fumaca", "cheiro de gas", "socorro*",
    # Radical em vez de forma fixa: "ameaçaram de morte", "ameaçou de morte" e
    # "ameaça de morte" são a mesma coisa para quem está sendo ameaçado.
    "ameac* de morte", "vai me matar", "vao me matar",
]

# Medo ou perseguição sem categoria clara. Não é emergência confirmada, mas
# também não é assunto de ouvidoria: sem isto, "tem alguém atrás de mim" viraria
# orientação.
SINAIS_AMEACA = [
    "medo", "seguindo", "me seguindo", "atras de mim", "sozinha", "sozinho",
    "estranho", "estranhos", "fugindo", "escondid*", "me ajuda", "perseguindo",
]


def normalizar(texto: str) -> str:
    """Minúsculas e sem acento.

    Normalizar uma vez aqui elimina a duplicação que a referência carregava
    (`"assédio"` **e** `"assedio"` em cada lista) e ainda pega quem digitou sem
    acento — o que, num tablet e sob estresse, é a regra e não a exceção.
    """
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _compilar(termos: list[str]) -> re.Pattern[str]:
    """Traduz a notação das listas para regex.

    O `*` vale em **qualquer** posição, não só no fim: `ameac* de morte` precisa
    casar "ameaçaram de morte" e "ameaçou de morte" igualmente.
    """
    partes = []
    for termo in termos:
        alvo = normalizar(termo)
        # Escapa tudo e só então devolve o significado ao asterisco.
        corpo = re.escape(alvo).replace(r"\*", r"\w*")
        # Sem `\b` final quando o termo acaba em radical: o `\w*` já consumiu a
        # palavra inteira, e exigir fronteira ali nunca casaria.
        fim = "" if alvo.endswith("*") else r"\b"
        partes.append(rf"\b{corpo}{fim}")
    return re.compile("|".join(partes))


_PADROES = {tipo: _compilar(termos) for tipo, termos in PALAVRAS.items()}
_CRITICOS = _compilar(SINAIS_CRITICOS)
_AMEACA = _compilar(SINAIS_AMEACA)


def tem_sinal_critico(texto: str | None) -> bool:
    """Emergência inequívoca no texto. Consumido pelo merge protetivo."""
    return bool(texto) and bool(_CRITICOS.search(normalizar(texto)))


def tem_sinal_ameaca(texto: str | None) -> bool:
    return bool(texto) and bool(_AMEACA.search(normalizar(texto)))


def classificar(texto: str | None) -> dict:
    """Classifica por contagem de palavras. **Nunca devolve `None`.**

    Diferente do classificador, que devolve `None` quando não pode opinar, a
    heurística é o último recurso: sempre precisa produzir um encaminhamento.
    """
    alvo = normalizar(texto or "")

    pontos = {tipo: len(padrao.findall(alvo)) for tipo, padrao in _PADROES.items()}
    melhor = max(pontos, key=lambda t: pontos[t])
    critico = tem_sinal_critico(texto)
    ameaca = tem_sinal_ameaca(texto)

    if pontos[melhor] == 0:
        # Sem categoria clara. Havendo sinal de medo ou perseguição, trata como
        # segurança — canal 24h — em vez de ouvidoria. É a escolha protetiva:
        # errar para cima custa uma notificação, errar para baixo custa tempo de
        # quem está em risco.
        melhor = TipoOcorrencia.seguranca if ameaca else TipoOcorrencia.ouvidoria

    if critico:
        gravidade = Gravidade.risco_imediato
    elif ameaca or melhor in (TipoOcorrencia.seguranca, TipoOcorrencia.mulher):
        gravidade = Gravidade.risco_potencial
    else:
        gravidade = Gravidade.orientacao

    return {
        "tipo": melhor.value,
        "gravidade": gravidade.value,
        "confianca": _confianca(pontos[melhor], critico),
        "sinal_critico": critico,
    }


def _confianca(ocorrencias: int, critico: bool) -> float:
    """Deliberadamente modesta.

    A heurística é fallback: alta confiança aqui daria a impressão de uma
    certeza que contagem de palavras não sustenta. O teto é 0,75, e só com
    sinal crítico — quando a evidência é literal.
    """
    if ocorrencias == 0:
        return 0.2
    base = min(0.35 + 0.15 * ocorrencias, 0.65)
    return round(min(base + 0.10, 0.75) if critico else base, 2)
