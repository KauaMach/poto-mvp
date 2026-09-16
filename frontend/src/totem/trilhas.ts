/* As quatro trilhas do totem — MVP-050.
 *
 * A tabela vive em um lugar só. A ordem **é** a ordem da tela, e não é
 * arbitrária: Emergência médica e Segurança primeiro porque são as duas que
 * mais aparecem e as duas de maior gravidade; "Outros" por último porque é o
 * destino de quem não se encaixa nas três anteriores.
 *
 * O `modo` aqui é **intenção**, não decisão. O roteador do backend força
 * `discreto` na trilha `mulher` de qualquer jeito (MVP-012); mandá-lo daqui
 * apenas evita que o primeiro quadro da tela de confirmação apareça no modo
 * errado enquanto a resposta não chegou.
 */
import type { GlifoSym } from "../componentes/Sym";
import type { Modo, TipoOcorrencia } from "../comum/tipos";

export type Trilha = {
  tipo: TipoOcorrencia;
  rotulo: string;
  icone: GlifoSym;
  /** `muted` para o que não é emergência — ver MVP-045. */
  variante?: "padrao" | "muted";
  modo?: Modo;
  /** Lido por leitor de tela. Diz o que **vai acontecer**, não o que o botão é. */
  descricao: string;
};

export const TRILHAS: Trilha[] = [
  {
    tipo: "saude",
    rotulo: "Emergência médica",
    icone: "stethoscope",
    descricao: "Acionar emergência médica. Envia seu pedido para a central.",
  },
  {
    tipo: "seguranca",
    rotulo: "Segurança",
    icone: "shield",
    descricao: "Acionar segurança. Envia seu pedido para a central.",
  },
  {
    tipo: "mulher",
    rotulo: "Assédio / Sala Lilás",
    icone: "female",
    /* Discreto: a tela de confirmação não mostra protocolo nem cita o canal.
     * Se o agressor está a três metros, isso é a diferença entre socorro e
     * risco. */
    modo: "discreto",
    descricao:
      "Acionar atendimento. Envia seu pedido para a central de forma discreta.",
  },
  {
    tipo: "ouvidoria",
    rotulo: "Outros",
    icone: "info",
    variante: "muted",
    descricao: "Registrar outro tipo de ocorrência.",
  },
];
