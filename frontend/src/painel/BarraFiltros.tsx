/* Barra de filtros e busca — MVP-065. */
import type { Chamado } from "../comum/tipos";
import { COR_GRAVIDADE, ROTULO_GRAVIDADE } from "./rotulos";
import {
  contarPorGravidade,
  temFiltro,
  type FiltroGravidade,
  type FiltroSituacao,
  type Filtros,
} from "./filtros";

const GRAVIDADES: FiltroGravidade[] = [
  "todos",
  "risco_imediato",
  "risco_potencial",
  "orientacao",
];

const SITUACOES: { valor: FiltroSituacao; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas as situações" },
  { valor: "abertos", rotulo: "Precisam de mim" },
  { valor: "resolvidos", rotulo: "Já resolvidos" },
];

type Props = {
  chamados: Chamado[];
  filtros: Filtros;
  onMudar: (filtros: Filtros) => void;
  onLimpar: () => void;
};

export function BarraFiltros({ chamados, filtros, onMudar, onLimpar }: Props) {
  const contagem = contarPorGravidade(chamados);

  return (
    <div className="poto-filtros">
      <label className="poto-busca">
        <span className="visually-hidden">Buscar chamado</span>
        <input
          type="search"
          value={filtros.busca}
          placeholder="Buscar protocolo, totem ou relato…"
          onChange={(e) => onMudar({ ...filtros, busca: e.target.value })}
        />
      </label>

      {/* `role="group"` com nome: o leitor de tela anuncia o conjunto antes do
          primeiro chip, o que dá o contexto que o arranjo visual dá. */}
      <div className="poto-chips" role="group" aria-label="Filtrar por gravidade">
        {GRAVIDADES.map((g) => {
          const ativo = filtros.gravidade === g;
          return (
            <button
              key={g}
              type="button"
              className={ativo ? "poto-chip poto-chip-ativo" : "poto-chip"}
              /* `aria-pressed` e não `aria-selected`: são botões alternáveis,
               * não itens de uma lista de seleção. Sem isto o leitor de tela
               * não anuncia qual filtro está aplicado. */
              aria-pressed={ativo}
              onClick={() => onMudar({ ...filtros, gravidade: g })}
            >
              <span
                aria-hidden="true"
                className="poto-ponto"
                style={{
                  background: g === "todos" ? "var(--ink)" : COR_GRAVIDADE[g],
                }}
              />
              {g === "todos" ? "Todos" : ROTULO_GRAVIDADE[g]}
              <span className="poto-chip-contador tabular">{contagem[g]}</span>
            </button>
          );
        })}
      </div>

      <label className="poto-seletor">
        <span className="visually-hidden">Filtrar por situação</span>
        <select
          value={filtros.situacao}
          onChange={(e) =>
            onMudar({ ...filtros, situacao: e.target.value as FiltroSituacao })
          }
        >
          {SITUACOES.map((s) => (
            <option key={s.valor} value={s.valor}>
              {s.rotulo}
            </option>
          ))}
        </select>
      </label>

      {/* Só aparece quando há o que limpar: um botão sempre presente e sempre
          inerte ensina o operador a ignorá-lo. */}
      {temFiltro(filtros) && (
        <button type="button" className="poto-limpar" onClick={onLimpar}>
          Limpar filtros
        </button>
      )}
    </div>
  );
}
