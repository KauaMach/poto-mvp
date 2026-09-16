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
 * As ações do operador são a MVP-063; o contador de SLA é a MVP-064.
 */
import type { Chamado } from "../comum/tipos";
import {
  COR_GRAVIDADE,
  ROTULO_GRAVIDADE,
  ROTULO_STATUS,
  TITULO_TIPO,
} from "./rotulos";

type Props = {
  chamado: Chamado;
  onMudou: (chamado: Chamado) => void;
  /** Prazo da gravidade deste chamado, ou `null` se não escalona (MVP-064). */
  slaSegundos: number | null;
};

export function CardChamado({ chamado }: Props) {
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

      {chamado.texto_livre && (
        /* Itálico e entre aspas: é a voz de quem pediu ajuda, não texto do
         * sistema. A distinção importa quando se lê rápido. */
        <p className="poto-card-relato">“{chamado.texto_livre}”</p>
      )}

      <footer className="poto-card-rodape">
        <span className="poto-status">{ROTULO_STATUS[chamado.status]}</span>
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
