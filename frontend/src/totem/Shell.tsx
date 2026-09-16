/* Shell do totem — as três zonas de DESIGN.md §12 (MVP-049).
 *
 *   header   wordmark à esquerda, status à direita
 *   main     flex: 1, centralizado nos dois eixos
 *   footer   margin-top: auto
 *
 * O `main` centralizado nos dois eixos é o que faz a tela funcionar num tablet
 * de parede: o conteúdo fica na altura dos olhos e das mãos, não no topo. E o
 * `footer` empurrado por `margin-top: auto` mantém o botão de pânico sempre no
 * mesmo lugar — quem precisa dele não deve ter que procurar onde ele foi parar
 * nesta tela.
 *
 * `100dvh` e não `100vh`: no Chrome do Android a barra de endereço entra e sai,
 * e `100vh` usa a altura *sem* ela — o rodapé ficaria abaixo da borda visível
 * justamente enquanto a barra está presente.
 */
import type { ReactNode } from "react";
import { StatusPill } from "../componentes/StatusPill";
import { Wordmark } from "../componentes/Wordmark";

type Props = {
  children: ReactNode;
  rodape?: ReactNode;
  online: boolean;
  naFila?: number;
  onInicio?: () => void;
  /** Fundo alternativo — a tela de alerta ativo é ferrugem inteira. */
  fundo?: string;
  /** Oculta header e rodapé. O alerta ativo ocupa a tela toda. */
  semCromo?: boolean;
};

export function Shell({
  children,
  rodape,
  online,
  naFila = 0,
  onInicio,
  fundo,
  semCromo = false,
}: Props) {
  return (
    <div
      className="poto-shell"
      style={fundo ? { background: fundo } : undefined}
    >
      <div className="poto-shell-interno">
        {!semCromo && (
          <header className="poto-header">
            <Wordmark onInicio={onInicio} />
            <StatusPill online={online} naFila={naFila} />
          </header>
        )}

        <main className="poto-main">{children}</main>

        {!semCromo && rodape && <footer className="poto-footer">{rodape}</footer>}
      </div>
    </div>
  );
}
