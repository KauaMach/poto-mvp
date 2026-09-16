/* Lista de chamados do painel — MVP-060.
 *
 * A ordenação — a decisão que importa — vive em `ordenacao.ts`.
 */
import type { Chamado, Dispositivo } from "../comum/tipos";
import { CardChamado } from "./CardChamado";
import { ordenar } from "./ordenacao";

type Props = {
  chamados: Chamado[];
  /** Dispositivos de captura, buscados uma vez pelo painel (MVP-078). */
  dispositivos: Dispositivo[];
  onMudou: (chamado: Chamado) => void;
  /** Prazos de SLA, de `GET /config` (MVP-064). */
  sla?: Record<string, number | null>;
  /** Marcado quando a lista está filtrada, para a mensagem de vazio mudar. */
  filtrado?: boolean;
};

export function ListaChamados({
  chamados,
  onMudou,
  sla,
  dispositivos,
  filtrado,
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
          onMudou={onMudou}
          slaSegundos={sla?.[chamado.gravidade] ?? null}
          dispositivos={dispositivos}
        />
      ))}
    </div>
  );
}
