"""Dreno da fila offline — a versão offline do defeito de rebaixamento.

No projeto de referência, conversa sem rede virava **sempre** `ouvidoria`. Era
o mesmo defeito do rebaixamento visto de outro ângulo: a informação que a
pessoa deu — o texto, a trilha — era descartada pelo caminho, e o que chegava à
central era a classificação mais fraca possível.

O código que protege contra isso já existe e é o mesmo de um evento ao vivo:
`/eventos` chama `merge_acionamento()` (MVP-030), e o merge promove por sinal
crítico independentemente da trilha. **Este arquivo não acrescenta caminho
novo — ele trava o cenário.**

Vale como arquivo próprio porque a regressão que ele guarda é diferente. Um
evento drenado tem três propriedades que um evento ao vivo não tem, e cada uma
já quebrou algum sistema:

- chega **horas depois** do acontecimento;
- chega possivelmente **mais de uma vez**, porque o dreno pode falhar no meio;
- carrega um `timestamp_local` muito anterior ao `created_at`.

Alguém otimizando o `/eventos` no futuro pode achar seguro pular a triagem
"quando o evento é antigo", ou confiar no `timestamp_local` para rotear. Os
testes abaixo é que dizem que não é.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import criar_app
from app.models import Gravidade, TipoOcorrencia

EVENTOS = "/api/v1/eventos"
PANICO = "/api/v1/panico"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")
    monkeypatch.setattr(
        config, "_CONTATOS", {c: "5586999990001" for c in config.CANAIS}
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    with TestClient(criar_app()) as c:
        yield c


def enfileirado(
    tipo: str = "ouvidoria",
    texto: str | None = None,
    *,
    horas_atras: float = 7,
) -> dict:
    """Payload como a fila do cliente o guarda.

    O `evento_id` já vem gerado — é isso que a MVP-048 garante e o que faz o
    reenvio ser idempotente. O `timestamp_local` é antigo, como num evento que
    ficou horas no `localStorage`.
    """
    quando = datetime.now(UTC) - timedelta(hours=horas_atras)
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": tipo,
        "timestamp_local": quando.isoformat(),
    }
    if texto is not None:
        corpo["texto_livre"] = texto
    return corpo


# ===========================================================================
# O caso que a task nomeia
# ===========================================================================


def test_ouvidoria_com_texto_grave_e_promovida(cliente):
    """O cenário literal do "Como validar": enfileirar
    `{tipo: ouvidoria, texto: "socorro tem um homem me seguindo"}` e drenar."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")

    resposta = cliente.post(EVENTOS, json=corpo)

    assert resposta.status_code == 201
    assert resposta.json()["gravidade"] == Gravidade.risco_imediato


def test_promocao_troca_a_trilha_e_o_canal(cliente):
    """Não é só a gravidade que sobe: o encaminhamento acompanha. Promover a
    gravidade e deixar o chamado na ouvidoria mandaria um risco imediato para
    uma caixa de e-mail."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")

    resposta = cliente.post(EVENTOS, json=corpo).json()

    chamado = db.obter_chamado(resposta["chamado_id"])
    assert chamado["tipo_ocorrencia"] == TipoOcorrencia.mulher
    assert chamado["canal_roteado"] != "ouvidoria"


def test_trilha_original_fica_na_auditoria(cliente):
    """A promoção não apaga o que a pessoa escolheu. Sem `trilha_escolhida` não
    haveria como responder "por que este chamado virou Sala Lilás?" depois."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")

    resposta = cliente.post(EVENTOS, json=corpo).json()

    auditoria = json.loads(db.obter_chamado(resposta["chamado_id"])["triagem_json"])
    assert auditoria["trilha_escolhida"] == "ouvidoria"


# ===========================================================================
# A idade do evento não muda nada
# ===========================================================================


@pytest.mark.parametrize("horas", [0.1, 7, 72, 720])
def test_evento_antigo_recebe_a_mesma_triagem(cliente, horas):
    """De dez minutos a um mês na fila. Um evento velho **não** é menos grave —
    é mais, porque ninguém apareceu nesse tempo. Qualquer atalho que pulasse a
    triagem "porque já passou" quebraria aqui."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo", horas_atras=horas)

    resposta = cliente.post(EVENTOS, json=corpo).json()

    assert resposta["gravidade"] == Gravidade.risco_imediato


def test_timestamp_local_nao_roteia(cliente):
    """O relógio do tablet não decide nada. Um aparelho com a hora errada — ou
    um payload adulterado — não pode mudar o encaminhamento, e o horário
    autoritativo é o `created_at` do servidor."""
    absurdo = enfileirado("seguranca", horas_atras=0)
    absurdo["timestamp_local"] = "1999-01-01T00:00:00"

    resposta = cliente.post(EVENTOS, json=absurdo).json()

    assert resposta["gravidade"] == Gravidade.risco_imediato
    chamado = db.obter_chamado(resposta["chamado_id"])
    assert chamado["timestamp_local"] == "1999-01-01T00:00:00"
    # O servidor registrou a chegada com o **próprio** relógio.
    assert chamado["created_at"][:4] != "1999"


def test_timestamp_local_ilegivel_nao_impede_o_dreno(cliente):
    """`timestamp_local` é `str` e não `datetime` de propósito (MVP-014). Um
    evento que ficou na fila não pode ser **perdido** por causa de metadado."""
    corpo = enfileirado("seguranca")
    corpo["timestamp_local"] = "ontem à noite, mais ou menos"

    assert cliente.post(EVENTOS, json=corpo).status_code == 201


def test_sem_timestamp_local_tambem_drena(cliente):
    corpo = enfileirado("seguranca")
    del corpo["timestamp_local"]
    assert cliente.post(EVENTOS, json=corpo).status_code == 201


# ===========================================================================
# Idempotência do reenvio — o dreno pode falhar no meio
# ===========================================================================


def test_dreno_repetido_nao_duplica(cliente):
    """O dreno falha no meio, tenta de novo, e o mesmo item vai duas vezes. Se
    isto duplicasse, uma emergência viraria dois alarmes e a central despacharia
    duas equipes."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")

    primeiro = cliente.post(EVENTOS, json=corpo).json()
    segundo = cliente.post(EVENTOS, json=corpo).json()
    terceiro = cliente.post(EVENTOS, json=corpo).json()

    assert [primeiro["duplicado"], segundo["duplicado"], terceiro["duplicado"]] == [
        False,
        True,
        True,
    ]
    assert len({r["chamado_id"] for r in (primeiro, segundo, terceiro)}) == 1
    assert len(db.listar_chamados()) == 1


def test_reenvio_nao_notifica_de_novo(cliente):
    """Reenviar não pode reavisar o CSV. O plantonista receberia a mesma
    emergência duas vezes e não saberia se são dois casos."""
    corpo = enfileirado("seguranca")

    cliente.post(EVENTOS, json=corpo)
    cliente.post(EVENTOS, json=corpo)

    chamado_id = db.listar_chamados()[0]["chamado_id"]
    assert len(db.listar_notificacoes(chamado_id)) == 1


def test_reenvio_preserva_a_promocao(cliente):
    """A segunda resposta tem que dizer o mesmo que a primeira. Se ela
    recalculasse e devolvesse a gravidade da trilha crua, a tela do totem
    mostraria uma coisa e o painel outra."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")

    primeiro = cliente.post(EVENTOS, json=corpo).json()
    segundo = cliente.post(EVENTOS, json=corpo).json()

    assert segundo["gravidade"] == primeiro["gravidade"] == Gravidade.risco_imediato
    assert segundo["canal_roteado"] == primeiro["canal_roteado"]


def test_reenvio_nao_sobrescreve_o_relato(cliente):
    """O `evento_id` nasce no totem junto com o conteúdo. Conteúdo diferente com
    o mesmo id é erro de cliente, e o registro original é o que vale."""
    corpo = enfileirado("ouvidoria", "socorro tem um homem me seguindo")
    cliente.post(EVENTOS, json=corpo)

    adulterado = {**corpo, "texto_livre": "era brincadeira"}
    resposta = cliente.post(EVENTOS, json=adulterado).json()

    chamado = db.obter_chamado(resposta["chamado_id"])
    assert chamado["texto_livre"] == "socorro tem um homem me seguindo"
    assert chamado["gravidade"] == Gravidade.risco_imediato


# ===========================================================================
# A fila inteira, como o dreno a envia
# ===========================================================================


def test_fila_de_tres_trilhas_drena_inteira(cliente):
    """O cenário de validação da MVP-057: três trilhas acionadas offline."""
    fila = [
        enfileirado("saude", "estou passando mal"),
        enfileirado("seguranca", "socorro"),
        enfileirado("mulher"),
    ]

    respostas = [cliente.post(EVENTOS, json=c).json() for c in fila]

    assert all(r["duplicado"] is False for r in respostas)
    assert len(db.listar_chamados()) == 3
    assert len({r["chamado_id"] for r in respostas}) == 3


def test_nenhum_item_da_fila_e_rebaixado(cliente):
    """A invariante do projeto aplicada à fila: a gravidade de cada item
    drenado nunca é menor que a da trilha que a pessoa escolheu."""
    from app.triagem.merge import RANK_GRAVIDADE
    from app.triagem.roteador import rotear

    for tipo in TipoOcorrencia:
        for texto in (None, "socorro", "quero saber o horário da biblioteca"):
            corpo = enfileirado(str(tipo), texto)
            piso = rotear(tipo)["gravidade"]

            resposta = cliente.post(EVENTOS, json=corpo).json()

            assert (
                RANK_GRAVIDADE[Gravidade(resposta["gravidade"])]
                >= RANK_GRAVIDADE[piso]
            ), f"{tipo} + {texto!r} rebaixou {piso}"


def test_panico_enfileirado_drena_como_panico(cliente):
    """O pânico guardado offline mantém `alerta_ativo` ao chegar — o estado não
    é rebaixado por ter esperado."""
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "timestamp_local": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
    }

    resposta = cliente.post(PANICO, json=corpo).json()

    assert resposta["status"] == "alerta_ativo"
    assert resposta["gravidade"] == Gravidade.risco_imediato
    assert len(resposta["resultados"]) == 2


def test_panico_enfileirado_nao_duplica(cliente):
    corpo = {"evento_id": str(uuid4()), "totem_id": "T1"}

    cliente.post(PANICO, json=corpo)
    segundo = cliente.post(PANICO, json=corpo).json()

    assert segundo["duplicado"] is True
    assert len(db.listar_chamados()) == 1


# ===========================================================================
# Limitação conhecida
# ===========================================================================


def test_backend_nao_distingue_evento_drenado_de_ao_vivo(cliente):
    """**Documenta uma lacuna, não uma garantia.**

    O payload de um evento drenado é byte a byte o mesmo do original — é isso
    que preserva a idempotência — então `origem_acionamento` vem `touch` nos
    dois casos e o backend não tem como saber que houve atraso.

    O sinal existe, mas é indireto: a diferença entre `timestamp_local` (relógio
    do tablet) e `created_at` (relógio do servidor). O painel da Fase 8 pode
    calculá-la e mostrar "registrado há 7 horas".

    Não é defeito de segurança — responder a uma emergência de sete horas atrás
    continua sendo a ação certa, porque ninguém sabe se a pessoa está bem. É
    falta de **contexto** para o operador, e este teste existe para que a
    lacuna seja encontrada por quem for construir o painel.
    """
    corpo = enfileirado("seguranca", horas_atras=7)

    resposta = cliente.post(EVENTOS, json=corpo).json()

    chamado = db.obter_chamado(resposta["chamado_id"])
    assert chamado["origem_acionamento"] == "touch"

    # O sinal indireto disponível ao painel:
    local = datetime.fromisoformat(chamado["timestamp_local"])
    servidor = datetime.fromisoformat(chamado["created_at"])
    assert (servidor - local) > timedelta(hours=6)
