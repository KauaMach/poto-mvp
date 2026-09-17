/* Cartão de chamado — MVP-061, reformado na MEL-009.
 *
 * O que o operador lê em um relance, na ordem em que ele lê: gravidade,
 * protocolo, hora, tipo, onde, e o relato.
 *
 * A **borda esquerda de 5px** na cor da gravidade é o que permite varrer vinte
 * cartões sem ler nenhum. Mas ela nunca vem sozinha: o chip ao lado diz
 * "Imediato", "Potencial" ou "Orientação". Cor como único sinal excluiria os
 * ~8% dos homens com alguma deficiência na percepção de vermelho e verde, e
 * este é um painel de emergência.
 *
 * **O cartão virou um resumo clicável.** Antes ele carregava botão de
 * reconhecer, seletor de estado, seletor de dispositivo de mídia e a
 * videochamada — quatro controles disputando espaço com o dado que se precisa
 * ler de relance, vezes vinte cartões. E a videochamada, que é a ação mais
 * importante de um pânico, terminava como um botão apagado no pé.
 *
 * Agora o cartão mostra e o detalhe faz. O rodapé guarda só a **situação** e um
 * resumo do que já aconteceu — é o que diz se este cartão precisa de alguém.
 */
import type { Chamado } from "../comum/tipos";
import { Sym } from "../componentes/Sym";
import { ContadorSLA } from "./ContadorSLA";
import {
  ABERTOS,
  COR_GRAVIDADE,
  ROTULO_GRAVIDADE,
  ROTULO_STATUS,
  TITULO_TIPO,
} from "./rotulos";

type Props = {
  chamado: Chamado;
  /** Prazo da gravidade deste chamado, ou `null` se não escalona (MVP-064). */
  slaSegundos: number | null;
  /** Abre o detalhe. É a única ação do cartão. */
  onAbrir: () => void;
  selecionado?: boolean;
};

export function CardChamado({
  chamado,
  slaSegundos,
  onAbrir,
  selecionado = false,
}: Props) {
  const aberto = ABERTOS.has(chamado.status);
  const precisaDeAlguem = aberto && chamado.acked_at === null;

  return (
    /* `<button>` e não `<div onClick>`: o cartão inteiro é o alvo, e um botão
     * de verdade traz foco por teclado, `Enter`/`Espaço` e anúncio correto no
     * leitor de tela — de graça. Um `div` clicável exigiria replicar os três. */
    <button
      type="button"
      onClick={onAbrir}
      className={
        selecionado ? "poto-card poto-card-selecionado" : "poto-card"
      }
      style={{ borderLeftColor: COR_GRAVIDADE[chamado.gravidade] }}
      aria-label={`${TITULO_TIPO[chamado.tipo_ocorrencia]}, ${
        ROTULO_GRAVIDADE[chamado.gravidade]
      }, ${chamado.chamado_id} — abrir detalhe`}
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
        <span className="poto-card-hora tabular">
          <time dateTime={chamado.created_at}>{hora(chamado.created_at)}</time>
        </span>
      </header>

      <h2 className="poto-card-titulo">
        {TITULO_TIPO[chamado.tipo_ocorrencia]}
      </h2>
      <p className="poto-protocolo tabular">{chamado.chamado_id}</p>

      <p className="poto-card-local">
        {chamado.totem_id}
        {chamado.canal_roteado && (
          <span className="poto-card-canal"> · {chamado.canal_roteado}</span>
        )}
        {atrasado(chamado) && (
          /* A lacuna que a MVP-059 documentou, resolvida aqui.
           *
           * Um evento que ficou na fila offline chega com payload **idêntico**
           * a um ao vivo — é isso que preserva a idempotência — e o único sinal
           * disponível é a distância entre o relógio do tablet e o do servidor.
           * Sem esta marca o operador trata um pedido de horas atrás como se
           * estivesse acontecendo agora. */
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

      <footer className="poto-card-rodape">
        <span
          className={
            precisaDeAlguem ? "poto-status poto-status-espera" : "poto-status"
          }
        >
          {precisaDeAlguem && (
            <span aria-hidden="true" className="poto-ponto poto-ponto-vivo" />
          )}
          {ROTULO_STATUS[chamado.status]}
        </span>

        {/* Afordância explícita de que o cartão abre algo. Sem ela, um cartão
          * clicável parece um cartão inerte — e o operador não descobre o
          * detalhe por tentativa. */}
        <span className="poto-card-abrir" aria-hidden="true">
          Detalhes
          <Sym nome="arrow_back" tamanho="xs" />
        </span>
      </footer>
    </button>
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
