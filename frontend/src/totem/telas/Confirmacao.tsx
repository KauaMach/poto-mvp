/* Tela de confirmação do totem — MVP-051 / MVP-052 / MVP-053.
 *
 * Envolve o `<Confirm>` do design system com o que é específico do totem: o
 * som e o **retorno automático ao repouso**.
 *
 * Só as trilhas passam por aqui. O pânico tem tela própria — `AlertaAtivo`
 * (MVP-054), que é persistente e não tem timer nenhum. Esta versão chegou a ter
 * uma prop `persistente` para cobrir o pânico provisoriamente (MVP-052);
 * removida quando a tela real existiu, para não ficar código sem consumidor.
 *
 * Tudo que decide a aparência vem do `instrucao_totem` do backend. O cliente
 * não infere discrição, não escolhe mensagem e não decide se toca som — se
 * fizesse, a garantia de modo discreto passaria a depender de o frontend
 * lembrar de aplicá-la, e é exatamente esse tipo de dependência que a
 * MVP-030 tirou do cliente.
 */
import { useEffect, useRef } from "react";
import { Confirm } from "../../componentes/Confirm";
import { beep } from "../../comum/beep";
import type { EventoOut } from "../../comum/tipos";
import { prazoDe, varianteDe } from "./retorno";

type Props = {
  resultado: EventoOut;
  onVoltar: () => void;
  /** Evento ficou na fila offline (MVP-057): não houve resposta do servidor. */
  offline?: boolean;
};

export function Confirmacao({ resultado, onVoltar, offline = false }: Props) {
  const variante = varianteDe(resultado);
  /* `ref` para o callback: sem isto, um `onVoltar` recriado pelo pai reiniciaria
   * o timer a cada render e o totem nunca voltaria ao repouso. */
  const voltar = useRef(onVoltar);
  useEffect(() => {
    voltar.current = onVoltar;
  }, [onVoltar]);

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
