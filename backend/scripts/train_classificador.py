#!/usr/bin/env python3
"""Treina o classificador de triagem e mede o resultado no held-out.

    make train-clf

Treina em `triagem_dataset.json` e avalia em `bench_dataset.json` — conjuntos
separados, sem sobreposição (verificada por `tests/test_datasets.py`). O número
reportado é de frases que o modelo nunca viu.

Sai com código 1 se o resultado ficar abaixo da linha de base. A intenção é que
uma regressão pare o `make setup` em vez de passar despercebida: um
classificador ruim não dá erro em produção, só manda gente para o canal errado.
Use `--permitir-regressao` para experimentar sem o portão.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent))

# Linha de base. Não são metas aspiracionais: são o piso abaixo do qual a
# triagem deixa de ser confiável o bastante para governar o encaminhamento.
MIN_ACURACIA_TIPO = 0.83
MIN_ACURACIA_GRAVIDADE = 0.85
MAX_LATENCIA_MS = 10.0

# Ordem de proteção — usada para separar erro seguro de erro perigoso.
RANK = {"orientacao": 1, "risco_potencial": 2, "risco_imediato": 3}


def _carregar(nome: str) -> list[dict]:
    return json.loads((SCRIPTS / nome).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--permitir-regressao",
        action="store_true",
        help="não falha quando o resultado fica abaixo da linha de base",
    )
    ap.add_argument("--saida", help="caminho do artefato (default: POTO_CLF_PATH)")
    args = ap.parse_args()

    from app import config
    from app.triagem import classificador as clf

    # `--saida` precisa redirecionar a LEITURA também, não só a escrita: sem
    # isto o script treinaria num caminho e avaliaria o artefato antigo do
    # caminho padrão, reportando números que não correspondem ao modelo recém
    # treinado.
    if args.saida:
        config.CLF_PATH = args.saida

    treino = _carregar("triagem_dataset.json")
    bench = _carregar("bench_dataset.json")

    print(f"\n  Treinando em {len(treino)} exemplos…")
    inicio = time.perf_counter()
    resumo = clf.treinar(treino, caminho=args.saida)
    duracao = time.perf_counter() - inicio
    print(f"  {duracao:.2f} s · {resumo['tamanho_kb']} KB · {resumo['caminho']}")

    # Aquece antes de cronometrar: a primeira chamada carrega o artefato do
    # disco e distorceria a média (foi o que aconteceu numa medição anterior,
    # onde a média saiu maior que o p95).
    clf.classificar("aquecendo o modelo")

    acertos_tipo = acertos_gravidade = 0
    latencias: list[float] = []
    erros_tipo: list[tuple[str, str, str]] = []
    subestimou: list[tuple[str, str, str]] = []
    superestimou: list[tuple[str, str, str]] = []

    for item in bench:
        t0 = time.perf_counter()
        previsto = clf.classificar(item["texto"])
        latencias.append((time.perf_counter() - t0) * 1000)

        if previsto["tipo"] == item["tipo"]:
            acertos_tipo += 1
        else:
            erros_tipo.append((item["texto"], item["tipo"], previsto["tipo"]))

        esperada, obtida = item["gravidade"], previsto["gravidade"]
        if obtida == esperada:
            acertos_gravidade += 1
        elif RANK[obtida] < RANK[esperada]:
            subestimou.append((item["texto"], esperada, obtida))
        else:
            superestimou.append((item["texto"], esperada, obtida))

    n = len(bench)
    acuracia_tipo = acertos_tipo / n
    acuracia_gravidade = acertos_gravidade / n
    latencias.sort()
    media = sum(latencias) / n
    p95 = latencias[int(n * 0.95) - 1]

    print(f"\n  Held-out: {n} exemplos nunca vistos no treino\n")
    print(f"    acurácia tipo       {acuracia_tipo * 100:5.1f}%   ({acertos_tipo}/{n})")
    print(
        f"    acurácia gravidade  {acuracia_gravidade * 100:5.1f}%   "
        f"({acertos_gravidade}/{n})"
    )
    print(f"    latência média      {media:5.2f} ms")
    print(f"    latência p95        {p95:5.2f} ms")

    # A métrica que mais importa. Acurácia trata todo erro como igual; aqui não
    # são: superestimar custa uma notificação a mais, subestimar manda alguém em
    # risco imediato para um canal de orientação.
    print("\n  Direção do erro de gravidade:\n")
    print(f"    subestimou    {len(subestimou):2}   ← perigoso: protege menos que o esperado")
    print(f"    superestimou  {len(superestimou):2}   ← seguro: protege mais que o esperado")

    if subestimou:
        print("\n    Casos subestimados:")
        for texto, esperada, obtida in subestimou:
            print(f"      {texto[:52]!r}  {esperada} → {obtida}")

    if erros_tipo:
        print(f"\n  Erros de tipo ({len(erros_tipo)}):")
        for texto, esperado, obtido in erros_tipo:
            print(f"    {texto[:52]!r}  {esperado} → {obtido}")

    # --- Portão ---
    falhas = []
    if acuracia_tipo < MIN_ACURACIA_TIPO:
        falhas.append(
            f"acurácia de tipo {acuracia_tipo * 100:.1f}% < {MIN_ACURACIA_TIPO * 100:.0f}%"
        )
    if acuracia_gravidade < MIN_ACURACIA_GRAVIDADE:
        falhas.append(
            f"acurácia de gravidade {acuracia_gravidade * 100:.1f}% "
            f"< {MIN_ACURACIA_GRAVIDADE * 100:.0f}%"
        )
    if media > MAX_LATENCIA_MS:
        falhas.append(f"latência média {media:.2f} ms > {MAX_LATENCIA_MS:.0f} ms")

    if falhas:
        print("\n  ABAIXO DA LINHA DE BASE:")
        for f in falhas:
            print(f"    · {f}")
        if args.permitir_regressao:
            print("\n  (--permitir-regressao: seguindo mesmo assim)\n")
            return 0
        print("\n  O artefato foi salvo, mas não deveria ir para produção assim.")
        print("  Para ignorar: make train-clf ARGS=--permitir-regressao\n")
        return 1

    print("\n  Dentro da linha de base.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
