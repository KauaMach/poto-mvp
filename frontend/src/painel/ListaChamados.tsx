/* Lista de chamados do painel — MVP-060, reformada na MEL-009.
 *
 * A ordenação — a decisão que importa — vive em `ordenacao.ts`.
 *
 * A lista deixou de repassar `onMudou` e `dispositivos`: as ações saíram do
 * cartão e foram para o detalhe (ver `CardChamado`). O que a lista faz agora é
 * ordenar, renderizar e dizer qual cartão está aberto.
 */
import type { Chamado } from "../comum/tipos";
import { CardChamado } from "./CardChamado";
import { ordenar } from "./ordenacao";

type Props = {
  chamados: Chamado[];
  /** Prazos de SLA, de `GET /config` (MVP-064). */
  sla?: Record<string, number | null>;
  /** Marcado quando a lista está filtrada, para a mensagem de vazio mudar. */
  filtrado?: boolean;
  onAbrir: (chamado: Chamado) => void;
  /** Protocolo do chamado aberto no detalhe, para destacá-lo na lista. */
  abertoId?: string | null;
};

export function ListaChamados({
  chamados,
  sla,
  filtrado,
  onAbrir,
  abertoId,
}: Props) {
  if (chamados.length === 0) {
    return (
      <p className="poto-vazio">
        {filtrado
          ? "Nenhum chamado corresponde aos filtros."
          : "Nenhum chamado registrado. O painel acende sozinho quando um totem for acionado."}
      </p>
    );
  }

  return (
    <div className="poto-lista">
      {ordenar(chamados).map((chamado) => (
        <CardChamado
          key={chamado.chamado_id}
          chamado={chamado}
          slaSegundos={sla?.[chamado.gravidade] ?? null}
          onAbrir={() => onAbrir(chamado)}
          selecionado={chamado.chamado_id === abertoId}
        />
      ))}
    </div>
  );
}
