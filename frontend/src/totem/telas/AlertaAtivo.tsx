/* Tela de alerta ativo — MVP-054.
 *
 * O estado persistente do sistema. Não sai sozinha: `alerta_ativo` só muda por
 * ação humana (MVP-031), e a tela reflete isso — não há timer, só o botão
 * "Voltar ao início".
 *
 * Três coisas acontecem aqui ao mesmo tempo, e cada uma responde a uma pergunta
 * de quem está esperando:
 *
 *   protocolo     "o pedido existe?"          — grande, tabular, para ler em voz alta
 *   cronômetro    "há quanto tempo?"          — MM:SS desde o acionamento
 *   status ao vivo "alguém já viu?"           — muda por WebSocket, sem recarregar
 *
 * O status ao vivo é o que diferencia esta tela de um cartaz. Sem ele a pessoa
 * não tem como saber se o pedido chegou, e a única coisa que resta a fazer é
 * tocar de novo.
 */
import { useCallback, useState } from "react";
import { escalonarChamado } from "../../comum/api";
import type { CanalOpcao, EventoWS, PanicoOut, StatusChamado } from "../../comum/tipos";
import { useCronometro } from "../../comum/useCronometro";
import { useEventosWS } from "../../comum/useEventosWS";
import { Sym } from "../../componentes/Sym";
import { textoDoStatus } from "./statusAlerta";


type Props = {
  alerta: PanicoOut;
  /** Instante do acionamento, para o cronômetro. */
  desde: Date;
  /** O alerta está na fila: não houve resposta do servidor. */
  offline?: boolean;
  onVoltar: () => void;
};

export function AlertaAtivo({ alerta, desde, offline = false, onVoltar }: Props) {
  const [status, setStatus] = useState<StatusChamado>(alerta.status);
  const [acionados, setAcionados] = useState<Record<string, boolean>>({});
  const tempo = useCronometro(desde);

  const aoEvento = useCallback(
    (evento: EventoWS) => {
      /* Só interessa **este** chamado. Um outro totem acionando ao mesmo tempo
       * não pode mudar o status desta tela. */
      if (evento.evento !== "atualizado" && evento.evento !== "novo_chamado") return;
      if (evento.dados.chamado_id !== alerta.chamado_id) return;
      setStatus(evento.dados.status);
    },
    [alerta.chamado_id],
  );

  /* Offline não há WebSocket para assinar, e tentar reconectar em laço numa
   * tela de pânico só aquece o aparelho. */
  useEventosWS(aoEvento, !offline);

  const escalonar = useCallback(
    async (canal: CanalOpcao) => {
      /* Marca antes da resposta: o botão precisa reagir ao toque. Se falhar, o
       * registro do acionamento humano é o que importa — e ele acontece no
       * backend mesmo quando o canal não tem contato (MVP-034). */
      setAcionados((a) => ({ ...a, [canal.canal]: true }));
      /* Offline não há chamado no servidor para anexar o escalonamento. A marca
       * na tela ainda vale: ela diz à pessoa quais números ela já tentou, que é
       * o uso real destes botões quando não há sistema do outro lado. */
      if (offline) return;
      try {
        await escalonarChamado(alerta.chamado_id, canal.canal);
      } catch {
        /* Mantém marcado. Desmarcar sugeriria "não acionei", e a pessoa
         * tentaria de novo — mas ela **já ligou**, que é o que o botão
         * registra. O painel mostra o resultado real. */
      }
    },
    [alerta.chamado_id, offline],
  );

  return (
    <section className="poto-alerta" role="status" aria-live="polite">
      <span className="poto-alerta-pulso" aria-hidden="true">
        <Sym nome="emergency" tamanho="xl" cor="#fff" />
      </span>

      <p className="poto-alerta-status">
        {offline ? "Sem conexão — alerta guardado" : textoDoStatus(status)}
      </p>

      <div>
        <p className="poto-alerta-legenda">
          {offline ? "Situação" : "Protocolo"}
        </p>
        <p className="poto-alerta-protocolo tabular">{alerta.chamado_id}</p>
      </div>

      <p className="poto-alerta-cronometro tabular" aria-label={`Tempo: ${tempo}`}>
        {tempo}
      </p>

      <div className="poto-alerta-escalonar">
        <p className="poto-alerta-legenda">
          {offline
            ? "Sem conexão. Ligue diretamente:"
            : "Se precisar, acione diretamente"}
        </p>
        <div className="poto-alerta-botoes">
          {alerta.escalonamento_disponivel.map((canal) => (
            <button
              key={canal.canal}
              type="button"
              className="poto-escalonar"
              onClick={() => void escalonar(canal)}
              disabled={acionados[canal.canal]}
            >
              {acionados[canal.canal] && (
                <Sym nome="check" tamanho="sm" cor="var(--ok)" />
              )}
              {canal.nome}
            </button>
          ))}
        </div>
      </div>

      {/* Único jeito de sair. Não há timer: `alerta_ativo` é persistente. */}
      <button type="button" className="poto-alerta-voltar" onClick={onVoltar}>
        <Sym nome="arrow_back" tamanho="sm" cor="#fff" />
        Voltar ao início
      </button>
    </section>
  );
}
