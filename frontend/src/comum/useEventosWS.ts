/* Assinatura do WebSocket — MVP-054, escopo em COR-002.
 *
 * O totem usa isto para acompanhar **o próprio chamado** durante um alerta
 * ativo: é o que faz a tela sair de "Aguardando central" para "Central
 * recebeu" sem ninguém recarregar nada.
 *
 * **Dois canais, e a diferença é de privacidade, não de conveniência.** O
 * painel assina `/ws` e recebe todos os eventos, completos — ele precisa, e
 * está atrás do token. O totem assina `/ws/chamado/{id}` e recebe **só** o
 * chamado dele, **só** com `chamado_id` e `status`.
 *
 * Antes da COR-002 o totem assinava `/ws` também, e o servidor entregava tudo
 * a todos: um aparelho de corredor recebia o `texto_livre` — o relato — de
 * cada pessoa que acionasse o totem. O que impedia de aparecer na tela era o
 * filtro daqui, no cliente, depois de o dado já ter chegado ao aparelho.
 *
 * Reconecta com espera crescente. Um totem em alerta ativo com a conexão caída
 * não pode ficar tentando a cada 100 ms — isso aquece o aparelho e enche o log
 * do servidor justamente durante uma emergência. Mas também não pode desistir:
 * o intervalo cresce até um teto e para ali.
 */
import { useEffect, useRef, useState } from "react";
import type { EventoWS } from "./tipos";

const ESPERA_INICIAL_MS = 500;
const ESPERA_MAXIMA_MS = 10000;

export type EstadoWS = "conectando" | "aberto" | "fechado";

export function useEventosWS(
  ao: (evento: EventoWS) => void,
  ativo = true,
  /** Chamado a acompanhar. Omitido = painel (todos os eventos, completos). */
  chamadoId?: string,
): EstadoWS {
  /* `estadoSocket` guarda só o que vem do socket. O caso `!ativo` é
   * **derivado** no retorno, não armazenado: guardá-lo exigiria um `setState`
   * síncrono no corpo do efeito, que provoca um render extra e pode sair de
   * sincronia com a prop. Estado derivável não deve ser estado. */
  const [estadoSocket, setEstadoSocket] = useState<EstadoWS>("conectando");
  /* O callback num `ref`: sem isto, um handler recriado a cada render
   * reabriria o socket em laço. */
  const tratar = useRef(ao);
  useEffect(() => {
    tratar.current = ao;
  }, [ao]);

  useEffect(() => {
    if (!ativo) return;

    let socket: WebSocket | null = null;
    let religar: number | null = null;
    let espera = ESPERA_INICIAL_MS;
    let vivo = true;

    const conectar = () => {
      if (!vivo) return;
      /* `wss` quando a página é https. Fixar `ws` quebraria o painel servido
       * por HTTPS, e fixar `wss` quebraria o totem na rede local, que é HTTP. */
      const esquema = location.protocol === "https:" ? "wss:" : "ws:";
      /* Com `chamadoId`, o canal restrito da COR-002. O `encodeURIComponent`
       * porque o protocolo entra no caminho da URL. */
      const caminho = chamadoId
        ? `/api/v1/ws/chamado/${encodeURIComponent(chamadoId)}`
        : "/api/v1/ws";
      socket = new WebSocket(`${esquema}//${location.host}${caminho}`);
      setEstadoSocket("conectando");

      socket.onopen = () => {
        espera = ESPERA_INICIAL_MS; // reconexão bem-sucedida zera a espera
        setEstadoSocket("aberto");
      };

      socket.onmessage = (e) => {
        try {
          tratar.current(JSON.parse(e.data) as EventoWS);
        } catch {
          /* Mensagem malformada não derruba a conexão: perder um evento é
           * melhor que perder o canal. */
        }
      };

      socket.onclose = () => {
        setEstadoSocket("fechado");
        if (!vivo) return;
        religar = window.setTimeout(conectar, espera);
        espera = Math.min(espera * 2, ESPERA_MAXIMA_MS);
      };

      /* `onerror` não precisa de tratamento próprio: o navegador sempre dispara
       * `onclose` depois dele, e é lá que a reconexão acontece. Tratar os dois
       * agendaria duas reconexões. */
    };

    conectar();

    return () => {
      vivo = false;
      if (religar !== null) window.clearTimeout(religar);
      /* Remove o handler antes de fechar: sem isto o `onclose` do próprio
       * fechamento agendaria uma reconexão depois de o componente sair. */
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
    /* `chamadoId` na dependência: sem ele, o socket continuaria no canal
     * antigo se o chamado mudasse — e o totem acompanharia o alerta errado. */
  }, [ativo, chamadoId]);

  /* Derivado: sem socket ativo não há conexão a reportar. */
  return ativo ? estadoSocket : "fechado";
}
