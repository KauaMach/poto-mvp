"""Enums do domínio — a linguagem do sistema.

Estes cinco tipos são o vocabulário que atravessa todas as camadas: triagem,
roteamento, persistência, API e interface falam nestes termos.

Todos são `StrEnum` (Python 3.11+), e não `(str, Enum)`: com a forma antiga,
`str(Gravidade.risco_imediato)` devolve `"Gravidade.risco_imediato"` em vez do
valor. Bastaria um `str(...)` ou uma f-string no caminho até o SQLite ou até a
mensagem de notificação para gravar lixo silenciosamente. Com `StrEnum`, o
valor é o que aparece em qualquer contexto de string.

Os contratos Pydantic de entrada e saída ficam neste mesmo módulo, mas chegam
na MVP-010.
"""

from __future__ import annotations

from enum import StrEnum


class TipoOcorrencia(StrEnum):
    """As quatro trilhas do totem. Cada uma tem canal, gravidade e
    comportamento de tela diferentes — por isso são tipos distintos, e não um
    chamado genérico com campos opcionais."""

    seguranca = "seguranca"
    mulher = "mulher"
    saude = "saude"
    ouvidoria = "ouvidoria"


class Modo(StrEnum):
    """`discreto` não é preferência de quem usa: é decisão do roteador.

    A trilha `mulher` é sempre discreta. Se o agressor está a três metros, uma
    tela que anuncia "Sala Lilás acionada" transforma o socorro em risco.
    """

    normal = "normal"
    discreto = "discreto"


class OrigemAcionamento(StrEnum):
    """Como o chamado nasceu.

    `botao_fisico` já existe no vocabulário embora o botão GPIO esteja fora do
    MVP (o pânico é virtual, MVP-046). É o gancho que permite o daemon de
    hardware entrar depois sem tocar no backend.
    """

    touch = "touch"
    botao_fisico = "botao_fisico"
    panico = "panico"


class Gravidade(StrEnum):
    """Ordem de proteção: orientacao < risco_potencial < risco_imediato.

    Esta ordem é o que o merge protetivo (MVP-023) usa para garantir que nada
    rebaixe a proteção já atribuída pelo roteador. A ordenação vive lá, não
    aqui — o enum só nomeia os degraus.
    """

    risco_imediato = "risco_imediato"
    risco_potencial = "risco_potencial"
    orientacao = "orientacao"


class StatusChamado(StrEnum):
    """Máquina de estados do chamado, registrada em `estado_log` (MVP-017).

    `alerta_ativo` é o único estado persistente: um pânico não fecha sozinho,
    só por ação da central.
    """

    recebido = "recebido"
    roteado = "roteado"
    notificado = "notificado"
    alerta_ativo = "alerta_ativo"
    reconhecido = "reconhecido"
    em_atendimento = "em_atendimento"
    escalonado = "escalonado"
    encerrado = "encerrado"
    falha_notificacao = "falha_notificacao"
    cancelado = "cancelado"
