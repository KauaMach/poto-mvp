"""Worker de SLA — o silêncio humano nunca arquiva um chamado.

Um laço que verifica, a cada `POTO_SLA_CHECK_INTERVAL`, se algum chamado passou
do prazo sem ninguém reconhecer. Passou, ele aciona o **canal de fallback** e
marca o chamado como `escalonado`.

É a única parte do sistema que age sem ninguém pedir, e por isso a mais
delicada de escrever. Duas garantias moldam o arquivo:

- **Escalona uma vez por chamado.** O status muda para `escalonado`, que não
  está entre os escalonáveis, então a próxima varredura não o vê. Se alguém na
  central mover o chamado de volta, a decisão é humana e registrada — não é o
  worker repetindo.
- **Nada derruba o laço.** Uma exceção numa varredura não pode encerrar o
  worker: ele é o que garante que uma emergência esquecida seja reencaminhada, e
  um worker morto falha em silêncio, que é a pior forma de falhar.

O que **não** escalona:

- `orientacao`, porque não há urgência a proteger (`config.SLA_SEGUNDOS` traz
  `None`);
- `alerta_ativo`, porque é persistente por decisão de projeto — mudar seu status
  rebaixaria o alerta que mantém o cronômetro do totem correndo. Um pânico já
  nasce com broadcast paralelo e com escalonamento manual na tela.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from . import canais, config, db
from .hub import hub
from .models import StatusChamado, para_painel

logger = logging.getLogger(__name__)


def prazo_de(gravidade: str) -> int | None:
    """Segundos até o ACK, ou `None` se aquela gravidade não escalona."""
    return config.SLA_SEGUNDOS.get(str(gravidade))


def atrasado(chamado: dict, agora: datetime | None = None) -> bool:
    """Se este chamado já passou do prazo sem reconhecimento.

    Mede a partir de `created_at`, o horário do servidor — nunca de
    `timestamp_local`, que é o relógio do tablet e pode estar dessincronizado.
    Um aparelho com a hora adiantada faria o chamado nascer "já atrasado"; com a
    hora atrasada, ele nunca escalonaria.
    """
    prazo = prazo_de(chamado["gravidade"])
    if prazo is None:
        return False

    agora = agora or datetime.now(UTC)
    try:
        criado = datetime.fromisoformat(chamado["created_at"])
    except (TypeError, ValueError):
        # Registro com data ilegível: não escalona, mas avisa. Escalonar por
        # não saber a hora seria acionar a PM por causa de um dado corrompido.
        logger.warning("%s: created_at ilegível, sem SLA", chamado["chamado_id"])
        return False

    if criado.tzinfo is None:
        criado = criado.replace(tzinfo=UTC)
    return (agora - criado).total_seconds() >= prazo


async def escalonar(chamado: dict) -> bool:
    """Aciona o fallback e move o chamado para `escalonado`.

    Devolve se houve escalonamento. Chamado sem `fallback` configurado **muda de
    status de todo modo**: o prazo estourou e isso é fato, mesmo que não haja
    para onde encaminhar. Deixá-lo em `notificado` faria a varredura seguinte
    tentar de novo, para sempre, e esconderia do painel que o prazo venceu.
    """
    canal = chamado.get("fallback")
    chamado_id = chamado["chamado_id"]

    if canal:
        sucesso, detalhe = await canais.notificar(chamado, canal)
        logger.info(
            "%s: SLA estourado, fallback %s -> %s (%s)",
            chamado_id,
            canal,
            "ok" if sucesso else "falhou",
            detalhe,
        )
    else:
        logger.warning("%s: SLA estourado sem canal de fallback", chamado_id)

    atualizado = db.atualizar_chamado(chamado_id, status=StatusChamado.escalonado)
    if atualizado is None:
        return False

    await hub.broadcast("atualizado", para_painel(atualizado))
    return True


async def varrer(agora: datetime | None = None) -> int:
    """Uma passada. Devolve quantos chamados escalonaram.

    Separada do laço de propósito: é o que permite o teste exercitar a decisão
    sem esperar relógio nenhum.
    """
    escalonados = 0
    for chamado in db.pendentes_de_ack():
        if atrasado(chamado, agora) and await escalonar(chamado):
            escalonados += 1
    return escalonados


async def loop() -> None:
    """O laço do worker. Roda até ser cancelado no encerramento do serviço.

    Dorme **antes** de varrer: quando o serviço acabou de subir, nada pode ter
    estourado prazo ainda, e uma varredura imediata a cada reinício seria só
    trabalho perdido.

    `except Exception` é o ponto inteiro desta função. Um erro de banco, um
    registro malformado, uma falha de rede no fallback — nada disso pode encerrar
    o worker. Ele é a rede que apara a emergência esquecida, e um worker morto
    falha em silêncio.
    """
    logger.info("worker de SLA iniciado (intervalo %ss)", config.SLA_CHECK_INTERVAL)
    while True:
        try:
            await asyncio.sleep(config.SLA_CHECK_INTERVAL)
            if (n := await varrer()) :
                logger.info("SLA: %d chamado(s) escalonado(s)", n)
        except asyncio.CancelledError:
            logger.info("worker de SLA encerrado")
            raise
        except Exception:
            logger.exception("erro na varredura de SLA; o worker continua")
