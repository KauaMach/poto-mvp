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
import { useCallback, useRef, useState } from "react";
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
  /* URL do vídeo do operador, quando a central inicia a chamada (MEL-006).
   * Chega pelo WebSocket com escopo da COR-002, então só este chamado a
   * recebe. */
  const [videoDaCentral, setVideoDaCentral] = useState<string | null>(null);
  const [audioDaCentral, setAudioDaCentral] = useState<string | null>(null);
  /* O navegador pode **bloquear a reprodução com som** se julgar que não houve
   * interação do usuário. Aqui houve — a pessoa acabou de segurar o pânico por
   * 1 s — mas a heurística não é garantida, e falhar em silêncio seria o pior
   * resultado: ela veria o rosto do operador e não ouviria a voz, sem saber por
   * quê. Se o `play()` for recusado, a tela oferece um toque. */
  const [precisaTocar, setPrecisaTocar] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [acionados, setAcionados] = useState<Record<string, boolean>>({});
  const tempo = useCronometro(desde);

  const aoEvento = useCallback(
    (evento: EventoWS) => {
      /* Só interessa **este** chamado. Um outro totem acionando ao mesmo tempo
       * não pode mudar o status desta tela. */
      /* Descarta os eventos sem `chamado_id` **antes** de comparar: são
       * `conectado` e `ping`, e é essa ordem que permite ao TypeScript
       * estreitar a união — invertê-la dá erro de tipo, porque `dados` daqueles
       * dois não tem o campo. */
      if (evento.evento === "conectado" || evento.evento === "ping") return;
      if (evento.dados.chamado_id !== alerta.chamado_id) return;

      /* A central iniciou ou encerrou a videochamada (MEL-006). Encerrar
       * **tem** que tirar o `<img>` da tela: mantê-lo montado contra um stream
       * que acabou deixaria a última imagem do operador congelada, parecendo
       * que alguém ainda está ali — o oposto de informar. */
      if (evento.evento === "chamada_iniciada") {
        setVideoDaCentral(evento.dados.stream_url);
        setAudioDaCentral(evento.dados.audio_url);
        return;
      }
      if (evento.evento === "chamada_encerrada") {
        setVideoDaCentral(null);
        setAudioDaCentral(null);
        setPrecisaTocar(false);
        return;
      }

      setStatus(evento.dados.status);
    },
    [alerta.chamado_id],
  );

  /* Offline não há WebSocket para assinar, e tentar reconectar em laço numa
   * tela de pânico só aquece o aparelho.
   *
   * O terceiro argumento é o escopo (COR-002): o totem assina
   * `/ws/chamado/{id}` e recebe **só** este chamado, **só** com `chamado_id` e
   * `status`. Antes assinava o `/ws` do painel e recebia o relato de todas as
   * outras pessoas — o filtro do `aoEvento` abaixo descartava, mas depois de o
   * dado já ter chegado ao aparelho. */
  useEventosWS(aoEvento, !offline, alerta.chamado_id);

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

      {/* O operador, ao vivo (MEL-006).
        *
        * Entra **abaixo** do protocolo, do cronômetro e do status, e não acima:
        * a função desta tela é informar quem está esperando, e o vídeo é
        * acompanhamento. Empurrar o protocolo para fora da vista trocaria o
        * essencial pelo acessório.
        *
        * MJPEG num `<img>`, sem uma linha de JavaScript de player — e sem
        * exigir contexto seguro, porque **tocar** não exige, só capturar.
        *
        * `onError` limpa: se o stream cair, a moldura sai em vez de ficar um
        * quadro quebrado na tela de alguém em pânico. */}
      {videoDaCentral && (
        <figure className="poto-alerta-video">
          <img
            src={videoDaCentral}
            alt="Atendente da central, ao vivo"
            onError={() => setVideoDaCentral(null)}
          />
          <figcaption>
            <span aria-hidden="true" className="poto-ponto poto-ponto-vivo" />
            {precisaTocar ? "Atendente na linha — sem som" : "Atendente na linha"}
          </figcaption>
        </figure>
      )}

      {/* A voz do operador (MEL-007).
        *
        * Sem `controls`: quem está em pânico não deve precisar operar um player.
        * O elemento é invisível (`poto-alerta-audio`) e só existe para tocar.
        *
        * `onCanPlay` tenta iniciar e **captura a recusa**: se o navegador
        * bloquear o autoplay, `precisaTocar` acende um botão. Sem isso o
        * silêncio seria indistinguível de "o operador não está falando". */}
      {audioDaCentral && (
        <audio
          ref={audioRef}
          className="poto-alerta-audio"
          src={audioDaCentral}
          autoPlay
          onCanPlay={() => {
            void audioRef.current
              ?.play()
              .then(() => setPrecisaTocar(false))
              .catch(() => setPrecisaTocar(true));
          }}
          onError={() => setAudioDaCentral(null)}
        />
      )}

      {precisaTocar && (
        <button
          type="button"
          className="poto-alerta-ouvir"
          onClick={() => {
            void audioRef.current
              ?.play()
              .then(() => setPrecisaTocar(false))
              .catch(() => {});
          }}
        >
          <Sym nome="mic" tamanho="sm" cor="#fff" />
          Toque para ouvir o atendente
        </button>
      )}

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
