/* "Descrever por voz" — a tela que o blueprint previa e o MVP ainda não entrega.
 *
 * O `DESIGN.md` do projeto de referência traz esta sub-ação no rodapé da tela
 * inicial, entre a grade de trilhas e o pânico. O MVP a deixou de fora porque
 * **voz foi cortada do escopo** (`PLAN.md §3`: STT/Whisper e conversa por voz
 * são P2), e o botão foi acrescentado agora para a tela ficar fiel ao blueprint
 * — **sabendo que ainda não funciona**.
 *
 * Daí esta tela existir e dizer isso, em vez de o botão não levar a lugar
 * nenhum. Três razões, em ordem de importância:
 *
 * 1. **Num totem de emergência, um botão que não responde é pior que um botão
 *    ausente.** Quem toca e não vê nada acontecer conclui que o aparelho
 *    travou — e desiste, em vez de usar as trilhas que funcionam.
 * 2. **A saída tem que estar à vista.** Toda a tela é um caminho de volta: o
 *    texto diz o que fazer em lugar disso, e o botão devolve para as trilhas.
 * 3. Nenhuma promessa de gravação. Não há indicador de "gravando", não há
 *    animação de microfone ativo, nada que sugira que a fala está sendo
 *    captada. Fingir captura numa tela de socorro seria o pior tipo de
 *    engano.
 *
 * Quando a voz entrar no escopo, esta tela é onde o fluxo de gravação nasce —
 * o caminho até ela já existe, e é só o conteúdo que muda.
 */
import { Sym } from "../../componentes/Sym";

type Props = { onVoltar: () => void };

export function Voz({ onVoltar }: Props) {
  return (
    <>
      <h1 className="poto-titulo">Descrever por voz</h1>

      <div className="poto-voz-aviso">
        {/* Decorativo: quem carrega o significado é o texto. */}
        <Sym nome="mic" tamanho="xl" cor="var(--faint)" />
        <p className="poto-voz-texto">
          Esta forma de pedir ajuda <strong>ainda não está disponível</strong>.
        </p>
        <p className="poto-voz-texto poto-voz-secundario">
          Use uma das opções da tela inicial — elas já avisam a central na hora.
          Se for urgente, o botão de pânico funciona sem escolher nada.
        </p>
      </div>

      <button type="button" className="poto-voz-voltar" onClick={onVoltar}>
        <Sym nome="arrow_back" tamanho="sm" cor="#fff" />
        Voltar às opções
      </button>
    </>
  );
}
