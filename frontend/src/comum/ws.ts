/* Indicador de conexão do WebSocket — MVP-062.
 *
 * O `useEventosWS` (MVP-054) já faz a conexão e a reconexão com espera
 * crescente. O que falta para o painel é a **legenda**: o operador precisa
 * saber se o que está na tela é ao vivo ou uma foto do momento em que ele
 * abriu a página.
 *
 * É a mesma pergunta do `StatusPill` do totem, mas a resposta é diferente e a
 * diferença importa: `navigator.onLine` diz se a rede subiu; isto diz se **os
 * eventos estão chegando**. Num painel onde nada acontece por vinte minutos,
 * "silêncio" e "conexão morta" parecem idênticos na tela e significam o
 * oposto.
 */
import type { EstadoWS } from "./useEventosWS";

export const ROTULO_WS: Record<EstadoWS, string> = {
  aberto: "Tempo real",
  conectando: "Reconectando…",
  fechado: "Sem tempo real",
};

/** Cor do indicador. Sempre acompanhada do rótulo — cor nunca é único sinal. */
export const COR_WS: Record<EstadoWS, string> = {
  aberto: "var(--ok)",
  conectando: "var(--warn)",
  fechado: "var(--rust)",
};
