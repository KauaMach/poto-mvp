"""Roteamento determinístico: decide para onde o chamado vai.

Esta é a rede de segurança do sistema. Não consulta classificador, não consulta
LLM, não consulta nada que possa estar fora do ar — só a trilha que a pessoa
escolheu, o modo e o relógio. Se toda a camada de IA falhar, o encaminhamento
continua correto.

A tabela que ele implementa está em ARCHITECTURE.md §4 e é a fonte da verdade:
qualquer divergência entre este arquivo e aquela tabela é bug aqui.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from ..config import FUSO_LOCAL, HORARIO_COMERCIAL
from ..models import Gravidade, InstrucaoTotem, Modo, TipoOcorrencia


class Roteamento(TypedDict):
    canal_roteado: str
    fallback: str
    gravidade: Gravidade
    instrucao: InstrucaoTotem
    horario_comercial: bool


# Mostrada no lugar da mensagem real quando o chamado é discreto. Não cita o
# canal acionado, não usa a palavra "denúncia", não revela nada a quem estiver
# olhando a tela por cima do ombro de quem pediu ajuda.
MENSAGEM_DISCRETA = "Seu pedido foi registrado. Aguarde atendimento."


def em_horario_comercial(agora: datetime) -> bool:
    """Se há alguém do outro lado para atender agora.

    Sala Lilás e SAPSI têm expediente. Encaminhar para uma sala vazia às 2h da
    manhã é o mesmo que não encaminhar.
    """
    if agora.weekday() not in HORARIO_COMERCIAL["dias"]:
        return False
    return any(inicio <= agora.hour < fim for inicio, fim in HORARIO_COMERCIAL["janelas"])


def rotear(
    tipo: TipoOcorrencia,
    modo: Modo = Modo.normal,
    *,
    emergencia: bool = False,
    agora: datetime | None = None,
) -> Roteamento:
    """Decide canal, fallback, gravidade e o que a tela deve mostrar.

    `emergencia` só afeta a trilha de saúde: separa "estou passando mal agora"
    (SAMU) de "preciso de apoio psicológico" (SAPSI). Quem determina isso é a
    triagem do texto, não a pessoa — na tela existe uma trilha de saúde só.

    `agora` é injetável para que o teste não dependa do relógio da máquina.
    """
    agora = agora or datetime.now(FUSO_LOCAL)
    comercial = em_horario_comercial(agora)
    discreto = modo == Modo.discreto

    if tipo == TipoOcorrencia.seguranca:
        canal, fallback = "csv", "pm_190"
        gravidade = Gravidade.risco_imediato
        mensagem = "Pedido de segurança enviado. Mantenha a calma, ajuda a caminho."

    elif tipo == TipoOcorrencia.mulher:
        # Sempre discreto, sem opção de desligar. Se o agressor está a três
        # metros, uma tela que anuncia "Sala Lilás acionada" transforma o
        # socorro em risco.
        discreto = True
        if comercial:
            canal, fallback = "sala_lilas", "central_180"
        else:
            # Fora do expediente a Sala Lilás não atende: vai direto para a
            # central estadual, que é 24h.
            canal, fallback = "central_180", "pm_190"
        gravidade = Gravidade.risco_potencial
        mensagem = "Recebido. Você está sendo encaminhada com sigilo."

    elif tipo == TipoOcorrencia.saude:
        if emergencia:
            canal, fallback = "samu_192", "csv"
            gravidade = Gravidade.risco_imediato
            mensagem = "Emergência de saúde acionada. Socorro a caminho (SAMU 192)."
        else:
            canal = "sapsi" if comercial else "ouvidoria"
            fallback = "ouvidoria"
            gravidade = Gravidade.orientacao
            mensagem = "Seu pedido de apoio foi registrado. A equipe entrará em contato."

    else:  # ouvidoria
        canal, fallback = "ouvidoria", "ouvidoria"
        gravidade = Gravidade.orientacao
        mensagem = "Manifestação registrada. Use o Fala.BR para o registro formal."

    return Roteamento(
        canal_roteado=canal,
        fallback=fallback,
        gravidade=gravidade,
        instrucao=InstrucaoTotem(
            mensagem_tela=MENSAGEM_DISCRETA if discreto else mensagem,
            # Sem bipe no modo discreto: nenhum som denuncia que o botão foi usado.
            feedback_sonoro=not discreto,
            tela_neutra=discreto,
        ),
        horario_comercial=comercial,
    )
