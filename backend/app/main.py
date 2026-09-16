"""P.O.T.O — aplicação FastAPI.

Este arquivo só monta: cria o app, liga o ciclo de vida, registra os routers e
serve o frontend. **Nenhuma regra de negócio mora aqui.** Quem decide o que é a
ocorrência está em `triagem/`, quem decide como avisar está em `canais/`, e quem
fala HTTP está em `api/`.

Um servidor serve tudo: a aplicação React compilada e a API na mesma origem.
O tablet e o notebook da central carregam as duas do mesmo lugar, então não há
CORS nem endpoint para configurar no cliente.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocketClose

from . import config, db, sla
from .api import chamados, eventos, midia, sistema

API = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialização e encerramento do serviço.

    `init_db()` é idempotente, então rodar a cada start é seguro e garante que
    um banco apagado (ou uma Pi com cartão novo) se reconstrua sozinho.

    O worker de SLA sobe aqui e é **cancelado no encerramento**. Sem o cancel,
    um `reload` em desenvolvimento deixaria workers acumulados varrendo o mesmo
    banco, e o encerramento do serviço travaria esperando uma tarefa que nunca
    termina.
    """
    db.init_db()
    worker = asyncio.create_task(sla.loop())
    try:
        yield
    finally:
        worker.cancel()
        # `suppress` porque o cancelamento é o caminho normal de saída: o laço
        # relança `CancelledError` de propósito, para que o cancel de fato
        # aconteça em vez de ser engolido.
        with suppress(asyncio.CancelledError):
            await worker


def criar_app() -> FastAPI:
    app = FastAPI(
        title="P.O.T.O",
        description="Totem de Segurança — UFPI",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
    )

    # Nunca "*". Em produção a aplicação vem da mesma origem do backend e o CORS
    # é irrelevante; a lista existe para o servidor do Vite em desenvolvimento.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sistema.router, prefix=API)
    app.include_router(eventos.router, prefix=API)
    app.include_router(chamados.router, prefix=API)
    app.include_router(chamados.router_ws, prefix=API)
    app.include_router(midia.router, prefix=API)
    app.include_router(midia.router_stream, prefix=API)

    _montar_frontend(app)
    return app


class _EstaticoSPA(StaticFiles):
    """Serve os arquivos do build e devolve `index.html` para rotas da aplicação.

    Sem isto, abrir `/painel` direto no navegador daria 404: não existe arquivo
    com esse nome. A aplicação é de página única e o roteamento acontece no
    cliente, então qualquer caminho desconhecido precisa entregar o `index.html`
    e deixar o React decidir.

    **Exceto sob `/api`.** O router trata as rotas registradas, mas uma rota de
    API inexistente cai aqui — e devolver `index.html` com 200 faria um cliente
    receber HTML onde espera JSON, além de mascarar erro de digitação no
    endpoint. Ali o 404 tem que continuar sendo 404.
    """

    async def __call__(self, scope, receive, send) -> None:
        """Recusa conexões WebSocket em vez de deixar o `StaticFiles` estourar.

        Montado na raiz, este app recebe **tudo** que o router não casou — e um
        WebSocket em caminho desconhecido chega aqui com `scope["type"] ==
        "websocket"`. O `StaticFiles` do Starlette começa com
        `assert scope["type"] == "http"`, então o resultado era um
        `AssertionError` virando **500 com traceback no log**.

        Encontrado ao digitar `/api/v1/ws/painel` em vez de `/api/v1/ws`: o
        erro dizia "500 Internal Server Error", que manda procurar defeito no
        servidor quando o problema é o caminho do cliente. Num painel que
        reconecta com espera crescente (MVP-054), um caminho errado encheria o
        journal de tracebacks idênticos.

        `WebSocketClose` é o que o próprio router do Starlette usa para rota
        WebSocket não encontrada; o cliente recebe uma recusa de handshake.
        """
        if scope["type"] != "http":
            await WebSocketClose()(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as erro:
            if erro.status_code != 404 or _e_rota_de_api(path):
                raise
            indice = Path(self.directory) / "index.html"
            if indice.is_file():
                return FileResponse(indice)
            raise


def _e_rota_de_api(path: str) -> bool:
    """`path` chega sem a barra inicial: `/api/v1/x` vira `api/v1/x`.

    Precisa cobrir também o `/api` exato, que não casa com um prefixo `api/`.
    """
    return path == "api" or path.startswith("api/")


def _montar_frontend(app: FastAPI) -> None:
    """Monta o build do Vite na raiz, se ele existir.

    Em desenvolvimento não existe: o Vite serve na 5173 e faz proxy de `/api`
    para cá. Em produção o build é gerado na máquina de desenvolvimento e
    enviado por `make deploy` — a Pi não compila (ARCHITECTURE.md D1c).
    """
    dist = Path(config.FRONTEND_DIST)
    if not dist.is_dir():
        return
    app.mount("/", _EstaticoSPA(directory=str(dist), html=True), name="app")


app = criar_app()
