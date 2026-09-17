"""Sessão de mídia — o controle que impede a câmera de virar vigilância.

**Nenhum stream existe fora daqui.** É a afirmação mais importante do módulo, e
é o que separa um totem de um sistema de monitoramento: a câmera e o microfone
da Pi só capturam quando há uma sessão válida, e uma sessão só existe **vinculada
a um chamado ativo**, aberta por alguém, com prazo.

Quatro restrições, e cada uma fecha um caminho pelo qual a mídia deixaria de
ser socorro e passaria a ser observação:

- **Vinculada a chamado.** Sem chamado não há sessão. Não existe "ver a câmera
  do totem" como ação independente — só "ver a câmera **deste** chamado".
- **Chamado encerrado ou cancelado recusa** (`409`). Um chamado resolvido não
  justifica olhar o corredor, e permitir isso transformaria o histórico numa
  lista de pretextos.
- **Expira sozinha em 10 minutos.** Ninguém deixa uma câmera aberta por
  esquecimento. Renovar exige pedir de novo — o que gera nova linha de
  auditoria, e é de propósito: o custo de manter a câmera aberta é deixar
  rastro repetido.
- **Abertura e fechamento são auditados.** Sem o par não há como saber por
  quanto tempo alguém olhou, e uma linha só de abertura dá a informação errada.

Sem sessão válida, os endpoints de stream devolvem **403** — testado
explicitamente, porque é a garantia de que tudo acima não é decoração.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass

from .. import db
from ..models import StatusChamado
from . import obter

logger = logging.getLogger(__name__)

# Dez minutos. Curto o bastante para que esquecer não signifique vigiar, longo
# o bastante para acompanhar um atendimento em curso.
DURACAO_SEG = 600

# Estados em que olhar o local **não** se justifica.
ENCERRADOS = frozenset({StatusChamado.encerrado, StatusChamado.cancelado})


class SessaoRecusada(Exception):
    """Motivo pelo qual a sessão não pode ser aberta.

    Carrega o status HTTP porque a distinção importa para quem chama: 404 é
    "não existe", 409 é "existe e não pode".
    """

    def __init__(self, status: int, detalhe: str) -> None:
        super().__init__(detalhe)
        self.status = status
        self.detalhe = detalhe


@dataclass
class Sessao:
    sessao_id: str
    chamado_id: str
    dispositivo_id: str
    tipo: str
    operador: str | None
    aberta_em: float
    expira_em: float

    @property
    def expirada(self) -> bool:
        return time.monotonic() >= self.expira_em

    @property
    def duracao_seg(self) -> int:
        return int(time.monotonic() - self.aberta_em)


# As sessões vivem em memória, não no banco.
#
# É a escolha certa aqui: uma sessão não sobrevive a um reinício do serviço — e
# **não deve**. Se o processo caiu, a captura caiu com ele, e uma sessão
# ressuscitada do banco autorizaria um stream que ninguém está assistindo. O que
# precisa persistir é a **auditoria**, e ela está no banco.
_sessoes: dict[str, Sessao] = {}
_trava = threading.Lock()


def abrir(
    chamado_id: str, dispositivo_id: str, operador: str | None = None
) -> Sessao:
    """Autoriza captura de um dispositivo para um chamado.

    Levanta `SessaoRecusada` com o status apropriado. Recusar é o caminho
    esperado, não excepcional: a maior parte dos pedidos inválidos vem de um
    painel com dado velho — um chamado que outro operador acabou de encerrar,
    uma câmera que foi desconectada.
    """
    chamado = db.obter_chamado(chamado_id)
    if chamado is None:
        raise SessaoRecusada(404, "chamado não encontrado")

    if chamado["status"] in ENCERRADOS:
        raise SessaoRecusada(
            409,
            f"chamado {chamado['status']}: não é possível abrir mídia de um "
            "atendimento concluído",
        )

    dispositivo = obter(dispositivo_id)
    if dispositivo is None:
        raise SessaoRecusada(404, f"dispositivo {dispositivo_id!r} não disponível")

    agora = time.monotonic()
    sessao = Sessao(
        # `token_urlsafe` e não um sequencial: o id vai na URL do stream, e um
        # sequencial deixaria adivinhar a sessão do vizinho.
        sessao_id=secrets.token_urlsafe(16),
        chamado_id=chamado_id,
        dispositivo_id=dispositivo_id,
        tipo=dispositivo["tipo"],
        operador=operador,
        aberta_em=agora,
        expira_em=agora + DURACAO_SEG,
    )

    with _trava:
        _sessoes[sessao.sessao_id] = sessao

    db.registrar_midia(
        sessao.sessao_id,
        chamado_id,
        dispositivo_id,
        "abertura",
        dispositivo=dispositivo["nome"],
        operador=operador,
    )
    logger.info(
        "mídia aberta: %s %s por %s (chamado %s)",
        sessao.sessao_id,
        dispositivo_id,
        operador or "—",
        chamado_id,
    )
    return sessao


def validar(sessao_id: str, dispositivo_id: str) -> Sessao:
    """A sessão que autoriza este stream, ou levanta.

    Confere também o **dispositivo**: uma sessão aberta para a câmera não
    autoriza o microfone. Sem essa checagem, um único pedido de vídeo daria
    acesso ao áudio do local — e áudio é mais invasivo que imagem.
    """
    with _trava:
        sessao = _sessoes.get(sessao_id)

    if sessao is None:
        raise SessaoRecusada(403, "sessão de mídia inválida")

    if sessao.expirada:
        _encerrar(sessao, "expiracao", "prazo de 10 min esgotado")
        raise SessaoRecusada(403, "sessão de mídia expirada")

    if sessao.dispositivo_id != dispositivo_id:
        raise SessaoRecusada(
            403, "sessão não autoriza este dispositivo"
        )

    return sessao


def fechar(sessao_id: str, motivo: str = "encerrada pelo operador") -> bool:
    """Encerra uma sessão. Devolve se havia o que encerrar.

    Idempotente: o painel pode mandar o `DELETE` e o navegador reenviar no
    `beforeunload`, e um erro no segundo não ajudaria ninguém.
    """
    with _trava:
        sessao = _sessoes.get(sessao_id)
    if sessao is None:
        return False
    _encerrar(sessao, "fechamento", motivo)
    return True


def fechar_do_chamado(chamado_id: str, motivo: str) -> int:
    """Encerra todas as sessões de um chamado. Quantas fechou.

    Usado quando o chamado é encerrado: deixar a câmera aberta depois disso
    seria justamente a vigilância que o módulo existe para impedir.
    """
    with _trava:
        alvos = [s for s in _sessoes.values() if s.chamado_id == chamado_id]
    for sessao in alvos:
        _encerrar(sessao, "fechamento", motivo)
    return len(alvos)


def _encerrar(sessao: Sessao, acao: str, motivo: str) -> None:
    """Remove e audita. A duração é o dado que a abertura sozinha não dá."""
    with _trava:
        _sessoes.pop(sessao.sessao_id, None)
    db.registrar_midia(
        sessao.sessao_id,
        sessao.chamado_id,
        sessao.dispositivo_id,
        acao,
        operador=sessao.operador,
        motivo=motivo,
        duracao_seg=sessao.duracao_seg,
    )
    logger.info(
        "mídia %s: %s após %ds (%s)",
        acao,
        sessao.sessao_id,
        sessao.duracao_seg,
        motivo,
    )


def limpar_expiradas() -> int:
    """Audita e remove sessões cujo prazo venceu. Quantas removeu.

    Chamada pelo worker de SLA, que já roda periodicamente. Sem uma varredura,
    uma sessão que ninguém tentou usar depois de expirar ficaria sem linha de
    fechamento — e a auditoria mostraria uma câmera aberta para sempre.
    """
    with _trava:
        vencidas = [s for s in _sessoes.values() if s.expirada]
    for sessao in vencidas:
        _encerrar(sessao, "expiracao", "prazo de 10 min esgotado")
    return len(vencidas)


def fechar_todas(motivo: str = "serviço encerrado") -> int:
    """Audita e remove **todas** as sessões, expiradas ou não. Quantas fechou.

    Chamada no encerramento da aplicação, e existe por causa de um buraco
    encontrado ao analisar a auditoria da Pi depois de um dia de uso.

    As sessões vivem em memória de propósito (ver a nota no topo). A
    consequência que eu não havia coberto: um `systemctl restart` com sessão
    aberta **descarta a sessão sem escrever a linha de fechamento**. O
    `limpar_expiradas` não alcança essas, porque ele varre o dicionário em
    memória — que o reinício já esvaziou.

    O resultado medido na Pi: duas linhas de `abertura` de 16/09 sem par,
    mostrando câmeras "abertas" havia **24 horas**. Para quem audita, isso lê
    exatamente como o que a MVP-077 existe para impedir — e é pior que não ter
    auditoria, porque acusa algo que não aconteceu.

    A MVP-077 listava três caminhos de fechamento: pelo operador, por expiração
    e pelo encerramento do chamado. Este é o quarto, e o único que não parte de
    uma ação de quem usa.
    """
    with _trava:
        todas = list(_sessoes.values())
    for sessao in todas:
        _encerrar(sessao, "fechamento", motivo)
    return len(todas)


def ativas() -> list[Sessao]:
    with _trava:
        return [s for s in _sessoes.values() if not s.expirada]


def url_do_stream(sessao: Sessao) -> str:
    """Onde o painel busca a mídia desta sessão."""
    recurso = "camera" if sessao.tipo == "camera" else "microfone"
    return (
        f"/api/v1/midia/{recurso}/{sessao.dispositivo_id}"
        f"/stream?sessao={sessao.sessao_id}"
    )
