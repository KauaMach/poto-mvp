/* Cartão de chamado — MVP-060 (esqueleto).
 *
 * Esta versão existe para a lista compilar e ser verificável. A leitura em um
 * relance — borda de gravidade, chip, relato — é a MVP-061; as ações do
 * operador são a MVP-063; o contador de SLA é a MVP-064.
 */
import type { Chamado } from "../comum/tipos";
import { ROTULO_STATUS, TITULO_TIPO } from "./rotulos";

type Props = {
  chamado: Chamado;
  onMudou: (chamado: Chamado) => void;
  /** Prazo da gravidade deste chamado, ou `null` se não escalona (MVP-064). */
  slaSegundos: number | null;
};

export function CardChamado({ chamado }: Props) {
  return (
    <article className="poto-card">
      <header className="poto-card-topo">
        <span className="poto-protocolo tabular">{chamado.chamado_id}</span>
      </header>

      <h2 className="poto-card-titulo">{TITULO_TIPO[chamado.tipo_ocorrencia]}</h2>

      <p className="poto-card-linha">
        <span className="poto-card-rotulo">Totem</span>
        {chamado.totem_id}
      </p>

      <footer className="poto-card-rodape">
        <span className="poto-status">{ROTULO_STATUS[chamado.status]}</span>
      </footer>
    </article>
  );
}
