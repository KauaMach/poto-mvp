/* Prazos e escolha de variante da confirmação — MVP-051 / MVP-052 / MVP-053.
 *
 * Em arquivo próprio para não quebrar o fast refresh do `Confirmacao`, e de
 * quebra porque o `verificar-prazos.mjs` lê a tabela daqui: um módulo que
 * também exporta componente arrastaria React para um script de verificação.
 */
import type { VarianteConfirm } from "../../componentes/Confirm";
import type { EventoOut } from "../../comum/tipos";

/* Prazos de retorno, em milissegundos (MVP-052).
 *
 * Discreto é o mais curto: a tela não deve ficar aberta mais do que o
 * necessário se alguém puder estar olhando por cima do ombro. Crítico é o mais
 * longo porque o protocolo precisa ser lido e anotado, possivelmente por
 * alguém com a mão tremendo.
 */
export const RETORNO_MS = {
  discreto: 5000,
  critico: 12000,
  padrao: 9000,
} as const;

/** Qual das três variantes do `<Confirm>` usar, a partir do que o backend disse. */
export function varianteDe(resultado: EventoOut): VarianteConfirm {
  /* Discreto **antes** de crítico: a trilha mulher pode chegar com gravidade
   * alta, e a tela neutra tem que vencer. Inverter esta ordem transformaria um
   * pedido discreto numa tela vermelha que anuncia emergência. */
  if (resultado.instrucao_totem.tela_neutra) return "neutral";
  if (resultado.gravidade === "risco_imediato") return "critico";
  return "padrao";
}

/** Quanto tempo a confirmação fica na tela, pela variante. Exportada para que
 * a verificação de prazos não duplique a tabela. */
export function prazoDe(variante: VarianteConfirm): number {
  if (variante === "neutral") return RETORNO_MS.discreto;
  if (variante === "critico") return RETORNO_MS.critico;
  return RETORNO_MS.padrao;
}
