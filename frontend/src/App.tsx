/**
 * Ponto de entrada da aplicação.
 *
 * Duas rotas, servidas do mesmo build pelo backend:
 *   /        → totem   (tela do Galaxy Tab A11)
 *   /painel  → central (notebook/desktop)
 *
 * Roteamento manual, sem react-router: são duas rotas estáticas e o kiosk
 * nunca navega entre elas. Uma dependência a mais não se pagaria aqui.
 */

import { lazy, Suspense } from "react";

/* Import dinâmico e guardado por `import.meta.env.DEV`, que é uma constante
 * estática: no build de produção a condição é `false`, o ramo é eliminado e o
 * módulo da galeria **não entra no bundle**. Com um `import` estático no topo
 * ele entrava (medido: +11,7 KB), porque o bundler não descarta um módulo só
 * por o único uso estar atrás de um `if` falso. */
const Galeria = import.meta.env.DEV
  ? lazy(() => import("./Galeria").then((m) => ({ default: m.Galeria })))
  : null;

type Rota = "totem" | "painel" | "galeria";

function rotaAtual(): Rota {
  // Normaliza a barra final: /painel e /painel/ são a mesma rota.
  const caminho = window.location.pathname.replace(/\/+$/, "");
  if (caminho === "/painel") return "painel";
  // `/galeria` só existe em desenvolvimento. `import.meta.env.DEV` é estático,
  // então o bundler remove a rota **e o módulo da galeria** do build de
  // produção — o totem não tem como chegar nela nem por URL digitada.
  if (caminho === "/galeria" && import.meta.env.DEV) return "galeria";
  return "totem";
}

export function App() {
  const rota = rotaAtual();
  if (rota === "painel") return <PainelPlaceholder />;
  if (rota === "galeria" && Galeria) {
    return (
      <Suspense fallback={null}>
        <Galeria />
      </Suspense>
    );
  }
  return <TotemPlaceholder />;
}

// --- Placeholders -----------------------------------------------------------
// Substituídos pelas telas reais nas tasks MVP-049/050 (totem) e MVP-060 (painel).

function TotemPlaceholder() {
  return (
    <main>
      <h1>P.O.T.O — Totem</h1>
      <p>Scaffold ativo. A tela inicial chega na MVP-050.</p>
    </main>
  );
}

function PainelPlaceholder() {
  return (
    <main>
      <h1>P.O.T.O — Painel da central</h1>
      <p>Scaffold ativo. A lista de chamados chega na MVP-060.</p>
    </main>
  );
}
