/* Contêiner do totem — MVP-050 (tela) / MVP-051 (fluxo).
 *
 * Nesta task ele apenas monta a tela inicial dentro do shell. O fluxo de
 * acionamento — POST, estado de carregamento, confirmação — entra na MVP-051.
 */
import { useOnline } from "../comum/useOnline";
import { Panic, PanicAjuda } from "../componentes/Panic";
import { Shell } from "./Shell";
import { Home } from "./telas/Home";
import type { Trilha } from "./trilhas";

export function Totem() {
  const online = useOnline();

  /* Substituídos pelo fluxo real na MVP-051. */
  const escolher = (trilha: Trilha) => {
    console.info("[totem] trilha escolhida:", trilha.tipo, trilha.modo ?? "normal");
  };
  const panico = () => {
    console.info("[totem] pânico acionado");
  };

  return (
    <Shell
      online={online}
      onInicio={() => window.location.reload()}
      rodape={
        <>
          <Panic onAcionar={panico} />
          <PanicAjuda />
        </>
      }
    >
      <Home onEscolher={escolher} />
    </Shell>
  );
}
