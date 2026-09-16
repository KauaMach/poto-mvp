"""Provider `log` — o default, e o que roda na demonstração.

Não envia nada: escreve a notificação no log do serviço. É o que permite o
sistema inteiro funcionar de ponta a ponta sem WhatsApp, sem Evolution API e
sem internet — útil em desenvolvimento, e indispensável na banca, onde a rede
não é confiável e ninguém quer acionar o CSV de verdade.

Por ser o default, é também o comportamento de quem sobe o serviço sem
configurar nada. Isso é intencional: o estado inicial do sistema não pode ser
"disca para o 190".
"""

from __future__ import annotations

import logging

logger = logging.getLogger("poto.notificacao")


class LogProvider:
    """Registra a notificação no log e reporta sucesso."""

    nome = "log"

    async def enviar(
        self, destino: str, mensagem: str, meta: dict
    ) -> tuple[bool, str]:
        logger.info(
            "[%s] %s -> %s\n%s",
            meta.get("gravidade", "—"),
            meta.get("chamado_id", "—"),
            mascarar(destino),
            mensagem,
        )
        return True, "registrado no log"


def mascarar(destino: str) -> str:
    """Esconde o contato, preservando o fim para conferência.

    O log é o lugar mais fácil de vazar sem perceber: journald é copiado,
    colado num chat de suporte, anexado a um relatório. Os últimos dígitos
    bastam para distinguir o CSV da Sala Lilás durante a depuração, que é o
    único uso legítimo do número aqui.
    """
    if not destino:
        return "(sem contato configurado)"
    if len(destino) <= 4:
        return "*" * len(destino)
    return f"…{destino[-4:]}"
