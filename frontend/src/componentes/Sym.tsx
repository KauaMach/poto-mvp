/* Ícone — envelope sobre Material Symbols Rounded (MVP-043).
 *
 * Material Symbols funciona por **ligadura**: o nome do glifo vai como texto
 * dentro do elemento e a fonte o substitui pelo desenho. Isso tem duas
 * consequências que este componente existe para administrar.
 *
 * A primeira é de acessibilidade. Se a fonte não carregar, o leitor de tela —
 * e o olho — encontram a palavra `stethoscope` no meio da interface em
 * português. Daí o `aria-hidden`: quem carrega o significado é sempre o rótulo
 * textual ao lado, nunca o ícone. É também a regra do projeto de que **cor e
 * ícone nunca são o único sinal**.
 *
 * A segunda é de tamanho. Os glifos são desenhados numa grade óptica, e o eixo
 * `opsz` da fonte ajusta a espessura do traço conforme o tamanho — um ícone de
 * 56px com a espessura de 18px fica frágil. Por isso o `font-variation-settings`
 * acompanha o tamanho em vez de ficar fixo.
 */

const TAMANHOS = {
  xs: 18,
  sm: 22,
  md: 28,
  lg: 40,
  xl: 56,
} as const;

export type TamanhoSym = keyof typeof TAMANHOS;

/* Os glifos que a interface usa, enumerados de propósito.
 *
 * A fonte é servida **subsetada por estes nomes** (MVP-041): pedir um glifo
 * fora desta lista renderiza o nome como texto, porque ele não existe no
 * arquivo. O tipo transforma esse erro silencioso em erro de compilação.
 */
export type GlifoSym =
  | "stethoscope" /* trilha Saúde */
  | "shield" /* trilha Segurança */
  | "female" /* trilha Assédio / Sala Lilás */
  | "info" /* trilha Outros / Ouvidoria */
  | "emergency" /* botão de pânico */
  | "check" /* confirmação */
  | "mic" /* sub-ação "Descrever por voz" */
  | "arrow_back"; /* voltar */

type Props = {
  nome: GlifoSym;
  tamanho?: TamanhoSym;
  cor?: string;
  className?: string;
};

export function Sym({ nome, tamanho = "md", cor, className }: Props) {
  const px = TAMANHOS[tamanho];

  return (
    <span
      className={className}
      /* `aria-hidden` sem exceção. Um `aria-label` aqui leria o ícone *e* o
       * rótulo ao lado, e o leitor de tela anunciaria a mesma coisa duas
       * vezes. */
      aria-hidden="true"
      style={{
        fontFamily: '"Material Symbols Rounded"',
        fontWeight: 400,
        fontSize: px,
        /* Sem isto a ligadura ocupa altura de linha de texto e desalinha o
         * ícone dentro do botão. */
        lineHeight: 1,
        display: "inline-block",
        color: cor,
        /* FILL 0 (contorno, não preenchido) é a escolha do projeto; `opsz`
         * acompanha o tamanho para o traço não afinar nos ícones grandes. */
        fontVariationSettings: `"FILL" 0, "wght" 400, "GRAD" 0, "opsz" ${px}`,
        /* A ligadura precisa que o texto não seja transformado: um
         * `text-transform: uppercase` herdado de um rótulo em caixa-alta
         * transformaria `shield` em `SHIELD`, que não é ligadura nenhuma — e o
         * ícone viraria a palavra escrita na tela. */
        textTransform: "none",
        letterSpacing: "normal",
        whiteSpace: "nowrap",
        fontFeatureSettings: '"liga"',
        /* Sem seleção: o nome do glifo não deve poder ser copiado como texto. */
        userSelect: "none",
      }}
    >
      {nome}
    </span>
  );
}

export const TAMANHOS_SYM = TAMANHOS;
