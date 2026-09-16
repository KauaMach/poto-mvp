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

type Rota = "totem" | "painel";

function rotaAtual(): Rota {
  // Normaliza a barra final: /painel e /painel/ são a mesma rota.
  const caminho = window.location.pathname.replace(/\/+$/, "");
  return caminho === "/painel" ? "painel" : "totem";
}

export function App() {
  const rota = rotaAtual();
  return rota === "painel" ? <PainelPlaceholder /> : <TotemPlaceholder />;
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
