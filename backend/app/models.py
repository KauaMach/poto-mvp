"""Enums do domínio — a linguagem do sistema.

Estes cinco tipos são o vocabulário que atravessa todas as camadas: triagem,
roteamento, persistência, API e interface falam nestes termos.

Todos são `StrEnum` (Python 3.11+), e não `(str, Enum)`: com a forma antiga,
`str(Gravidade.risco_imediato)` devolve `"Gravidade.risco_imediato"` em vez do
valor. Bastaria um `str(...)` ou uma f-string no caminho até o SQLite ou até a
mensagem de notificação para gravar lixo silenciosamente. Com `StrEnum`, o
valor é o que aparece em qualquer contexto de string.

A segunda metade do módulo traz os contratos Pydantic da API — o que entra e o
que sai de cada endpoint.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


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


# ===========================================================================
# Contratos da API
# ===========================================================================
#
# Princípio que guia a validação daqui: `/eventos` e `/panico` são caminhos de
# emergência. Rejeitar um acionamento por um campo diagnóstico malformado seria
# negar socorro por causa de metadado. Por isso a validação é estrita onde a
# correção importa (o `evento_id`, que garante idempotência) e tolerante onde
# não importa (o relógio do tablet).


class EventoIn(BaseModel):
    """Acionamento de uma trilha pelo totem."""

    # UUID de verdade, não string livre: este campo é a chave de idempotência.
    # Um valor malformado viraria uma chave inútil e o reenvio criaria um
    # segundo chamado para a mesma emergência.
    evento_id: UUID = Field(description="UUID gerado no totem, antes do envio.")
    totem_id: str = Field(min_length=1, max_length=64, examples=["TOTEM-CCS-01"])
    tipo_ocorrencia: TipoOcorrencia

    # O modo aqui é uma intenção do cliente, não a palavra final: o roteador
    # força `discreto` na trilha `mulher` independentemente do que chegue.
    modo: Modo = Modo.normal
    origem_acionamento: OrigemAcionamento = OrigemAcionamento.touch

    texto_livre: str | None = Field(
        default=None,
        max_length=2000,
        description="Descrição opcional, usada pela triagem. Nunca sai na notificação.",
    )

    # Relógio do tablet, só para diagnóstico — `str` e não `datetime` de
    # propósito. O horário autoritativo é o `created_at` do servidor, e um
    # aparelho com a hora dessincronizada não pode fazer um pedido de socorro
    # falhar com 422.
    timestamp_local: str | None = None


class InstrucaoTotem(BaseModel):
    """O que a tela deve mostrar e se deve emitir som.

    Quem decide é o backend, não o cliente. O modo discreto não pode depender
    de o frontend lembrar de aplicá-lo.
    """

    mensagem_tela: str
    feedback_sonoro: bool = True
    tela_neutra: bool = False


class EventoOut(BaseModel):
    """Resposta do acionamento."""

    chamado_id: str = Field(examples=["CALL-2026-000001"])
    status: StatusChamado
    canal_roteado: str
    gravidade: Gravidade
    instrucao_totem: InstrucaoTotem
    duplicado: bool = False


class PanicoIn(BaseModel):
    """Pânico: não passa por triagem de texto, é crítico por definição."""

    evento_id: UUID
    totem_id: str = Field(min_length=1, max_length=64)
    modo: Modo = Modo.normal
    timestamp_local: str | None = None


# `destino` não aparece em nenhum dos dois contratos abaixo, embora o projeto
# de referência o expusesse. `/panico` é um endpoint ABERTO — sem credencial,
# por decisão de projeto (um totem em pânico não pode falhar por autenticação).
# Devolver o telefone do CSV ou da Sala Lilás ali significaria entregar os
# contatos institucionais a qualquer um que alcance a API. O destino efetivo
# fica registrado na tabela `notificacoes`, atrás do token do painel.


class CanalResultado(BaseModel):
    """Resultado de uma perna do broadcast de pânico."""

    canal: str = Field(examples=["csv"])
    nome: str = Field(examples=["CSV / PREUNI"])
    sucesso: bool
    detalhe: str | None = None


class CanalOpcao(BaseModel):
    """Autoridade do estado oferecida para escalonamento manual na tela."""

    canal: str = Field(examples=["samu_192"])
    nome: str = Field(examples=["SAMU"])


class PanicoOut(BaseModel):
    chamado_id: str
    status: StatusChamado
    gravidade: Gravidade
    resultados: list[CanalResultado] = Field(default_factory=list)
    escalonamento_disponivel: list[CanalOpcao] = Field(default_factory=list)
    duplicado: bool = False


class ChamadoUpdate(BaseModel):
    """Atualização parcial pelo operador da central."""

    status: StatusChamado | None = None
    observacao: str | None = Field(default=None, max_length=2000)


class EscalonamentoIn(BaseModel):
    """Acionamento manual de uma autoridade do estado.

    Registra que um humano acionou o canal — o sistema não robo-disca.
    """

    canal: str = Field(examples=["samu_192"])
