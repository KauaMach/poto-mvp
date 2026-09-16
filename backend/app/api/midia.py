"""`GET /dispositivos` — o que a Pi tem para capturar (MVP-073).

Rota da central: exige `X-POTO-Token`. Saber quais câmeras e microfones existem
num totem é informação de operação, não pública — e a lista é o primeiro passo
de qualquer captura.

Os endpoints de stream e de sessão entram nas MVP-075, 076 e 077.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import midia
from .deps import exigir_token

router = APIRouter(tags=["midia"], dependencies=[Depends(exigir_token)])


@router.get("/dispositivos")
def dispositivos() -> list[midia.Dispositivo]:
    """Câmeras e microfones detectados agora.

    **Lista vazia é resposta válida**, não erro: a Pi pode não ter câmera
    plugada, e a API sobe igual. Um 404 ou 503 aqui faria o painel tratar
    "sem hardware" como falha do serviço.

    Detecta a cada chamada, sem cache: uma câmera USB pode ser conectada com o
    sistema no ar, e um cache faria o operador ter que reiniciar o serviço para
    ela aparecer.
    """
    return midia.listar()
