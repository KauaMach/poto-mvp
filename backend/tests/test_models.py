"""Contratos da API: o que é aceito, o que é rejeitado e como serializa."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    CanalOpcao,
    CanalResultado,
    ChamadoUpdate,
    EscalonamentoIn,
    EventoIn,
    EventoOut,
    Gravidade,
    InstrucaoTotem,
    Modo,
    OrigemAcionamento,
    PanicoIn,
    PanicoOut,
    StatusChamado,
    TipoOcorrencia,
)


def _evento_minimo(**extra) -> dict:
    return {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": "seguranca",
        **extra,
    }


# --- EventoIn ---------------------------------------------------------------


def test_evento_aceita_o_minimo_e_aplica_defaults():
    ev = EventoIn(**_evento_minimo())
    assert ev.modo is Modo.normal
    assert ev.origem_acionamento is OrigemAcionamento.touch
    assert ev.texto_livre is None
    assert ev.timestamp_local is None


def test_evento_id_e_validado_como_uuid():
    ev = EventoIn(**_evento_minimo())
    assert isinstance(ev.evento_id, UUID)


@pytest.mark.parametrize("valor", ["", "nao-e-uuid", "12345", "TOTEM-CCS-01"])
def test_evento_id_malformado_e_rejeitado(valor):
    """A idempotência inteira depende deste campo: chave inválida significaria
    um segundo chamado para a mesma emergência no reenvio."""
    dados = _evento_minimo()
    dados["evento_id"] = valor
    with pytest.raises(ValidationError):
        EventoIn(**dados)


def test_trilha_e_obrigatoria():
    dados = _evento_minimo()
    del dados["tipo_ocorrencia"]
    with pytest.raises(ValidationError):
        EventoIn(**dados)


def test_totem_id_vazio_e_rejeitado():
    with pytest.raises(ValidationError):
        EventoIn(**_evento_minimo(totem_id=""))


def test_relogio_dessincronizado_nao_derruba_o_acionamento():
    """`timestamp_local` é diagnóstico. Um tablet com a hora errada não pode
    fazer um pedido de socorro falhar com 422 — o horário autoritativo é o do
    servidor."""
    ev = EventoIn(**_evento_minimo(timestamp_local="horario-bizarro-do-tablet"))
    assert ev.timestamp_local == "horario-bizarro-do-tablet"


def test_texto_livre_tem_teto():
    EventoIn(**_evento_minimo(texto_livre="a" * 2000))
    with pytest.raises(ValidationError):
        EventoIn(**_evento_minimo(texto_livre="a" * 2001))


def test_modo_do_cliente_e_apenas_intencao():
    """O cliente pode pedir `normal` na trilha mulher; quem decide é o roteador
    (MVP-012), que força discreto. Aqui o contrato só transporta."""
    ev = EventoIn(**_evento_minimo(tipo_ocorrencia="mulher", modo="normal"))
    assert ev.tipo_ocorrencia is TipoOcorrencia.mulher
    assert ev.modo is Modo.normal


# --- Saídas -----------------------------------------------------------------


def test_instrucao_totem_default_e_o_caso_comum():
    i = InstrucaoTotem(mensagem_tela="Pedido enviado.")
    assert i.feedback_sonoro is True
    assert i.tela_neutra is False


def test_evento_out_serializa_enums_como_valor():
    out = EventoOut(
        chamado_id="CALL-2026-000001",
        status=StatusChamado.notificado,
        canal_roteado="csv",
        gravidade=Gravidade.risco_imediato,
        instrucao_totem=InstrucaoTotem(mensagem_tela="Ajuda a caminho."),
    )
    dados = json.loads(out.model_dump_json())
    assert dados["status"] == "notificado"
    assert dados["gravidade"] == "risco_imediato"
    assert dados["duplicado"] is False
    assert dados["instrucao_totem"]["feedback_sonoro"] is True


def test_modo_discreto_viaja_na_instrucao_e_nao_na_tela_do_cliente():
    """Tela neutra e ausência de som vêm decididas do backend."""
    out = EventoOut(
        chamado_id="CALL-2026-000002",
        status=StatusChamado.notificado,
        canal_roteado="sala_lilas",
        gravidade=Gravidade.risco_potencial,
        instrucao_totem=InstrucaoTotem(
            mensagem_tela="Seu pedido foi registrado. Aguarde atendimento.",
            feedback_sonoro=False,
            tela_neutra=True,
        ),
    )
    assert out.instrucao_totem.tela_neutra is True
    assert out.instrucao_totem.feedback_sonoro is False


# --- Pânico -----------------------------------------------------------------


def test_panico_out_nasce_com_listas_vazias():
    out = PanicoOut(
        chamado_id="CALL-2026-000003",
        status=StatusChamado.alerta_ativo,
        gravidade=Gravidade.risco_imediato,
    )
    assert out.resultados == []
    assert out.escalonamento_disponivel == []


@pytest.mark.parametrize("modelo", [CanalOpcao, CanalResultado])
def test_contratos_de_canal_nao_expoem_o_destino(modelo):
    """`/panico` é aberto, sem credencial. Devolver o telefone do CSV ou da
    Sala Lilás ali entregaria os contatos institucionais a qualquer um que
    alcance a API. O destino efetivo fica em `notificacoes`, atrás do token."""
    assert "destino" not in modelo.model_fields


def test_panico_exige_uuid_tambem():
    with pytest.raises(ValidationError):
        PanicoIn(evento_id="nao-e-uuid", totem_id="TOTEM-CCS-01")


# --- Operações da central ---------------------------------------------------


def test_chamado_update_e_parcial():
    assert ChamadoUpdate().status is None
    assert ChamadoUpdate(status="encerrado").status is StatusChamado.encerrado
    assert ChamadoUpdate(observacao="sem resposta").observacao == "sem resposta"


def test_chamado_update_rejeita_status_inexistente():
    with pytest.raises(ValidationError):
        ChamadoUpdate(status="status_que_nao_existe")


def test_escalonamento_exige_canal():
    assert EscalonamentoIn(canal="samu_192").canal == "samu_192"
    with pytest.raises(ValidationError):
        EscalonamentoIn()
