/* Cartão de chamado — MVP-061.
 *
 * O que o operador lê em um relance, na ordem em que ele lê: gravidade,
 * protocolo, tipo, onde, e o relato.
 *
 * A **borda esquerda de 5px** na cor da gravidade é o que permite varrer vinte
 * cartões sem ler nenhum. Mas ela nunca vem sozinha: o chip ao lado diz
 * "Imediato", "Potencial" ou "Orientação". Cor como único sinal excluiria os
 * ~8% dos homens com alguma deficiência na percepção de vermelho e verde, e
 * este é um painel de emergência.
 *
 * As ações do operador (MVP-063) ficam no rodapé e só aparecem em chamado que
 * ainda espera alguém. O contador de SLA (MVP-064) aparece pela mesma condição
 * — e só onde há prazo: `orientacao` traz `null` no `/config`, que é informação
 * e não ausência dela (não há urgência a proteger numa dúvida de ouvidoria).
 */
import { useCallback, useState } from "react";
import { ackChamado, atualizarChamado } from "../comum/api";
import type { Chamado, Dispositivo, StatusChamado } from "../comum/tipos";
import { Sym } from "../componentes/Sym";
import { ChamadaChamado } from "./ChamadaChamado";
import { ContadorSLA } from "./ContadorSLA";
import { MidiaChamado } from "./MidiaChamado";
import {
  ABERTOS,
  COR_GRAVIDADE,
  ROTULO_GRAVIDADE,
  ROTULO_STATUS,
  TITULO_TIPO,
} from "./rotulos";

/* Estados que o operador escolhe no seletor.
 *
 * `reconhecido` **não** está aqui, e a omissão é deliberada: ele vem do botão
 * "Reconhecer", que grava também o `acked_at` de onde sai a métrica de tempo
 * até o reconhecimento. Oferecê-lo no seletor daria dois caminhos para a mesma
 * transição, e um deles não pararia o relógio do SLA.
 *
 * `cancelado` também fica fora: marcar um pedido de socorro como trote é uma
 * decisão que merece mais atrito que um item de lista suspensa.
 */
const TRANSICOES: { valor: StatusChamado; rotulo: string }[] = [
  { valor: "em_atendimento", rotulo: "Em atendimento" },
  { valor: "encerrado", rotulo: "Encerrado" },
];

type Props = {
  chamado: Chamado;
  onMudou: (chamado: Chamado) => void;
  /** Prazo da gravidade deste chamado, ou `null` se não escalona (MVP-064). */
  slaSegundos: number | null;
  /** Dispositivos de captura disponíveis no totem (MVP-078). */
  dispositivos: Dispositivo[];
};

export function CardChamado({
  chamado,
  onMudou,
  slaSegundos,
  dispositivos,
}: Props) {
  const [ocupado, setOcupado] = useState(false);
  const aberto = ABERTOS.has(chamado.status);

  const agir = useCallback(
    async (acao: () => Promise<Chamado>) => {
      /* Trava antes de qualquer `await`: dois cliques rápidos no "Reconhecer"
       * mandariam dois POST. O segundo é inofensivo — o backend preserva o
       * `acked_at` original (MVP-033) — mas o cartão piscaria duas vezes, e
       * num painel de vinte cartões isso é o operador perdendo o lugar. */
      setOcupado(true);
      try {
        onMudou(await acao());
      } catch {
        /* Mantém o cartão como está. Se a ação chegou, o WebSocket corrige o
         * estado sozinho (MVP-062); se não chegou, o operador tenta de novo.
         * Um alerta de erro aqui seria uma caixa para fechar no meio de uma
         * emergência. */
      } finally {
        setOcupado(false);
      }
    },
    [onMudou],
  );

  return (
    <article
      className="poto-card"
      /* A cor vem por `style` porque depende do dado; a espessura e o estilo
       * ficam no CSS. */
      style={{ borderLeftColor: COR_GRAVIDADE[chamado.gravidade] }}
    >
      <header className="poto-card-topo">
        <span
          className="poto-chip-gravidade"
          style={{ color: COR_GRAVIDADE[chamado.gravidade] }}
        >
          {/* O ponto é decorativo; o rótulo ao lado é o que informa. */}
          <span aria-hidden="true" className="poto-ponto" />
          {ROTULO_GRAVIDADE[chamado.gravidade]}
        </span>
        <span className="poto-protocolo tabular">{chamado.chamado_id}</span>
      </header>

      <h2 className="poto-card-titulo">{TITULO_TIPO[chamado.tipo_ocorrencia]}</h2>

      <p className="poto-card-linha">
        <span className="poto-card-rotulo">Totem</span>
        {chamado.totem_id}
      </p>
      <p className="poto-card-linha">
        <span className="poto-card-rotulo">Canal</span>
        {chamado.canal_roteado || "—"}
      </p>
      <p className="poto-card-linha">
        <span className="poto-card-rotulo">Recebido</span>
        <time dateTime={chamado.created_at} className="tabular">
          {hora(chamado.created_at)}
        </time>
        {atrasado(chamado) && (
          /* A lacuna que a MVP-059 documentou, resolvida aqui.
           *
           * Um evento que ficou na fila offline chega com payload **idêntico**
           * a um ao vivo — é isso que preserva a idempotência — e o único sinal
           * disponível é a distância entre o relógio do tablet e o do servidor.
           * Sem esta marca o operador não sabe que está vendo um pedido de
           * horas atrás, e trata como se estivesse acontecendo agora.
           */
          <span className="poto-atraso">
            esperou {haQuantoTempo(chamado)} na fila
          </span>
        )}
      </p>

      {/* Duas condições, e as duas importam. `aberto`: um chamado encerrado
        * não tem prazo a correr. `slaSegundos !== null`: `orientacao` não
        * escalona, e um contador ali sugeriria urgência que não existe. */}
      {aberto && slaSegundos !== null && (
        <ContadorSLA chamado={chamado} segundos={slaSegundos} />
      )}

      {chamado.texto_livre && (
        /* Itálico e entre aspas: é a voz de quem pediu ajuda, não texto do
         * sistema. A distinção importa quando se lê rápido. */
        <p className="poto-card-relato">“{chamado.texto_livre}”</p>
      )}

      {/* Mídia só em chamado **ativo** (MVP-078).
        *
        * Duas razões, e a segunda é a que importa. A primeira é técnica: o
        * backend recusa com 409 em chamado encerrado ou cancelado, então o
        * botão não funcionaria. A segunda é de projeto: um atendimento
        * concluído não justifica olhar o corredor, e oferecer o botão ali
        * transformaria o histórico de chamados numa lista de pretextos para
        * ligar a câmera.
        *
        * `aberto` é o mesmo conjunto que governa as ações do operador — a
        * condição é uma só, e não duas que podem divergir. */}
      {aberto && (
        <MidiaChamado chamado={chamado} dispositivos={dispositivos} />
      )}

      {/* Videochamada só em **pânico** ativo (MEL-005).
        *
        * A condição não é preferência: `alerta_ativo` é o único estado com tela
        * persistente no totem. As outras trilhas mostram a confirmação por 9 s
        * e voltam para a Home — não há onde o vídeo aparecer. Oferecer o botão
        * ali abriria uma chamada para uma tela que já saiu.
        *
        * `origem_acionamento` e não `status`: o pânico pode estar em
        * `reconhecido` ou `em_atendimento` e a tela de alerta continua aberta,
        * porque ela só fecha por ação de quem está no totem. */}
      {aberto && chamado.origem_acionamento === "panico" && (
        <ChamadaChamado chamado={chamado} />
      )}

      <footer className="poto-card-rodape">
        <span className="poto-status">{ROTULO_STATUS[chamado.status]}</span>

        <div className="poto-card-acoes">
          {/* Some depois do sucesso porque desaparece a condição que o traz:
            * `acked_at` deixa de ser nulo. Não há estado de "já cliquei" a
            * manter — o dado é a fonte. */}
          {aberto && chamado.acked_at === null && (
            <button
              type="button"
              className="poto-botao-primario"
              disabled={ocupado}
              onClick={() => void agir(() => ackChamado(chamado.chamado_id))}
            >
              <Sym nome="check" tamanho="sm" cor="#fff" />
              Reconhecer
            </button>
          )}

          {(aberto ||
            chamado.status === "reconhecido" ||
            chamado.status === "em_atendimento") && (
            <label className="poto-seletor">
              <span className="visually-hidden">
                Mudar estado de {chamado.chamado_id}
              </span>
              {/* Valor fixo em "" e não controlado pelo status: o seletor é um
                * disparador de ação, não um espelho do estado. Mostrar o
                * estado atual ali convidaria o operador a "voltar" mudando a
                * seleção, e o rodapé já diz em que estado o chamado está. */}
              <select
                value=""
                disabled={ocupado}
                onChange={(e) => {
                  const destino = e.target.value as StatusChamado;
                  if (destino) {
                    void agir(() =>
                      atualizarChamado(chamado.chamado_id, { status: destino }),
                    );
                  }
                }}
              >
                <option value="">Mudar estado…</option>
                {TRANSICOES.filter((t) => t.valor !== chamado.status).map((t) => (
                  <option key={t.valor} value={t.valor}>
                    {t.rotulo}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </footer>
    </article>
  );
}

function hora(iso: string): string {
  /* `created_at` vem em UTC (decisão do `db.agora_iso()`) e o navegador o
   * converte para o fuso de quem olha. É por isso que o backend não formata
   * data: ele não sabe onde o painel está. */
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Quanto tempo o evento passou na fila antes de chegar, em segundos.
 *
 * `timestamp_local` é o relógio do **tablet** e não é confiável — por isso o
 * resultado só é usado como indício visual, nunca para rotear nem para o SLA.
 */
function atrasoSegundos(chamado: Chamado): number | null {
  if (!chamado.timestamp_local) return null;
  const local = Date.parse(chamado.timestamp_local);
  if (Number.isNaN(local)) return null;
  return (Date.parse(chamado.created_at) - local) / 1000;
}

/** Só marca acima de 2 minutos: abaixo disso a diferença é relógio
 * dessincronizado, não fila. Marcar tudo transformaria o aviso em ruído, e um
 * aviso que aparece sempre não é lido. */
function atrasado(chamado: Chamado): boolean {
  const s = atrasoSegundos(chamado);
  return s !== null && s > 120;
}

function haQuantoTempo(chamado: Chamado): string {
  const s = atrasoSegundos(chamado) ?? 0;
  const horas = Math.floor(s / 3600);
  if (horas >= 1) return `${horas} h`;
  return `${Math.floor(s / 60)} min`;
}
