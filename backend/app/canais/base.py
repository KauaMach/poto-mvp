"""Contrato dos providers e a montagem do que sai do sistema.

Aqui mora a fronteira de dados do P.O.T.O: tudo que atravessa daqui para fora
— WhatsApp, webhook, log — passa por `resumo()`. O resto do chamado fica no
banco, atrás do token do painel.

**`texto_livre` nunca sai.** É o relato de quem pediu ajuda, muitas vezes de
uma violência que a pessoa está sofrendo naquele momento. A notificação chega
num grupo de WhatsApp institucional, onde pode ser encaminhada, printada ou
lida por quem passar pelo celular do plantonista. O que o destinatário precisa
saber para agir é *onde*, *que tipo* e *quão grave* — não o relato.

A garantia é estrutural, não um cuidado ao escrever a f-string: `resumo()`
copia uma **lista de campos permitidos**, então um campo novo no chamado não
vaza por esquecimento. Vazaria pelo caminho oposto — alguém teria que
acrescentá-lo a `CAMPOS_NOTIFICAVEIS` de propósito, e essa linha é revisável.
"""

from __future__ import annotations

from typing import Protocol

from .. import config
from ..models import Gravidade, Modo, TipoOcorrencia


class NotificationProvider(Protocol):
    """Como um meio de notificação se comporta.

    `enviar` é assíncrono porque o webhook (MVP-029) fala HTTP com timeout de
    10 s. Num provider síncrono, esses 10 s congelariam o event loop inteiro —
    e com ele o painel, o WebSocket e o acionamento de qualquer outro totem.
    Numa Pi rodando um processo só, uma notificação lenta pararia o sistema.

    Nunca levanta: devolve `(sucesso, detalhe)`. Falhar em avisar é um evento
    esperado (rede caiu, webhook fora do ar) e precisa virar registro, não
    exceção — o chamado já existe e não pode ser perdido por causa do aviso.
    """

    nome: str

    async def enviar(
        self, destino: str, mensagem: str, meta: dict
    ) -> tuple[bool, str]: ...


# A lista de campos que podem sair do sistema. Curta de propósito.
#
# Ausentes e por quê:
#   texto_livre    o relato — o dado mais sensível do banco
#   triagem_json   o que o classificador inferiu sobre o relato
#   observacao     nota interna do operador da central
#   acked_at, updated_at, id   ruído operacional, sem uso para quem atende
CAMPOS_NOTIFICAVEIS = (
    "chamado_id",
    "totem_id",
    "tipo_ocorrencia",
    "gravidade",
    "canal_roteado",
    "modo",
    "created_at",
)

ROTULO_TIPO = {
    TipoOcorrencia.seguranca: "Segurança",
    TipoOcorrencia.mulher: "Assédio / Sala Lilás",
    TipoOcorrencia.saude: "Saúde",
    TipoOcorrencia.ouvidoria: "Ouvidoria",
}

ROTULO_GRAVIDADE = {
    Gravidade.risco_imediato: "RISCO IMEDIATO",
    Gravidade.risco_potencial: "Risco potencial",
    Gravidade.orientacao: "Orientação",
}

# Marcador visual para quem bate o olho no celular às 3h da manhã.
MARCA_GRAVIDADE = {
    Gravidade.risco_imediato: "🔴",
    Gravidade.risco_potencial: "🟠",
    Gravidade.orientacao: "🔵",
}


def resumo(chamado: dict) -> dict:
    """Projeção do chamado com os campos que podem sair do sistema.

    Única porta de saída. `montar_mensagem` e `montar_meta` leem daqui e não do
    chamado, para que nem o texto da mensagem nem o corpo JSON do webhook
    possam carregar o relato.
    """
    return {campo: chamado.get(campo) for campo in CAMPOS_NOTIFICAVEIS}


def montar_mensagem(chamado: dict) -> str:
    """O texto que chega ao plantonista.

    Formatado para ser lido de relance num celular: gravidade primeiro,
    protocolo em seguida (é por ele que a central e a pessoa se encontram),
    local depois.
    """
    dados = resumo(chamado)
    gravidade = _ou(Gravidade, dados["gravidade"])
    tipo = _ou(TipoOcorrencia, dados["tipo_ocorrencia"])

    marca = MARCA_GRAVIDADE.get(gravidade, "⚪")
    rotulo = ROTULO_GRAVIDADE.get(gravidade, dados["gravidade"] or "—")

    linhas = [
        f"{marca} P.O.T.O — {rotulo}",
        f"Protocolo: {dados['chamado_id']}",
        f"Tipo: {ROTULO_TIPO.get(tipo, dados['tipo_ocorrencia'] or '—')}",
        f"Local: {dados['totem_id']}",
        f"Canal: {config.nome_canal(dados['canal_roteado'] or '')}",
    ]

    # Quem vai atender precisa saber que a abordagem é discreta: a pessoa pode
    # estar ao lado de quem a ameaça. Isto não revela nada que o canal já não
    # revele — a trilha `mulher` é sempre discreta.
    if dados["modo"] == Modo.discreto:
        linhas.append("Abordagem discreta — a pessoa pode estar acompanhada.")

    return "\n".join(linhas)


def montar_meta(chamado: dict) -> dict:
    """Payload estruturado que acompanha a mensagem no webhook.

    Mesma projeção da mensagem. É o ponto onde o vazamento seria mais fácil e
    mais silencioso: passar o chamado inteiro como `meta` mandaria o relato
    para fora sem que ninguém notasse, porque o texto da mensagem continuaria
    impecável.
    """
    return resumo(chamado)


def _ou(enum, valor):
    """Converte para o enum quando o valor é conhecido; devolve `None` se não.

    O chamado vem do SQLite como strings. Um valor inesperado — banco de uma
    versão antiga, registro adulterado — não pode derrubar a notificação de
    uma emergência por `ValueError`.
    """
    try:
        return enum(valor)
    except ValueError:
        return None
