"""Captura de vídeo — MVP-074.

Uma interface, duas origens. `abrir(id)` devolve um gerador de frames JPEG, e
quem consome não sabe se está lendo de uma câmera CSI pelo `picamera2` ou de
uma USB pelo V4L2.

Três decisões moldam o arquivo, e todas vêm do mesmo fato: **a Pi 5 não tem
encoder H.264 por hardware**.

- **JPEG, não H.264.** Sem encoder dedicado, comprimir H.264 seria software puro
  competindo com o núcleo do sistema. É também por isso que o transporte é
  MJPEG (MVP-075).

  Uma nota sobre o *mecanismo*, porque a primeira versão deste comentário
  errava: o JPEG aqui **é** codificado em software, pelo PIL — não sai pronto do
  ISP. O que a medição na Pi mostrou é que isso **não importa**: 640×480 a
  qualidade 80 custa menos de 2 ms por frame, dentro do ruído da medição. O
  custo real é a captura em si (~33 ms), não a compressão.

- **640×480 a 10 fps, por escolha e não por limite.** Medido na Pi: a captura
  sustenta **31,8 fps** com o encode incluído. O gerador desacelera para 10 de
  propósito — três vezes menos CPU, e 10 fps já mostra o que acontece num
  corredor. O critério da MVP-079 é "abaixo de 50% de CPU com um stream ativo",
  e é a folga que garante que acionar uma trilha durante um stream continue
  respondendo em menos de 2 s.
- **Um capturador por dispositivo, compartilhado.** Duas sessões simultâneas na
  mesma câmera não abrem duas capturas: a câmera é hardware exclusivo, e a
  segunda abertura falharia com "device busy". Compartilhar também é o que faz
  dois operadores verem a mesma imagem em vez de um deles ver um erro.

**Liberar sempre.** Uma câmera que não é fechada fica travada até o processo
morrer, e o sintoma é "a câmera parou de funcionar" depois de algumas sessões —
o pior tipo de bug de hardware, porque exige reiniciar o serviço para
diagnosticar.
"""

from __future__ import annotations

import io
import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator

from . import obter

logger = logging.getLogger(__name__)

# Suficiente para um corredor, barato para a Pi. Ver a nota no topo.
LARGURA = 640
ALTURA = 480
FPS = 10

# Qualidade JPEG. 80 é o ponto em que o artefato deixa de ser visível numa tela
# de painel; acima disso o arquivo cresce sem ganho perceptível.
QUALIDADE = 80


class CameraIndisponivel(RuntimeError):
    """O dispositivo não existe, não abriu, ou não é uma câmera."""


class _Captura:
    """Um capturador compartilhado por várias sessões.

    O contador de assinantes é o que permite liberar a câmera no momento certo:
    **quando o último sai**, não quando o primeiro sai. Sem ele, dois
    operadores vendo a mesma câmera perderiam a imagem assim que um fechasse a
    aba.
    """

    def __init__(self, dispositivo_id: str) -> None:
        self.dispositivo_id = dispositivo_id
        self._assinantes = 0
        self._trava = threading.Lock()
        self._ultimo_frame: bytes | None = None
        self._impl: _CameraCSI | _CameraUSB | None = None

    def entrar(self) -> None:
        with self._trava:
            if self._assinantes == 0:
                self._impl = _abrir_impl(self.dispositivo_id)
            self._assinantes += 1

    def sair(self) -> None:
        with self._trava:
            self._assinantes = max(0, self._assinantes - 1)
            if self._assinantes == 0 and self._impl is not None:
                try:
                    self._impl.fechar()
                finally:
                    self._impl = None
                    logger.info("câmera %s liberada", self.dispositivo_id)

    def frame(self) -> bytes:
        """Um frame JPEG. Levanta se a captura caiu no meio."""
        impl = self._impl
        if impl is None:
            raise CameraIndisponivel(f"{self.dispositivo_id} não está aberta")
        dados = impl.capturar()
        self._ultimo_frame = dados
        return dados

    @property
    def assinantes(self) -> int:
        return self._assinantes


# Um `_Captura` por dispositivo, criado na primeira abertura e mantido: o objeto
# é leve e guarda o contador; a câmera em si só fica aberta enquanto há
# assinante.
_capturas: dict[str, _Captura] = {}
_trava_registro = threading.Lock()


def _captura_de(dispositivo_id: str) -> _Captura:
    with _trava_registro:
        if dispositivo_id not in _capturas:
            _capturas[dispositivo_id] = _Captura(dispositivo_id)
        return _capturas[dispositivo_id]


# --- Implementações ---------------------------------------------------------


class _CameraCSI:
    """Câmera no conector CSI, via `picamera2`.

    A captura vem do ISP como RGB888 e o JPEG é feito pelo PIL. Medido na Pi:
    31,8 fps com o encode, 30,0 fps sem — a compressão desaparece no ruído.
    """

    def __init__(self, indice: int, rotacao: int = 0) -> None:
        from picamera2 import Picamera2

        self._cam = Picamera2(camera_num=indice)
        config = self._cam.create_video_configuration(
            main={"size": (LARGURA, ALTURA), "format": "RGB888"}
        )
        # A rotação vem do device-tree (MVP-073). A imx219 desta Pi reporta
        # 180°, e sem aplicar isso a imagem chega de cabeça para baixo.
        if rotacao == 180:
            config["transform"] = _transformada_180()
        self._cam.configure(config)
        self._cam.start()
        # A câmera precisa de alguns frames para o auto-exposure estabilizar;
        # sem esta pausa o primeiro frame do stream sai preto ou estourado.
        time.sleep(0.5)

    def capturar(self) -> bytes:
        from PIL import Image

        vetor = self._cam.capture_array("main")
        buffer = io.BytesIO()
        Image.fromarray(vetor).save(buffer, format="JPEG", quality=QUALIDADE)
        return buffer.getvalue()

    def fechar(self) -> None:
        try:
            self._cam.stop()
        finally:
            self._cam.close()


def _transformada_180():
    """Espelhamento duplo = 180°. `libcamera` não tem "rotação", tem flips."""
    from libcamera import Transform

    return Transform(hflip=1, vflip=1)


class _CameraUSB:
    """Câmera USB, via `ffmpeg` sobre V4L2.

    `ffmpeg` e não OpenCV: o segundo traria ~80 MB de dependência para fazer o
    que um pipe resolve, e a Pi não precisa de visão computacional — precisa de
    bytes JPEG.

    Não há câmera USB na Pi deste projeto (MVP-073 detectou só a CSI), então
    este caminho está **implementado e não exercitado em hardware**. O teste
    com captura falsa cobre a interface.
    """

    def __init__(self, device: str) -> None:
        if not shutil.which("ffmpeg"):
            raise CameraIndisponivel("ffmpeg ausente: sem suporte a câmera USB")
        self._proc = subprocess.Popen(
            [
                "ffmpeg", "-loglevel", "error",
                "-f", "v4l2", "-framerate", str(FPS),
                "-video_size", f"{LARGURA}x{ALTURA}",
                "-i", device,
                "-f", "image2pipe", "-vcodec", "mjpeg",
                "-q:v", "5", "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._buffer = b""

    def capturar(self) -> bytes:
        """Lê até completar um JPEG.

        MJPEG por pipe não delimita frames: o consumidor procura os marcadores
        `FFD8` (início) e `FFD9` (fim). Ler "um chunk e devolver" entregaria
        meio frame, e o navegador mostraria a imagem cortada.
        """
        assert self._proc.stdout is not None
        while True:
            inicio = self._buffer.find(b"\xff\xd8")
            fim = self._buffer.find(b"\xff\xd9", inicio + 2)
            if inicio != -1 and fim != -1:
                frame = self._buffer[inicio : fim + 2]
                self._buffer = self._buffer[fim + 2 :]
                return frame
            pedaco = self._proc.stdout.read(8192)
            if not pedaco:
                raise CameraIndisponivel("ffmpeg encerrou a captura")
            self._buffer += pedaco

    def fechar(self) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Um ffmpeg que ignora SIGTERM mantém a câmera travada. O SIGKILL
            # é feio e é o certo aqui.
            self._proc.kill()
            self._proc.wait(timeout=2)


def _abrir_impl(dispositivo_id: str):
    """Escolhe a implementação pelo dispositivo detectado."""
    disp = obter(dispositivo_id)
    if disp is None or disp["tipo"] != "camera":
        raise CameraIndisponivel(f"{dispositivo_id} não é uma câmera disponível")

    cap = disp["capacidades"]
    try:
        if cap.get("origem") == "csi":
            return _CameraCSI(int(cap["indice"]), int(cap.get("rotacao", 0)))
        return _CameraUSB(str(cap["device"]))
    except CameraIndisponivel:
        raise
    except Exception as erro:
        raise CameraIndisponivel(f"falha ao abrir {dispositivo_id}: {erro!r}") from erro


# --- Interface pública ------------------------------------------------------


def abrir(dispositivo_id: str) -> Iterator[bytes]:
    """Gerador de frames JPEG do dispositivo.

    O `finally` é o que impede a câmera de ficar travada: ele roda quando o
    cliente desconecta (o gerador é fechado), quando a aplicação encerra, e
    quando a captura falha no meio. Sem ele, o sintoma é "a câmera parou de
    funcionar" depois de algumas sessões — e só reiniciar o serviço resolve.
    """
    captura = _captura_de(dispositivo_id)
    captura.entrar()
    intervalo = 1.0 / FPS
    try:
        while True:
            inicio = time.monotonic()
            yield captura.frame()
            # Dorme o que resta do intervalo em vez de dormir fixo: se a
            # captura levou 60 ms, dormir 100 ms daria 6 fps em vez de 10.
            resto = intervalo - (time.monotonic() - inicio)
            if resto > 0:
                time.sleep(resto)
    finally:
        captura.sair()


def assinantes(dispositivo_id: str) -> int:
    """Quantas sessões estão lendo este dispositivo. Usado pelo `status`."""
    return _capturas[dispositivo_id].assinantes if dispositivo_id in _capturas else 0
