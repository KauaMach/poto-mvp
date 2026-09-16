"""Triagem — a porta única.

Quem chama nunca sabe qual motor rodou. Isso é o que permite trocar a
implementação depois — um modelo ONNX, um acelerador, um LLM melhor — sem que
nada fora deste pacote precise mudar.

Precedência:

    classificador (TF-IDF + LogReg)  →  heurística (palavras-chave)

O classificador governa quando está disponível. A heurística é a rede de
segurança: funciona sem artefato treinado, sem dependência externa, sempre.

Sobre `fonte`: ela diz **a verdade** sobre qual motor produziu o resultado. O
projeto de referência carimbava `"agentes"` mesmo quando nenhum LLM havia
respondido — só a heurística tinha rodado — e não havia como perceber que a
triagem estava degradada. Aqui o campo reflete o que de fato executou.
"""

from __future__ import annotations

from datetime import datetime

from ..models import Gravidade, Modo, TipoOcorrencia
from . import classificador, heuristica
from .merge import mais_protetiva, merge_acionamento
from .roteador import Roteamento, rotear

__all__ = [
    "Roteamento",
    "mais_protetiva",
    "merge_acionamento",
    "motor_ativo",
    "rotear",
    "triar",
]


def motor_ativo() -> str:
    """Qual motor a próxima triagem usaria. Consumido pelo `/health`."""
    return "classificador" if classificador.disponivel() else "heuristica"


def triar(
    texto: str | None,
    modo: Modo = Modo.normal,
    *,
    agora: datetime | None = None,
) -> dict:
    """O que o **texto** indica, isoladamente.

    Devolve `tipo`, `gravidade`, `confianca`, `canal_sugerido`, `sinal_critico`
    e `fonte`. Nunca levanta exceção e nunca devolve `None` — um acionamento de
    emergência não pode falhar porque a triagem teve um problema.

    O resultado é uma **sugestão**, não a decisão: quem decide é
    `merge_acionamento()`, combinando isto com a trilha que a pessoa escolheu.
    """
    if not texto or not texto.strip():
        return _neutro(modo, agora)

    bruto = classificador.classificar(texto)
    fonte = "classificador"
    if bruto is None:
        bruto = heuristica.classificar(texto)
        fonte = "heuristica"

    # O sinal crítico é evidência literal no texto ("socorro", "sangrando",
    # "ameaça de morte") e precisa valer independentemente de qual motor
    # classificou. O classificador não produz este campo; sem calculá-lo aqui,
    # um resultado dele chegaria ao merge sem a rede de evidência literal.
    critico = bool(bruto.get("sinal_critico")) or heuristica.tem_sinal_critico(texto)

    tipo = TipoOcorrencia(bruto["tipo"])
    gravidade = Gravidade(bruto["gravidade"])
    if critico:
        gravidade = mais_protetiva(gravidade, Gravidade.risco_imediato)

    sugerido = rotear(
        tipo,
        modo,
        emergencia=gravidade == Gravidade.risco_imediato,
        agora=agora,
    )

    return {
        "tipo": tipo.value,
        "gravidade": gravidade.value,
        "confianca": bruto.get("confianca", 0.0),
        "canal_sugerido": sugerido["canal_roteado"],
        "sinal_critico": critico,
        "fonte": fonte,
    }


def _neutro(modo: Modo, agora: datetime | None) -> dict:
    """Resultado para texto ausente.

    `fonte` é `"vazio"` e não o nome de um motor: nenhum dos dois rodou, e
    dizer que rodou seria a mesma desonestidade que o projeto de referência
    cometia ao carimbar `"agentes"` sem LLM nenhum ter respondido.
    """
    sugerido = rotear(TipoOcorrencia.ouvidoria, modo, agora=agora)
    return {
        "tipo": TipoOcorrencia.ouvidoria.value,
        "gravidade": Gravidade.orientacao.value,
        "confianca": 0.0,
        "canal_sugerido": sugerido["canal_roteado"],
        "sinal_critico": False,
        "fonte": "vazio",
    }
