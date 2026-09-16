"""Endpoints de sistema: diagnóstico e configuração.

O `/health` aqui é a versão mínima que a MVP-026 exige para validação. A MVP-036
o expande com o modo de triagem, os canais sem contato e o build-id do frontend.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import db

router = APIRouter(tags=["sistema"])


@router.get("/health")
def health() -> dict:
    """Diagnóstico do serviço.

    Reporta o que **de fato** está funcionando, não o que deveria estar — o
    projeto de referência afirmava usar IA sem estar usando, e não havia como
    perceber a degradação. A MVP-036 acrescenta os demais campos.
    """
    return {
        "status": "ok",
        "banco": _banco_responde(),
    }


def _banco_responde() -> bool:
    try:
        with db.conectar() as con:
            con.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False
