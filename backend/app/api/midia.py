"""Mídia: dispositivos, sessões e streams.

Três grupos de rota, com exigências diferentes:

- `GET /dispositivos` (MVP-073) — o que existe para capturar.
- `POST/DELETE /chamados/{id}/midia` (MVP-077) — abre e fecha a autorização.
- `GET /midia/{tipo}/{id}/stream` (MVP-075/076) — a captura em si.

Os dois primeiros exigem `X-POTO-Token`. **O terceiro não pode**, e a razão é
técnica: o stream vai num `<img src="…">` e num `<audio src="…">`, e o navegador
não deixa definir cabeçalhos nesses elementos. A autorização dele é a
`sessao` na query string — um token de uso único, com prazo de 10 minutos,
que só existe se alguém autenticado o pediu para um chamado ativo.

É a mesma troca consciente do `/ws` (MVP-040): query string aparece em log de
acesso, e por isso o que vai ali é um token efêmero e não a credencial do
painel.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from .. import midia
from ..midia import camera, microfone
from ..midia import sessao as sessoes
from ..models import MidiaIn, MidiaOut
from .deps import CABECALHO, exigir_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["midia"], dependencies=[Depends(exigir_token)])

# Sem a dependência de token: a autorização é a `sessao` da query string.
router_stream = APIRouter(tags=["midia"])


@router.get("/dispositivos")
def dispositivos() -> list[midia.Dispositivo]:
    """Câmeras e microfones detectados agora.

    **Lista vazia é resposta válida**, não erro: a Pi pode não ter câmera
    plugada, e a API sobe igual. Um 404 ou 503 aqui faria o painel tratar
    "sem hardware" como falha do serviço.

    Detecta a cada chamada, sem cache: uma câmera USB pode ser conectada com o
    sistema no ar, e um cache faria o operador reiniciar o serviço para ela
    aparecer.
    """
    return midia.listar()


@router.post("/chamados/{chamado_id}/midia", response_model=MidiaOut, status_code=201)
def abrir_midia(chamado_id: str, pedido: MidiaIn, request: Request) -> MidiaOut:
    """Autoriza captura de um dispositivo para este chamado.

    Recusa com **409** se o chamado está encerrado ou cancelado: um atendimento
    concluído não justifica olhar o corredor, e permitir isso transformaria o
    histórico de chamados numa lista de pretextos para ligar a câmera.
    """
    try:
        s = sessoes.abrir(chamado_id, pedido.dispositivo_id, _operador(request))
    except sessoes.SessaoRecusada as recusa:
        raise HTTPException(status_code=recusa.status, detail=recusa.detalhe) from None

    return MidiaOut(
        sessao_id=s.sessao_id,
        stream_url=sessoes.url_do_stream(s),
        expira_em=sessoes.DURACAO_SEG,
        dispositivo_id=s.dispositivo_id,
        tipo=s.tipo,
    )


@router.delete("/chamados/{chamado_id}/midia", status_code=204)
def fechar_midia(chamado_id: str, sessao: str | None = None) -> None:
    """Encerra imediatamente.

    Sem `sessao`, encerra **todas** as do chamado — é o que o painel chama ao
    fechar o detalhe, quando pode haver vídeo e áudio abertos juntos.
    """
    if sessao:
        sessoes.fechar(sessao)
    else:
        sessoes.fechar_do_chamado(chamado_id, "detalhe do chamado fechado")


@router.get("/chamados/{chamado_id}/midia/auditoria")
def auditoria(chamado_id: str) -> list[dict]:
    """O rastro de acesso à mídia deste chamado.

    Exposto na API, e não só no banco, porque auditoria que exige acesso ao
    servidor não é auditoria — é arquivo. Quem fiscaliza precisa poder olhar.
    """
    return midia_auditoria(chamado_id)


def midia_auditoria(chamado_id: str) -> list[dict]:
    from .. import db

    return db.listar_auditoria_midia(chamado_id)


# ===========================================================================
# Streams (MVP-075 / MVP-076)
# ===========================================================================
#
# Estas duas rotas ficam **fora** do router com token, e a razão é técnica: o
# vídeo vai num `<img src="…">` e o áudio num `<audio src="…">`, e o navegador
# não deixa definir cabeçalhos nesses elementos. A autorização é a `sessao` na
# query string — token efêmero, de 10 minutos, que só existe se alguém
# autenticado o pediu para um chamado ativo (MVP-077).
#
# Mesma troca consciente do `/ws` (MVP-040): query string aparece em log de
# acesso, e por isso o que vai ali é o token descartável e não a credencial do
# painel.

# Delimitador do multipart. Precisa ser o mesmo no cabeçalho e entre os frames.
LIMITE = "frame"


@router_stream.get("/midia/camera/{dispositivo_id}/stream")
def stream_camera(
    request: Request, dispositivo_id: str, sessao: str = ""
) -> StreamingResponse:
    """Vídeo ao vivo em MJPEG.

    `multipart/x-mixed-replace` é HTTP de 1995 e é exatamente o que serve aqui:
    o navegador renderiza num `<img>` **sem uma linha de JavaScript**, sem
    WebRTC, sem biblioteca, sem negociação de codec. Numa Pi 5 sem encoder
    H.264, é também o único transporte que não custa CPU de compressão
    (MVP-074).

    Sem `sessao` válida → **403**.
    """
    s = _validar(sessao, dispositivo_id)

    return StreamingResponse(
        _multipart(request, dispositivo_id, s),
        media_type=f"multipart/x-mixed-replace; boundary={LIMITE}",
        headers={
            # Um proxy ou o navegador guardando frames de câmera em cache seria
            # ao mesmo tempo inútil (a imagem muda) e indesejável (a imagem é
            # de um chamado).
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            # Impede o buffer do nginx, se alguém puser um na frente: com
            # buffer, o stream só aparece depois de acumular alguns KB, e o
            # operador vê tela preta por segundos.
            "X-Accel-Buffering": "no",
        },
    )


async def _multipart(
    request: Request, dispositivo_id: str, s: sessoes.Sessao
) -> AsyncIterator[bytes]:
    """Gera o corpo multipart, um frame por parte.

    **Assíncrono, e não síncrono — isto é uma correção de bug encontrado na Pi
    real.** Com um gerador síncrono, o Starlette o roda num threadpool, e quando
    o cliente desconecta o gerador fica bloqueado dentro da captura sem que o
    Python possa interrompê-lo: o `finally` não roda, e **a câmera fica presa
    até o processo morrer**. Verificado na Pi: depois de um `curl` interrompido,
    abrir a câmera de outro processo falhava com
    `RuntimeError: Camera __init__ sequence did not complete`.

    Sendo assíncrono, o Starlette chama `aclose()` ao cancelar a resposta, e o
    `finally` executa. Mais a checagem explícita de `is_disconnected()`, que
    encerra no primeiro frame após o cliente sair em vez de esperar a falha de
    escrita.

    A captura em si vai para um thread (`run_in_threadpool`): ela leva ~33 ms
    (MVP-074), e rodá-la no event loop bloquearia o servidor por um terço do
    tempo a 10 fps — o suficiente para atrasar um `POST /eventos`.
    """
    frames = camera.abrir(dispositivo_id)
    try:
        while True:
            # Duas condições de parada, e as duas são necessárias.
            #
            # `is_disconnected` é o caminho **normal** de encerramento de um
            # MJPEG: o operador fecha a aba. Sem checar, o stream só pararia na
            # próxima falha de escrita, um frame depois.
            if await request.is_disconnected():
                return
            # A sessão é checada a cada frame, não só na abertura. Sem isso, um
            # stream aberto no minuto 9 continuaria entregando vídeo por horas:
            # o prazo de 10 minutos existe para limitar a duração, e checar uma
            # vez só o tornaria decorativo.
            if s.expirada:
                logger.info("stream encerrado por expiração: %s", s.sessao_id)
                return

            frame = await run_in_threadpool(next, frames)
            yield (
                f"--{LIMITE}\r\n"
                f"Content-Type: image/jpeg\r\n"
                f"Content-Length: {len(frame)}\r\n\r\n"
            ).encode() + frame + b"\r\n"
    except StopIteration:
        return
    except camera.CameraIndisponivel as erro:
        # Câmera desconectada no meio. Encerrar o stream é o certo: o `<img>`
        # do painel mostra a última imagem e o operador percebe que congelou.
        logger.warning("stream de %s interrompido: %r", dispositivo_id, erro)
    finally:
        # A linha que impede a câmera de ficar travada. Roda no desconecte, na
        # expiração, no erro e no encerramento da aplicação.
        frames.close()


# ---------------------------------------------------------------------------
# Áudio (MVP-076)
# ---------------------------------------------------------------------------


@router_stream.get("/midia/microfone/{dispositivo_id}/stream")
def stream_microfone(
    request: Request, dispositivo_id: str, sessao: str = ""
) -> StreamingResponse:
    """Áudio ao vivo em WAV por chunks.

    Mesma escolha do MJPEG no vídeo: `audio/wav` toca num `<audio src="…">`
    **sem uma linha de JavaScript** — sem WebRTC, sem MSE, sem biblioteca. Um
    formato de 1991 que resolve o problema de 2026.

    O cabeçalho vai com tamanho desconhecido (`0xFFFFFFFF`), que é a convenção
    para WAV em fluxo — o mesmo que o `ffmpeg` escreve num pipe. O custo é o
    player mostrar uma duração absurda; para escuta ao vivo isso não atrapalha.

    **A sessão da câmera não serve aqui.** `validar()` confere o dispositivo, e
    áudio é mais invasivo que imagem: sem essa checagem, um pedido de vídeo
    daria de graça o som do local (MVP-077).

    Sem `sessao` válida → **403**.
    """
    s = _validar(sessao, dispositivo_id)

    return StreamingResponse(
        _wav(request, dispositivo_id, s),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _wav(
    request: Request, dispositivo_id: str, s: sessoes.Sessao
) -> AsyncIterator[bytes]:
    """Cabeçalho WAV, depois os blocos PCM crus.

    **Assíncrono pelo mesmo motivo do vídeo**, e a consequência aqui é ainda
    pior: um gerador síncrono no threadpool deixaria o `arecord` rodando depois
    de o cliente sair, e um `arecord` órfão mantém o dispositivo ALSA preso — a
    próxima sessão falharia com "device busy" até alguém reiniciar o serviço.

    O `next()` vai para um thread porque a leitura espera o bloco encher: 100 ms
    a cada volta, que bloqueariam o event loop e atrasariam um `POST /eventos`.
    """
    blocos = microfone.abrir(dispositivo_id)
    try:
        # O cabeçalho primeiro: o player precisa dele para saber a taxa e o
        # número de canais antes da primeira amostra.
        yield microfone.cabecalho_wav()
        while True:
            if await request.is_disconnected():
                return
            # Checado a cada bloco, não só na abertura: sem isso, um stream
            # aberto no minuto 9 seguiria entregando áudio por horas, e o prazo
            # de 10 min da sessão viraria decoração.
            if s.expirada:
                logger.info("áudio encerrado por expiração: %s", s.sessao_id)
                return
            yield await run_in_threadpool(next, blocos)
    except StopIteration:
        return
    except microfone.MicrofoneIndisponivel as erro:
        # Microfone desconectado no meio. Encerrar é o certo: o player para e o
        # operador percebe, em vez de ouvir silêncio achando que o local está
        # calmo. **Silêncio falso é pior que erro visível** num totem de
        # emergência.
        logger.warning("áudio de %s interrompido: %r", dispositivo_id, erro)
    finally:
        blocos.close()


@router_stream.get("/midia/microfone/{dispositivo_id}/clipe")
async def clipe_microfone(dispositivo_id: str, sessao: str = "", segundos: float = 15.0):
    """Um WAV fechado, de duração definida.

    É o **fallback previsto pela task**: se o stream contínuo se mostrar
    instável — rede oscilando, player que não lida com tamanho desconhecido —
    um clipe resolve o essencial, que é ouvir o local. Sendo arquivo completo,
    toca em qualquer player e pode ser baixado.

    O teto de 60 s não é arbitrário: a sessão dura 10 min e um clipe longo
    ocuparia o dispositivo sem o operador poder interromper, além de segurar a
    resposta HTTP todo esse tempo.
    """
    s = _validar(sessao, dispositivo_id)
    duracao = max(1.0, min(float(segundos), 60.0))

    try:
        dados = await run_in_threadpool(microfone.clipe, dispositivo_id, duracao)
    except microfone.MicrofoneIndisponivel as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from None

    return Response(
        content=dados,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            # `inline` e não `attachment`: o padrão é ouvir no painel, não
            # baixar um arquivo com o som de um chamado para a pasta de
            # downloads de quem atende.
            "Content-Disposition": (
                f'inline; filename="poto-{s.chamado_id}-{int(duracao)}s.wav"'
            ),
        },
    )


def _validar(sessao_id: str, dispositivo_id: str) -> sessoes.Sessao:
    """Traduz a recusa de sessão em HTTP.

    Tudo vira **403**, inclusive sessão inexistente: distinguir "não existe" de
    "expirou" diria a quem tenta adivinhar se acertou o formato do token.
    """
    try:
        return sessoes.validar(sessao_id, dispositivo_id)
    except sessoes.SessaoRecusada as recusa:
        raise HTTPException(status_code=403, detail=recusa.detalhe) from None


def _operador(request: Request) -> str | None:
    """Quem pediu a sessão.

    Hoje o sistema tem **um** token compartilhado (MVP-040), não contas
    individuais, então o melhor disponível é o endereço de quem chamou. Fica
    registrado como tal, sem fingir identidade que o sistema não tem — um campo
    `operador` com um nome inventado seria pior que um IP honesto.
    """
    quem = request.client.host if request.client else "?"
    marcado = "com token" if request.headers.get(CABECALHO.lower()) else "sem token"
    return f"{quem} ({marcado})"
