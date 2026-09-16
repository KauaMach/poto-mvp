/* Marca do header — MVP-044.
 *
 * "P.O.T.O" em Michroma com os **pontos em ferrugem**. É a única aplicação de
 * `--rust` na tela inicial fora do botão de pânico, e é de propósito: a regra
 * 60/30/10 reserva a ferrugem para ação e alerta, e a marca pega apenas os
 * quatro pontos.
 *
 * Clicar volta ao início. Num totem de parede isso não é navegação, é **saída
 * de emergência de interface**: alguém que entrou numa trilha por engano, ou
 * que precisa que a tela pare de mostrar o que está mostrando, toca a marca.
 * É o gesto mais aprendido que existe na web.
 */
import type { CSSProperties } from "react";

type Props = {
  /** Volta à tela inicial. Sem isto a marca é um rótulo, não uma saída. */
  onInicio?: () => void;
};

const BASE: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: 16,
  /* Michroma só tem peso 400 — ver a nota em `tokens.css`. */
  fontWeight: 400,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "var(--ink)",
  /* A marca é pequena e o alvo mínimo de 64px do `base.css` a esticaria,
   * empurrando o header. Aqui o alvo cresce por `padding`, mantendo a
   * tipografia no tamanho especificado. */
  minHeight: 0,
  minWidth: 0,
  padding: "var(--space-sm) var(--space-xs)",
  display: "inline-flex",
  alignItems: "center",
  lineHeight: 1,
  whiteSpace: "nowrap",
};

export function Wordmark({ onInicio }: Props) {
  /* O texto é montado peça por peça em vez de escrito como "P.O.T.O" porque os
   * pontos precisam de cor própria. Um `aria-label` cobre o custo disso: sem
   * ele o leitor de tela soletraria os quatro `span` separados. */
  const conteudo = (
    <>
      {["P", "O", "T", "O"].map((letra, i) => (
        <span key={`${letra}-${i}`}>
          {letra}
          {i < 3 && <span style={{ color: "var(--rust)" }}>.</span>}
        </span>
      ))}
    </>
  );

  if (!onInicio) {
    return (
      <span style={BASE} aria-label="P.O.T.O">
        {conteudo}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onInicio}
      style={{ ...BASE, background: "none", border: "none", cursor: "pointer" }}
      aria-label="P.O.T.O — voltar ao início"
    >
      {conteudo}
    </button>
  );
}
