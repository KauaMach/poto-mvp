/* As abas do painel — MEL-009.
 *
 * O blueprint de referência (`../poto/referencia/screen-painel.png`) tem uma
 * barra lateral com Dashboard, Incidents, Totems e Analytics. O MVP tinha uma
 * lista e nada mais.
 *
 * **As quatro são reais, e nenhuma é placeholder.** Foi a decisão que guiou
 * este arquivo: eu poderia ter posto as abas com uma tela de "em breve" em três
 * delas — como fiz, com razão, na sub-ação de voz, que depende de STT que não
 * existe. Aqui não precisa: **os dados já estão na tela**. `GET /chamados`
 * devolve `totem_id`, `tipo_ocorrencia`, `gravidade`, `status`, `created_at` e
 * `acked_at` de cada chamado — e disso saem totens e números sem uma linha de
 * backend novo.
 *
 * Aba com "em breve" num projeto que vai ser apresentado é pior que aba
 * nenhuma: ela promete e não entrega, e quem assiste percebe.
 */
import type { Chamado, Gravidade, StatusChamado, TipoOcorrencia } from "../comum/tipos";
import { ABERTOS } from "./rotulos";

export type Aba = "agora" | "historico" | "totens" | "analises";

export const ABAS: { id: Aba; rotulo: string; descricao: string }[] = [
  {
    id: "agora",
    rotulo: "Agora",
    descricao: "Chamados que ainda esperam alguém",
  },
  {
    id: "historico",
    rotulo: "Histórico",
    descricao: "Chamados encerrados e cancelados",
  },
  { id: "totens", rotulo: "Totens", descricao: "Atividade por aparelho" },
  { id: "analises", rotulo: "Análises", descricao: "Distribuição e tempos" },
];

/** Um totem, como a aba "Totens" o resume. */
export type ResumoTotem = {
  totem_id: string;
  total: number;
  abertos: number;
  ultimo: string;
  porGravidade: Record<Gravidade, number>;
};

/**
 * Agrupa os chamados por totem.
 *
 * Deriva de `totem_id`, que **já está em todo registro** desde a MVP-015 — é a
 * mesma coluna que o `ARCHITECTURE.md §9` aponta como o que torna "multi-totem"
 * uma extensão e não um redesenho.
 */
export function resumirTotens(chamados: Chamado[]): ResumoTotem[] {
  const mapa = new Map<string, ResumoTotem>();

  for (const c of chamados) {
    const atual =
      mapa.get(c.totem_id) ??
      {
        totem_id: c.totem_id,
        total: 0,
        abertos: 0,
        ultimo: c.created_at,
        porGravidade: { risco_imediato: 0, risco_potencial: 0, orientacao: 0 },
      };

    atual.total += 1;
    if (ABERTOS.has(c.status)) atual.abertos += 1;
    atual.porGravidade[c.gravidade] += 1;
    /* Comparação de string em ISO-8601 com o mesmo fuso **é** ordem
     * cronológica — e o backend grava tudo em UTC (`db.agora_iso()`). Evita
     * construir dois `Date` por comparação. */
    if (c.created_at > atual.ultimo) atual.ultimo = c.created_at;

    mapa.set(c.totem_id, atual);
  }

  /* Mais chamados abertos primeiro: a aba existe para mostrar **onde está
   * acontecendo**, não para listar em ordem alfabética. Empate cai para o
   * total, e depois para o mais recente. */
  return [...mapa.values()].sort(
    (a, b) =>
      b.abertos - a.abertos ||
      b.total - a.total ||
      b.ultimo.localeCompare(a.ultimo),
  );
}

export type Analises = {
  total: number;
  abertos: number;
  porTipo: Record<TipoOcorrencia, number>;
  porGravidade: Record<Gravidade, number>;
  porStatus: Partial<Record<StatusChamado, number>>;
  /** Mediana do tempo até o reconhecimento, em segundos. `null` se nenhum. */
  medianaAck: number | null;
  reconhecidos: number;
  /** Quantos passaram do prazo sem reconhecimento (só onde há prazo). */
  semAckNoPrazo: number;
};

/**
 * Números do conjunto que está na tela.
 *
 * **Mediana e não média**, para o tempo de reconhecimento: um único chamado
 * esquecido a noite inteira puxa a média para horas e faz o número mentir sobre
 * a operação. A mediana descreve o caso típico, que é o que se quer saber.
 */
export function analisar(
  chamados: Chamado[],
  sla?: Record<string, number | null>,
): Analises {
  const porTipo: Record<TipoOcorrencia, number> = {
    seguranca: 0,
    mulher: 0,
    saude: 0,
    ouvidoria: 0,
  };
  const porGravidade: Record<Gravidade, number> = {
    risco_imediato: 0,
    risco_potencial: 0,
    orientacao: 0,
  };
  const porStatus: Partial<Record<StatusChamado, number>> = {};
  const esperas: number[] = [];
  let abertos = 0;
  let semAckNoPrazo = 0;

  for (const c of chamados) {
    porTipo[c.tipo_ocorrencia] += 1;
    porGravidade[c.gravidade] += 1;
    porStatus[c.status] = (porStatus[c.status] ?? 0) + 1;
    if (ABERTOS.has(c.status)) abertos += 1;

    if (c.acked_at) {
      esperas.push(
        (Date.parse(c.acked_at) - Date.parse(c.created_at)) / 1000,
      );
    } else {
      const prazo = sla?.[c.gravidade];
      /* `orientacao` traz `null` no `/config` — não escalona, então não há
       * prazo a estourar. Contá-lo aqui inventaria um atraso que não existe. */
      if (
        prazo != null &&
        ABERTOS.has(c.status) &&
        (Date.now() - Date.parse(c.created_at)) / 1000 > prazo
      ) {
        semAckNoPrazo += 1;
      }
    }
  }

  esperas.sort((a, b) => a - b);
  const medianaAck = esperas.length
    ? esperas[Math.floor(esperas.length / 2)]
    : null;

  return {
    total: chamados.length,
    abertos,
    porTipo,
    porGravidade,
    porStatus,
    medianaAck,
    reconhecidos: esperas.length,
    semAckNoPrazo,
  };
}
