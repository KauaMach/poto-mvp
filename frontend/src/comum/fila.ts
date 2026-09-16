/* Fila offline — o totem não para porque a rede parou (MVP-057).
 *
 * O que esta fila protege não é conveniência: é a premissa do projeto. Um totem
 * que exibe "sem conexão, tente mais tarde" para quem está em perigo é pior que
 * um totem desligado, porque promete socorro e não entrega.
 *
 * A peça que faz isso funcionar está em outro arquivo: o `evento_id` nasce no
 * **cliente**, antes do envio (`api.ts`). Por isso um evento pode falhar, ficar
 * guardado horas e ser reenviado carregando o mesmo id — e o backend devolve o
 * chamado que já existe em vez de criar um segundo alarme para a mesma
 * emergência. Sem essa decisão, a fila multiplicaria chamados em vez de
 * salvá-los.
 *
 * **Nenhuma função aqui levanta.** `localStorage` falha de três maneiras reais:
 * cota estourada (`QuotaExceededError`), acesso bloqueado (navegação privada,
 * política de terceiros) e conteúdo corrompido. Em todas, perder a fila é ruim;
 * derrubar a tela do totem é pior.
 */
import type { EventoIn, PanicoIn } from "./tipos";

const CHAVE = "poto.fila.v1";

/** Teto de itens guardados.
 *
 * Existe porque `localStorage` tem cota (tipicamente 5 MB) e porque uma fila
 * sem limite cresceria para sempre num totem esquecido offline por semanas.
 * Quando estoura, o **mais antigo** sai: entre um pedido de dez dias atrás e um
 * de agora, o de agora é o que ainda pode ser atendido.
 */
const LIMITE = 50;

export type ItemFila = {
  /** `evento` para uma trilha, `panico` para o alerta imediato. */
  tipo: "evento" | "panico";
  /** O payload exato que falhou, com o `evento_id` original. */
  corpo: EventoIn | PanicoIn;
  /** Quando entrou na fila, em ISO. Só para diagnóstico. */
  enfileirado_em: string;
  /** Tentativas de dreno já feitas, para diagnóstico no `/galeria`. */
  tentativas: number;
};

/* --- Acesso ao armazenamento ---------------------------------------------- */

function ler(): ItemFila[] {
  try {
    const bruto = window.localStorage.getItem(CHAVE);
    if (!bruto) return [];
    const dados = JSON.parse(bruto);
    /* Valida a forma antes de confiar: um `localStorage` de uma versão
     * anterior, ou editado à mão, não pode fazer a tela quebrar ao montar. */
    if (!Array.isArray(dados)) return [];
    return dados.filter(
      (i): i is ItemFila =>
        i && typeof i === "object" && "corpo" in i && "tipo" in i,
    );
  } catch {
    /* Bloqueado ou corrompido. Fila vazia é a degradação correta — o
     * acionamento continua funcionando, só não sobrevive ao recarregamento. */
    return [];
  }
}

function escrever(itens: ItemFila[]): boolean {
  try {
    window.localStorage.setItem(CHAVE, JSON.stringify(itens));
    return true;
  } catch {
    return false;
  }
}

/* --- API ------------------------------------------------------------------ */

/** Guarda um envio que falhou. Devolve se conseguiu persistir.
 *
 * O retorno importa: a tela precisa saber se pode prometer "será enviado
 * automaticamente" ou se o pedido só existe na memória desta sessão.
 */
export function enfileirar(
  tipo: ItemFila["tipo"],
  corpo: EventoIn | PanicoIn,
): boolean {
  const itens = ler();

  /* Não duplica: um dreno que falhou no meio pode tentar enfileirar de novo o
   * que já está lá. O `evento_id` é a identidade. */
  if (itens.some((i) => i.corpo.evento_id === corpo.evento_id)) return true;

  itens.push({
    tipo,
    corpo,
    enfileirado_em: new Date().toISOString(),
    tentativas: 0,
  });

  /* Descarta os mais antigos, não os mais novos. */
  const cortados = itens.slice(-LIMITE);
  return escrever(cortados);
}

/** Itens aguardando envio, do mais antigo para o mais novo. */
export function pendentes(): ItemFila[] {
  return ler();
}

export function quantosPendentes(): number {
  return ler().length;
}

/** Remove um item pelo `evento_id`. Usado pelo dreno ao ter sucesso. */
export function remover(eventoId: string): void {
  escrever(ler().filter((i) => i.corpo.evento_id !== eventoId));
}

/** Incrementa o contador de tentativas de um item. */
export function marcarTentativa(eventoId: string): void {
  escrever(
    ler().map((i) =>
      i.corpo.evento_id === eventoId
        ? { ...i, tentativas: i.tentativas + 1 }
        : i,
    ),
  );
}

/** Esvazia a fila. Existe para `make demo-reset` (MVP-071) e para teste. */
export function limpar(): void {
  try {
    window.localStorage.removeItem(CHAVE);
  } catch {
    /* Nada a fazer; ver a nota no topo. */
  }
}

export const FILA_CHAVE = CHAVE;
export const FILA_LIMITE = LIMITE;
