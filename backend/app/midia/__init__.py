"""Detecção de câmeras e microfones da Raspberry Pi — MVP-073.

A Pi é **headless**: nenhum navegador roda nela, então `getUserMedia` não
existe e o tablet não enxerga esses dispositivos. A captura é server-side, e
este módulo é quem descobre o que há para capturar.

**Degradação graciosa é o requisito, não um extra.** Sem câmera, sem microfone,
sem `picamera2` instalado ou rodando numa máquina que não é uma Pi, a lista sai
vazia e a API sobe normalmente. Um totem que se recusa a atender porque a
câmera não foi plugada seria pior que um totem sem câmera — o núcleo do sistema
é o acionamento, e a mídia é apoio.

O `dono` de cada dispositivo já existe no contrato para que, no futuro, a
central possa listar câmeras de **outros** aparelhos (o tablet, um segundo
totem) sem mudar a forma da resposta.

Medido na Pi real (16/09): uma câmera CSI `imx219` e um microfone USB. A Pi
expõe **nove** `/dev/video*` para essa única câmera — CFE, sete nós do ISP e um
decodificador HEVC — e sete deles anunciam "Video Capture". Ver `_cameras_usb`
para o filtro que separa câmera de nó de processamento.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)

TipoDispositivo = Literal["camera", "microfone"]
StatusDispositivo = Literal["disponivel", "em_uso", "indisponivel"]


class Dispositivo(TypedDict):
    """Um dispositivo de captura. Contrato de `GET /dispositivos`."""

    id: str
    tipo: TipoDispositivo
    nome: str
    dono: str
    status: StatusDispositivo
    capacidades: dict[str, Any]


def dono() -> str:
    """Identificação de quem hospeda os dispositivos.

    Hoje é sempre esta Pi. O campo existe para que listar dispositivos de
    outros aparelhos depois não mude a forma da resposta.
    """
    try:
        return Path("/etc/hostname").read_text(encoding="utf-8").strip() or "pi"
    except OSError:
        return "pi"


# --- Câmeras ----------------------------------------------------------------


def _cameras_csi() -> list[Dispositivo]:
    """Câmeras conectadas ao conector CSI, via `picamera2`.

    Toda a detecção fica dentro do `try`: `picamera2` não existe fora da Pi, e
    mesmo nela ele levanta se o venv não foi criado com
    `--system-site-packages` — o módulo vem do apt, não do PyPI. Encontrado na
    Pi real, onde um venv de uma fase anterior deixava o import falhar.
    """
    try:
        from picamera2 import Picamera2
    except Exception as erro:
        logger.info("picamera2 indisponível: %r", erro)
        return []

    try:
        infos = Picamera2.global_camera_info()
    except Exception:
        logger.warning("picamera2 instalado mas falhou ao listar", exc_info=True)
        return []

    dispositivos: list[Dispositivo] = []
    for i, info in enumerate(infos):
        modelo = str(info.get("Model", "camera"))
        dispositivos.append(
            {
                # `csi:<índice>` e não o caminho do device-tree: aquele tem 60
                # caracteres e vai numa URL de stream.
                "id": f"csi:{i}",
                "tipo": "camera",
                "nome": f"Câmera CSI ({modelo})",
                "dono": dono(),
                "status": "disponivel",
                "capacidades": {
                    "origem": "csi",
                    "modelo": modelo,
                    # `Rotation` vem do device-tree e importa: a imx219 desta Pi
                    # reporta 180°, e sem aplicar isso a imagem chega de cabeça
                    # para baixo no painel.
                    "rotacao": info.get("Rotation", 0),
                    "indice": i,
                },
            }
        )
    return dispositivos


def _cameras_usb() -> list[Dispositivo]:
    """Câmeras USB, via V4L2.

    **O filtro é o ponto desta função**, e a primeira versão errou nele.
    `/dev/video*` na Pi 5 tem muito mais que câmeras: a Pi real expõe **nove**
    nós para **uma** câmera CSI — a interface CFE (`rp1-cfe`), sete nós do ISP
    (`pispbe`) e o decodificador HEVC (`rpi-hevc-dec`). Sete deles anunciam
    "Video Capture", então filtrar por isso listava oito câmeras inexistentes,
    e o operador escolheria uma que nunca entregaria imagem.

    A correção não foi acrescentar `pispbe` e `rpi-hevc-dec` a uma lista de
    exclusão — essa lista cresceria a cada versão de kernel e falharia em
    silêncio no primeiro nó novo. O teste é **positivo**, sobre o `Bus info`:

        /dev/video0   platform:1f00128000.csi        ← CSI
        /dev/video33  platform:1000880000.pisp_be    ← ISP
        câmera USB    usb-xhci-hcd.1-1.2             ← esta

    Um dispositivo no barramento USB é uma câmera de verdade; um em
    `platform:` é hardware interno da Pi, já coberto pelo `picamera2`. É a
    mesma escolha do `resumo()` em `canais/base.py`: permitir o que se conhece
    em vez de proibir o que se lembrou.

    Exige também `Video Capture` **single-planar**: os nós do ISP anunciam a
    variante *Multiplanar*, e webcams UVC não.
    """
    if not shutil.which("v4l2-ctl"):
        logger.info("v4l2-ctl ausente: sem detecção de câmera USB")
        return []

    dispositivos: list[Dispositivo] = []
    for node in sorted(Path("/dev").glob("video*")):
        try:
            saida = subprocess.run(
                ["v4l2-ctl", "-d", str(node), "--info"],
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout
        except (subprocess.SubprocessError, OSError):
            continue

        driver = _campo(saida, "Driver name")
        cartao = _campo(saida, "Card type")
        barramento = _campo(saida, "Bus info")

        # Teste positivo: só o que está no barramento USB.
        if not barramento.startswith("usb-"):
            continue
        # `Video Capture` seguido de fim de linha — a variante *Multiplanar* é
        # nó de ISP, não câmera.
        if not re.search(r"^\s*Video Capture\s*$", saida, re.M):
            continue
        if "Memory-to-Memory" in saida:
            continue

        dispositivos.append(
            {
                "id": f"usb:{node.name}",
                "tipo": "camera",
                "nome": cartao or f"Câmera USB ({node.name})",
                "dono": dono(),
                "status": "disponivel",
                "capacidades": {
                    "origem": "usb",
                    "device": str(node),
                    "driver": driver,
                    "barramento": barramento,
                },
            }
        )
    return dispositivos


def _campo(texto: str, rotulo: str) -> str:
    achado = re.search(rf"^\s*{re.escape(rotulo)}\s*:\s*(.+)$", texto, re.M)
    return achado.group(1).strip() if achado else ""


# --- Microfones -------------------------------------------------------------


def _microfones() -> list[Dispositivo]:
    """Entradas de áudio via ALSA, lendo `arecord -l`.

    `arecord` e não `sounddevice`: o segundo é binding de PortAudio, uma
    biblioteca C que **não vem** com o pacote pip e exige `libportaudio2` do
    apt. Na Pi real o import falha com `OSError: PortAudio library not found`.
    O `arecord` faz parte do `alsa-utils`, que já está instalado, e o critério
    da MVP-076 aceita os dois.
    """
    if not shutil.which("arecord"):
        logger.info("arecord ausente: sem detecção de microfone")
        return []

    try:
        saida = subprocess.run(
            ["arecord", "-l"], capture_output=True, text=True, timeout=3
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []

    dispositivos: list[Dispositivo] = []
    # "card 2: Device [USB Composite Device], device 0: USB Audio [USB Audio]"
    padrao = re.compile(
        r"^card (\d+): \S+ \[([^\]]+)\], device (\d+): [^\[]*\[([^\]]+)\]", re.M
    )
    for cartao, nome_cartao, device, nome_device in padrao.findall(saida):
        dispositivos.append(
            {
                # `plughw` e não `hw`: o plugin de conversão do ALSA permite
                # pedir 16 kHz mono mesmo que o hardware só faça 48 kHz
                # estéreo. Com `hw` direto, a captura falharia com
                # "Invalid argument" em metade dos microfones USB.
                "id": f"alsa:{cartao},{device}",
                "tipo": "microfone",
                "nome": f"{nome_cartao} — {nome_device}",
                "dono": dono(),
                "status": "disponivel",
                "capacidades": {
                    "origem": "alsa",
                    "device": f"plughw:{cartao},{device}",
                    # Voz não precisa de mais: 16 kHz mono é o padrão de
                    # telefonia e corta a banda em ~4×.
                    "taxa_hz": 16000,
                    "canais": 1,
                },
            }
        )
    return dispositivos


# --- API do módulo ----------------------------------------------------------


def listar() -> list[Dispositivo]:
    """Tudo que a Pi tem para capturar. Lista vazia é resposta válida.

    Nunca levanta: cada detector contém as próprias falhas, e um erro na
    enumeração de câmeras não pode esconder os microfones.
    """
    dispositivos: list[Dispositivo] = []
    for detectar in (_cameras_csi, _cameras_usb, _microfones):
        try:
            dispositivos.extend(detectar())
        except Exception:
            logger.exception("falha ao detectar com %s", detectar.__name__)
    return dispositivos


def obter(dispositivo_id: str) -> Dispositivo | None:
    """Um dispositivo pelo id, ou `None` se não existe mais.

    Redetecta em vez de usar cache: uma câmera USB pode ter sido desconectada
    entre a listagem no painel e o pedido de sessão, e abrir um stream para um
    dispositivo que sumiu daria erro no meio do vídeo em vez de um 404 claro.
    """
    return next((d for d in listar() if d["id"] == dispositivo_id), None)
