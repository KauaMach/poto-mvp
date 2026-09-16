"""Worker de SLA — a única parte do sistema que age sem ninguém pedir.

O princípio em `config.SLA_SEGUNDOS`: **o silêncio humano nunca arquiva um
chamado.** Se o operador não reconhece dentro do prazo, o sistema aciona o
canal de fallback sozinho.

Por ser automático, é o código onde um erro faz o maior dano nas duas direções:
escalonar sem motivo aciona a PM por engano; não escalonar deixa uma emergência
esquecida. Os testes vêm em pares por isso — para cada caso que deve escalonar,
um vizinho que não deve.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app import canais, config, db, sla
from app.hub import hub as hub_global
from app.models import Gravidade, Modo, StatusChamado, TipoOcorrencia
from app.triagem.roteador import rotear


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(
        config,
        "_CONTATOS",
        {"csv": "5586999990001", "pm_190": "190", "sala_lilas": "5586999990002"},
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    db.init_db()


@pytest.fixture(autouse=True)
def hub_limpo():
    yield
    hub_global._clientes.clear()


class PainelFalso:
    def __init__(self):
        self.eventos: list[tuple[str, dict]] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, mensagem: dict) -> None:
        self.eventos.append((mensagem["evento"], mensagem["dados"]))

    def nomes(self) -> list[str]:
        return [n for n, _ in self.eventos]


@pytest.fixture
async def painel():
    p = PainelFalso()
    await hub_global.connect(p)
    return p


def criar(
    tipo: TipoOcorrencia = TipoOcorrencia.seguranca,
    *,
    status: str = StatusChamado.notificado,
    idade_seg: float = 0.0,
) -> dict:
    """Cria um chamado com idade controlada, escrevendo `created_at` no passado.

    Envelhecer o registro em vez de esperar o relógio é o que torna estes testes
    instantâneos **e** determinísticos.
    """
    evento = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": tipo,
        "modo": Modo.normal,
        "origem_acionamento": "touch",
    }
    chamado = db.criar_chamado(evento, rotear(tipo), status=status)
    if idade_seg:
        nascimento = (datetime.now(UTC) - timedelta(seconds=idade_seg)).isoformat()
        with db.conectar() as con:
            con.execute(
                "UPDATE chamados SET created_at = ? WHERE chamado_id = ?",
                (nascimento, chamado["chamado_id"]),
            )
    return db.obter_chamado(chamado["chamado_id"])


# ===========================================================================
# Prazos por gravidade
# ===========================================================================


@pytest.mark.parametrize(
    ("gravidade", "prazo"),
    [
        (Gravidade.risco_imediato, 120),
        (Gravidade.risco_potencial, 600),
        (Gravidade.orientacao, None),
    ],
)
def test_prazo_de_cada_gravidade(gravidade, prazo):
    assert sla.prazo_de(gravidade) == prazo


def test_orientacao_nunca_escalona():
    """Critério explícito. Não há urgência a proteger — escalonar uma dúvida de
    ouvidoria para a PM seria transformar uma pergunta num incidente."""
    chamado = {"gravidade": Gravidade.orientacao, "created_at": "2020-01-01T00:00:00Z"}
    assert sla.atrasado(chamado) is False


def test_gravidade_desconhecida_nao_escalona():
    """Registro de uma versão futura ou adulterado: sem prazo conhecido, não
    age. Acionar a PM por não saber interpretar um dado seria pior."""
    chamado = {"gravidade": "gravissimo", "created_at": "2020-01-01T00:00:00Z"}
    assert sla.atrasado(chamado) is False


# ===========================================================================
# Quando está atrasado
# ===========================================================================


def test_recem_criado_nao_esta_atrasado(banco):
    assert sla.atrasado(criar(idade_seg=0)) is False


def test_dentro_do_prazo_nao_esta_atrasado(banco):
    assert sla.atrasado(criar(idade_seg=60)) is False


def test_alem_do_prazo_esta_atrasado(banco):
    assert sla.atrasado(criar(idade_seg=121)) is True


def test_exatamente_no_prazo_esta_atrasado(banco):
    """Fronteira inclusiva: o prazo é o tempo *concedido*, e quando ele termina
    já passou. Meio segundo de tolerância num risco imediato não ajuda ninguém."""
    assert sla.atrasado(criar(idade_seg=120)) is True


def test_risco_potencial_tem_prazo_mais_longo(banco):
    """A mesma idade que já estourou um risco imediato ainda não estoura um
    potencial — é a razão de haver dois prazos."""
    chamado = criar(TipoOcorrencia.mulher, idade_seg=200)
    assert chamado["gravidade"] == Gravidade.risco_potencial
    assert sla.atrasado(chamado) is False
    assert sla.atrasado(criar(TipoOcorrencia.mulher, idade_seg=601)) is True


def test_created_at_ilegivel_nao_escalona(banco, caplog):
    """Escalonar por não saber a hora seria acionar a PM por causa de um dado
    corrompido."""
    chamado = {**criar(), "created_at": "ontem"}
    assert sla.atrasado(chamado) is False


def test_usa_o_relogio_do_servidor_nao_do_tablet(banco):
    """`timestamp_local` é o relógio do tablet e pode estar dessincronizado. Um
    aparelho adiantado faria o chamado nascer "já atrasado"; atrasado, ele nunca
    escalonaria."""
    chamado = criar(idade_seg=10)
    chamado["timestamp_local"] = "1999-01-01T00:00:00"
    assert sla.atrasado(chamado) is False


# ===========================================================================
# A varredura
# ===========================================================================


async def test_varrer_sem_chamados_nao_faz_nada(banco):
    assert await sla.varrer() == 0


async def test_varrer_escalona_o_atrasado(banco):
    chamado = criar(idade_seg=200)

    assert await sla.varrer() == 1

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.escalonado
    )


async def test_varrer_nao_toca_no_que_esta_no_prazo(banco):
    chamado = criar(idade_seg=10)

    assert await sla.varrer() == 0

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


async def test_notifica_o_canal_de_fallback(banco):
    """Não o canal original: ele já foi acionado e ninguém respondeu. Repetir o
    mesmo destino seria insistir com quem está calado.

    O helper `criar()` escreve direto no banco e **não** notifica — isso é
    trabalho do endpoint. Então tudo que aparece em `notificacoes` aqui foi posto
    pela varredura, o que torna a asserção mais limpa: exatamente um
    acionamento, no `fallback`.
    """
    chamado = criar(idade_seg=200)
    assert chamado["canal_roteado"] == "csv"
    assert chamado["fallback"] == "pm_190"

    await sla.varrer()

    canais_acionados = [
        n["canal"] for n in db.listar_notificacoes(chamado["chamado_id"])
    ]
    assert canais_acionados == ["pm_190"]
    assert chamado["canal_roteado"] not in canais_acionados


async def test_escalonamento_do_sla_nao_e_marcado_como_humano(banco):
    """`escalonamento=1` significa "uma pessoa decidiu isto" (MVP-034). O
    escalonamento de SLA é o oposto: acontece **porque** nenhuma pessoa agiu.
    Confundir os dois tornaria "quem decidiu?" — a única pergunta que a coluna
    existe para responder — insolúvel.

    O que registra o escalonamento automático é a transição em `estado_log`.
    """
    chamado = criar(idade_seg=200)

    await sla.varrer()

    registros = db.listar_notificacoes(chamado["chamado_id"])
    assert all(not n["escalonamento"] for n in registros)
    assert db.listar_estados(chamado["chamado_id"])[-1]["para"] == (
        StatusChamado.escalonado
    )


async def test_escalona_uma_unica_vez(banco):
    """Critério explícito. Duas varreduras seguidas não podem acionar a PM duas
    vezes — o status sai de `notificado` e a segunda passada não o vê."""
    chamado = criar(idade_seg=200)

    assert await sla.varrer() == 1
    assert await sla.varrer() == 0
    assert await sla.varrer() == 0

    acionados = [n["canal"] for n in db.listar_notificacoes(chamado["chamado_id"])]
    assert acionados.count("pm_190") == 1


async def test_chamado_reconhecido_nao_escalona(banco):
    """O ACK para o relógio. É a razão de o worker existir: medir o silêncio."""
    chamado = criar(idade_seg=500)
    db.ack_chamado(chamado["chamado_id"])

    assert await sla.varrer() == 0


async def test_ack_depois_do_prazo_ainda_protege(banco):
    """Reconhecer um chamado já vencido, antes da varredura, impede o
    escalonamento: o operador chegou tarde, mas chegou."""
    chamado = criar(idade_seg=1000)
    db.ack_chamado(chamado["chamado_id"])

    await sla.varrer()

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.reconhecido
    )


async def test_chamado_reaberto_apos_ack_nao_escalona(banco):
    """O cenário que justifica o `acked_at IS NULL` na consulta.

    A checagem de status já impede o caso comum: depois do ACK o chamado sai de
    `notificado`. Mas um operador pode movê-lo de volta — reabrir um chamado que
    voltou é uso legítimo do `PATCH` (MVP-033, que de propósito não restringe
    transições).

    Aí o `acked_at`, que é gravado **uma vez só** e nunca reescrito, é o que
    garante o critério na sua leitura mais forte: o escalonamento **automático**
    acontece no máximo uma vez na vida de um chamado. Sem essa cláusula, um
    chamado reaberto seria escalonado de novo a cada ciclo de reabertura.
    """
    chamado = criar(idade_seg=200)
    db.ack_chamado(chamado["chamado_id"])
    db.atualizar_chamado(chamado["chamado_id"], status=StatusChamado.notificado)

    assert await sla.varrer() == 0

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


async def test_alerta_ativo_nao_e_rebaixado(banco):
    """Pânico é persistente por decisão de projeto. Mover seu status apagaria da
    tela do totem o estado que mantém o cronômetro correndo — e o pânico já nasce
    com broadcast paralelo e escalonamento manual na tela."""
    chamado = criar(idade_seg=5000, status=StatusChamado.alerta_ativo)

    assert await sla.varrer() == 0

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


async def test_falha_de_notificacao_tambem_escalona(banco):
    """**Extensão deliberada do critério**, que fala só de `notificado`.

    `falha_notificacao` significa que **ninguém** foi avisado, porque o canal
    falhou. Deixá-lo fora faria o pior caso receber menos atenção que o normal:
    um chamado sobre o qual nenhuma mensagem saiu ficaria esperando para sempre.
    """
    chamado = criar(idade_seg=200, status=StatusChamado.falha_notificacao)

    assert await sla.varrer() == 1

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.escalonado
    )


@pytest.mark.parametrize(
    "status",
    [
        StatusChamado.reconhecido,
        StatusChamado.em_atendimento,
        StatusChamado.encerrado,
        StatusChamado.cancelado,
        StatusChamado.escalonado,
        StatusChamado.alerta_ativo,
    ],
)
async def test_status_nao_escalonavel(banco, status):
    """Todos já foram tratados por alguém, ou são persistentes. Escalonar um
    chamado encerrado acionaria a PM por um caso resolvido."""
    criar(idade_seg=5000, status=status)
    assert await sla.varrer() == 0


async def test_varre_varios_de_uma_vez(banco):
    criar(idade_seg=200)
    criar(idade_seg=200)
    criar(idade_seg=10)

    assert await sla.varrer() == 2


async def test_mais_antigo_primeiro(banco):
    """Quem espera há mais tempo é atendido antes — se a varredura for
    interrompida no meio, o mais urgente já passou."""
    velho = criar(idade_seg=900)
    novo = criar(idade_seg=200)

    pendentes = db.pendentes_de_ack()

    assert [c["chamado_id"] for c in pendentes] == [
        velho["chamado_id"],
        novo["chamado_id"],
    ]


# ===========================================================================
# Falhas não impedem o escalonamento
# ===========================================================================


async def test_sem_fallback_configurado_muda_o_status(banco):
    """O prazo estourou e isso é fato, mesmo sem para onde encaminhar. Deixá-lo
    em `notificado` faria a varredura tentar de novo para sempre e esconderia do
    painel que o prazo venceu."""
    chamado = criar(idade_seg=200)
    with db.conectar() as con:
        con.execute(
            "UPDATE chamados SET fallback = NULL WHERE chamado_id = ?",
            (chamado["chamado_id"],),
        )

    assert await sla.varrer() == 1

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.escalonado
    )


async def test_fallback_sem_contato_ainda_escalona(banco, monkeypatch):
    monkeypatch.setattr(config, "_CONTATOS", {"csv": "5586999990001"})
    chamado = criar(idade_seg=200)

    assert await sla.varrer() == 1

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.escalonado
    )
    registro = db.listar_notificacoes(chamado["chamado_id"])[-1]
    assert registro["sucesso"] is False


async def test_notificacao_que_estoura_nao_impede_o_status(banco, monkeypatch):
    """O `canais.notificar` promete não levantar, mas se levantar, o
    escalonamento não pode ficar pela metade — um chamado em `notificado` com a
    PM já acionada seria pior que qualquer dos dois estados puros."""

    async def estoura(*args, **kwargs):
        raise RuntimeError("bug no caminho da notificação")

    monkeypatch.setattr(canais, "notificar", estoura)
    chamado = criar(idade_seg=200)

    with pytest.raises(RuntimeError):
        await sla.varrer()

    # A exceção sobe da varredura, mas o `loop` a contém — é o teste seguinte.
    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


async def test_painel_e_avisado(banco, painel):
    """Sem isto, o chamado mudaria de estado no banco e o painel continuaria
    mostrando "notificado" até alguém recarregar a página."""
    criar(idade_seg=200)

    await sla.varrer()

    assert painel.nomes() == ["atualizado"]
    assert painel.eventos[0][1]["status"] == StatusChamado.escalonado


async def test_painel_morto_nao_impede_o_escalonamento(banco):
    class PainelQuebrado(PainelFalso):
        async def send_json(self, mensagem):
            raise ConnectionResetError("painel morto")

    await hub_global.connect(PainelQuebrado())
    chamado = criar(idade_seg=200)

    assert await sla.varrer() == 1
    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.escalonado
    )


async def test_broadcast_usa_o_formato_do_painel(banco, painel):
    """Mesmo contrato do REST (MVP-033): sem `id`, `evento_id` nem
    `triagem_json`."""
    criar(idade_seg=200)

    await sla.varrer()

    dados = painel.eventos[0][1]
    assert "id" not in dados
    assert "evento_id" not in dados
    assert "triagem_json" not in dados


# ===========================================================================
# O laço
# ===========================================================================


async def test_loop_varre_no_intervalo(banco, monkeypatch):
    monkeypatch.setattr(config, "SLA_CHECK_INTERVAL", 0.02)
    chamado = criar(idade_seg=200)

    tarefa = asyncio.create_task(sla.loop())
    try:
        await _esperar(
            lambda: db.obter_chamado(chamado["chamado_id"])["status"]
            == StatusChamado.escalonado
        )
    finally:
        tarefa.cancel()


async def test_loop_dorme_antes_de_varrer(banco, monkeypatch):
    """Quando o serviço acabou de subir, nada pode ter estourado prazo ainda.
    Varrer imediatamente a cada reinício seria só trabalho perdido."""
    monkeypatch.setattr(config, "SLA_CHECK_INTERVAL", 5.0)
    chamado = criar(idade_seg=200)

    tarefa = asyncio.create_task(sla.loop())
    await asyncio.sleep(0.05)
    tarefa.cancel()

    assert db.obter_chamado(chamado["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


async def test_excecao_na_varredura_nao_derruba_o_loop(banco, monkeypatch):
    """O critério que mais importa aqui. O worker é a rede que apara a
    emergência esquecida, e um worker morto falha **em silêncio** — ninguém
    percebe que os escalonamentos pararam de acontecer."""
    monkeypatch.setattr(config, "SLA_CHECK_INTERVAL", 0.02)
    tentativas = []
    varrer_real = sla.varrer

    async def varrer_instavel(*args, **kwargs):
        tentativas.append(1)
        if len(tentativas) <= 2:
            raise RuntimeError("banco indisponível")
        return await varrer_real(*args, **kwargs)

    monkeypatch.setattr(sla, "varrer", varrer_instavel)
    chamado = criar(idade_seg=200)

    tarefa = asyncio.create_task(sla.loop())
    try:
        await _esperar(
            lambda: db.obter_chamado(chamado["chamado_id"])["status"]
            == StatusChamado.escalonado
        )
        assert len(tentativas) >= 3
    finally:
        tarefa.cancel()


async def test_loop_para_quando_cancelado(banco, monkeypatch):
    """O `lifespan` cancela no encerramento. Sem relançar `CancelledError`, o
    cancel seria engolido e o encerramento do serviço travaria."""
    monkeypatch.setattr(config, "SLA_CHECK_INTERVAL", 0.01)

    tarefa = asyncio.create_task(sla.loop())
    await asyncio.sleep(0.03)
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert tarefa.cancelled()


async def _esperar(condicao, prazo: float = 2.0) -> None:
    """Espera uma condição, reprovando em vez de pendurar a suíte."""
    limite = asyncio.get_running_loop().time() + prazo
    while asyncio.get_running_loop().time() < limite:
        if condicao():
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"condição não ocorreu em {prazo}s")
