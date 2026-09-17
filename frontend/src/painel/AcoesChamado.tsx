/* Ações do operador — extraído do `CardChamado` na MEL-009.
 *
 * Estavam dentro do cartão. Saíram porque o cartão passou a ser **um resumo
 * clicável**: numa lista de vinte, cada cartão tinha botão de reconhecer, um
 * seletor de estado, um seletor de dispositivo de mídia e uma videochamada —
 * quatro controles competindo com o dado que o operador precisa ler de relance.
 *
 * Agora vivem no detalhe, onde há largura. O cartão fica com o que se lê num
 * relance; o detalhe, com o que se faz.
 */
import { useCallback, useState } from "react";
import { ackChamado, atualizarChamado } from "../comum/api";
import type { Chamado, StatusChamado } from "../comum/tipos";
import { Sym } from "../componentes/Sym";
import { ABERTOS } from "./rotulos";

/* Estados que o operador escolhe no seletor.
 *
 * `reconhecido` **não** está aqui, e a omissão é deliberada: ele vem do botão
 * "Reconhecer", que grava também o `acked_at` de onde sai a métrica de tempo
 * até o reconhecimento. Oferecê-lo no seletor daria dois caminhos para a mesma
 * transição, e um deles não pararia o relógio do SLA.
 *
 * `cancelado` também fica fora: marcar um pedido de socorro como trote é uma
 * decisão que merece mais atrito que um item de lista suspensa.
 */
const TRANSICOES: { valor: StatusChamado; rotulo: string }[] = [
  { valor: "em_atendimento", rotulo: "Em atendimento" },
  { valor: "encerrado", rotulo: "Encerrado" },
];

type Props = {
  chamado: Chamado;
  onMudou: (chamado: Chamado) => void;
};

export function AcoesChamado({ chamado, onMudou }: Props) {
  const [ocupado, setOcupado] = useState(false);
  const aberto = ABERTOS.has(chamado.status);

  const agir = useCallback(
    async (acao: () => Promise<Chamado>) => {
      /* Trava antes de qualquer `await`: dois cliques rápidos no "Reconhecer"
       * mandariam dois POST. O segundo é inofensivo — o backend preserva o
       * `acked_at` original (MVP-033) — mas a tela piscaria duas vezes. */
      setOcupado(true);
      try {
        onMudou(await acao());
      } catch {
        /* Mantém o estado como está. Se a ação chegou, o WebSocket corrige
         * sozinho (MVP-062); se não chegou, o operador tenta de novo. Um alerta
         * de erro aqui seria uma caixa para fechar no meio de uma emergência. */
      } finally {
        setOcupado(false);
      }
    },
    [onMudou],
  );

  const podeMudarEstado =
    aberto ||
    chamado.status === "reconhecido" ||
    chamado.status === "em_atendimento";

  return (
    <div className="poto-acoes">
      {/* Some depois do sucesso porque desaparece a condição que o traz:
          `acked_at` deixa de ser nulo. Não há estado de "já cliquei" a
          manter — o dado é a fonte. */}
      {aberto && chamado.acked_at === null && (
        <button
          type="button"
          className="poto-botao-primario"
          disabled={ocupado}
          onClick={() => void agir(() => ackChamado(chamado.chamado_id))}
        >
          <Sym nome="check" tamanho="sm" cor="#fff" />
          Reconhecer
        </button>
      )}

      {podeMudarEstado && (
        <label className="poto-seletor">
          <span className="visually-hidden">
            Mudar estado de {chamado.chamado_id}
          </span>
          {/* Valor fixo em "" e não controlado pelo status: o seletor é um
              disparador de ação, não um espelho do estado. Mostrar o estado
              atual ali convidaria o operador a "voltar" mudando a seleção. */}
          <select
            value=""
            disabled={ocupado}
            onChange={(e) => {
              const destino = e.target.value as StatusChamado;
              if (destino) {
                void agir(() =>
                  atualizarChamado(chamado.chamado_id, { status: destino }),
                );
              }
            }}
          >
            <option value="">Mudar estado…</option>
            {TRANSICOES.filter((t) => t.valor !== chamado.status).map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
