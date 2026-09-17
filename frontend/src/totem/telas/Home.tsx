/* Tela inicial — "Como podemos ajudar?" (MVP-050).
 *
 * Todo o fluxo principal em **dois toques**: um na trilha, e a confirmação já
 * aparece. Não há tela intermediária de detalhamento, não há "tem certeza?",
 * não há formulário. O texto livre existe no contrato do backend e é opcional
 * de propósito — quem está em emergência não digita.
 *
 * O pânico fica no rodapé e é o único elemento em ferrugem cheia da tela, pela
 * regra 60/30/10. Ele não é uma quinta trilha: é o caminho para quem não
 * consegue nem escolher.
 *
 * Abaixo da grade vem **"Descrever por voz"**, a sub-ação que o blueprint de
 * design previa (`DESIGN.md §12`) e que o MVP não tinha. Ela é deliberadamente
 * discreta — ícone contornado, texto em `--muted`, sem preenchimento: é uma
 * alternativa, não uma quinta opção competindo com as quatro trilhas. Quem está
 * em emergência deve tocar numa trilha; quem não sabe qual escolher pode falar.
 *
 * **Ela ainda não funciona**, e a tela de destino diz isso (`telas/Voz.tsx`).
 * Voz está fora do escopo do MVP (`PLAN.md §3`).
 */
import { Choice } from "../../componentes/Choice";
import { Sym } from "../../componentes/Sym";
import { TRILHAS, type Trilha } from "../trilhas";

type Props = {
  onEscolher: (trilha: Trilha) => void;
  onDescreverPorVoz: () => void;
  /** Desabilita durante um envio — sem isto dois toques geram dois chamados. */
  enviando?: boolean;
};

export function Home({ onEscolher, onDescreverPorVoz, enviando = false }: Props) {
  return (
    <>
      <h1 className="poto-titulo">Como podemos ajudar?</h1>

      {/* `role="group"` com rótulo: o leitor de tela anuncia "grupo, escolha o
          tipo de atendimento, 4 itens" antes do primeiro botão, o que dá o
          contexto que a grade visual dá pelo arranjo. */}
      <div
        className="poto-grid"
        role="group"
        aria-label="Escolha o tipo de atendimento"
      >
        {TRILHAS.map((trilha) => (
          <Choice
            key={trilha.tipo}
            icone={trilha.icone}
            rotulo={trilha.rotulo}
            variante={trilha.variante}
            descricao={trilha.descricao}
            desabilitado={enviando}
            onClick={() => onEscolher(trilha)}
          />
        ))}
      </div>

      {/* A sub-ação do blueprint. `aria-label` **contém** o texto visível
          (WCAG 2.5.3): quem usa controle por voz diz "descrever por voz" e o
          comando precisa casar com o rótulo lido. */}
      <button
        type="button"
        className="poto-voz-acao"
        disabled={enviando}
        onClick={onDescreverPorVoz}
        aria-label="Descrever por voz — ainda não disponível"
      >
        <span aria-hidden="true" className="poto-voz-circulo">
          <Sym nome="mic" tamanho="md" cor="var(--rust)" />
        </span>
        Descrever por voz
      </button>
    </>
  );
}
