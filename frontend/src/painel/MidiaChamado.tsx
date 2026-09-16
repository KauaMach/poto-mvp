/* Câmera e microfone dentro do chamado — MVP-078.
 *
 * O operador escolhe um dispositivo e vê ou ouve. O que este arquivo faz de
 * fato é **traduzir a sessão de mídia do backend (MVP-077) para a tela**, e
 * quase todas as decisões daqui vêm de uma única ideia:
 *
 *   Uma câmera num espaço público só é aceitável se cada ativação deixar
 *   rastro e tiver fim. A diferença entre um totem de segurança e um
 *   equipamento de vigilância **é** essa.
 *
 * Daí:
 *
 * - **Nada aparece em chamado encerrado.** Um atendimento concluído não
 *   justifica olhar o corredor, e o backend recusa com 409 — mas oferecer o
 *   botão e receber erro ensinaria o operador a tentar.
 * - **Nada aparece sem dispositivo.** Botão que abre um quadro preto faz o
 *   operador achar que a câmera falhou, quando não há câmera.
 * - **O prazo fica visível.** A sessão morre em 10 minutos e o backend a
 *   encerra sozinho. Um stream que congela sem explicação parece defeito;
 *   com o contador à vista, é o sistema funcionando.
 * - **Sair encerra.** Fechar o chamado, mudar o filtro ou fechar a aba
 *   dispara `DELETE`. Sem isso, a auditoria registraria dez minutos de câmera
 *   aberta com ninguém assistindo — o que é, para quem fiscaliza, indistinguível
 *   de vigilância.
 *
 * O transporte é deliberadamente antigo: MJPEG num `<img>` e WAV num `<audio>`,
 * **sem uma linha de JavaScript de player**. Sem WebRTC, sem MSE, sem
 * biblioteca, sem negociação de codec. Numa Pi 5 sem encoder H.264 é também o
 * que não custa CPU de compressão (MVP-074/075).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  abrirMidia,
  fecharMidia,
  fecharMidiaAoSair,
} from "../comum/api";
import type { Chamado, Dispositivo, MidiaSessao } from "../comum/tipos";

/* **Sem `<Sym>` aqui, de propósito.** A fonte Material Symbols é servida
 * subsetada pelos sete nomes que o `GlifoSym` enumera (MVP-041) — são 2,3 KB em
 * vez de 363 KB. `camera` e `mic` não estão nela, e pedir um glifo ausente
 * renderiza o **nome como texto**: o botão mostraria a palavra "camera".
 *
 * Acrescentá-los exigiria rebaixar a fonte do Google Fonts com um `icon_names=`
 * novo e revalidar as ligaduras do subset. Não vale: o próprio `Sym` documenta
 * que o ícone é decorativo e "quem carrega o significado é sempre o rótulo" —
 * e aqui os rótulos ("Ver câmera", "Ouvir microfone", "AO VIVO") já dizem tudo.
 */

type Props = {
  chamado: Chamado;
  /** Dispositivos detectados, buscados **uma vez** pelo painel.
   *
   * Vêm por props e não de um `fetch` daqui: com vinte cartões na tela, cada
   * um pedindo `/dispositivos`, seriam vinte requisições para a mesma resposta.
   */
  dispositivos: Dispositivo[];
};

const ROTULO_TIPO = {
  camera: "câmera",
  microfone: "microfone",
} as const;

export function MidiaChamado({ chamado, dispositivos }: Props) {
  const [escolhido, setEscolhido] = useState("");
  const [sessoes, setSessoes] = useState<MidiaSessao[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const disponiveis = useMemo(
    () => dispositivos.filter((d) => d.status === "disponivel"),
    [dispositivos],
  );

  /* Ids das sessões abertas, como string, para a dependência do efeito de
   * limpeza ser estável. Um array novo a cada render — que `sessoes` é —
   * reexecutaria o efeito sem parar, e cada reexecução encerraria a sessão que
   * acabou de abrir. */
  const abertas = sessoes.map((s) => s.sessao_id).join(",");

  const encerrar = useCallback(
    async (sessao: MidiaSessao) => {
      /* Tira da tela **antes** de esperar a resposta. O `<img>` do MJPEG mantém
       * a conexão aberta enquanto estiver montado, então deixá-lo na tela até o
       * `DELETE` voltar continuaria consumindo a câmera — e o operador já pediu
       * para parar. */
      setSessoes((atuais) => atuais.filter((s) => s.sessao_id !== sessao.sessao_id));
      await fecharMidia(chamado.chamado_id, sessao.sessao_id).catch(() => {
        /* O backend expira a sessão sozinho em 10 min e o worker de SLA varre
         * as vencidas. Uma falha aqui atrasa a liberação, não a impede. */
      });
    },
    [chamado.chamado_id],
  );

  const abrir = useCallback(async () => {
    if (!escolhido) return;
    setOcupado(true);
    setErro(null);
    try {
      const sessao = await abrirMidia(chamado.chamado_id, escolhido);
      setSessoes((atuais) => [
        /* Substitui a sessão do mesmo dispositivo em vez de acumular: dois
         * streams da mesma câmera mostrariam a mesma imagem duas vezes e
         * gastariam o dobro de banda. */
        ...atuais.filter((s) => s.dispositivo_id !== sessao.dispositivo_id),
        sessao,
      ]);
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      setOcupado(false);
    }
  }, [chamado.chamado_id, escolhido]);

  /* Encerra tudo quando o componente sai — chamado encerrado, filtro mudado,
   * painel fechado. É o `DELETE` que o critério da task cobra.
   *
   * Sem a limpeza, a sessão viveria até expirar e a auditoria mostraria dez
   * minutos de câmera aberta sem ninguém assistindo. */
  useEffect(() => {
    if (!abertas) return;
    return () => {
      void fecharMidia(chamado.chamado_id).catch(() => {});
    };
  }, [abertas, chamado.chamado_id]);

  /* O caso que o `useEffect` não cobre: fechar a aba.
   *
   * `pagehide` e não `beforeunload` — o segundo não dispara em iOS nem quando
   * a aba é descartada por memória, que são justamente os cenários de um painel
   * aberto num tablet por horas. */
  useEffect(() => {
    if (!abertas) return;
    const aoSair = () => fecharMidiaAoSair(chamado.chamado_id);
    window.addEventListener("pagehide", aoSair);
    return () => window.removeEventListener("pagehide", aoSair);
  }, [abertas, chamado.chamado_id]);

  if (disponiveis.length === 0) {
    /* Mensagem clara, não um quadro preto — o critério da task.
     *
     * A distinção importa: "não há câmera" manda conferir o cabo; "a câmera
     * falhou" manda reiniciar o serviço. Confundir os dois custa o tempo de um
     * atendimento. */
    return (
      <p className="poto-midia-vazio">
        Nenhuma câmera ou microfone disponível neste totem.
      </p>
    );
  }

  return (
    <section className="poto-midia" aria-label={`Mídia de ${chamado.chamado_id}`}>
      <div className="poto-midia-controles">
        <label className="poto-seletor">
          <span className="visually-hidden">
            Escolher dispositivo de {chamado.chamado_id}
          </span>
          <select
            value={escolhido}
            disabled={ocupado}
            onChange={(e) => setEscolhido(e.target.value)}
          >
            <option value="">Escolher dispositivo…</option>
            {disponiveis.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome} — {ROTULO_TIPO[d.tipo]}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="poto-botao-secundario"
          disabled={!escolhido || ocupado}
          onClick={() => void abrir()}
        >
          {rotuloDoBotao(disponiveis, escolhido)}
        </button>
      </div>

      {erro && (
        <p className="poto-midia-erro" role="alert">
          {erro}
        </p>
      )}

      {sessoes.map((sessao) => (
        <Player
          key={sessao.sessao_id}
          sessao={sessao}
          nome={nomeDoDispositivo(disponiveis, sessao.dispositivo_id)}
          onEncerrar={() => void encerrar(sessao)}
        />
      ))}
    </section>
  );
}

/* --- Player ---------------------------------------------------------------- */

function Player({
  sessao,
  nome,
  onEncerrar,
}: {
  sessao: MidiaSessao;
  nome: string;
  onEncerrar: () => void;
}) {
  const restante = useRestante(sessao.expira_em);
  const [falhou, setFalhou] = useState(false);

  return (
    <figure className="poto-midia-player">
      <figcaption className="poto-midia-cabecalho">
        <span className="poto-ao-vivo">
          {/* O ponto é decorativo; "AO VIVO" é o que informa — a mesma regra do
            * chip de gravidade, e pelo mesmo motivo. */}
          <span aria-hidden="true" className="poto-ponto poto-ponto-vivo" />
          AO VIVO
        </span>
        <span className="poto-midia-nome">{nome}</span>
        {/* O prazo à vista. Um stream que congela sem explicação parece
          * defeito; com o contador, é o sistema encerrando como projetado. */}
        <span className="poto-midia-prazo tabular">
          encerra em {formatar(restante)}
        </span>
        <button
          type="button"
          className="poto-botao-texto"
          onClick={onEncerrar}
        >
          Encerrar
        </button>
      </figcaption>

      {falhou ? (
        <p className="poto-midia-erro" role="alert">
          A captura foi interrompida. Feche e abra de novo para tentar
          novamente.
        </p>
      ) : sessao.tipo === "camera" ? (
        /* MJPEG direto no `<img>`. O navegador renderiza quadro a quadro sem
         * nenhum JavaScript — é HTTP de 1995 fazendo exatamente o que serve
         * aqui. */
        <img
          className="poto-midia-video"
          src={sessao.stream_url}
          alt={`Vídeo ao vivo de ${nome}`}
          onError={() => setFalhou(true)}
        />
      ) : (
        /* `controls` para o operador poder mudar o volume; sem `loop`, porque
         * não há o que repetir num fluxo ao vivo. A barra de progresso vai
         * mostrar uma duração absurda: o WAV de stream declara tamanho
         * desconhecido, que é a convenção para fluxo (MVP-076). */
        <audio
          className="poto-midia-audio"
          src={sessao.stream_url}
          controls
          autoPlay
          onError={() => setFalhou(true)}
        >
          Áudio ao vivo de {nome}
        </audio>
      )}
    </figure>
  );
}

/** Conta para trás até a sessão expirar.
 *
 * Um intervalo próprio e não o `useCronometro` do totem: aquele conta para
 * frente desde um instante, este para trás até zero, e forçar um a servir os
 * dois deixaria os dois piores.
 *
 * **Deriva de um prazo absoluto, não de um contador decrementado.** A primeira
 * versão fazia `setRestante((s) => s - 1)` a cada segundo, e tinha dois
 * defeitos:
 *
 * 1. O navegador **estrangula `setInterval` em aba de fundo** — para uma vez
 *    por minuto, ou congela. Um painel que fica minutos em segundo plano
 *    mostraria "encerra em 8:30" com a sessão já morta há muito, e o operador
 *    veria o stream congelar contrariando o que a tela diz.
 * 2. O `setRestante(inicial)` no início do efeito era `setState` síncrono
 *    dentro de efeito, que o oxlint acusa com razão — e era redundante, porque
 *    o `<Player>` é chaveado por `sessao_id` e já remonta a cada sessão nova.
 *
 * Com prazo absoluto, o relógio serve só para *reavaliar*: a conta vem sempre
 * da diferença até o instante final, então estrangulamento atrasa a atualização
 * da tela mas não falsifica o número.
 */
function useRestante(segundos: number): number {
  /* O prazo é calculado uma vez, na inicialização do estado — e não num efeito.
   * Em efeito, o primeiro render mostraria o valor errado por um quadro. */
  const [prazo] = useState(() => Date.now() + segundos * 1000);
  const [restante, setRestante] = useState(segundos);

  useEffect(() => {
    const recalcular = () =>
      setRestante(Math.max(0, Math.round((prazo - Date.now()) / 1000)));
    const relogio = window.setInterval(recalcular, 1000);
    /* Reavalia ao voltar para a aba, sem esperar o próximo tique: é justo o
     * momento em que o número na tela está mais defasado. */
    document.addEventListener("visibilitychange", recalcular);
    return () => {
      window.clearInterval(relogio);
      document.removeEventListener("visibilitychange", recalcular);
    };
  }, [prazo]);

  return restante;
}

function formatar(segundos: number): string {
  const m = Math.floor(segundos / 60);
  const s = segundos % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function nomeDoDispositivo(dispositivos: Dispositivo[], id: string): string {
  return dispositivos.find((d) => d.id === id)?.nome ?? id;
}

/** "Ver câmera" ou "Ouvir microfone", conforme o que está escolhido.
 *
 * O critério da task nomeia o botão "Ver câmera", e para um microfone isso
 * estaria errado — ninguém vê um microfone.
 */
function rotuloDoBotao(dispositivos: Dispositivo[], id: string): string {
  const escolhido = dispositivos.find((d) => d.id === id);
  if (!escolhido) return "Ver câmera";
  return escolhido.tipo === "camera" ? "Ver câmera" : "Ouvir microfone";
}

function mensagemDeErro(falha: unknown): string {
  /* Traduz o status em linguagem de operador. O `detalhe` do backend é escrito
   * para quem depura, não para quem atende no meio de uma emergência. */
  if (falha instanceof Error && falha.name === "ErroApi") {
    const status = (falha as Error & { status: number }).status;
    if (status === 409) return "Este chamado já foi encerrado.";
    if (status === 404) return "Dispositivo não encontrado.";
    if (status === 401) return "Sem permissão. Confira o token do painel.";
  }
  return "Não foi possível abrir a captura.";
}
