/* Indicador de conectividade — MVP-044.
 *
 * Um ponto de 8px: verde online, ferrugem offline. Discreto de propósito — a
 * tela inicial não é lugar para alarmar sobre rede quando o sistema **continua
 * funcionando offline** (a fila da MVP-057 guarda o acionamento e drena
 * depois).
 *
 * O que o ponto realmente comunica não é "tem internet": é **"o que você tocar
 * chega agora ou fica guardado"**. Daí o contador `· N na fila`, que é a única
 * informação acionável aqui.
 *
 * Cor não é o único sinal: o texto ao lado diz "Offline" e o `aria-live`
 * anuncia a mudança. 8% dos homens têm alguma deficiência na percepção de
 * vermelho e verde, e este é um sistema de emergência.
 */

type Props = {
  online: boolean;
  /** Eventos aguardando dreno. Vem da fila offline (MVP-057). */
  naFila?: number;
};

export function StatusPill({ online, naFila = 0 }: Props) {
  const cor = online ? "var(--ok)" : "var(--rust)";
  const rotulo = online ? "Online" : "Offline";

  return (
    <span
      /* `polite` e não `assertive`: a mudança de conectividade é contexto, e
       * interromper o leitor de tela no meio de uma trilha de socorro para
       * anunciar "offline" seria pior do que esperar a pausa. */
      aria-live="polite"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-xs)",
        fontFamily: "var(--font-ui)",
        fontSize: 13,
        color: "var(--muted)",
        whiteSpace: "nowrap",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: "var(--r-pill)",
          background: cor,
          /* O ponto não pode encolher quando o texto ao lado cresce com o
           * contador da fila. */
          flex: "0 0 auto",
        }}
      />
      {rotulo}
      {naFila > 0 && (
        <span className="tabular" style={{ color: "var(--rust)" }}>
          {" · "}
          {naFila} na fila
        </span>
      )}
    </span>
  );
}
