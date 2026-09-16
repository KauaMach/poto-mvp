/* Ordenação da lista do painel — MVP-060.
 *
 * Em arquivo próprio por dois motivos que se somam: um módulo que exporta
 * componente **e** função quebra o fast refresh do Vite, e importar `ordenar`
 * de dentro de `ListaChamados` arrastaria `CardChamado` e o cliente de API
 * inteiro — o que torna a função impossível de testar fora do navegador,
 * porque `api.ts` lê `import.meta.env`.
 *
 * A regra não é "mais recentes primeiro". É **críticos no topo, e entre iguais
 * os mais recentes**, o que resolve o caso que uma lista cronológica erra: um
 * risco imediato de dois minutos atrás empurrado para baixo por três dúvidas
 * de ouvidoria que chegaram depois.
 */
import type { Chamado } from "../comum/tipos";
import { ABERTOS, PESO_GRAVIDADE } from "./rotulos";

export function ordenar(chamados: Chamado[]): Chamado[] {
  return [...chamados].sort((a, b) => {
    /* 1. Gravidade. */
    const peso = PESO_GRAVIDADE[b.gravidade] - PESO_GRAVIDADE[a.gravidade];
    if (peso !== 0) return peso;

    /* 2. Aberto antes de resolvido: um encerrado no topo ocupa o lugar de algo
     * que ainda espera alguém. */
    const abertoA = ABERTOS.has(a.status) ? 1 : 0;
    const abertoB = ABERTOS.has(b.status) ? 1 : 0;
    if (abertoA !== abertoB) return abertoB - abertoA;

    /* 3. Mais recente primeiro. Comparar string ISO em UTC equivale a comparar
     * instante — é por isso que o `agora_iso()` do backend usa UTC. */
    return b.created_at.localeCompare(a.created_at);
  });
}
