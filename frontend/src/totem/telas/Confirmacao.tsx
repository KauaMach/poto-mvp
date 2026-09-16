/* Tela de confirmação do totem — MVP-051 / MVP-052 / MVP-053.
 *
 * Envolve o `<Confirm>` do design system com o que é específico do totem: o
 * som e o **retorno automático ao repouso**.
 *
 * Tudo que decide a aparência vem do `instrucao_totem` do backend. O cliente
 * não infere discrição, não escolhe mensagem e não decide se toca som — se
 * fizesse, a garantia de modo discreto passaria a depender de o frontend
 * lembrar de aplicá-la, e é exatamente esse tipo de dependência que a
 * MVP-030 tirou do cliente.
 */
import { useEffect, useRef } from "react";
import { Confirm, type VarianteConfirm } from "../../componentes/Confirm";
import { beep } from "../../comum/beep";
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

type Props = {
  resultado: EventoOut;
  onVoltar: () => void;
  /** Evento ficou na fila offline (MVP-057): não houve resposta do servidor. */
  offline?: boolean;
};

/** Qual das três variantes do `<Confirm>` usar, a partir do que o backend disse. */
export function varianteDe(resultado: EventoOut): VarianteConfirm {
  /* Discreto **antes** de crítico: a trilha mulher pode chegar com gravidade
   * alta, e a tela neutra tem que vencer. Inverter esta ordem transformaria um
   * pedido discreto numa tela vermelha que anuncia emergência. */
  if (resultado.instrucao_totem.tela_neutra) return "neutral";
  if (resultado.gravidade === "risco_imediato") return "critico";
  return "padrao";
}

function prazoDe(variante: VarianteConfirm): number {
  if (variante === "neutral") return RETORNO_MS.discreto;
  if (variante === "critico") return RETORNO_MS.critico;
  return RETORNO_MS.padrao;
}

export function Confirmacao({ resultado, onVoltar, offline = false }: Props) {
  const variante = varianteDe(resultado);
  /* `ref` para o callback: sem isto, um `onVoltar` recriado pelo pai reiniciaria
   * o timer a cada render e o totem nunca voltaria ao repouso. */
  const voltar = useRef(onVoltar);
  voltar.current = onVoltar;

  /* O som é decisão do backend. Na trilha discreta `feedback_sonoro` vem
   * `false`, e é o que garante que a tela neutra seja **silenciosa** — um beep
   * numa biblioteca é tão revelador quanto um protocolo na tela. */
  const soou = useRef(false);
  useEffect(() => {
    if (soou.current) return;
    soou.current = true;
    if (resultado.instrucao_totem.feedback_sonoro) beep();
  }, [resultado]);

  useEffect(() => {
    const timer = window.setTimeout(() => voltar.current(), prazoDe(variante));
    /* Limpeza obrigatória: sem ela, acionar duas vezes em sequência deixaria
     * dois timers vivos e o segundo devolveria o totem ao início no meio da
     * confirmação seguinte. */
    return () => window.clearTimeout(timer);
  }, [variante]);

  return (
    <Confirm
      variante={variante}
      /* A mensagem é a do backend, não uma tabela no cliente. */
      mensagem={resultado.instrucao_totem.mensagem_tela}
      protocolo={resultado.chamado_id}
      offline={offline}
    />
  );
}
