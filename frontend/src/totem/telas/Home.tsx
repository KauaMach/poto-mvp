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
 */
import { Choice } from "../../componentes/Choice";
import { TRILHAS, type Trilha } from "../trilhas";

type Props = {
  onEscolher: (trilha: Trilha) => void;
  /** Desabilita durante um envio — sem isto dois toques geram dois chamados. */
  enviando?: boolean;
};

export function Home({ onEscolher, enviando = false }: Props) {
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
    </>
  );
}
