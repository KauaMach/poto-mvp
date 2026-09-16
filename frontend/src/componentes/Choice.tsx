/* Botão-cartão das trilhas — MVP-045.
 *
 * O elemento mais importante da interface: é por um destes quatro que passa
 * todo acionamento que não é pânico. Tudo aqui é dimensionado para ser tocado
 * de pé, com pressa, possivelmente com a mão tremendo — `min-height: 168px` é
 * mais do dobro do alvo mínimo de toque, e é assim de propósito.
 *
 * **A cor do ícone é informação.** Três trilhas usam ferrugem; "Outros" usa
 * `--muted`. Não é decoração: é a regra 60/30/10 dizendo que aquela trilha não
 * é emergência, e é o que a captura de tela de referência mostra. Quem chega
 * com pressa precisa que as três opções urgentes se destaquem da quarta.
 */
import type { CSSProperties } from "react";
import { Sym, type GlifoSym } from "./Sym";

type Props = {
  icone: GlifoSym;
  /** Rótulo visível. É ele que carrega o significado — o ícone é `aria-hidden`. */
  rotulo: string;
  onClick: () => void;
  /** `muted` para trilhas que não são emergência (Outros / Ouvidoria). */
  variante?: "padrao" | "muted";
  /** Desabilita durante um envio em curso, para não gerar dois chamados. */
  desabilitado?: boolean;
  /** Complemento lido por leitor de tela, anexado **depois** do rótulo.
   *
   * O nome acessível final é `"<rotulo> — <descricao>"`, e a ordem importa: a
   * WCAG 2.5.3 (Label in Name) exige que o texto visível esteja contido no nome
   * acessível, senão o controle por voz deixa de funcionar — dizer "Segurança"
   * não acionaria um botão cujo nome fosse "Acionar atendimento de segurança".
   */
  descricao?: string;
};

const ESTILO: CSSProperties = {
  /* Medidas de PLAN.md §6, tabela de componentes. */
  minHeight: 168,
  padding: "28px 16px",
  /* 1.5px e não 1px: a borda tem que sobreviver à densidade de tela do tablet
   * sem virar um fio cinza. */
  border: "1.5px solid var(--line)",
  borderRadius: "var(--r-lg)",
  background: "var(--bg)",

  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: "var(--space-md)",
  width: "100%",
  textAlign: "center",

  /* Só borda, fundo e transform fazem transição. Incluir `all` aqui animaria
   * também a cor do texto e o raio, que devem ser instantâneos. */
  transition:
    "border-color var(--t-micro), background-color var(--t-micro), transform var(--t-micro)",
};

const ROTULO: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 400,
  fontSize: 13,
  letterSpacing: "0.04em",
  lineHeight: 1.3,
  color: "var(--ink)",
  /* Sem isto, "Assédio / Sala Lilás" quebra em três linhas e desalinha o
   * cartão em relação ao vizinho. */
  maxWidth: "18ch",
};

export function Choice({
  icone,
  rotulo,
  onClick,
  variante = "padrao",
  desabilitado = false,
  descricao,
}: Props) {
  const cor = variante === "muted" ? "var(--muted)" : "var(--rust)";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={desabilitado}
      aria-label={descricao ? `${rotulo} — ${descricao}` : undefined}
      className="poto-choice"
      style={{ ...ESTILO, opacity: desabilitado ? 0.5 : 1 }}
    >
      <Sym nome={icone} tamanho="xl" cor={cor} />
      <span style={ROTULO}>{rotulo}</span>
    </button>
  );
}
