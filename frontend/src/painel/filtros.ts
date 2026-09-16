/* Filtros e busca do painel — MVP-065.
 *
 * Tudo acontece **no cliente**, sobre a lista que já está em memória. O
 * `GET /chamados` aceita filtros (MVP-032), mas usá-los aqui seria errado por
 * dois motivos que se somam:
 *
 * - o WebSocket entrega chamados novos sem passar pelo endpoint, e um filtro
 *   de servidor não os incluiria — o painel ficaria mostrando um recorte
 *   congelado no momento da última busca;
 * - filtrar 200 objetos em memória é instantâneo, enquanto uma ida ao servidor
 *   a cada tecla digitada na busca seria uma requisição por caractere.
 *
 * Os filtros do endpoint continuam úteis para quem consome a API de fora.
 */
import type { Chamado, Gravidade } from "../comum/tipos";
import { ABERTOS } from "./rotulos";

/** Recorte por gravidade. `todos` é o estado inicial. */
export type FiltroGravidade = "todos" | Gravidade;

/** Recorte por situação. Não é o `StatusChamado` cru: o operador pensa em
 * "precisa de mim" e "já resolvido", não nos dez estados da máquina. */
export type FiltroSituacao = "todas" | "abertos" | "resolvidos";

export type Filtros = {
  gravidade: FiltroGravidade;
  situacao: FiltroSituacao;
  busca: string;
};

export const FILTROS_VAZIOS: Filtros = {
  gravidade: "todos",
  situacao: "todas",
  busca: "",
};

export function temFiltro(f: Filtros): boolean {
  return (
    f.gravidade !== "todos" || f.situacao !== "todas" || f.busca.trim() !== ""
  );
}

/** Normaliza para busca: sem acento, sem caixa.
 *
 * Sem isto, procurar "seguranca" não acharia "Segurança" — e ninguém digita
 * cedilha com pressa. `NFD` separa o acento do caractere e o range remove as
 * marcas combinantes.
 */
function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/**
 * Aplica os três filtros. Combináveis por construção — cada um estreita o
 * conjunto que o anterior devolveu.
 */
export function aplicarFiltros(
  chamados: Chamado[],
  filtros: Filtros,
): Chamado[] {
  const busca = normalizar(filtros.busca.trim());

  return chamados.filter((c) => {
    if (filtros.gravidade !== "todos" && c.gravidade !== filtros.gravidade) {
      return false;
    }

    if (filtros.situacao !== "todas") {
      const aberto = ABERTOS.has(c.status);
      if (filtros.situacao === "abertos" && !aberto) return false;
      if (filtros.situacao === "resolvidos" && aberto) return false;
    }

    if (!busca) return true;

    /* Protocolo e totem são o que o critério pede. O **relato** entra também:
     * quando alguém liga para a central dizendo "é sobre a moça que falou do
     * estacionamento", procurar por "estacionamento" é o único caminho — o
     * operador não tem o protocolo. */
    return [c.chamado_id, c.totem_id, c.canal_roteado, c.texto_livre ?? ""]
      .map(normalizar)
      .some((campo) => campo.includes(busca));
  });
}

/** Contagem por gravidade para os chips.
 *
 * Calculada sobre a lista **inteira**, não sobre a filtrada: os contadores
 * dizem quanto existe de cada tipo, e é por eles que o operador decide para
 * onde ir. Contar o que já está filtrado mostraria zero em tudo que não é o
 * filtro ativo.
 */
export function contarPorGravidade(
  chamados: Chamado[],
): Record<FiltroGravidade, number> {
  return {
    todos: chamados.length,
    risco_imediato: chamados.filter((c) => c.gravidade === "risco_imediato").length,
    risco_potencial: chamados.filter((c) => c.gravidade === "risco_potencial").length,
    orientacao: chamados.filter((c) => c.gravidade === "orientacao").length,
  };
}
