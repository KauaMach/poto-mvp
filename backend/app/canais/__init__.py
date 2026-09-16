"""Notificação dos canais — registry de providers e o acionamento em si.

Uma função só é chamada de fora: `notificar(chamado, canal)`. Ela resolve o
destino, monta o que pode sair, entrega ao provider configurado e grava a
tentativa. Quem aciona — `/eventos`, `/panico`, o escalonamento manual, o
worker de SLA — não sabe se o meio é WhatsApp, webhook ou log.

Duas garantias atravessam o módulo:

- **`notificar` nunca levanta.** O chamado já está no banco quando ela é
  chamada. Perder o registro de uma emergência porque o webhook está fora do
  ar seria trocar um problema pequeno por um grave.
- **Toda tentativa é gravada**, inclusive as que falharam. É o que torna
  "ninguém foi avisado" distinguível de "ninguém apareceu".
"""

from __future__ import annotations

import logging

from .. import config, db
from .base import NotificationProvider, montar_mensagem, montar_meta, resumo
from .log import LogProvider
from .webhook import WebhookProvider

logger = logging.getLogger(__name__)

PROVIDERS: dict[str, type] = {
    "log": LogProvider,
    "webhook": WebhookProvider,
}

PROVIDER_PADRAO = "log"


def obter_provider(nome: str | None = None) -> NotificationProvider:
    """O provider configurado, ou o `log` se o nome não existir.

    Nome desconhecido **não** impede o serviço de subir. Um erro de digitação
    em `POTO_NOTIF_PROVIDER` não pode derrubar um totem de emergência — o
    sistema degrada para o log, que continua registrando tudo, e o `/health`
    avisa (MVP-036). É a mesma escolha feita para o classificador ausente.

    Lê a configuração a cada chamada, sem cache: é o que permite trocar o
    provider em teste, e o custo de instanciar é irrelevante para o volume
    real (dezenas de acionamentos por dia).
    """
    escolhido = (nome or config.NOTIF_PROVIDER or PROVIDER_PADRAO).strip().lower()
    fabrica = PROVIDERS.get(escolhido)
    if fabrica is None:
        logger.warning(
            "provider de notificação desconhecido: %r — usando %r",
            escolhido,
            PROVIDER_PADRAO,
        )
        fabrica = PROVIDERS[PROVIDER_PADRAO]
    return fabrica()


def provider_configurado() -> str:
    """Nome do provider que será usado de fato — o que o `/health` reporta.

    Difere de `config.NOTIF_PROVIDER` quando este traz um nome inválido, e é
    justamente essa diferença que o diagnóstico precisa mostrar.
    """
    return obter_provider().nome


async def notificar(
    chamado: dict,
    canal: str,
    *,
    escalonamento: bool = False,
    provider: NotificationProvider | None = None,
) -> tuple[bool, str]:
    """Aciona um canal para um chamado e registra a tentativa.

    `escalonamento=True` marca o acionamento como decisão humana na tela de
    alerta ativo (MVP-034), separando-o do encaminhamento automático.
    """
    provider = provider or obter_provider()
    destino = config.contato_canal(canal)
    mensagem = montar_mensagem(chamado)
    chamado_id = chamado["chamado_id"]

    if not destino:
        # A trava contra o telefone embutido em código (ver `config.py`): sem
        # contato configurado, o canal simplesmente não é acionável. Registrado
        # como falha para que o painel mostre *por que* ninguém foi avisado, em
        # vez de um silêncio sem explicação.
        detalhe = "canal sem contato configurado"
        logger.warning("%s: canal %r sem contato — não acionado", chamado_id, canal)
        sucesso = False
    else:
        sucesso, detalhe = await _entregar(provider, destino, mensagem, chamado)

    db.registrar_notificacao(
        chamado_id,
        canal,
        destino,
        provider.nome,
        sucesso,
        mensagem=mensagem,
        detalhe=detalhe,
        escalonamento=escalonamento,
    )
    return sucesso, detalhe


async def _entregar(
    provider: NotificationProvider, destino: str, mensagem: str, chamado: dict
) -> tuple[bool, str]:
    """Chama o provider contendo qualquer falha dele.

    O contrato pede que `enviar` não levante, mas o contrato é uma promessa e
    esta é a rede embaixo dela: um provider com bug não pode fazer o
    acionamento de uma emergência estourar antes de ser registrado.
    """
    try:
        return await provider.enviar(destino, mensagem, montar_meta(chamado))
    except Exception as erro:
        logger.exception("provider %r falhou ao enviar", provider.nome)
        return False, f"erro no provider: {erro!r}"


__all__ = [
    "PROVIDERS",
    "LogProvider",
    "NotificationProvider",
    "WebhookProvider",
    "montar_mensagem",
    "montar_meta",
    "notificar",
    "obter_provider",
    "provider_configurado",
    "resumo",
]
