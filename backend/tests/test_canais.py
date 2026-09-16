"""Notificação: o que sai do sistema, para onde, e o que fica.

A metade destes testes existe para uma única frase do projeto: **o relato nunca
sai**. `texto_livre` é a descrição que a pessoa escreveu — muitas vezes de uma
violência em curso — e a notificação chega num grupo de WhatsApp institucional,
onde pode ser encaminhada, printada ou lida por quem pegar o celular do
plantonista. Quem atende precisa de *onde*, *que tipo* e *quão grave*.

A outra metade protege o registro: toda tentativa de acionamento é gravada,
inclusive as que falharam, porque é isso que torna "ninguém foi avisado"
distinguível de "ninguém apareceu".
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

import httpx
import pytest

from app import canais, config, db
from app.canais import base, webhook
from app.canais.log import LogProvider, mascarar
from app.canais.webhook import WebhookProvider
from app.models import Gravidade, Modo, StatusChamado, TipoOcorrencia
from app.triagem.roteador import rotear

RELATO = "meu ex está me esperando na saída do bloco e disse que vai me matar"


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    db.init_db()


@pytest.fixture
def contatos(monkeypatch):
    """Contatos configurados. Sem isto nenhum canal é acionável — de propósito
    (ver `config.py`: nunca há telefone com valor default)."""
    monkeypatch.setattr(
        config,
        "_CONTATOS",
        {"csv": "5586999990001", "sala_lilas": "5586999990002"},
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")


def chamado(**extra) -> dict:
    """Chamado como ele sai do banco: strings, e com o relato dentro."""
    return {
        "id": 1,
        "chamado_id": "CALL-2026-000001",
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": "seguranca",
        "modo": "normal",
        "origem_acionamento": "touch",
        "gravidade": "risco_imediato",
        "canal_roteado": "csv",
        "fallback": "pm_190",
        "status": "roteado",
        "texto_livre": RELATO,
        "triagem_json": '{"tipo": "seguranca", "confianca": 0.93}',
        "observacao": "operador achou estranho",
        "timestamp_local": "2026-09-16T14:32:00",
        "created_at": "2026-09-16T17:32:10+00:00",
        "updated_at": "2026-09-16T17:32:10+00:00",
        "acked_at": None,
        **extra,
    }


class ProviderEspiao:
    """Provider que registra o que recebeu, sem enviar nada."""

    nome = "espiao"

    def __init__(self, resultado=(True, "ok")):
        self.resultado = resultado
        self.chamadas: list[tuple[str, str, dict]] = []

    async def enviar(self, destino, mensagem, meta):
        self.chamadas.append((destino, mensagem, meta))
        return self.resultado


class ProviderQueEstoura:
    nome = "bugado"

    async def enviar(self, destino, mensagem, meta):
        raise RuntimeError("bug no provider")


def criar_chamado_real(**extra) -> dict:
    evento = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": TipoOcorrencia.seguranca,
        "modo": Modo.normal,
        "origem_acionamento": "touch",
        "texto_livre": RELATO,
        **extra,
    }
    return db.criar_chamado(evento, rotear(TipoOcorrencia.seguranca))


# ===========================================================================
# O relato não sai
# ===========================================================================


def test_payload_sem_relato():
    """O teste que a MVP-028 nomeia. Nem a mensagem nem o `meta` carregam o
    relato — e o `meta` é o mais perigoso dos dois, porque é o corpo JSON do
    webhook: passar o chamado inteiro ali mandaria o relato para fora sem que
    ninguém notasse, já que o texto da mensagem continuaria impecável."""
    c = chamado()

    mensagem = base.montar_mensagem(c)
    meta = base.montar_meta(c)

    assert RELATO not in mensagem
    assert RELATO not in str(meta)
    assert "texto_livre" not in meta


@pytest.mark.parametrize(
    "relato",
    [
        "fui estuprada ontem no estacionamento",
        "meu orientador me assedia desde março",
        "tentei me matar na semana passada",
        "o segurança do bloco me seguiu até o ponto",
    ],
)
def test_nenhum_relato_vaza(relato):
    """Relatos reais, verificados por valor em toda a saída.

    Nenhum deles colide com valor de campo legítimo — de propósito. Um relato
    que fosse literalmente `"TOTEM-CCS-01"` apareceria na saída como `totem_id`
    e a busca por valor não saberia distinguir vazamento de campo legítimo.
    Contra essa classe de caso quem responde é
    `test_meta_so_tem_campos_permitidos`, que checa a estrutura em vez do
    conteúdo.
    """
    c = chamado(texto_livre=relato)
    assert relato not in base.montar_mensagem(c)
    assert relato not in str(base.montar_meta(c))


@pytest.mark.parametrize(
    "relato", ["CALL-2026-000001", "risco_imediato", "TOTEM-CCS-01"]
)
def test_relato_que_imita_campo_legitimo(relato):
    """O complemento estrutural: aqui a busca por valor é inútil, porque o
    relato é indistinguível de um campo que deve sair mesmo. O que se cobra é
    que a saída tenha exatamente as chaves permitidas — nem uma a mais."""
    meta = base.montar_meta(chamado(texto_livre=relato))
    assert set(meta) == set(base.CAMPOS_NOTIFICAVEIS)


def test_meta_so_tem_campos_permitidos():
    assert set(base.montar_meta(chamado())) == set(base.CAMPOS_NOTIFICAVEIS)


@pytest.mark.parametrize("campo", ["texto_livre", "triagem_json", "observacao"])
def test_campos_internos_ficam_no_banco(campo):
    """Três campos internos, três razões: o relato é o dado mais sensível, a
    triagem é o que a máquina inferiu sobre ele, e a observação é nota do
    operador — nenhuma delas ajuda quem vai atender."""
    meta = base.montar_meta(chamado())
    assert campo not in meta
    assert campo not in base.montar_mensagem(chamado())


def test_campo_novo_no_chamado_nao_vaza():
    """A propriedade que faz a garantia ser estrutural.

    `resumo()` copia uma lista de campos permitidos em vez de remover os
    proibidos. Então uma coluna acrescentada ao schema amanhã — anexo de áudio,
    transcrição, coordenada — não vaza por esquecimento. Vazaria pelo caminho
    oposto: alguém teria que acrescentá-la a `CAMPOS_NOTIFICAVEIS`, e essa
    linha aparece no diff.
    """
    c = chamado(transcricao_audio="socorro ele está aqui", foto_path="/var/x.jpg")

    meta = base.montar_meta(c)

    assert "transcricao_audio" not in meta
    assert "foto_path" not in meta
    assert "socorro ele está aqui" not in str(meta)


def test_resumo_nao_muta_o_chamado():
    c = chamado()
    base.resumo(c)
    assert c["texto_livre"] == RELATO


# ===========================================================================
# A mensagem que chega ao plantonista
# ===========================================================================


def test_mensagem_tem_o_protocolo():
    """É por ele que a central e a pessoa se encontram."""
    assert "CALL-2026-000001" in base.montar_mensagem(chamado())


def test_mensagem_tem_o_totem():
    assert "TOTEM-CCS-01" in base.montar_mensagem(chamado())


def test_mensagem_tem_a_gravidade():
    assert "RISCO IMEDIATO" in base.montar_mensagem(chamado())


def test_mensagem_tem_o_tipo_legivel():
    """"seguranca" é vocabulário do código; quem lê no celular é uma pessoa."""
    mensagem = base.montar_mensagem(chamado())
    assert "Segurança" in mensagem
    assert "seguranca" not in mensagem


def test_mensagem_tem_o_canal_legivel():
    assert "CSV / PREUNI" in base.montar_mensagem(chamado())


@pytest.mark.parametrize(
    ("gravidade", "rotulo"),
    [
        (Gravidade.risco_imediato, "RISCO IMEDIATO"),
        (Gravidade.risco_potencial, "Risco potencial"),
        (Gravidade.orientacao, "Orientação"),
    ],
)
def test_rotulo_de_cada_gravidade(gravidade, rotulo):
    assert rotulo in base.montar_mensagem(chamado(gravidade=str(gravidade)))


@pytest.mark.parametrize(
    ("tipo", "rotulo"),
    [
        (TipoOcorrencia.seguranca, "Segurança"),
        (TipoOcorrencia.mulher, "Assédio / Sala Lilás"),
        (TipoOcorrencia.saude, "Saúde"),
        (TipoOcorrencia.ouvidoria, "Ouvidoria"),
    ],
)
def test_rotulo_de_cada_tipo(tipo, rotulo):
    assert rotulo in base.montar_mensagem(chamado(tipo_ocorrencia=str(tipo)))


def test_modo_discreto_avisa_a_abordagem():
    """Quem vai atender precisa saber que a pessoa pode estar ao lado de quem a
    ameaça. Não revela nada novo — a trilha `mulher` é sempre discreta."""
    mensagem = base.montar_mensagem(
        chamado(modo=str(Modo.discreto), tipo_ocorrencia="mulher")
    )
    assert "discreta" in mensagem.lower()


def test_modo_normal_nao_avisa():
    assert "discreta" not in base.montar_mensagem(chamado()).lower()


def test_valor_desconhecido_nao_derruba_a_mensagem():
    """Banco de uma versão antiga, registro adulterado, migração incompleta —
    nada disso pode fazer o aviso de uma emergência estourar com `ValueError`
    antes de sair."""
    mensagem = base.montar_mensagem(
        chamado(gravidade="gravissimo", tipo_ocorrencia="incendio")
    )
    assert "CALL-2026-000001" in mensagem
    assert "gravissimo" in mensagem


def test_campo_ausente_nao_derruba_a_mensagem():
    magro = {"chamado_id": "CALL-2026-000009"}
    assert "CALL-2026-000009" in base.montar_mensagem(magro)


# ===========================================================================
# Provider `log`
# ===========================================================================


async def test_log_provider_reporta_sucesso():
    sucesso, detalhe = await LogProvider().enviar("5586999990001", "oi", {})
    assert sucesso is True
    assert detalhe


async def test_log_provider_escreve_no_log(caplog):
    with caplog.at_level(logging.INFO, logger="poto.notificacao"):
        await LogProvider().enviar("5586999990001", "corpo da mensagem", {})
    assert "corpo da mensagem" in caplog.text


async def test_log_provider_nao_escreve_o_contato_inteiro(caplog):
    """O log é o lugar mais fácil de vazar sem perceber: journald é copiado,
    colado num chat de suporte, anexado a relatório."""
    with caplog.at_level(logging.INFO, logger="poto.notificacao"):
        await LogProvider().enviar("5586999990001", "oi", {})
    assert "5586999990001" not in caplog.text
    assert "0001" in caplog.text  # o fim basta para depurar


@pytest.mark.parametrize(
    ("destino", "esperado"),
    [
        ("5586999990001", "…0001"),
        ("190", "***"),
        ("", "(sem contato configurado)"),
    ],
)
def test_mascarar(destino, esperado):
    assert mascarar(destino) == esperado


# ===========================================================================
# Registry
# ===========================================================================


def test_default_e_o_log(monkeypatch):
    """O estado inicial de quem sobe o serviço sem configurar nada não pode ser
    "disca para o 190"."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "")
    assert canais.obter_provider().nome == "log"


def test_provider_vem_da_configuracao(monkeypatch):
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    assert canais.obter_provider().nome == "log"


def test_nome_explicito_vence_a_configuracao(monkeypatch):
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "inexistente")
    assert canais.obter_provider("log").nome == "log"


def test_provider_desconhecido_degrada_para_log(monkeypatch, caplog):
    """Erro de digitação em `POTO_NOTIF_PROVIDER` não derruba um totem de
    emergência: degrada para o log, que continua registrando tudo, e o
    `/health` avisa (MVP-036)."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "whatsapp-de-verdade")
    with caplog.at_level(logging.WARNING):
        provider = canais.obter_provider()
    assert provider.nome == "log"
    assert "desconhecido" in caplog.text


def test_provider_configurado_reporta_o_efetivo(monkeypatch):
    """O que o `/health` mostra é o que será usado, não o que foi pedido."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "nao-existe")
    assert canais.provider_configurado() == "log"


def test_nome_com_espaco_e_maiuscula_funciona(monkeypatch):
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "  LOG  ")
    assert canais.obter_provider().nome == "log"


# ===========================================================================
# notificar() — acionamento e registro
# ===========================================================================


async def test_notificar_entrega_ao_provider(banco, contatos):
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    sucesso, _ = await canais.notificar(c, "csv", provider=espiao)

    assert sucesso is True
    assert len(espiao.chamadas) == 1


async def test_notificar_resolve_o_destino(banco, contatos):
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    await canais.notificar(c, "csv", provider=espiao)

    destino, _, _ = espiao.chamadas[0]
    assert destino == "5586999990001"


async def test_notificar_grava_a_tentativa(banco, contatos):
    c = criar_chamado_real()

    await canais.notificar(c, "csv", provider=ProviderEspiao())

    registros = db.listar_notificacoes(c["chamado_id"])
    assert len(registros) == 1
    assert registros[0]["canal"] == "csv"
    assert registros[0]["sucesso"] is True
    assert registros[0]["provider"] == "espiao"


async def test_destino_fica_no_banco(banco, contatos):
    """O contato não aparece em resposta de endpoint aberto (`models.py`): mora
    nesta tabela, atrás do token do painel."""
    c = criar_chamado_real()

    await canais.notificar(c, "csv", provider=ProviderEspiao())

    assert db.listar_notificacoes(c["chamado_id"])[0]["destino"] == "5586999990001"


async def test_falha_do_provider_e_gravada(banco, contatos):
    """Registrar só os sucessos deixaria o silêncio indistinguível de nunca ter
    tentado."""
    c = criar_chamado_real()
    espiao = ProviderEspiao(resultado=(False, "webhook devolveu 502"))

    sucesso, detalhe = await canais.notificar(c, "csv", provider=espiao)

    assert sucesso is False
    assert detalhe == "webhook devolveu 502"
    registro = db.listar_notificacoes(c["chamado_id"])[0]
    assert registro["sucesso"] is False
    assert registro["detalhe"] == "webhook devolveu 502"


async def test_provider_que_estoura_nao_propaga(banco, contatos):
    """O chamado já está no banco quando `notificar` é chamada. Perder o
    registro de uma emergência porque o provider tem bug seria trocar um
    problema pequeno por um grave."""
    c = criar_chamado_real()

    sucesso, detalhe = await canais.notificar(c, "csv", provider=ProviderQueEstoura())

    assert sucesso is False
    assert "bug no provider" in detalhe


async def test_provider_que_estoura_ainda_grava(banco, contatos):
    c = criar_chamado_real()

    await canais.notificar(c, "csv", provider=ProviderQueEstoura())

    assert db.listar_notificacoes(c["chamado_id"])[0]["sucesso"] is False


async def test_mensagem_gravada_e_a_que_foi_enviada(banco, contatos):
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    await canais.notificar(c, "csv", provider=espiao)

    _, enviada, _ = espiao.chamadas[0]
    assert db.listar_notificacoes(c["chamado_id"])[0]["mensagem"] == enviada


async def test_o_relato_nao_chega_ao_provider(banco, contatos):
    """O caminho completo, não só a função de montagem: o que o provider recebe
    é o que vai para fora."""
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    await canais.notificar(c, "csv", provider=espiao)

    _, mensagem, meta = espiao.chamadas[0]
    assert RELATO not in mensagem
    assert RELATO not in str(meta)


async def test_relato_nao_fica_na_tabela_de_notificacoes(banco, contatos):
    """`notificacoes.mensagem` guarda o que foi enviado — se o relato entrasse
    ali, estaria fora da coluna que a LGPD trata como sensível e dentro de uma
    que o painel exibe em lista."""
    c = criar_chamado_real()

    await canais.notificar(c, "csv", provider=ProviderEspiao())

    assert RELATO not in db.listar_notificacoes(c["chamado_id"])[0]["mensagem"]


# --- Canal sem contato ------------------------------------------------------


async def test_canal_sem_contato_nao_aciona(banco, contatos):
    """A trava contra o telefone embutido em código: o projeto de referência
    trazia um celular real de Teresina no fonte. Aqui, canal sem contato
    configurado simplesmente não é acionável."""
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    sucesso, detalhe = await canais.notificar(c, "sapsi", provider=espiao)

    assert sucesso is False
    assert "sem contato" in detalhe
    assert espiao.chamadas == []


async def test_canal_sem_contato_e_gravado(banco, contatos):
    """O painel precisa mostrar *por que* ninguém foi avisado, em vez de um
    silêncio sem explicação."""
    c = criar_chamado_real()

    await canais.notificar(c, "sapsi", provider=ProviderEspiao())

    registro = db.listar_notificacoes(c["chamado_id"])[0]
    assert registro["sucesso"] is False
    assert "sem contato" in registro["detalhe"]
    assert registro["destino"] == ""


async def test_contact_override_redireciona(banco, contatos, monkeypatch):
    """Trava de bancada: impede discar 190/192/193/180 de verdade durante o
    teste e a demonstração."""
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "5586900000000")
    c = criar_chamado_real()
    espiao = ProviderEspiao()

    await canais.notificar(c, "pm_190", provider=espiao)

    destino, _, _ = espiao.chamadas[0]
    assert destino == "5586900000000"


# --- Escalonamento ----------------------------------------------------------


async def test_escalonamento_marcado(banco, contatos):
    """Separa a decisão humana na tela de alerta ativo (MVP-034) do
    encaminhamento automático — o sistema não robo-disca."""
    c = criar_chamado_real()

    await canais.notificar(c, "csv", escalonamento=True, provider=ProviderEspiao())

    assert db.listar_notificacoes(c["chamado_id"])[0]["escalonamento"] is True


async def test_acionamento_normal_nao_e_escalonamento(banco, contatos):
    c = criar_chamado_real()
    await canais.notificar(c, "csv", provider=ProviderEspiao())
    assert db.listar_notificacoes(c["chamado_id"])[0]["escalonamento"] is False


# --- Múltiplas tentativas ---------------------------------------------------


async def test_varias_tentativas_no_mesmo_chamado(banco, contatos):
    """O caso do pânico (canais em paralelo) e do SLA (fallback depois do
    prazo): o histórico acumula em ordem."""
    c = criar_chamado_real()

    await canais.notificar(c, "csv", provider=ProviderEspiao())
    await canais.notificar(c, "sala_lilas", provider=ProviderEspiao())

    registros = db.listar_notificacoes(c["chamado_id"])
    assert [r["canal"] for r in registros] == ["csv", "sala_lilas"]


async def test_notificacoes_de_outro_chamado_nao_aparecem(banco, contatos):
    a, b = criar_chamado_real(), criar_chamado_real()

    await canais.notificar(a, "csv", provider=ProviderEspiao())

    assert db.listar_notificacoes(b["chamado_id"]) == []


async def test_provider_default_funciona_de_ponta_a_ponta(banco, contatos, monkeypatch):
    """Sem `provider=` explícito: o caminho que `/eventos` vai usar."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    c = criar_chamado_real()

    sucesso, _ = await canais.notificar(c, "csv")

    assert sucesso is True
    assert db.listar_notificacoes(c["chamado_id"])[0]["provider"] == "log"


async def test_chamado_recem_criado_notifica(banco, contatos):
    """Integração real: o dicionário que `criar_chamado` devolve é aceito pela
    montagem da mensagem sem adaptação."""
    c = criar_chamado_real()
    assert c["status"] == StatusChamado.roteado

    mensagem = base.montar_mensagem(c)

    assert c["chamado_id"] in mensagem
    assert RELATO not in mensagem


# ===========================================================================
# Provider `webhook`
# ===========================================================================
#
# Testado com `httpx.MockTransport`: exercita o caminho real do provider —
# montagem do corpo, cabeçalhos, tratamento de status e de exceção — sem rede.


class WebhookFalso:
    """Endpoint de mentira. Registra o que recebeu e devolve o que mandarem."""

    def __init__(self, status=200, corpo="", erro=None, demora=0.0, destino=None):
        self.status = status
        self.corpo = corpo
        self.erro = erro
        self.demora = demora
        self.destino = destino  # Location, para o teste de redirecionamento
        self.requisicoes: list[httpx.Request] = []

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._responder)

    async def _responder(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        if self.demora:
            await asyncio.sleep(self.demora)
        if self.erro is not None:
            raise self.erro
        cabecalhos = {"location": self.destino} if self.destino else {}
        return httpx.Response(self.status, text=self.corpo, headers=cabecalhos)

    @property
    def urls(self) -> list[str]:
        return [str(r.url) for r in self.requisicoes]

    @property
    def corpo_enviado(self) -> dict:
        import json

        return json.loads(self.requisicoes[0].content)


@pytest.fixture
def url(monkeypatch):
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_URL", "https://evolution.local/mensagem")
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_TOKEN", "")


# --- O contrato do POST -----------------------------------------------------


async def test_webhook_posta_na_url_configurada(url):
    falso = WebhookFalso()

    await WebhookProvider(falso.transport).enviar("5586999990001", "oi", {})

    assert str(falso.requisicoes[0].url) == "https://evolution.local/mensagem"
    assert falso.requisicoes[0].method == "POST"


async def test_corpo_tem_number_text_e_meta(url):
    falso = WebhookFalso()

    await WebhookProvider(falso.transport).enviar(
        "5586999990001", "corpo da mensagem", {"chamado_id": "CALL-2026-000001"}
    )

    assert falso.corpo_enviado == {
        "number": "5586999990001",
        "text": "corpo da mensagem",
        "meta": {"chamado_id": "CALL-2026-000001"},
    }


async def test_sucesso_em_2xx(url):
    sucesso, detalhe = await WebhookProvider(WebhookFalso(201).transport).enviar(
        "5586999990001", "oi", {}
    )
    assert sucesso is True
    assert "201" in detalhe


@pytest.mark.parametrize("status", [400, 401, 404, 422, 500, 502, 503])
async def test_status_de_erro_vira_falha(url, status):
    sucesso, detalhe = await WebhookProvider(
        WebhookFalso(status, corpo="instance not found").transport
    ).enviar("5586999990001", "oi", {})

    assert sucesso is False
    assert str(status) in detalhe
    assert "instance not found" in detalhe


async def test_redirecionamento_nao_e_seguido(url, monkeypatch):
    """Seguir um 3xx mandaria o token e o payload para um host que ninguém
    configurou. O default do httpx já é não seguir; este teste trava a decisão,
    para que um `follow_redirects=True` futuro não passe despercebido.

    O `location` é essencial e foi o que faltou na primeira versão deste teste:
    sem ele o httpx não tem para onde seguir, e a checagem passaria mesmo com o
    redirecionamento ligado.
    """
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_TOKEN", "segredo-123")
    falso = WebhookFalso(302, destino="https://host-que-ninguem-configurou/")

    sucesso, _ = await WebhookProvider(falso.transport).enviar("558699", "oi", {})

    assert sucesso is False
    assert falso.urls == ["https://evolution.local/mensagem"]


async def test_detalhe_da_resposta_e_truncado(url):
    """A resposta pode ser uma página de erro inteira. `notificacoes` é tabela
    de auditoria, não lixeira de HTML."""
    falso = WebhookFalso(500, corpo="x" * 5000)

    _, detalhe = await WebhookProvider(falso.transport).enviar("558699", "oi", {})

    assert len(detalhe) < webhook.LIMITE_DETALHE + 50


# --- Falhas de rede ---------------------------------------------------------


@pytest.mark.parametrize(
    "erro",
    [
        httpx.ConnectError("conexão recusada"),
        httpx.ReadTimeout("leitura expirou"),
        httpx.ConnectTimeout("conexão expirou"),
        httpx.RemoteProtocolError("resposta malformada"),
    ],
)
async def test_falha_de_rede_nao_levanta(url, erro, caplog):
    """O chamado já está no banco quando `enviar` é chamada. Nenhuma falha aqui
    pode virar exceção e fazer o acionamento parecer que não aconteceu.

    Cobra também que a falha seja tratada como **esperada**, e não caia no
    `except Exception` genérico. A diferença não aparece no retorno — as duas
    devolvem `(False, ...)` — mas o caminho genérico chama `logger.exception()`.
    Numa Pi com rede instável isso despejaria um traceback a cada notificação
    perdida, afogando os erros que de fato merecem stack trace.
    """
    with caplog.at_level(logging.ERROR):
        sucesso, detalhe = await WebhookProvider(
            WebhookFalso(erro=erro).transport
        ).enviar("5586999990001", "oi", {})

    assert sucesso is False
    assert detalhe.startswith(type(erro).__name__)
    assert "inesperado" not in detalhe
    assert "Traceback" not in caplog.text


async def test_erro_inesperado_nao_levanta(url, caplog):
    """Rede embaixo da rede: nem uma exceção fora da família do httpx escapa.

    Aqui o traceback é bem-vindo — isto é um bug, não uma rede ruim."""
    with caplog.at_level(logging.ERROR):
        sucesso, detalhe = await WebhookProvider(
            WebhookFalso(erro=ValueError("algo bem estranho")).transport
        ).enviar("5586999990001", "oi", {})

    assert sucesso is False
    assert "inesperado" in detalhe
    assert "algo bem estranho" in detalhe
    assert "Traceback" in caplog.text


async def test_timeout_e_teto_total(url, monkeypatch):
    """O `timeout` do httpx é **por fase** — conectar, escrever, ler, esperar no
    pool. 10.0 ali significa até ~40 s no pior caso. No caminho de uma
    emergência o que importa é o total, então o teto é explícito.

    Sem ele este teste espera a demora inteira; com ele, corta no prazo.
    """
    monkeypatch.setattr(webhook, "TIMEOUT", 0.05)
    falso = WebhookFalso(demora=5.0)

    sucesso, detalhe = await asyncio.wait_for(
        WebhookProvider(falso.transport).enviar("5586999990001", "oi", {}),
        timeout=2.0,
    )

    assert sucesso is False
    assert "timeout" in detalhe.lower()


# --- Configuração ausente ---------------------------------------------------


async def test_sem_url_falha_explicitamente(monkeypatch):
    """Provider selecionado sem URL **não** cai para o `log`: isso faria o
    `/health` dizer "webhook" enquanto nada sai. Falha explícita, gravada."""
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_URL", "")
    falso = WebhookFalso()

    sucesso, detalhe = await WebhookProvider(falso.transport).enviar("558699", "oi", {})

    assert sucesso is False
    assert "URL" in detalhe
    assert falso.requisicoes == []


# --- Autenticação -----------------------------------------------------------


async def test_token_vai_nos_dois_cabecalhos(url, monkeypatch):
    """Evolution API espera `apikey`; n8n espera `Authorization: Bearer`.
    Mandar os dois faz o provider funcionar com qualquer um sem configuração
    extra — e vão para o mesmo endpoint, já escolhido pelo operador."""
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_TOKEN", "segredo-123")
    falso = WebhookFalso()

    await WebhookProvider(falso.transport).enviar("558699", "oi", {})

    cabecalhos = falso.requisicoes[0].headers
    assert cabecalhos["apikey"] == "segredo-123"
    assert cabecalhos["authorization"] == "Bearer segredo-123"


async def test_sem_token_nao_manda_cabecalho(url):
    falso = WebhookFalso()

    await WebhookProvider(falso.transport).enviar("558699", "oi", {})

    cabecalhos = falso.requisicoes[0].headers
    assert "apikey" not in cabecalhos
    assert "authorization" not in cabecalhos


# --- Integração com o registry e o registro ---------------------------------


def test_registry_conhece_o_webhook(monkeypatch):
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "webhook")
    assert canais.obter_provider().nome == "webhook"


async def test_relato_nao_sai_no_corpo_do_webhook(banco, contatos, url):
    """O caminho completo até o fio: o que chega ao endpoint externo."""
    c = criar_chamado_real()
    falso = WebhookFalso()

    await canais.notificar(c, "csv", provider=WebhookProvider(falso.transport))

    assert RELATO not in falso.requisicoes[0].content.decode()


async def test_falha_do_webhook_e_gravada(banco, contatos, url):
    c = criar_chamado_real()
    falso = WebhookFalso(502, corpo="bad gateway")

    sucesso, _ = await canais.notificar(
        c, "csv", provider=WebhookProvider(falso.transport)
    )

    registro = db.listar_notificacoes(c["chamado_id"])[0]
    assert sucesso is False
    assert registro["provider"] == "webhook"
    assert "502" in registro["detalhe"]


async def test_falha_de_rede_nao_desfaz_o_chamado(banco, contatos, url):
    """O critério da MVP-029, verificado no banco: o registro vem primeiro e
    sobrevive à falha do aviso. É o que permite o SLA escalonar depois
    (MVP-038) em vez de a emergência simplesmente sumir."""
    c = criar_chamado_real()
    falso = WebhookFalso(erro=httpx.ConnectError("sem rota para o host"))

    await canais.notificar(c, "csv", provider=WebhookProvider(falso.transport))

    persistido = db.obter_chamado(c["chamado_id"])
    assert persistido is not None
    assert persistido["status"] == StatusChamado.roteado
    assert persistido["texto_livre"] == RELATO
    assert db.listar_notificacoes(c["chamado_id"])[0]["sucesso"] is False
