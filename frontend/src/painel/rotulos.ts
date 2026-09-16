/* Vocabulário do painel — MVP-060.
 *
 * O operador não lê `risco_imediato` nem `mulher`: ele lê "Imediato" e
 * "Atendimento à Mulher". A tradução fica num lugar só porque ela aparece no
 * cartão, no chip de filtro e no contador, e três cópias divergiriam.
 *
 * Os textos seguem a captura de referência
 * (`../poto-pitch/capturas-de-tela/Tela-Central-painel.png`).
 */
import type { Gravidade, StatusChamado, TipoOcorrencia } from "../comum/tipos";

/** Rótulo curto da gravidade, para o chip do cartão. */
export const ROTULO_GRAVIDADE: Record<Gravidade, string> = {
  risco_imediato: "Imediato",
  risco_potencial: "Potencial",
  orientacao: "Orientação",
};

/** Token de cor da gravidade. Sempre acompanhado do rótulo — **cor nunca é o
 * único sinal**, e 8% dos homens têm alguma deficiência na percepção de
 * vermelho e verde. */
export const COR_GRAVIDADE: Record<Gravidade, string> = {
  risco_imediato: "var(--crit)",
  risco_potencial: "var(--warn)",
  orientacao: "var(--info)",
};

/** Ordem de urgência, para o topo da lista. Espelha `RANK_GRAVIDADE` do
 * backend — é a mesma ordem de proteção, vista pelo lado de quem responde. */
export const PESO_GRAVIDADE: Record<Gravidade, number> = {
  risco_imediato: 3,
  risco_potencial: 2,
  orientacao: 1,
};

/** Título do cartão. É o que o operador lê primeiro. */
export const TITULO_TIPO: Record<TipoOcorrencia, string> = {
  seguranca: "Segurança",
  mulher: "Atendimento à Mulher",
  saude: "Emergência médica",
  ouvidoria: "Ouvidoria",
};

export const ROTULO_STATUS: Record<StatusChamado, string> = {
  recebido: "Recebido",
  roteado: "Roteado",
  notificado: "Notificado",
  alerta_ativo: "Alerta ativo",
  reconhecido: "Reconhecido",
  em_atendimento: "Em atendimento",
  escalonado: "Escalonado",
  encerrado: "Encerrado",
  /* "Falha no envio" e não "falha_notificacao": o operador precisa entender
   * que **ninguém foi avisado** e que ele tem que ligar por fora. */
  falha_notificacao: "Falha no envio",
  cancelado: "Cancelado",
};

/** Estados em que o chamado ainda exige ação da central.
 *
 * Usado para ordenar e para decidir se o SLA corre. `escalonado` entra: o
 * fallback foi acionado, mas ninguém reconheceu ainda.
 */
export const ABERTOS: ReadonlySet<StatusChamado> = new Set<StatusChamado>([
  "recebido",
  "roteado",
  "notificado",
  "alerta_ativo",
  "escalonado",
  "falha_notificacao",
]);
