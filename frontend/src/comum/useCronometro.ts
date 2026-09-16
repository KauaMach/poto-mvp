/* Cronômetro MM:SS desde um instante — MVP-054.
 *
 * Conta a partir de um `Date` e não somando 1 a cada segundo. A diferença
 * aparece quando o navegador **estrangula o timer**: uma aba em segundo plano,
 * ou o Android economizando bateria, faz o `setInterval` disparar menos vezes
 * que o relógio avança. Um contador incremental ficaria atrasado — e este
 * cronômetro diz há quanto tempo alguém está esperando socorro.
 */
import { useEffect, useState } from "react";

export function useCronometro(desde: Date): string {
  const [agora, setAgora] = useState(() => Date.now());

  useEffect(() => {
    const t = window.setInterval(() => setAgora(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);

  const segundos = Math.max(0, Math.floor((agora - desde.getTime()) / 1000));
  const mm = String(Math.floor(segundos / 60)).padStart(2, "0");
  const ss = String(segundos % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}
