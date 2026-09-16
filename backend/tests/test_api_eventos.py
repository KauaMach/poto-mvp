"""`POST /eventos` — o acionamento, de ponta a ponta por HTTP.

Este é o primeiro arquivo em que a regra de negócio do projeto é exercitada
como um cliente de verdade a exercita. Tudo que a Fase 3 construiu — triagem,
roteamento, merge protetivo — passou a suíte inteira chamando funções; aqui
passa pelo Pydantic, pelo SQLite, pelo hub e pelos canais.

Por isso a primeira seção repete, via HTTP, o defeito que originou o módulo de
merge: na trilha Segurança, a palavra **"socorro"** rebaixava o chamado de
`risco_imediato` para `orientacao`. Pedir ajuda tornava o sistema menos
responsivo do que ficar calado. Se algum dia esse comportamento voltar, tem que
falhar aqui também — não só nos testes de unidade do merge.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import canais, config, db
from app.hub import hub as hub_global
from app.main import criar_app
from app.models import Gravidade, Modo, StatusChamado, TipoOcorrencia

ROTA = "/api/v1/eventos"


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Serviço de pé: banco temporário, sem frontend, contatos configurados."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(
        config,
        "_CONTATOS",
        {
            "csv": "5586999990001",
            "sala_lilas": "5586999990002",
            "samu_192": "192",
            "sapsi": "5586999990003",
            "ouvidoria": "5586999990004",
        },
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")


@pytest.fixture
def cliente(ambiente):
    with TestClient(criar_app()) as c:
        yield c


@pytest.fixture(autouse=True)
def hub_limpo():
    """O hub é um singleton do módulo — não pode vazar conexão entre testes."""
    yield
    hub_global._clientes.clear()


class PainelFalso:
    """Painel conectado ao hub, registrando o que recebeu."""

    def __init__(self, quebrado: bool = False):
        self.quebrado = quebrado
        self.eventos: list[tuple[str, dict]] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, mensagem: dict) -> None:
        if self.quebrado:
            raise ConnectionResetError("painel morto")
        self.eventos.append((mensagem["evento"], mensagem["dados"]))

    def nomes(self) -> list[str]:
        return [nome for nome, _ in self.eventos]


@pytest.fixture
async def painel():
    p = PainelFalso()
    await hub_global.connect(p)
    return p


def corpo(**extra) -> dict:
    from uuid import uuid4

    return {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": "seguranca",
        **extra,
    }


def acionar(cliente, **extra):
    return cliente.post(ROTA, json=corpo(**extra))


# ===========================================================================
# A regra de negócio: nada rebaixa a proteção já concedida
# ===========================================================================


def test_socorro_na_trilha_seguranca_nao_rebaixa(cliente):
    """O defeito original, por HTTP. No projeto de referência esta requisição
    devolvia `orientacao` e retinha o chamado aguardando operador."""
    r = acionar(cliente, tipo_ocorrencia="seguranca", texto_livre="socorro")

    assert r.status_code == 201
    assert r.json()["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize(
    "texto",
    [
        "socorro",
        "preciso de ajuda",
        "um homem está me seguindo",
        "estou com medo",
        "não sei o que fazer",
        "",
        None,
    ],
)
def test_nenhum_texto_rebaixa_a_trilha_seguranca(cliente, texto):
    """Varredura ampla: a trilha Segurança nasce `risco_imediato` e **nenhum**
    texto pode reduzir isso. É a forma mais direta de expressar a regra."""
    r = acionar(cliente, tipo_ocorrencia="seguranca", texto_livre=texto)
    assert r.json()["gravidade"] == Gravidade.risco_imediato


def test_texto_trivial_nao_rebaixa_nem_desvia(cliente):
    """O caso que `_tipo_final` trata de propósito: sem sinal crítico, o texto
    não redireciona o tipo. Sem essa restrição, "preciso de um atestado" numa
    trilha de Segurança chamaria o SAMU."""
    r = acionar(
        cliente, tipo_ocorrencia="seguranca", texto_livre="preciso de um atestado"
    )

    corpo_r = r.json()
    assert corpo_r["gravidade"] == Gravidade.risco_imediato
    assert corpo_r["canal_roteado"] == "csv"


def test_sinal_critico_promove_a_gravidade(cliente):
    r = acionar(
        cliente, tipo_ocorrencia="ouvidoria", texto_livre="ele disse que vai me matar"
    )
    assert r.json()["gravidade"] == Gravidade.risco_imediato


def test_sinal_critico_de_saude_redireciona(cliente):
    """Com sinal crítico, redirecionar é claramente certo: quem toca Segurança e
    escreve "estou desmaiando" precisa do SAMU, não do CSV."""
    r = acionar(
        cliente, tipo_ocorrencia="seguranca", texto_livre="estou desmaiando, socorro"
    )
    assert r.json()["canal_roteado"] == "samu_192"
    assert r.json()["gravidade"] == Gravidade.risco_imediato


# ===========================================================================
# Tela e modo discreto
# ===========================================================================


def test_trilha_mulher_devolve_tela_neutra(cliente):
    """Se o agressor está a três metros, uma tela que anuncia "Sala Lilás
    acionada" transforma o socorro em risco. Quem decide é o backend."""
    r = acionar(cliente, tipo_ocorrencia="mulher")

    instrucao = r.json()["instrucao_totem"]
    assert instrucao["tela_neutra"] is True
    assert instrucao["feedback_sonoro"] is False


def test_trilha_mulher_ignora_modo_normal_do_cliente(cliente):
    """O modo que chega é intenção, não palavra final."""
    r = acionar(cliente, tipo_ocorrencia="mulher", modo="normal")
    assert r.json()["instrucao_totem"]["tela_neutra"] is True


def test_modo_discreto_persistido_como_decidido(cliente):
    r = acionar(cliente, tipo_ocorrencia="mulher", modo="normal")

    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["modo"] == Modo.discreto


def test_discreto_sobrevive_ao_redirecionamento(cliente):
    """O modo discreto nunca é revogado: mesmo que o texto redirecione o tipo, a
    tela continua neutra."""
    r = acionar(
        cliente, tipo_ocorrencia="mulher", texto_livre="estou sangrando muito, socorro"
    )
    assert r.json()["instrucao_totem"]["tela_neutra"] is True


# ===========================================================================
# O que fica no banco
# ===========================================================================


def test_chamado_persistido_com_protocolo(cliente):
    r = acionar(cliente)

    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado is not None
    assert chamado["chamado_id"].startswith("CALL-")


def test_tipo_persistido_e_o_decidido(cliente):
    """O painel mostra o tipo **final** — é ele que determina quem responde."""
    r = acionar(
        cliente, tipo_ocorrencia="seguranca", texto_livre="estou desmaiando, socorro"
    )

    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["tipo_ocorrencia"] == TipoOcorrencia.saude


def test_trilha_escolhida_fica_na_auditoria(cliente):
    """Sem isto não haveria como reconstruir que o merge redirecionou — e o
    merge é o mecanismo mais delicado do sistema."""
    import json

    r = acionar(
        cliente, tipo_ocorrencia="seguranca", texto_livre="estou desmaiando, socorro"
    )

    chamado = db.obter_chamado(r.json()["chamado_id"])
    auditoria = json.loads(chamado["triagem_json"])
    assert auditoria["trilha_escolhida"] == "seguranca"
    assert chamado["tipo_ocorrencia"] == TipoOcorrencia.saude


def test_fonte_da_triagem_e_registrada(cliente):
    """`fonte` diz a verdade sobre qual motor rodou. O projeto de referência
    carimbava "agentes" mesmo quando só a heurística havia executado."""
    import json

    r = acionar(cliente, texto_livre="um homem está me seguindo")

    auditoria = json.loads(db.obter_chamado(r.json()["chamado_id"])["triagem_json"])
    assert auditoria["fonte"] in {"classificador", "heuristica"}


def test_relato_fica_no_banco(cliente):
    r = acionar(cliente, texto_livre="ele me empurrou na escada")
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["texto_livre"] == "ele me empurrou na escada"


def test_estado_inicial_registrado_no_log(cliente):
    r = acionar(cliente)
    estados = db.listar_estados(r.json()["chamado_id"])
    assert estados[0]["para"] == StatusChamado.roteado


def test_timestamp_local_preservado(cliente):
    r = acionar(cliente, timestamp_local="2026-09-16T14:32:00")
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["timestamp_local"] == "2026-09-16T14:32:00"


# ===========================================================================
# Idempotência
# ===========================================================================


def test_reenvio_devolve_o_mesmo_protocolo(cliente):
    dados = corpo(texto_livre="socorro")

    primeiro = cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    assert segundo.status_code == 201
    assert segundo.json()["duplicado"] is True
    assert segundo.json()["chamado_id"] == primeiro.json()["chamado_id"]


def test_primeiro_envio_nao_e_duplicado(cliente):
    assert acionar(cliente).json()["duplicado"] is False


def test_tres_reenvios_geram_um_chamado(cliente):
    """É o que permite a fila offline drenar sem medo. Se falhar, uma emergência
    vira dois alarmes e a central despacha duas equipes."""
    dados = corpo()

    for _ in range(3):
        cliente.post(ROTA, json=dados)

    assert len(db.listar_chamados()) == 1


def test_reenvio_nao_notifica_de_novo(cliente):
    dados = corpo()

    cliente.post(ROTA, json=dados)
    cliente.post(ROTA, json=dados)

    chamado_id = db.listar_chamados()[0]["chamado_id"]
    assert len(db.listar_notificacoes(chamado_id)) == 1


async def test_reenvio_nao_avisa_a_central_de_novo(cliente, painel):
    """Um reenvio é a mesma emergência. Reanunciá-la no painel faria o operador
    achar que há dois chamados."""
    dados = corpo()

    cliente.post(ROTA, json=dados)
    quantos = painel.nomes().count("novo_chamado")
    cliente.post(ROTA, json=dados)

    assert painel.nomes().count("novo_chamado") == quantos


def test_reenvio_com_conteudo_diferente_devolve_o_original(cliente):
    """`criar_chamado` não sobrescreve. O `evento_id` nasce no totem antes do
    envio, então conteúdo divergente com o mesmo id é erro de cliente — e o
    registro original é o que vale."""
    dados = corpo(tipo_ocorrencia="ouvidoria")
    primeiro = cliente.post(ROTA, json=dados)

    segundo = cliente.post(ROTA, json={**dados, "tipo_ocorrencia": "seguranca"})

    assert segundo.json()["gravidade"] == primeiro.json()["gravidade"]
    assert segundo.json()["canal_roteado"] == primeiro.json()["canal_roteado"]


def test_reenvio_reconstroi_a_instrucao(cliente):
    """A instrução de tela não é persistida — é apresentação, não domínio. No
    reenvio ela é recalculada, e precisa dar a mesma tela."""
    dados = corpo(tipo_ocorrencia="mulher")

    primeiro = cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    assert segundo.json()["instrucao_totem"] == primeiro.json()["instrucao_totem"]


def test_eventos_distintos_geram_chamados_distintos(cliente):
    a = acionar(cliente)
    b = acionar(cliente)
    assert a.json()["chamado_id"] != b.json()["chamado_id"]


# ===========================================================================
# Ordem: broadcast antes da notificação
# ===========================================================================


async def test_central_e_avisada(cliente, painel):
    r = acionar(cliente)

    assert "novo_chamado" in painel.nomes()
    dados = dict(painel.eventos[0][1])
    assert dados["chamado_id"] == r.json()["chamado_id"]


async def test_painel_recebe_o_relato(cliente, painel):
    """Assimetria deliberada com a notificação externa: o `meta` do webhook
    **nunca** leva o relato (MVP-028), mas o painel leva. Quem atende precisa
    dele para decidir como responder, e o painel está dentro da fronteira de
    confiança — o grupo de WhatsApp não está.

    Isto é o que torna a autenticação do `WS /ws` (MVP-035) obrigatória, não
    opcional.
    """
    acionar(cliente, texto_livre="ele está me esperando na saída")

    assert painel.eventos[0][1]["texto_livre"] == "ele está me esperando na saída"


async def test_broadcast_acontece_antes_da_notificacao(cliente, painel, monkeypatch):
    """A ordem existe por causa do tempo: o painel acende em menos de um
    segundo, e o webhook tem teto de dez. Invertida, a central esperaria pelo
    WhatsApp."""
    sequencia: list[str] = []
    original = canais.notificar

    async def notificar_espiao(*args, **kwargs):
        sequencia.append("notificar")
        return await original(*args, **kwargs)

    monkeypatch.setattr(canais, "notificar", notificar_espiao)

    class PainelQueMarca(PainelFalso):
        async def send_json(self, mensagem):
            sequencia.append(mensagem["evento"])
            await super().send_json(mensagem)

    hub_global._clientes.clear()
    await hub_global.connect(PainelQueMarca())

    acionar(cliente)

    assert sequencia.index("novo_chamado") < sequencia.index("notificar")


async def test_painel_morto_nao_impede_o_acionamento(cliente):
    """Um tablet travado na sala ao lado não pode fazer um pedido de socorro
    falhar."""
    await hub_global.connect(PainelFalso(quebrado=True))

    r = acionar(cliente)

    assert r.status_code == 201
    assert db.obter_chamado(r.json()["chamado_id"]) is not None


async def test_sem_painel_conectado_o_acionamento_funciona(cliente):
    """Estado normal de madrugada: ninguém olhando o painel."""
    assert len(hub_global) == 0
    assert acionar(cliente).status_code == 201


# ===========================================================================
# Notificação
# ===========================================================================


def test_canal_notificado_e_o_do_merge(cliente):
    """Não o da trilha: se o texto redirecionou para saúde crítica, quem é
    avisado é o SAMU."""
    r = acionar(
        cliente, tipo_ocorrencia="seguranca", texto_livre="estou desmaiando, socorro"
    )

    notificacoes = db.listar_notificacoes(r.json()["chamado_id"])
    assert [n["canal"] for n in notificacoes] == ["samu_192"]


def test_notificacao_bem_sucedida_muda_o_status(cliente):
    r = acionar(cliente)
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


def test_falha_de_notificacao_nao_apaga_o_chamado(cliente, monkeypatch):
    """O critério da MVP-030. O chamado é o registro da emergência; a
    notificação é um aviso sobre ele. Perder o primeiro por falha do segundo
    seria inverter a importância dos dois."""

    async def sempre_falha(*args, **kwargs):
        return False, "webhook fora do ar"

    monkeypatch.setattr(canais, "notificar", sempre_falha)

    r = acionar(cliente, texto_livre="socorro")

    assert r.status_code == 201
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado is not None
    assert chamado["status"] == StatusChamado.falha_notificacao
    assert chamado["gravidade"] == Gravidade.risco_imediato


async def test_falha_de_notificacao_avisa_o_painel(cliente, painel, monkeypatch):
    """Sem isto, um chamado cuja notificação falhou ficaria parado em "roteado"
    no painel, e o operador não saberia que precisa ligar por fora."""

    async def sempre_falha(*args, **kwargs):
        return False, "sem rota para o host"

    monkeypatch.setattr(canais, "notificar", sempre_falha)

    acionar(cliente)

    assert "atualizado" in painel.nomes()
    atualizado = [d for n, d in painel.eventos if n == "atualizado"][0]
    assert atualizado["status"] == StatusChamado.falha_notificacao


def test_canal_sem_contato_nao_derruba_o_acionamento(cliente, monkeypatch):
    """A trava contra o telefone embutido em código, vista de cima: canal sem
    contato configurado não é acionável, mas o chamado existe e a falha fica
    registrada."""
    monkeypatch.setattr(config, "_CONTATOS", {})

    r = acionar(cliente)

    assert r.status_code == 201
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["status"] == StatusChamado.falha_notificacao
    assert "sem contato" in db.listar_notificacoes(chamado["chamado_id"])[0]["detalhe"]


def test_provider_que_estoura_nao_derruba_o_acionamento(cliente, monkeypatch):
    async def estoura(*args, **kwargs):
        raise RuntimeError("bug no caminho da notificação")

    monkeypatch.setattr(canais, "notificar", estoura)

    r = acionar(cliente)

    assert r.status_code == 201
    assert db.obter_chamado(r.json()["chamado_id"]) is not None


# ===========================================================================
# A notificação não é aguardada
# ===========================================================================


async def test_resposta_e_enviada_antes_da_notificacao(ambiente, monkeypatch):
    """A prova do "responde em < 2 s", observada no protocolo.

    Medir o relógio não serve: o `TestClient` executa as tarefas de segundo
    plano antes de devolver a resposta ao teste, então o cronômetro somaria as
    duas coisas. Olhar o `status` do corpo também não serve — foi a primeira
    versão deste teste e a mutação a derrubou: mesmo aguardando a notificação, o
    dicionário em mão continua o de `criar_chamado`, ainda em `roteado`. A
    divergência acontece nos dois desenhos.

    O que distingue é **quando o corpo da resposta sai pelo ASGI**. Chamando a
    aplicação crua e registrando a ordem dos eventos, aguardar a notificação
    inverteria a sequência. Num webhook com teto de 10 s, isso seria a tela do
    totem parada enquanto alguém está em perigo.
    """
    db.init_db()
    sequencia: list[str] = []

    async def notificar_marcado(*args, **kwargs):
        sequencia.append("notificar")
        return True, "ok"

    monkeypatch.setattr(canais, "notificar", notificar_marcado)

    await _asgi_cru(criar_app(), corpo(texto_livre="socorro"), sequencia)

    assert sequencia == ["resposta enviada", "notificar"]


async def _asgi_cru(app, dados: dict, sequencia: list[str]) -> None:
    """Executa um `POST /eventos` como ASGI puro, sem `TestClient`.

    É o único jeito de enxergar a fronteira entre "resposta enviada" e "tarefa
    de segundo plano": qualquer cliente HTTP roda as duas e devolve só o fim.
    """
    import json

    payload = json.dumps(dados).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "path": ROTA,
        "raw_path": ROTA.encode(),
        "query_string": b"",
        "root_path": "",
        "scheme": "http",
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(mensagem):
        if mensagem["type"] == "http.response.body" and not mensagem.get(
            "more_body", False
        ):
            sequencia.append("resposta enviada")

    await app(scope, receive, send)


def test_resposta_traz_o_status_do_momento(cliente):
    """Consequência de não aguardar: o `status` da resposta é o de antes da
    notificação. A tela do totem não depende dele — o protocolo já é definitivo
    — e o painel recebe o estado final por WebSocket."""
    r = acionar(cliente)

    assert r.json()["status"] == StatusChamado.roteado
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.notificado
    )


# ===========================================================================
# Contrato de entrada
# ===========================================================================


def test_evento_id_ausente_e_rejeitado(cliente):
    r = cliente.post(ROTA, json={"totem_id": "T", "tipo_ocorrencia": "seguranca"})
    assert r.status_code == 422


def test_evento_id_malformado_e_rejeitado(cliente):
    """A idempotência inteira depende dele: um valor malformado viraria chave
    inútil e o reenvio criaria um segundo chamado para a mesma emergência."""
    r = cliente.post(
        ROTA,
        json={
            "evento_id": "nao-e-uuid",
            "totem_id": "T",
            "tipo_ocorrencia": "seguranca",
        },
    )
    assert r.status_code == 422


def test_tipo_desconhecido_e_rejeitado(cliente):
    assert acionar(cliente, tipo_ocorrencia="incendio").status_code == 422


def test_totem_vazio_e_rejeitado(cliente):
    assert acionar(cliente, totem_id="").status_code == 422


def test_relogio_desregulado_do_tablet_nao_impede_o_socorro(cliente):
    """`timestamp_local` é `str` e não `datetime` de propósito. O horário
    autoritativo é o `created_at` do servidor, e um aparelho com a hora
    dessincronizada não pode fazer um pedido de socorro falhar com 422."""
    r = acionar(cliente, timestamp_local="ontem à noite, mais ou menos")
    assert r.status_code == 201


def test_relato_longo_demais_e_rejeitado(cliente):
    assert acionar(cliente, texto_livre="a" * 2001).status_code == 422


def test_relato_no_limite_e_aceito(cliente):
    assert acionar(cliente, texto_livre="a" * 2000).status_code == 201


def test_origem_default_e_touch(cliente):
    r = acionar(cliente)
    assert db.obter_chamado(r.json()["chamado_id"])["origem_acionamento"] == "touch"


def test_origem_explicita_e_preservada(cliente):
    """`botao_fisico` já existe no vocabulário embora o GPIO esteja fora do MVP —
    é o gancho que permite o daemon de hardware entrar sem tocar no backend."""
    r = acionar(cliente, origem_acionamento="botao_fisico")
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["origem_acionamento"] == "botao_fisico"


# ===========================================================================
# As quatro trilhas, pelo endpoint
# ===========================================================================


@pytest.mark.parametrize(
    ("tipo", "canal", "gravidade"),
    [
        ("seguranca", "csv", Gravidade.risco_imediato),
        ("mulher", "sala_lilas", Gravidade.risco_potencial),
        ("ouvidoria", "ouvidoria", Gravidade.orientacao),
    ],
)
def test_trilha_roteia_para_o_canal_certo(cliente, tipo, canal, gravidade):
    """Fora de horário comercial a trilha `mulher` cai no fallback, então o teste
    checka o canal só onde ele não depende do relógio."""
    r = acionar(cliente, tipo_ocorrencia=tipo)

    assert r.json()["gravidade"] == gravidade
    if tipo != "mulher":
        assert r.json()["canal_roteado"] == canal


def test_saude_sem_emergencia_vai_para_apoio(cliente):
    r = acionar(cliente, tipo_ocorrencia="saude", texto_livre="preciso de um atestado")
    assert r.json()["canal_roteado"] in {"sapsi", "ouvidoria"}


def test_saude_com_emergencia_vai_para_o_samu(cliente):
    r = acionar(
        cliente, tipo_ocorrencia="saude", texto_livre="estou sangrando muito, socorro"
    )
    assert r.json()["canal_roteado"] == "samu_192"
    assert r.json()["gravidade"] == Gravidade.risco_imediato
