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


# ---------------------------------------------------------------------------
# Leitura pelo painel da central
# ---------------------------------------------------------------------------
#
# Estes contratos são **lista de campos permitidos**, pelo mesmo motivo do
# `resumo()` em `canais/base.py`: uma coluna acrescentada ao schema amanhã não
# passa a sair pela API por esquecimento. Ficam de fora, de propósito:
#
#   id            rowid interno; o identificador público é o `chamado_id`
#   evento_id     chave de idempotência do totem, sem uso para quem atende
#   triagem_json  sai no detalhe já decodificado, como `triagem`
#
# A diferença em relação à notificação externa é o `texto_livre`, que **sai**
# aqui: quem atende precisa do relato para decidir como responder, e o painel
# está dentro da fronteira de confiança. É o que torna a autenticação do painel
# (MVP-040) obrigatória e não opcional.


class ChamadoOut(BaseModel):
    """Um chamado como o painel o lista."""

    chamado_id: str = Field(examples=["CALL-2026-000001"])
    totem_id: str
    tipo_ocorrencia: TipoOcorrencia
    modo: Modo
    origem_acionamento: OrigemAcionamento
    gravidade: Gravidade
    canal_roteado: str
    fallback: str | None = None
    status: StatusChamado
    texto_livre: str | None = None
    observacao: str | None = None
    timestamp_local: str | None = None
    created_at: str
    updated_at: str
    acked_at: str | None = None


class NotificacaoOut(BaseModel):
    """Uma tentativa de acionamento, como o painel a exibe.

    `destino` vem **mascarado**. O contato completo fica só no banco: se a
    autenticação do painel atrasar ou for cortada, uma rota de leitura aberta
    não pode ser o caminho para enumerar os contatos institucionais de toda a
    universidade. Os últimos dígitos bastam para o operador conferir qual
    número foi usado.
    """

    canal: str
    nome: str = Field(examples=["CSV / PREUNI"])
    destino: str = Field(examples=["…0001"])
    provider: str
    sucesso: bool
    mensagem: str | None = None
    detalhe: str | None = None
    escalonamento: bool = False
    created_at: str


class EstadoOut(BaseModel):
    """Uma transição de estado. `de` é nulo na criação do chamado."""

    de: StatusChamado | None = None
    para: StatusChamado
    created_at: str


class ChamadoDetalhe(ChamadoOut):
    """O chamado com sua história: quem foi acionado e como ele andou.

    `triagem` é o registro de auditoria do merge — o que a máquina inferiu e
    qual trilha a pessoa de fato tocou. É o que responde "por que este chamado
    foi para o SAMU?" meses depois.
    """

    triagem: dict | None = None
    notificacoes: list[NotificacaoOut] = Field(default_factory=list)
    estados: list[EstadoOut] = Field(default_factory=list)


def para_painel(chamado: dict) -> dict:
    """Projeta um chamado do banco no formato que o painel recebe.

    Existe para que **o WebSocket e o REST falem a mesma língua**. Sem isto,
    `broadcast("novo_chamado", ...)` mandaria a linha crua do SQLite — com
    `id`, `evento_id` e `triagem_json` — enquanto `GET /chamados` manda
    `ChamadoOut`. O painel teria que lidar com dois formatos para a mesma
    coisa, e o tipo declarado no frontend mentiria sobre um dos dois.

    De quebra, o payload do WebSocket herda a mesma lista de campos
    permitidos: é a rota com mais chance de ficar sem autenticação se a
    MVP-040 atrasar.
    """
    return ChamadoOut.model_validate(chamado).model_dump(mode="json")


# Campos que o **totem** pode receber pelo WebSocket — COR-002.
#
# Lista de permitidos, e pelo mesmo motivo do `CAMPOS_NOTIFICAVEIS` em
# `canais/base.py`: uma coluna acrescentada ao `ChamadoOut` amanhã não passa a
# vazar para um aparelho de corredor por esquecimento.
#
# O problema que isto corrige: a tela de alerta ativo do totem assinava o mesmo
# `/ws` do painel, e o `broadcast` não filtrava por cliente. O totem recebia o
# `ChamadoOut` **completo de todos os chamados** — inclusive o `texto_livre`, o
# relato de quem pediu ajuda. A única proteção era um filtro no cliente, que
# descartava o que não era do chamado dele **depois** de o dado já ter chegado
# ao aparelho: visível no DevTools e no tráfego, que é `ws://` sem TLS.
#
# O totem precisa de duas coisas, e só: saber **qual** chamado e em **que
# estado** ele está. É disso que a tela vive ("Aguardando central" → "Central
# recebeu" → "Atendimento a caminho"). Não precisa do relato, nem do canal, nem
# da gravidade, nem de nada de outro chamado.
#
# Filtrar por `chamado_id` sozinho não resolveria: quem adivinhasse um protocolo
# — e eles são sequenciais — receberia o relato daquela pessoa. O escopo limita
# *quais* eventos chegam; esta lista limita *o que* cada evento carrega. As duas
# coisas juntas é que fecham o caminho.
# `stream_url` entra na lista por causa da MEL-006: é assim que o totem
# descobre onde buscar o vídeo do operador quando a central inicia a chamada.
# Ele não existe no `ChamadoOut`, então em `novo_chamado`/`atualizado` sai como
# `None` — uniformidade tem preço, e é menor que o de abrir uma exceção na
# allowlist para um evento específico.
#
# **Limitação honesta, e ela é real:** a URL carrega o token da sessão, e o
# canal `/ws/chamado/{id}` é aberto (o totem não tem credencial — lacuna
# conhecida da MVP-040). Então o vídeo do operador fica protegido apenas na
# medida em que o protocolo do chamado é secreto, e eles são sequenciais. Numa
# rede dedicada, como a da demonstração, é aceitável; numa rede compartilhada,
# não. Quem for tratar isso tem que dar credencial ao totem primeiro — não
# tentar esconder a URL, que é o que um `chamado_id` aleatório faria parecer
# resolver sem resolver.
CAMPOS_TOTEM = ("chamado_id", "status", "stream_url", "audio_url")


def para_totem(dados: dict) -> dict:
    """Projeta um evento no que o totem pode ver (COR-002)."""
    return {campo: dados.get(campo) for campo in CAMPOS_TOTEM}


class ChamadoUpdate(BaseModel):
    """Atualização parcial pelo operador da central."""

    status: StatusChamado | None = None
    observacao: str | None = Field(default=None, max_length=2000)


class MidiaIn(BaseModel):
    """Pedido de sessão de mídia (MVP-077)."""

    dispositivo_id: str = Field(examples=["csi:0"])


class MidiaOut(BaseModel):
    """Autorização concedida.

    `stream_url` já vem montada com a sessão embutida: o painel não precisa
    saber como compor a URL, e isso mantém o formato do token dentro do
    backend.
    """

    sessao_id: str
    stream_url: str
    expira_em: int = Field(description="Segundos até a sessão expirar.")
    dispositivo_id: str
    tipo: str


class ChamadaOut(BaseModel):
    """Videochamada autorizada da central para o totem (MEL-004).

    Duas URLs porque são dois papéis: a central **envia** quadros, o totem
    **consome**. Vêm montadas pelo backend, como no `MidiaOut` — o formato do
    token de sessão não é assunto de quem chama.
    """

    sessao_id: str
    envio_url: str
    stream_url: str
    # Uma URL só: a central publica com `POST`, o totem consome com `GET`.
    audio_url: str
    expira_em: int = Field(description="Segundos até a sessão expirar.")


class EscalonamentoIn(BaseModel):
    """Acionamento manual de uma autoridade do estado.

    Registra que um humano acionou o canal — o sistema não robo-disca.
    """

    canal: str = Field(examples=["samu_192"])
