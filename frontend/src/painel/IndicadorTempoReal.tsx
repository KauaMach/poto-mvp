/* Indicador de tempo real do painel — MVP-062. */
import { COR_WS, ROTULO_WS } from "../comum/ws";
import type { EstadoWS } from "../comum/useEventosWS";

export function IndicadorTempoReal({ estado }: { estado: EstadoWS }) {
  return (
    <span
      className="poto-tempo-real"
      /* `polite`: a perda de conexão é contexto. Interromper a leitura de um
       * chamado para anunciar "reconectando" seria pior que esperar a pausa. */
      aria-live="polite"
      style={{ color: COR_WS[estado] }}
    >
      <span
        aria-hidden="true"
        className={
          estado === "aberto" ? "poto-ponto poto-ponto-vivo" : "poto-ponto"
        }
      />
      {ROTULO_WS[estado]}
    </span>
  );
}
