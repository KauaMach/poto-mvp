/* Tela de confirmação — MVP-047.
 *
 * O que esta tela resolve é uma pergunta só: **"funcionou?"**. Quem acabou de
 * acionar precisa de resposta imediata e inequívoca, porque a alternativa é
 * tocar de novo — e tocar de novo, na trilha errada, vira um segundo chamado.
 *
 * Três variantes, e a diferença entre elas não é estética:
 *
 * - `padrao` — papel, marca em ferrugem, protocolo visível.
 * - `critico` — fundo ferrugem inteiro. É a tela que se lê de três metros de
 *   distância, e o contraste invertido é o que a torna legível de longe.
 * - `neutral` — **sem protocolo**. É a trilha discreta (Assédio / Sala Lilás):
 *   se o agressor está a três metros, um protocolo na tela e a palavra
 *   "denúncia" transformam o socorro em risco. Quem decide isto é o backend,
 *   pelo `instrucao_totem.tela_neutra` — o frontend nunca escolhe ser discreto.
 */
import type { CSSProperties } from "react";
import { Sym } from "./Sym";

export type VarianteConfirm = "padrao" | "critico" | "neutral";

type Props = {
  variante?: VarianteConfirm;
  mensagem: string;
  /** Protocolo. Ignorado na variante `neutral`, que nunca o mostra. */
  protocolo?: string;
  /** Mostra a faixa de aviso quando o evento ficou na fila offline. */
  offline?: boolean;
};

const PALETA: Record<VarianteConfirm, { fundo: string; tinta: string; marca: string }> = {
  padrao: { fundo: "var(--paper)", tinta: "var(--ink)", marca: "var(--rust)" },
  critico: { fundo: "var(--rust)", tinta: "#fff", marca: "#fff" },
  /* A marca em `--muted` e não em ferrugem: nada nesta tela pode chamar
   * atenção de quem olha por cima do ombro. */
  neutral: { fundo: "var(--paper)", tinta: "var(--ink)", marca: "var(--muted)" },
};

const CENTRO: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: "var(--space-lg)",
  textAlign: "center",
  padding: "var(--space-totem) var(--space-lg)",
  minHeight: "100%",
};

export function Confirm({
  variante = "padrao",
  mensagem,
  protocolo,
  offline = false,
}: Props) {
  const { fundo, tinta, marca } = PALETA[variante];
  const mostraProtocolo = variante !== "neutral" && Boolean(protocolo);

  return (
    <section
      /* `role="status"` + `aria-live` fazem o leitor de tela anunciar a
       * confirmação sem que a pessoa precise procurá-la. `polite` porque a tela
       * acabou de trocar e não há nada competindo. */
      role="status"
      aria-live="polite"
      style={{ ...CENTRO, background: fundo, color: tinta }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 96,
          height: 96,
          borderRadius: "var(--r-pill)",
          border: `1.5px solid ${marca}`,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          /* Na variante crítica o círculo branco sobre ferrugem já tem
           * contraste; nas outras um fundo suave separa a marca do papel. */
          background: variante === "critico" ? "transparent" : "var(--bg)",
        }}
      >
        <Sym nome="check" tamanho="xl" cor={marca} />
      </span>

      <h1
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 400,
          /* `clamp` porque a mesma tela roda no tablet de 8,7" e num notebook.
           * Michroma não tem negrito — o tamanho é a hierarquia. */
          fontSize: "clamp(22px, 3.4vw, 32px)",
          lineHeight: 1.15,
          letterSpacing: "-0.01em",
          maxWidth: "28ch",
        }}
      >
        {mensagem}
      </h1>

      {mostraProtocolo && (
        <div>
          <p
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: 13,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              opacity: 0.75,
            }}
          >
            Protocolo
          </p>
          <p
            /* `tabular` porque o protocolo é lido em voz alta para a central e
             * copiado à mão: dígitos de largura variável atrapalham os dois. */
            className="tabular"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 400,
              fontSize: "clamp(20px, 3vw, 28px)",
              letterSpacing: "0.04em",
              marginTop: "var(--space-xs)",
            }}
          >
            {protocolo}
          </p>
        </div>
      )}

      {offline && (
        <p
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: 14,
            /* Faixa em `--rust-soft` até na variante crítica, onde o fundo já é
             * ferrugem: o aviso precisa se destacar do fundo, não combinar. */
            background: "var(--rust-soft)",
            color: "var(--ink)",
            padding: "var(--space-sm) var(--space-md)",
            borderRadius: "var(--r-md)",
            maxWidth: "40ch",
          }}
        >
          Sem conexão agora. Seu pedido está guardado e será enviado
          automaticamente.
        </p>
      )}
    </section>
  );
}
