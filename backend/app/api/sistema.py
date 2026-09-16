"""Endpoints de sistema: diagnóstico.

Este arquivo existe por causa de um defeito específico do projeto de
referência: ele **afirmava** usar IA sem estar usando. A triagem carimbava
`fonte: "agentes"` mesmo quando nenhum LLM havia respondido e só a heurística
de palavras-chave tinha rodado. Não havia como perceber a degradação — o
sistema parecia inteiro e estava operando com uma fração da capacidade.

Daí o princípio deste `/health`: **reportar o que de fato está funcionando, não
o que deveria estar.** Cada campo é lido da realidade no momento da pergunta —
o artefato é carregado, o banco é consultado, o arquivo do build é aberto.
Nenhum deles repete uma configuração de volta.

`status` continua `"ok"` enquanto o serviço responde: é sinal de vida, e uma
sonda de monitoramento precisa dele estável. A degradação vive em `avisos`, que
é o campo para ler quando algo parece estranho.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from .. import canais, config, db
from ..triagem import classificador, motor_ativo

router = APIRouter(tags=["sistema"])

# Nome do arquivo que o build do frontend grava, gerado por `make deploy`
# (MVP-066b).
#
# Fica **dentro** de `FRONTEND_DIST`, e não ao lado dele, de propósito. O
# deploy envia `dist/` por rsync; um build-id fora dessa pasta não viajaria com
# o artefato, e daria para ter um `dist/` velho com um build-id novo — que é
# exatamente o bug silencioso que o build-id existe para detectar.
ARQUIVO_BUILD_ID = "build-id"


@router.get("/health")
def health() -> dict:
    """Diagnóstico do serviço, verificado na hora."""
    triagem = _triagem()
    notificacao = _notificacao()
    frontend = _frontend()
    seguranca = _seguranca()
    banco = _banco_responde()

    return {
        "status": "ok",
        "banco": banco,
        "triagem": triagem,
        "notificacao": notificacao,
        "frontend": frontend,
        "seguranca": seguranca,
        "avisos": _avisos(banco, triagem, notificacao, frontend, seguranca),
    }


def _triagem() -> dict:
    """Qual motor a próxima triagem usaria, e por quê.

    `modo` é `classificador` **somente** se o artefato foi carregado de fato.
    `motor_ativo()` pergunta ao classificador se ele está disponível, o que
    obriga o carregamento a ter acontecido — não há caminho em que este campo
    diga `classificador` sem haver modelo em memória.
    """
    info = classificador.status()
    return {
        "modo": motor_ativo(),
        "artefato_existe": info["artefato_existe"],
        "caminho": info["caminho"],
        "meta": info.get("meta"),
    }


def _notificacao() -> dict:
    """Qual provider será usado de fato, e o que falta configurar.

    `provider` é o **efetivo**, não o pedido: um nome inválido em
    `POTO_NOTIF_PROVIDER` degrada para `log` (MVP-028), e é justamente essa
    diferença que o diagnóstico precisa mostrar.
    """
    efetivo = canais.provider_configurado()
    return {
        "provider": efetivo,
        "provider_configurado": config.NOTIF_PROVIDER,
        "webhook_url_definida": bool(config.NOTIF_WEBHOOK_URL),
        "canais_sem_contato": config.canais_sem_contato(),
        "contact_override_ativo": bool(config.CONTACT_OVERRIDE),
    }


def _frontend() -> dict:
    """Qual artefato do frontend está sendo servido.

    Comparar este `build_id` com o gerado localmente é o que responde "a Pi
    está rodando o código que eu acabei de enviar?". Sem ele, alterar o código,
    esquecer de reconstruir e depurar a versão antiga custa uma hora.
    """
    dist = Path(config.FRONTEND_DIST)
    arquivo = dist / ARQUIVO_BUILD_ID
    build_id = None
    if arquivo.is_file():
        build_id = arquivo.read_text(encoding="utf-8").strip() or None

    return {
        "montado": (dist / "index.html").is_file(),
        "build_id": build_id,
        "dist": str(dist),
    }


def _seguranca() -> dict:
    """Se o painel está protegido. **Nunca o token em si.**

    Um diagnóstico que devolvesse a credencial para provar que ela existe seria
    a forma mais direta possível de vazá-la.
    """
    return {"painel_protegido": bool(config.PAINEL_TOKEN)}


def _avisos(
    banco: bool,
    triagem: dict,
    notificacao: dict,
    frontend: dict,
    seguranca: dict,
) -> list[str]:
    """Tudo que está degradado, em frases que dizem o que fazer.

    Lista vazia significa sistema íntegro. É o campo que um humano lê quando
    algo parece estranho, então cada aviso nomeia a causa **e** a saída — um
    diagnóstico que só diz "degradado" obriga a ir ler o código.
    """
    avisos = []

    if not banco:
        avisos.append("banco não responde: nenhum chamado será registrado")

    if triagem["modo"] != "classificador":
        avisos.append(
            "triagem na heurística de palavras-chave: o artefato do "
            f"classificador não carregou ({triagem['caminho']}) — rode `make setup`"
        )

    pedido = (notificacao["provider_configurado"] or "").strip().lower()
    if pedido and pedido != notificacao["provider"]:
        avisos.append(
            f"POTO_NOTIF_PROVIDER={pedido!r} é desconhecido: "
            f"usando {notificacao['provider']!r}"
        )

    if notificacao["provider"] == "webhook" and not notificacao["webhook_url_definida"]:
        avisos.append(
            "provider webhook sem POTO_NOTIF_WEBHOOK_URL: nenhuma "
            "notificação sairá"
        )

    if faltando := notificacao["canais_sem_contato"]:
        avisos.append(
            f"canais sem contato configurado, não acionáveis: {', '.join(faltando)}"
        )

    if notificacao["contact_override_ativo"]:
        # Aviso e não erro: em bancada é o comportamento desejado. O que não
        # pode é chegar à operação real sem ninguém notar que todo acionamento
        # está sendo desviado para um número de teste.
        avisos.append(
            "POTO_CONTACT_OVERRIDE ativo: TODOS os canais estão sendo "
            "desviados para um único destino de teste"
        )

    if not seguranca["painel_protegido"]:
        # O aviso no log some no scroll. Este campo é onde alguém procura antes
        # de colocar em operação — é o que impede o modo desenvolvimento de
        # chegar à produção sem ninguém notar.
        avisos.append(
            "POTO_PAINEL_TOKEN vazio: /chamados e /ws estão liberados sem "
            "credencial, expondo o relato de quem pediu ajuda"
        )

    if not frontend["montado"]:
        avisos.append(
            f"frontend não montado em {frontend['dist']}: a API responde, "
            "mas a aplicação não é servida"
        )
    elif not frontend["build_id"]:
        avisos.append(
            "frontend sem build-id: não há como conferir se o artefato "
            "servido é o esperado"
        )

    return avisos


def _banco_responde() -> bool:
    try:
        with db.conectar() as con:
            con.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


# ===========================================================================
# Constantes para o frontend
# ===========================================================================
#
# Estes dois endpoints existem para matar duplicação. No projeto de referência o
# frontend repetia prazos de SLA e a lista de canais em constantes próprias, e
# mudar um prazo exigia alterar dois lugares — o segundo sempre esquecido. Aqui
# o backend é a fonte única: quem decide o domínio é quem o serve.
#
# **São endpoints abertos**, como `/health`: o totem precisa deles antes de
# qualquer autenticação. Logo, nada de contato institucional passa por aqui.


@router.get("/config")
def configuracao() -> dict:
    """As constantes de domínio que a interface consome.

    `sla` vem com os prazos por gravidade, `orientacao` incluída com valor
    nulo — que é informação, não ausência dela: diz ao painel que aquele nível
    **não** escalona, em vez de deixá-lo inferir por omissão.
    """
    return {
        "sla": dict(config.SLA_SEGUNDOS),
        "canais_estado": _canais([*config.CANAIS_ESTADO]),
        "totem_offline_seg": config.TOTEM_OFFLINE_SEG,
    }


@router.get("/canais")
def catalogo() -> list[dict]:
    """O catálogo de canais com nomes legíveis.

    **Sem `contato`.** A tabela de rotas em ARCHITECTURE.md §6 previa
    `{nome, contato}`, mas este endpoint é de sistema e não exige credencial:
    devolver o telefone aqui entregaria os contatos institucionais de toda a
    universidade a qualquer um que alcance a API. O `config.py` já tinha tomado
    essa decisão do outro lado — `CANAIS` guarda só `nome` justamente para que
    um `return CANAIS` descuidado não pudesse vazar nada.

    Quem precisa do destino é o roteamento, por `config.contato_canal()`, e ele
    aparece mascarado no detalhe do chamado (MVP-032).
    """
    return _canais(list(config.CANAIS))


def _canais(chaves: list[str]) -> list[dict]:
    """Lista em vez de dicionário: a **ordem** é significativa.

    `CANAIS_ESTADO` está na ordem em que os botões de escalonamento aparecem na
    tela de alerta ativo. Num objeto JSON essa ordem não é garantida pelo
    contrato, e o frontend teria que reordenar — duplicando a decisão que este
    endpoint existe para centralizar.
    """
    return [{"canal": canal, "nome": config.nome_canal(canal)} for canal in chaves]
