"""`GET /health` — o diagnóstico honesto.

Estes testes existem por causa de um defeito específico do projeto de
referência: ele **afirmava** usar IA sem estar usando. A triagem carimbava
`fonte: "agentes"` mesmo quando nenhum LLM havia respondido e só a heurística
de palavras-chave tinha rodado. Não havia como perceber a degradação — o
sistema parecia inteiro e operava com uma fração da capacidade.

Então a pergunta de cada teste aqui é a mesma: *se este subsistema estiver
quebrado, o `/health` conta?* Um diagnóstico que só sabe dizer "ok" é pior que
nenhum, porque dá confiança falsa.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import criar_app

ROTA = "/api/v1/health"


@pytest.fixture
def dist(tmp_path, monkeypatch):
    """Build do frontend enviado por `make deploy`, com build-id."""
    pasta = tmp_path / "dist"
    pasta.mkdir()
    (pasta / "index.html").write_text("<title>P.O.T.O</title>", encoding="utf-8")
    (pasta / "build-id").write_text("a1b2c3d4e5f6\n", encoding="utf-8")
    monkeypatch.setattr(config, "FRONTEND_DIST", str(pasta))
    return pasta


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_URL", "")
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "_CONTATOS", {"csv": "5586999990001"})
    monkeypatch.setattr(config, "PAINEL_TOKEN", "token-de-teste")


@pytest.fixture
def cliente(ambiente, dist):
    with TestClient(criar_app()) as c:
        yield c


def saude(cliente) -> dict:
    r = cliente.get(ROTA)
    assert r.status_code == 200
    return r.json()


# ===========================================================================
# Sinal de vida
# ===========================================================================


def test_responde_ok(cliente):
    """`status` é sinal de vida e permanece `"ok"` enquanto o serviço responde:
    uma sonda de monitoramento precisa dele estável. A degradação vive em
    `avisos`."""
    assert saude(cliente)["status"] == "ok"


def test_sistema_integro_nao_tem_avisos(cliente):
    """Lista vazia é a afirmação forte deste endpoint. Se ela nunca esvaziasse,
    ninguém olharia para ela."""
    assert saude(cliente)["avisos"] == []


def test_banco_responde(cliente):
    assert saude(cliente)["banco"] is True


def test_banco_inacessivel_e_reportado(cliente, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", "/caminho/que/nao/existe/x.db")

    dados = saude(cliente)

    assert dados["banco"] is False
    assert any("banco não responde" in a for a in dados["avisos"])


# ===========================================================================
# Triagem — o campo que o projeto de referência mentia
# ===========================================================================


def test_modo_e_classificador_quando_o_artefato_carrega(cliente):
    assert saude(cliente)["triagem"]["modo"] == "classificador"


def test_modo_cai_para_heuristica_sem_artefato(cliente, monkeypatch):
    """O cenário do "Como validar" da task: renomear o `.joblib` e conferir que
    o `/health` diz `heuristica`. **Sem isto o sistema opera degradado sem
    ninguém saber** — que é exatamente o defeito original."""
    monkeypatch.setattr(config, "CLF_PATH", "/nao/existe/triagem_clf.joblib")

    triagem = saude(cliente)["triagem"]

    assert triagem["modo"] == "heuristica"
    assert triagem["artefato_existe"] is False


def test_triagem_degradada_gera_aviso_com_a_saida(cliente, monkeypatch):
    """O aviso nomeia a causa **e** o que fazer. Um diagnóstico que só diz
    "degradado" obriga a ir ler o código."""
    monkeypatch.setattr(config, "CLF_PATH", "/nao/existe/triagem_clf.joblib")

    avisos = saude(cliente)["avisos"]

    assert any("heurística" in a for a in avisos)
    assert any("make setup" in a for a in avisos)


def test_modo_nunca_diz_classificador_sem_modelo(cliente, monkeypatch):
    """A propriedade central: o campo é lido da realidade, não da configuração.
    Apontar `CLF_PATH` para um arquivo que existe mas não é um modelo também
    tem que degradar — o artefato *existe*, mas não carrega."""
    monkeypatch.setattr(config, "CLF_PATH", str(__file__))

    triagem = saude(cliente)["triagem"]

    assert triagem["artefato_existe"] is True
    assert triagem["modo"] == "heuristica"


def test_triagem_informa_o_caminho(cliente):
    """Para que o aviso seja acionável: saber *onde* o artefato foi procurado é
    metade do diagnóstico."""
    assert saude(cliente)["triagem"]["caminho"] == config.CLF_PATH


def test_triagem_expoe_os_metadados_do_treino(cliente):
    meta = saude(cliente)["triagem"]["meta"]
    assert meta is not None
    assert "treinado_em" in meta


# ===========================================================================
# Notificação
# ===========================================================================


def test_provider_reportado(cliente):
    assert saude(cliente)["notificacao"]["provider"] == "log"


def test_provider_invalido_mostra_a_diferenca(cliente, monkeypatch):
    """O provider reportado é o **efetivo**, não o pedido. Um nome inválido
    degrada para `log` (MVP-028), e é justamente essa diferença que o
    diagnóstico precisa mostrar — senão o operador acha que o WhatsApp está
    configurado."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "whatsapp-de-verdade")

    dados = saude(cliente)

    assert dados["notificacao"]["provider"] == "log"
    assert dados["notificacao"]["provider_configurado"] == "whatsapp-de-verdade"
    assert any("desconhecido" in a for a in dados["avisos"])


def test_webhook_sem_url_gera_aviso(cliente, monkeypatch):
    """Configuração coerente mas incompleta: o provider existe, a URL não. Sem
    aviso, o `/health` diria "webhook" enquanto nada sai."""
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "webhook")
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_URL", "")

    dados = saude(cliente)

    assert dados["notificacao"]["provider"] == "webhook"
    assert dados["notificacao"]["webhook_url_definida"] is False
    assert any("POTO_NOTIF_WEBHOOK_URL" in a for a in dados["avisos"])


def test_webhook_com_url_nao_gera_aviso(cliente, monkeypatch):
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "webhook")
    monkeypatch.setattr(config, "NOTIF_WEBHOOK_URL", "https://evolution.local/x")

    assert saude(cliente)["avisos"] == []


def test_canais_sem_contato_sao_listados(cliente, monkeypatch):
    """Canal sem contato não é acionável (MVP-028). Quem sobe o serviço precisa
    saber **quais** faltam, não que "algo" falta."""
    monkeypatch.setattr(
        config, "_CONTATOS", {"csv": "5586999990001", "sala_lilas": "", "sapsi": ""}
    )

    dados = saude(cliente)

    assert dados["notificacao"]["canais_sem_contato"] == ["sala_lilas", "sapsi"]
    assert any("sala_lilas" in a for a in dados["avisos"])


def test_nao_expoe_os_contatos(cliente, monkeypatch):
    """`/health` é diagnóstico, não diretório telefônico. Ele diz *quais canais*
    estão sem contato — nunca qual é o contato dos que têm."""
    monkeypatch.setattr(config, "_CONTATOS", {"csv": "5586999990001"})

    assert "5586999990001" not in cliente.get(ROTA).text


def test_contact_override_e_avisado(cliente, monkeypatch):
    """Aviso e não erro: em bancada é o comportamento desejado. O que não pode é
    chegar à operação real sem ninguém notar que todo acionamento está sendo
    desviado para um número de teste."""
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "5586900000000")

    dados = saude(cliente)

    assert dados["notificacao"]["contact_override_ativo"] is True
    assert any("OVERRIDE" in a for a in dados["avisos"])


def test_contact_override_nao_aparece_na_resposta(cliente, monkeypatch):
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "5586900000000")
    assert "5586900000000" not in cliente.get(ROTA).text


# ===========================================================================
# Build-id do frontend
# ===========================================================================


def test_build_id_e_exposto(cliente):
    """Comparar este valor com o gerado localmente é o que responde "a Pi está
    rodando o código que eu acabei de enviar?"."""
    assert saude(cliente)["frontend"]["build_id"] == "a1b2c3d4e5f6"


def test_frontend_montado(cliente):
    assert saude(cliente)["frontend"]["montado"] is True


def test_build_id_ausente_gera_aviso(cliente, dist):
    """Build enviado sem o identificador: a aplicação funciona, mas não há como
    conferir se é a versão esperada."""
    (dist / "build-id").unlink()

    dados = saude(cliente)

    assert dados["frontend"]["build_id"] is None
    assert any("build-id" in a for a in dados["avisos"])


def test_build_id_vazio_conta_como_ausente(cliente, dist):
    """Arquivo criado por um build que falhou no meio. Devolver `""` faria a
    comparação com o build-id local passar por engano."""
    (dist / "build-id").write_text("\n", encoding="utf-8")

    assert saude(cliente)["frontend"]["build_id"] is None


def test_frontend_ausente_gera_aviso(cliente, monkeypatch, tmp_path):
    """Estado de desenvolvimento, e também o de um deploy que não completou."""
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))

    dados = saude(cliente)

    assert dados["frontend"]["montado"] is False
    assert any("não montado" in a for a in dados["avisos"])


def test_frontend_ausente_nao_gera_aviso_de_build_id(cliente, monkeypatch, tmp_path):
    """Um aviso só. "Sem dist" já explica a falta do build-id; os dois juntos
    fariam o operador procurar dois problemas onde há um."""
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))

    avisos = saude(cliente)["avisos"]

    assert len([a for a in avisos if "build-id" in a]) == 0


def test_build_id_fica_dentro_do_dist(cliente, dist):
    """**Decisão corrigida em relação ao plano.** A MVP-066b listava o arquivo
    como `frontend/build-id`, fora do `dist/`.

    O deploy envia `dist/` por rsync. Um build-id fora dessa pasta não viajaria
    com o artefato — daria para ter um `dist/` velho servindo com um build-id
    novo, que é precisamente o bug silencioso que o build-id existe para
    detectar. Então ele mora dentro.
    """
    from app.api.sistema import ARQUIVO_BUILD_ID

    assert (dist / ARQUIVO_BUILD_ID).is_file()
    assert saude(cliente)["frontend"]["build_id"] is not None


# ===========================================================================
# Vários problemas ao mesmo tempo
# ===========================================================================


def test_avisos_acumulam(cliente, monkeypatch, tmp_path):
    """O dia ruim: Pi com cartão novo, sem `make setup`, sem deploy e com a
    trava de bancada esquecida ligada. O diagnóstico precisa listar os quatro,
    não parar no primeiro."""
    monkeypatch.setattr(config, "CLF_PATH", "/nao/existe.joblib")
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "vazio"))
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "5586900000000")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "webhook")

    dados = saude(cliente)

    assert dados["status"] == "ok"  # o serviço responde
    assert len(dados["avisos"]) >= 4


def test_health_continua_respondendo_com_tudo_quebrado(cliente, monkeypatch, tmp_path):
    """O diagnóstico é a última coisa que pode cair: é por ele que se descobre
    que o resto caiu."""
    monkeypatch.setattr(config, "DB_PATH", "/nao/existe/x.db")
    monkeypatch.setattr(config, "CLF_PATH", "/nao/existe.joblib")
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "vazio"))
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "invalido")

    r = cliente.get(ROTA)

    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_formato_da_resposta(cliente):
    dados = saude(cliente)
    assert set(dados) == {
        "status",
        "banco",
        "triagem",
        "notificacao",
        "frontend",
        "seguranca",
        "avisos",
    }


# ===========================================================================
# Proteção do painel (MVP-040)
# ===========================================================================


def test_painel_protegido_e_reportado(cliente):
    assert saude(cliente)["seguranca"]["painel_protegido"] is True


def test_painel_aberto_gera_aviso(cliente, monkeypatch):
    """O modo desenvolvimento não pode chegar à produção em silêncio: as rotas
    liberadas são as que carregam o relato de quem pediu ajuda."""
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")

    dados = saude(cliente)

    assert dados["seguranca"]["painel_protegido"] is False
    assert any("PAINEL_TOKEN" in a for a in dados["avisos"])


def test_token_do_painel_nunca_aparece(cliente, monkeypatch):
    """Um diagnóstico que devolvesse a credencial para provar que ela existe
    seria a forma mais direta possível de vazá-la."""
    monkeypatch.setattr(config, "PAINEL_TOKEN", "segredo-do-painel-abc123")

    assert "segredo-do-painel-abc123" not in cliente.get(ROTA).text


# ===========================================================================
# MVP-037 — /config e /canais
# ===========================================================================
#
# Estes endpoints existem para matar duplicação: no projeto de referência o
# frontend repetia prazos de SLA e a lista de canais em constantes próprias, e
# mudar um prazo exigia alterar dois lugares — o segundo sempre esquecido.

CONFIG = "/api/v1/config"
CANAIS = "/api/v1/canais"


def test_config_traz_os_prazos_de_sla(cliente):
    sla = cliente.get(CONFIG).json()["sla"]
    assert sla["risco_imediato"] == config.SLA_SEGUNDOS["risco_imediato"]
    assert sla["risco_potencial"] == config.SLA_SEGUNDOS["risco_potencial"]


def test_orientacao_vem_com_prazo_nulo(cliente):
    """`null` aqui é informação, não ausência dela: diz ao painel que aquele
    nível **não** escalona, em vez de deixá-lo inferir por omissão."""
    sla = cliente.get(CONFIG).json()["sla"]
    assert "orientacao" in sla
    assert sla["orientacao"] is None


def test_config_traz_os_canais_de_escalonamento(cliente):
    canais = cliente.get(CONFIG).json()["canais_estado"]
    assert [c["canal"] for c in canais] == config.CANAIS_ESTADO


def test_ordem_dos_canais_de_escalonamento_e_preservada(cliente):
    """Lista e não dicionário: a ordem é a dos botões na tela de alerta ativo.
    Num objeto JSON ela não é garantida pelo contrato, e o frontend teria que
    reordenar — duplicando a decisão que este endpoint centraliza."""
    canais = cliente.get(CONFIG).json()["canais_estado"]
    assert [c["canal"] for c in canais][0] == "pm_190"
    assert isinstance(canais, list)


def test_config_traz_o_intervalo_de_dreno(cliente):
    assert cliente.get(CONFIG).json()["totem_offline_seg"] == config.TOTEM_OFFLINE_SEG


def test_config_reflete_a_configuracao(cliente, monkeypatch):
    """Lido na hora, não congelado na subida: é o que permite ajustar o prazo
    sem reconstruir o frontend."""
    monkeypatch.setattr(config, "TOTEM_OFFLINE_SEG", 45)
    assert cliente.get(CONFIG).json()["totem_offline_seg"] == 45


def test_formato_do_config(cliente):
    assert set(cliente.get(CONFIG).json()) == {
        "sla",
        "canais_estado",
        "totem_offline_seg",
    }


def test_canais_traz_o_catalogo_completo(cliente):
    catalogo = cliente.get(CANAIS).json()
    assert {c["canal"] for c in catalogo} == set(config.CANAIS)


def test_canais_traz_nomes_legiveis(cliente):
    """"csv" é vocabulário do código; quem lê na tela é uma pessoa."""
    catalogo = {c["canal"]: c["nome"] for c in cliente.get(CANAIS).json()}
    assert catalogo["csv"] == "CSV / PREUNI"
    assert catalogo["sala_lilas"] == "Sala Lilás"


def test_canais_nao_expoe_contato(cliente, monkeypatch):
    """**A correção ao plano.** A tabela de rotas em ARCHITECTURE.md §6 previa
    `{nome, contato}`, mas este endpoint é de sistema e não exige credencial:
    devolver o telefone aqui entregaria os contatos institucionais de toda a
    universidade a qualquer um que alcance a API.

    O `config.py` já tinha tomado a decisão do outro lado — `CANAIS` guarda só
    `nome` justamente para que um `return CANAIS` descuidado não vazasse nada.
    """
    monkeypatch.setattr(config, "_CONTATOS", {"csv": "5586999990001"})

    resposta = cliente.get(CANAIS)

    assert all(set(c) == {"canal", "nome"} for c in resposta.json())
    assert "5586999990001" not in resposta.text
    assert "contato" not in resposta.text


def test_config_nao_expoe_contato(cliente, monkeypatch):
    monkeypatch.setattr(config, "_CONTATOS", {"pm_190": "190555"})
    assert "190555" not in cliente.get(CONFIG).text


def test_canais_e_config_concordam_sobre_os_nomes(cliente):
    """Duas rotas, uma fonte. Se divergissem, o painel mostraria um nome na
    lista e outro no botão de escalonamento."""
    catalogo = {c["canal"]: c["nome"] for c in cliente.get(CANAIS).json()}
    estado = cliente.get(CONFIG).json()["canais_estado"]

    assert all(catalogo[c["canal"]] == c["nome"] for c in estado)
