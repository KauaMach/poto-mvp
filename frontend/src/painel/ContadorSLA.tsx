/* Contador de SLA — o prazo correndo na tela (MVP-064).
 *
 * É o **fail-safe visível**. O worker do backend escalona sozinho quando o
 * prazo estoura (MVP-038), mas se o operador só descobre isso depois, o
 * escalonamento automático deixa de ser rede de segurança e passa a ser o
 * caminho normal — e o fallback é sempre uma escolha pior que a resposta de
 * quem estava de plantão.
 *
 * **Os prazos vêm de `GET /config`.** Escrevê-los aqui criaria exatamente a
 * duplicação que o `/config` existe para matar (MVP-037): mudar 120 para 90 no
 * backend deixaria a tela mostrando o prazo antigo, e o cartão diria "faltam
 * 30 s" para um chamado que o worker já escalonou.
 */
import { useEffect, useState } from "react";
import type { Chamado } from "../comum/tipos";

type Props = {
  chamado: Chamado;
  /** Prazo da gravidade, em segundos. `orientacao` nunca chega aqui. */
  segundos: number;
};

export function ContadorSLA({ chamado, segundos }: Props) {
  const [agora, setAgora] = useState(() => Date.now());

  useEffect(() => {
    /* Relê o relógio em vez de decrementar um contador: com a aba em segundo
     * plano o navegador estrangula o `setInterval`, e um decremento ficaria
     * atrasado — mostrando tempo que já passou. */
    const t = window.setInterval(() => setAgora(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);

  /* Conta a partir de `created_at` — o relógio do **servidor**, o mesmo que o
   * worker de SLA usa (MVP-038). Usar `timestamp_local` faria a tela e o worker
   * discordarem sobre quando o prazo venceu, e a discordância apareceria como
   * "SLA expirado" num cartão que o backend ainda considera no prazo. */
  const restante = Math.floor(
    (Date.parse(chamado.created_at) + segundos * 1000 - agora) / 1000,
  );

  if (restante <= 0) {
    return (
      <p className="poto-sla-expirado" role="status">
        SLA expirado — escalonado para o canal de fallback
      </p>
    );
  }

  const mm = Math.floor(restante / 60);
  const ss = String(restante % 60).padStart(2, "0");

  return (
    <p className="poto-sla">
      Responder em{" "}
      {/* `tabular` porque o número muda a cada segundo: sem largura fixa de
        * dígito o texto ao lado "pula" e chama atenção sem informar. */}
      <span className="tabular">{`${mm}:${ss}`}</span>
    </p>
  );
}
