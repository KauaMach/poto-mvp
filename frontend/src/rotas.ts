/* Decisão de rota — MEL-003.
 *
 * Em arquivo próprio, e não dentro do `App.tsx`, por duas razões:
 *
 * 1. Um módulo que exporta componente **e** função perde o fast refresh do
 *    Vite. É o mesmo motivo que separou `retorno.ts` e `statusAlerta.ts`.
 * 2. A função recebe o caminho como **argumento**, em vez de ler
 *    `window.location` por dentro. Isso a torna verificável sem navegador —
 *    `scripts/verificar-rotas.mjs` a roda direto no Node.
 *
 * **Antes da MEL-003, `/totem` funcionava por acidente.** O `rotaAtual` só
 * checava `/painel` e `/galeria`, e devolvia `"totem"` para todo o resto. A
 * rota do totem não era uma rota: era o que sobrava. Agora ela é explícita, no
 * mesmo padrão de `/painel`, e a raiz **redireciona** para ela (o redirect vive
 * no backend, em `app/main.py`) — assim existe uma URL canônica só para o
 * totem, em vez de duas que fazem a mesma coisa.
 */

export type Rota = "totem" | "painel" | "galeria";

/** Caminho canônico do totem. O backend redireciona `/` para cá. */
export const CAMINHO_TOTEM = "/totem";

/**
 * Qual tela o caminho pede.
 *
 * @param caminho `window.location.pathname` — passado, não lido daqui.
 * @param dev     se a galeria existe (`import.meta.env.DEV` no chamador).
 */
export function rotaAtual(caminho: string, dev: boolean): Rota {
  // Normaliza a barra final: `/painel` e `/painel/` são a mesma rota.
  const limpo = caminho.replace(/\/+$/, "");

  if (limpo === "/painel") return "painel";
  if (limpo === CAMINHO_TOTEM) return "totem";

  /* `/galeria` só existe em desenvolvimento. Quem chama passa
   * `import.meta.env.DEV`, que é constante estática — então o bundler elimina
   * o ramo **e o módulo da galeria** do build de produção (MVP-047). O totem
   * não alcança essa tela nem digitando a URL. */
  if (limpo === "/galeria" && dev) return "galeria";

  /* Qualquer outro caminho cai no totem, e isso **continua sendo de
   * propósito**: num aparelho de corredor, uma URL digitada errado deve
   * terminar na tela de pedir ajuda, não num 404. A diferença que a MEL-003 faz
   * é que agora isso é um *fallback deliberado* — `/totem` tem sua própria
   * linha acima — e não a única forma de chegar ao totem. */
  return "totem";
}
