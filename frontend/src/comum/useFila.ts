/* Dreno automático e contagem da fila — MVP-058.
 *
 * Duas coisas acontecem aqui: a fila é drenada quando faz sentido tentar, e a
 * contagem fica disponível para o badge do header.
 *
 * **Quando faz sentido tentar** são dois gatilhos, e os dois são necessários:
 *
 * - o evento `online`, que é imediato mas mente (`navigator.onLine` diz que a
 *   interface de rede subiu, não que o backend responde — ver `useOnline`);
 * - um intervalo de 15 s, que é o que cobre o caso em que `online` nunca
 *   dispara porque o wi-fi nunca caiu: o que caiu foi o servidor.
 *
 * Sem o intervalo, um totem conectado a um backend reiniciado ficaria com a
 * fila parada para sempre. Sem o `online`, o dreno esperaria até 15 s depois de
 * a rede voltar — tempo longo quando alguém está esperando socorro.
 */
import { useCallback, useEffect, useState } from "react";
import { enviarEvento, enviarPanico } from "./api";
import { drenar, quantosPendentes } from "./fila";

export function useFila(intervaloSeg: number) {
  const [naFila, setNaFila] = useState(() => quantosPendentes());

  const tentar = useCallback(async () => {
    /* Nada guardado: não toca a rede. Um totem parado não deve gerar tráfego
     * a cada 15 s para descobrir que não tem nada a fazer. */
    if (quantosPendentes() === 0) return;
    await drenar(enviarEvento, enviarPanico);
    setNaFila(quantosPendentes());
  }, []);

  useEffect(() => {
    /* Tenta ao montar: o totem pode ter sido recarregado (ou reiniciado) com a
     * fila cheia e a rede já de volta.
     *
     * O `setNaFila` que vem depois acontece **após** o I/O do dreno, não no
     * corpo síncrono do efeito — é resultado de um sistema externo, que é
     * exatamente para o que efeito existe. */
    // oxlint-disable-next-line set-state-in-effect
    void tentar();

    const timer = window.setInterval(() => void tentar(), intervaloSeg * 1000);
    const aoVoltar = () => void tentar();
    window.addEventListener("online", aoVoltar);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("online", aoVoltar);
    };
  }, [tentar, intervaloSeg]);

  /* `recontar` para quem acabou de enfileirar: o badge precisa aparecer no
   * mesmo quadro da confirmação, sem esperar o próximo ciclo de 15 s. */
  const recontar = useCallback(() => setNaFila(quantosPendentes()), []);

  return { naFila, recontar, drenarAgora: tentar };
}
