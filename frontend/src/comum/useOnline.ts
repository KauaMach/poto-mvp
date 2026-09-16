/* Estado de conectividade — MVP-044.
 *
 * `navigator.onLine` responde a pergunta errada: ele diz se a **interface de
 * rede** está ativa, não se o backend responde. Num totem ligado no wi-fi da
 * universidade com o roteador fora do ar, ele diz `true`.
 *
 * Para o MVP isso é aceitável, e a razão é a arquitetura: o sinal verdadeiro de
 * "chegou ou não" é o resultado do POST, e quem trata a falha é a fila offline
 * (MVP-057), que enfileira o que não foi. O indicador aqui é uma **dica**, não
 * uma garantia — e o contador de fila, que vem do resultado real dos envios, é
 * o que informa de fato.
 */
import { useEffect, useState } from "react";

export function useOnline(): boolean {
  /* Em SSR e em navegador sem a API, assume online: um falso "offline" faria a
   * tela sugerir um problema que pode não existir. */
  const [online, setOnline] = useState(
    () => typeof navigator === "undefined" || navigator.onLine !== false,
  );

  useEffect(() => {
    const mudou = () => setOnline(navigator.onLine !== false);
    window.addEventListener("online", mudou);
    window.addEventListener("offline", mudou);
    /* Relê no mount: entre o `useState` inicial e o efeito o estado pode ter
     * mudado, e nesse caso nenhum dos dois eventos teria disparado. */
    mudou();
    return () => {
      window.removeEventListener("online", mudou);
      window.removeEventListener("offline", mudou);
    };
  }, []);

  return online;
}
