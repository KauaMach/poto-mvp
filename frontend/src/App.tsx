/**
 * Ponto de entrada da aplicação.
 *
 * Duas rotas, servidas do mesmo build pelo backend:
 *   /totem      → totem   (tela do Galaxy Tab A11)
 *   /totem/voz  → totem, abrindo direto na sub-ação "Descrever por voz"
 *   /painel     → central (notebook/desktop)
 *
 * A raiz (`/`) **redireciona** para `/totem`; o redirect vive no backend, em
 * `app/main.py`. Antes da MEL-003 a raiz *era* o totem e `/totem` funcionava só
 * por acidente do fallback — agora há uma URL canônica só.
 *
 * Mais `/galeria`, que só existe em desenvolvimento (MVP-047).
 *
 * Roteamento manual, sem react-router: são duas rotas estáticas e o kiosk
 * nunca navega entre elas. Uma dependência a mais não se pagaria aqui. A
 * decisão de qual rota é qual está em `rotas.ts`, separada para poder ser
 * verificada sem navegador.
 */

import { lazy, Suspense } from "react";
import { Painel } from "./painel/Painel";
import { rotaAtual } from "./rotas";
import { Totem } from "./totem/Totem";

/* Import dinâmico e guardado por `import.meta.env.DEV`, que é uma constante
 * estática: no build de produção a condição é `false`, o ramo é eliminado e o
 * módulo da galeria **não entra no bundle**. Com um `import` estático no topo
 * ele entrava (medido: +11,7 KB), porque o bundler não descarta um módulo só
 * por o único uso estar atrás de um `if` falso. */
const Galeria = import.meta.env.DEV
  ? lazy(() => import("./Galeria").then((m) => ({ default: m.Galeria })))
  : null;

export function App() {
  const rota = rotaAtual(window.location.pathname, import.meta.env.DEV);
  if (rota === "painel") return <Painel />;
  /* `/totem/voz` monta o mesmo totem, só começando por outra tela — não é uma
   * aplicação separada. */
  if (rota === "voz") return <Totem telaInicial="voz" />;
  if (rota === "galeria" && Galeria) {
    return (
      <Suspense fallback={null}>
        <Galeria />
      </Suspense>
    );
  }
  return <Totem />;
}

