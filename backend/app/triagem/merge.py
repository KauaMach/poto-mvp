"""Merge protetivo — a única fonte da verdade sobre o que vale.

Combina **duas fontes de informação** sobre a mesma ocorrência:

- a **trilha** que a pessoa escolheu ao tocar o botão, traduzida pelo roteador
  determinístico em canal e gravidade;
- a **triagem** do texto que ela eventualmente escreveu, vinda do classificador
  ou da heurística.

A regra que governa tudo: **nada que a pessoa digite pode reduzir a proteção que
ela já obteve ao escolher a trilha.** Informação nova pode elevar a resposta,
nunca rebaixá-la.

Este módulo existe porque o projeto de referência não tinha um. Lá, a gravidade
do roteador era sobrescrita pela gravidade inferida do texto, sem proteção
nenhuma (`main.py:183-185`). Reproduzido em 15/09: na trilha Segurança, a
palavra **"socorro"** rebaixava o chamado de `risco_imediato` para `orientacao`
e o retinha aguardando operador. Pedir ajuda tornava o sistema menos responsivo
do que ficar calado.
"""

from __future__ import annotations

from datetime import datetime

from ..models import Gravidade, TipoOcorrencia
from . import heuristica
from .roteador import Roteamento, rotear

# Ordem de proteção. É o único lugar do sistema que define o que significa
# "mais protetivo" para gravidade.
RANK_GRAVIDADE = {
    Gravidade.orientacao: 1,
    Gravidade.risco_potencial: 2,
    Gravidade.risco_imediato: 3,
}


def mais_protetiva(a: str, b: str) -> Gravidade:
    """A maior gravidade entre duas. Base de todo o resto."""
    ga, gb = Gravidade(a), Gravidade(b)
    return ga if RANK_GRAVIDADE[ga] >= RANK_GRAVIDADE[gb] else gb


def merge_acionamento(
    routing: Roteamento,
    triagem: dict | None = None,
    *,
    texto: str | None = None,
    agora: datetime | None = None,
) -> Roteamento:
    """Decisão final sobre um acionamento.

    Devolve um `Roteamento` — mesmo contrato do roteador, para que quem consome
    não precise saber se houve texto ou não.

    Sem triagem (o caso do toque puro e do pânico), devolve o roteamento
    intacto: não há informação nova a incorporar.
    """
    if triagem is None:
        return routing

    tipo_final = _tipo_final(routing, triagem, texto)
    gravidade_final = _gravidade_final(routing, triagem, texto)

    # Recalcula o encaminhamento para o tipo e a gravidade finais. Sem isto, o
    # canal poderia ficar incoerente com a decisão — apontando para o CSV num
    # chamado que virou emergência de saúde.
    decisao = rotear(
        tipo_final,
        routing["modo"],
        emergencia=gravidade_final == Gravidade.risco_imediato,
        agora=agora,
    )

    # O roteamento acima pode devolver gravidade menor que a já estabelecida —
    # `rotear(saude)` sem emergência devolve `orientacao`, por exemplo. A
    # palavra final é sempre a mais protetiva.
    decisao["gravidade"] = mais_protetiva(decisao["gravidade"], gravidade_final)

    # O modo discreto nunca é revogado: se a trilha escolhida era discreta, a
    # tela continua neutra mesmo que o texto tenha redirecionado o tipo.
    if routing["instrucao"].tela_neutra:
        decisao["instrucao"] = routing["instrucao"]

    return decisao


def _gravidade_final(
    routing: Roteamento, triagem: dict, texto: str | None
) -> Gravidade:
    """O máximo entre trilha, triagem e sinal crítico no texto.

    Três fontes, todas podendo elevar, nenhuma podendo rebaixar.
    """
    gravidade = mais_protetiva(routing["gravidade"], triagem["gravidade"])

    # Sinal crítico é evidência literal de emergência ("socorro", "sangrando",
    # "ameaça de morte"). Promove independente do que o modelo tenha achado —
    # é a rede embaixo da rede.
    if triagem.get("sinal_critico") or heuristica.tem_sinal_critico(texto):
        gravidade = Gravidade.risco_imediato

    return gravidade


def _tipo_final(
    routing: Roteamento, triagem: dict, texto: str | None
) -> TipoOcorrencia:
    """Qual trilha vale no fim.

    **A trilha escolhida vence por padrão.** O texto só redireciona o tipo
    quando traz um sinal crítico — ou seja, quando revela uma emergência de
    natureza diferente da que o botão indicava.

    Isto é mais restritivo do que "o texto sempre vence", e de propósito.
    Deixar o texto redirecionar livremente cria combinações que nenhuma das
    duas fontes produziria sozinha: quem toca **Segurança** (risco imediato) e
    escreve *"preciso de um atestado"* seria reclassificado como saúde, herdaria
    o risco imediato da trilha, e o sistema **chamaria o SAMU para um pedido de
    atestado**. Superproteger é aceitável; inventar uma emergência que ninguém
    relatou, não.

    Com sinal crítico, redirecionar é claramente certo: quem toca Segurança e
    escreve *"estou desmaiando"* precisa do SAMU, não do CSV.
    """
    sugerido = TipoOcorrencia(triagem["tipo"])
    escolhido = routing["tipo"]

    if sugerido == escolhido:
        return escolhido

    # Ouvidoria nunca toma o lugar de uma trilha mais séria. É o caso do
    # critério explícito: texto trivial numa trilha de emergência não rebaixa.
    if sugerido == TipoOcorrencia.ouvidoria:
        return escolhido

    critico = triagem.get("sinal_critico") or heuristica.tem_sinal_critico(texto)
    return sugerido if critico else escolhido
