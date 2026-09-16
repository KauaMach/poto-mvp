"""Captura de vídeo — MVP-074.

A Pi real tem uma câmera CSI `imx219` e nenhuma USB, então estes testes usam
**captura falsa**: eles exercitam o contrato e o ciclo de vida, que é onde os
erros doem. O hardware foi verificado à parte, na Pi (números na nota da task).

O que se cobra aqui é o que um erro de ciclo de vida custa: uma câmera que não
é liberada fica travada até o processo morrer, e o sintoma é "a câmera parou de
funcionar" depois de algumas sessões — o pior tipo de bug de hardware, porque
exige reiniciar o serviço só para diagnosticar.
"""

from __future__ import annotations

import pytest

from app.midia import camera

JPEG_FALSO = b"\xff\xd8" + b"corpo" + b"\xff\xd9"

# Capturados **antes** de qualquer fixture mexer: a fixture acelera o `FPS`
# para o teste não esperar, e sem guardar os originais o teste de constantes
# afirmaria sobre o valor falso. Foi o que aconteceu na primeira versão.
FPS_REAL = camera.FPS
_abrir_impl_real = camera._abrir_impl


class CapturaFalsa:
    """Dublê de câmera. Conta aberturas e fechamentos."""

    aberturas = 0
    fechamentos = 0

    def __init__(self) -> None:
        CapturaFalsa.aberturas += 1
        self.fechada = False
        self.frames = 0

    def capturar(self) -> bytes:
        if self.fechada:
            raise AssertionError("capturou de uma câmera fechada")
        self.frames += 1
        return JPEG_FALSO

    def fechar(self) -> None:
        self.fechada = True
        CapturaFalsa.fechamentos += 1


@pytest.fixture(autouse=True)
def camera_falsa(monkeypatch):
    """Substitui a abertura real e zera o registro de capturadores.

    O registro é global (um capturador por dispositivo, compartilhado), então
    sem limpá-lo um teste herdaria o contador do anterior.
    """
    CapturaFalsa.aberturas = 0
    CapturaFalsa.fechamentos = 0
    monkeypatch.setattr(camera, "_capturas", {})
    monkeypatch.setattr(camera, "_abrir_impl", lambda _id: CapturaFalsa())
    # Sem espera entre frames: o pacing de 10 fps é real em produção e só
    # tornaria o teste 100× mais lento.
    monkeypatch.setattr(camera, "FPS", 10_000)


def tomar(gerador, n: int) -> list[bytes]:
    return [next(gerador) for _ in range(n)]


# --- Contrato ---------------------------------------------------------------


def test_abrir_devolve_frames_jpeg(monkeypatch):
    g = camera.abrir("csi:0")
    try:
        frames = tomar(g, 3)
    finally:
        g.close()

    assert len(frames) == 3
    assert all(f.startswith(b"\xff\xd8") and f.endswith(b"\xff\xd9") for f in frames)


def test_dispositivo_inexistente_levanta(monkeypatch):
    """Erro claro na abertura, não no meio do vídeo.

    O patch é em `camera.obter` e **não** em `app.midia.obter`: o módulo faz
    `from . import obter`, então ele guarda a referência e substituir o
    atributo do pacote não o alcança. Errei nisto na primeira versão, e o
    teste passou a "não levantar" — que é o oposto do que ele verifica.
    """
    monkeypatch.setattr(camera, "_abrir_impl", _abrir_impl_real)
    monkeypatch.setattr(camera, "obter", lambda _id: None)

    with pytest.raises(camera.CameraIndisponivel):
        next(camera.abrir("csi:99"))


def test_microfone_nao_e_camera(monkeypatch):
    """Pedir vídeo de um microfone é erro de quem chamou, e precisa dizer isso."""
    monkeypatch.setattr(camera, "_abrir_impl", _abrir_impl_real)
    monkeypatch.setattr(
        camera,
        "obter",
        lambda _id: {"id": "alsa:2,0", "tipo": "microfone", "capacidades": {}},
    )

    with pytest.raises(camera.CameraIndisponivel):
        next(camera.abrir("alsa:2,0"))


# --- Ciclo de vida: o que importa -------------------------------------------


def test_fechar_o_gerador_libera_a_camera():
    g = camera.abrir("csi:0")
    tomar(g, 2)
    assert camera.assinantes("csi:0") == 1

    g.close()

    assert camera.assinantes("csi:0") == 0
    assert CapturaFalsa.fechamentos == 1


def test_abandonar_o_gerador_tambem_libera():
    """O cliente desconecta e ninguém chama `close()` — o caso comum no stream.

    O coletor de lixo fecha o gerador, o que dispara o `finally`. Sem esse
    caminho, cada aba fechada no painel deixaria a câmera presa.
    """
    import gc

    g = camera.abrir("csi:0")
    tomar(g, 1)
    del g
    gc.collect()

    assert camera.assinantes("csi:0") == 0
    assert CapturaFalsa.fechamentos == 1


def test_excecao_na_captura_libera():
    """Falha no meio do vídeo não pode deixar a câmera travada."""

    class Explode(CapturaFalsa):
        def capturar(self) -> bytes:
            raise RuntimeError("cabo arrancado")

    camera._abrir_impl = lambda _id: Explode()
    g = camera.abrir("csi:0")

    with pytest.raises(RuntimeError):
        next(g)
    g.close()

    assert camera.assinantes("csi:0") == 0


# --- Compartilhamento -------------------------------------------------------


def test_duas_sessoes_compartilham_um_capturador():
    """A câmera é hardware exclusivo: a segunda abertura falharia com "device
    busy". Compartilhar é também o que faz dois operadores verem a mesma imagem
    em vez de um deles ver um erro."""
    a = camera.abrir("csi:0")
    b = camera.abrir("csi:0")
    tomar(a, 1)
    tomar(b, 1)

    assert camera.assinantes("csi:0") == 2
    assert CapturaFalsa.aberturas == 1

    a.close()
    b.close()


def test_libera_quando_o_ULTIMO_sai():
    """Não quando o primeiro. Sem o contador, dois operadores vendo a mesma
    câmera perderiam a imagem assim que um fechasse a aba."""
    a = camera.abrir("csi:0")
    b = camera.abrir("csi:0")
    tomar(a, 1)
    tomar(b, 1)

    a.close()
    assert camera.assinantes("csi:0") == 1
    assert CapturaFalsa.fechamentos == 0

    # A segunda sessão continua recebendo.
    assert next(b) == JPEG_FALSO

    b.close()
    assert camera.assinantes("csi:0") == 0
    assert CapturaFalsa.fechamentos == 1


def test_reabrir_depois_de_liberar_funciona():
    """Prova que o fechamento foi limpo. Se a câmera tivesse ficado travada,
    esta segunda abertura falharia — e é assim que o bug apareceria em produção,
    algumas sessões depois."""
    a = camera.abrir("csi:0")
    tomar(a, 1)
    a.close()

    b = camera.abrir("csi:0")
    assert next(b) == JPEG_FALSO
    b.close()

    assert CapturaFalsa.aberturas == 2
    assert CapturaFalsa.fechamentos == 2


def test_dispositivos_diferentes_nao_compartilham():
    a = camera.abrir("csi:0")
    b = camera.abrir("usb:video4")
    tomar(a, 1)
    tomar(b, 1)

    assert camera.assinantes("csi:0") == 1
    assert camera.assinantes("usb:video4") == 1
    assert CapturaFalsa.aberturas == 2

    a.close()
    b.close()


def test_assinantes_de_dispositivo_nunca_aberto():
    assert camera.assinantes("csi:9") == 0


# --- Resolução e taxa -------------------------------------------------------


def test_resolucao_e_fps_default():
    """640×480 a 10 fps: escolha, não limite. Medido na Pi, a captura sustenta
    31,8 fps — desacelerar deixa CPU para o acionamento (MVP-079).

    Compara com `FPS_REAL`, capturado na importação: a fixture acelera o `FPS`
    para o teste não esperar, e comparar com `camera.FPS` leria o valor falso.
    """
    assert (camera.LARGURA, camera.ALTURA) == (640, 480)
    assert FPS_REAL == 10


def test_qualidade_jpeg_configurada():
    assert 60 <= camera.QUALIDADE <= 90
