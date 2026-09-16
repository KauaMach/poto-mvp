"""Regressão de segurança — o arquivo que não pode quebrar.

Cada caso aqui foi **reproduzido falhando** no projeto de referência
(`gutoportelaa/poto`) em 15/09/2026. Não são hipóteses: são defeitos que
existiram, que mandavam pedidos de socorro para a Ouvidoria ou retinham
emergências aguardando um operador.

Dois princípios que fazem esta suíte diferente das outras:

1. **Roda com os dois motores.** Cada caso é executado com o classificador
   treinado *e* com ele ausente. Uma Pi que subiu sem `make setup` precisa
   tratar emergência como emergência — o motor pode mudar, o desfecho não.

2. **Não mede acurácia, trava comportamento.** A acurácia honesta é medida no
   held-out por `make train-clf`. Aqui o que importa é que estas entradas
   específicas nunca mais falhem.

---

**O que a verificação por mutação revelou.** Esta suíte foi testada contra si
mesma, reintroduzindo o defeito original no `merge.py` para ver se ela pegaria.
O resultado mudou como o arquivo está organizado:

- Quebrar **uma** das proteções não produz o defeito. A gravidade é protegida em
  três pontos independentes: o `mais_protetiva()` entre trilha e triagem, a
  promoção por sinal crítico, e o `mais_protetiva()` aplicado de novo depois do
  re-roteamento. Isso é defesa em profundidade real — e é uma propriedade que
  alguém pode destruir sem perceber, ao "simplificar".
- Quebrando **duas**, 36 testes falham. Mas as falhas se concentram em
  `test_varredura_nenhuma_combinacao_rebaixa` (29 delas): **a varredura ampla é
  quem faz o trabalho pesado**, não a tabela.
- Os casos emblemáticos da tabela — inclusive **"socorro"** — continuam passando
  mesmo com duas proteções quebradas, porque o sinal crítico os resgata. Os
  únicos da tabela que pegam o defeito são *"preciso de ajuda"* e *"um homem
  está me seguindo"*, que **não** têm sinal crítico e dependem só do `max()`.

A conclusão prática: não remova a varredura ampla achando que a tabela cobre o
mesmo. Ela não cobre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from app import config
from app.models import Gravidade, TipoOcorrencia
from app.triagem import classificador, merge_acionamento, rotear, triar

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RANK = {
    Gravidade.orientacao: 1,
    Gravidade.risco_potencial: 2,
    Gravidade.risco_imediato: 3,
}


@dataclass(frozen=True)
class Caso:
    trilha: TipoOcorrencia
    texto: str | None
    gravidade: Gravidade
    canal: str | None = None
    origem: str = ""

    def __str__(self) -> str:
        return f"{self.trilha.value}+{self.texto or 'sem-texto'}"


# ---------------------------------------------------------------------------
# A tabela. Cada linha é um defeito que existiu.
# ---------------------------------------------------------------------------

CASOS = [
    Caso(
        TipoOcorrencia.seguranca, None, Gravidade.risco_imediato, "csv",
        "linha de base: o toque puro sempre funcionou",
    ),
    Caso(
        TipoOcorrencia.seguranca, "socorro", Gravidade.risco_imediato, "csv",
        "virava orientacao e ficava retido — a palavra mais direta de pedir "
        "ajuda era a que reduzia a urgência",
    ),
    Caso(
        TipoOcorrencia.seguranca, "preciso de ajuda", Gravidade.risco_imediato, "csv",
        "virava orientacao: rebaixamento de dois níveis",
    ),
    Caso(
        TipoOcorrencia.seguranca,
        "um homem está me seguindo perto do bloco 7",
        Gravidade.risco_imediato, "csv",
        "virava risco_potencial e ficava pendente_validacao",
    ),
    Caso(
        TipoOcorrencia.saude, "estou desmaiando",
        Gravidade.risco_imediato, "samu_192",
        "ia para a Ouvidoria: a lista tinha 'desmaio' e 'desmaiou', não "
        "'desmaiando'",
    ),
    Caso(
        TipoOcorrencia.saude, "to passando mal",
        Gravidade.risco_imediato, "samu_192",
        "ficava em orientacao e ia para o SAPSI em vez do SAMU",
    ),
    Caso(
        TipoOcorrencia.seguranca, "tem um cara armado no estacionamento",
        Gravidade.risco_imediato, "csv",
        "este já funcionava — fica como controle",
    ),
    Caso(
        TipoOcorrencia.ouvidoria, "sugerir mais bancos no pátio",
        Gravidade.orientacao, "ouvidoria",
        "abria portão de validação por confiança baixa, enchendo o painel de "
        "ruído e escondendo o caso real",
    ),
]


# ---------------------------------------------------------------------------
# Os dois motores
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def artefato(tmp_path_factory):
    destino = tmp_path_factory.mktemp("clf") / "regressao.joblib"
    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    classificador.treinar(dados, caminho=str(destino))
    return str(destino)


@pytest.fixture(params=["classificador", "heuristica"])
def motor(request, artefato, tmp_path, monkeypatch):
    """Cada teste roda duas vezes: com o artefato treinado e sem ele."""
    if request.param == "classificador":
        monkeypatch.setattr(config, "CLF_PATH", artefato)
    else:
        monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "ausente.joblib"))
    classificador._cache.update(caminho=None, modelo=None, tentado=False)
    yield request.param
    classificador._cache.update(caminho=None, modelo=None, tentado=False)


def acionar(trilha: TipoOcorrencia, texto: str | None):
    """O caminho completo de um acionamento: roteia, tria e funde."""
    routing = rotear(trilha)
    triagem = triar(texto) if texto else None
    return routing, merge_acionamento(routing, triagem, texto=texto)


# ---------------------------------------------------------------------------
# A tabela, caso a caso
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("caso", CASOS, ids=str)
def test_gravidade_exigida(caso, motor):
    _, decisao = acionar(caso.trilha, caso.texto)
    assert decisao["gravidade"] == caso.gravidade, (
        f"[{motor}] {caso}: esperado {caso.gravidade}, obtido "
        f"{decisao['gravidade']} — defeito original: {caso.origem}"
    )


@pytest.mark.parametrize("caso", [c for c in CASOS if c.canal], ids=str)
def test_canal_exigido(caso, motor):
    _, decisao = acionar(caso.trilha, caso.texto)
    assert decisao["canal_roteado"] == caso.canal, (
        f"[{motor}] {caso}: esperado {caso.canal}, obtido {decisao['canal_roteado']}"
    )


@pytest.mark.parametrize("caso", CASOS, ids=str)
def test_nunca_rebaixa_em_relacao_a_trilha(caso, motor):
    """O teste-invariante: a gravidade final nunca é menor que a que o roteador
    daria para a trilha sozinha."""
    routing, decisao = acionar(caso.trilha, caso.texto)
    assert RANK[Gravidade(decisao["gravidade"])] >= RANK[Gravidade(routing["gravidade"])]


@pytest.mark.parametrize("caso", CASOS, ids=str)
def test_emergencia_nunca_vira_orientacao(caso, motor):
    """O sintoma mais visível do defeito original: uma trilha de risco imediato
    terminando como orientação."""
    routing, decisao = acionar(caso.trilha, caso.texto)
    if routing["gravidade"] == Gravidade.risco_imediato:
        assert decisao["gravidade"] != Gravidade.orientacao


# ---------------------------------------------------------------------------
# Modo discreto
# ---------------------------------------------------------------------------

TEXTOS_VARIADOS = [
    None,
    "socorro",
    "estou desmaiando",
    "sofri assédio",
    "queria sugerir mais bancos",
    "tem um cara armado",
    "asdfghjkl",
]


@pytest.mark.parametrize("texto", TEXTOS_VARIADOS)
def test_trilha_mulher_e_sempre_discreta(texto, motor):
    """Qualquer texto. Se o agressor está a três metros, uma tela que anuncia
    o canal acionado transforma o socorro em risco."""
    _, decisao = acionar(TipoOcorrencia.mulher, texto)
    assert decisao["instrucao"].tela_neutra is True
    assert decisao["instrucao"].feedback_sonoro is False


@pytest.mark.parametrize("texto", TEXTOS_VARIADOS)
def test_tela_discreta_nao_nomeia_o_canal(texto, motor):
    _, decisao = acionar(TipoOcorrencia.mulher, texto)
    msg = decisao["instrucao"].mensagem_tela.lower()
    for proibida in ["lilás", "lilas", "samu", "polícia", "policia", "180", "denúncia", "denuncia"]:
        assert proibida not in msg, f"a tela discreta mencionou {proibida!r}"


# ---------------------------------------------------------------------------
# Varredura ampla
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("trilha", list(TipoOcorrencia))
@pytest.mark.parametrize(
    "texto",
    [
        # Emergências
        "socorro", "socorroo", "estou desmaiando", "desmaiei", "to passando mal",
        "estou sangrando", "me ameaçaram de morte", "tem fogo no laboratório",
        # Ameaça difusa
        "tem alguém atrás de mim", "estou com medo", "tão me seguindo",
        # Trivialidades
        "queria sugerir mais bancos", "onde fica a secretaria",
        "perdi minha carteirinha", "quero elogiar o atendimento",
        # Ruído
        "asdfghjkl", "🚨", "...", "obrigado",
    ],
)
def test_varredura_nenhuma_combinacao_rebaixa(trilha, texto, motor):
    """4 trilhas × 19 textos × 2 motores = 152 combinações.

    A rede larga: se existe alguma entrada capaz de rebaixar a proteção, é
    aqui que ela aparece.
    """
    routing, decisao = acionar(trilha, texto)
    assert RANK[Gravidade(decisao["gravidade"])] >= RANK[Gravidade(routing["gravidade"])], (
        f"[{motor}] {trilha.value} + {texto!r} rebaixou "
        f"{routing['gravidade']} → {decisao['gravidade']}"
    )


@pytest.mark.parametrize("trilha", list(TipoOcorrencia))
@pytest.mark.parametrize(
    "texto", ["socorro", "estou desmaiando", "me ameaçaram de morte", "estou sangrando"]
)
def test_emergencia_em_qualquer_trilha_termina_imediata(trilha, texto, motor):
    """Texto de emergência inequívoca eleva qualquer trilha ao topo, inclusive
    a Ouvidoria."""
    _, decisao = acionar(trilha, texto)
    assert decisao["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize("trilha", list(TipoOcorrencia))
@pytest.mark.parametrize("texto", TEXTOS_VARIADOS)
def test_canal_final_sempre_existe(trilha, texto, motor):
    """Roteamento para canal fora do catálogo seria um chamado perdido sem
    erro nenhum."""
    from app.config import CANAIS

    _, decisao = acionar(trilha, texto)
    assert decisao["canal_roteado"] in CANAIS
    assert decisao["fallback"] in CANAIS


# ---------------------------------------------------------------------------
# Equivalência entre motores
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("caso", CASOS, ids=str)
def test_desfecho_identico_nos_dois_motores(caso, artefato, tmp_path, monkeypatch):
    """O teste que sustenta o resto: nenhum destes casos depende de o
    classificador estar treinado."""
    def com_caminho(caminho):
        monkeypatch.setattr(config, "CLF_PATH", caminho)
        classificador._cache.update(caminho=None, modelo=None, tentado=False)
        _, d = acionar(caso.trilha, caso.texto)
        return d["gravidade"], d["canal_roteado"]

    com_clf = com_caminho(artefato)
    sem_clf = com_caminho(str(tmp_path / "ausente.joblib"))
    classificador._cache.update(caminho=None, modelo=None, tentado=False)

    assert com_clf == sem_clf, (
        f"{caso}: classificador→{com_clf}, heurística→{sem_clf}"
    )
