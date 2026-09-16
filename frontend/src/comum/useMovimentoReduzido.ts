/* Preferência de movimento reduzido — MVP-046.
 *
 * Não é preferência estética: movimento pode desencadear náusea e enxaqueca em
 * quem tem desordem vestibular, e num totem de emergência a pessoa já pode
 * estar em sofrimento.
 *
 * Existe como hook, e não só como `@media` no CSS, porque o `<Panic>` precisa
 * **decidir diferente** e não apenas animar diferente: ele troca o
 * preenchimento contínuo do anel por degraus discretos. Desligar a animação
 * não serviria — sem nenhuma realimentação, quem segura por 400 ms conclui que
 * o botão está quebrado e solta.
 */
import { useEffect, useState } from "react";

const CONSULTA = "(prefers-reduced-motion: reduce)";

export function useMovimentoReduzido(): boolean {
  const [reduzido, setReduzido] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia(CONSULTA).matches,
  );

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(CONSULTA);
    const mudou = (e: MediaQueryListEvent) => setReduzido(e.matches);
    mq.addEventListener("change", mudou);
    setReduzido(mq.matches);
    return () => mq.removeEventListener("change", mudou);
  }, []);

  return reduzido;
}
