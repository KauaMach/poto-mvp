/* Contraste AA de todos os pares de cor em uso — MVP-056.
 *
 * Calculado em vez de conferido no Lighthouse, por duas razões. O Lighthouse só
 * vê o que está renderizado na rota que ele abriu: a tela de alerta ativo, as
 * três variantes do `<Confirm>` e o estado desabilitado do `<Choice>` não
 * aparecem numa passada pela tela inicial. E ele dá uma nota, não uma lista do
 * que está errado.
 *
 * Os pares são declarados à mão porque só quem conhece o design sabe o que é
 * texto (4.5:1), o que é texto grande (3:1) e o que é apenas borda (3:1 como
 * componente de interface). Um script que varresse o CSS não saberia
 * distinguir.
 */

const T = {
  ink: "#17150F",
  muted: "#6F6862",
  faint: "#9A938B",
  line: "#E8E3DD",
  paper: "#FBF9F6",
  bg: "#FFFFFF",
  rust: "#C0392B",
  rustD: "#8F2A17",
  rustSoft: "#F6E7E3",
  ok: "#2F7D4F",
  warn: "#D68A2E",
  branco: "#FFFFFF",
};

/* nome, frente, fundo, mínimo exigido */
const PARES = [
  // Tela inicial
  ["título sobre papel", T.ink, T.paper, 4.5],
  ["rótulo de trilha sobre branco", T.ink, T.bg, 4.5],
  ["status (texto) sobre papel", T.muted, T.paper, 4.5],
  ["ícone de trilha sobre branco", T.rust, T.bg, 3],
  ["ícone 'Outros' sobre branco", T.muted, T.bg, 3],
  ["borda do cartão sobre branco", T.line, T.bg, 1.1],
  ["cartão em hover (ícone)", T.rust, T.rustSoft, 3],
  // Pânico
  ["texto do pânico", T.branco, T.rust, 4.5],
  ["texto do pânico em hover", T.branco, T.rustD, 4.5],
  ["texto do pânico sobre a barra", T.branco, T.rustD, 4.5],
  ["ajuda do pânico sobre papel", T.muted, T.paper, 4.5],
  // Confirmação
  ["mensagem crítica", T.branco, T.rust, 4.5],
  ["protocolo crítico (grande)", T.branco, T.rust, 3],
  ["mensagem padrão", T.ink, T.paper, 4.5],
  ["marca neutra sobre branco", T.muted, T.bg, 3],
  ["aviso offline", T.ink, T.rustSoft, 4.5],
  // Alerta ativo
  ["status do alerta", T.branco, T.rust, 4.5],
  ["cronômetro (grande)", T.branco, T.rust, 3],
  ["botão de escalonar", T.branco, T.rust, 4.5],
  ["escalonar acionado", T.ink, T.branco, 4.5],
  ["✓ de escalonado", T.ok, T.branco, 3],
  // Painel / gravidade
  ["rótulo de risco imediato", T.branco, T.rust, 4.5],
  ["rótulo de aviso", T.ink, T.warn, 4.5],
  ["rótulo de ok", T.branco, T.ok, 4.5],
  // Foco
  ["anel de foco sobre papel", T.rust, T.paper, 3],
  ["anel de foco sobre branco (alerta)", T.branco, T.rust, 3],
];

function luminancia(hex) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = c.map((v) =>
    v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function razao(a, b) {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

const falhas = [];
for (const [nome, frente, fundo, minimo] of PARES) {
  const r = razao(frente, fundo);
  const ok = r >= minimo;
  console.log(
    `  ${ok ? "✓" : "✗"} ${nome.padEnd(38)} ${r.toFixed(2)}:1 (≥ ${minimo})`,
  );
  if (!ok) falhas.push(`${nome}: ${r.toFixed(2)}:1 < ${minimo}`);
}

if (falhas.length) {
  console.error(`\n${falhas.length} par(es) abaixo do mínimo AA:`);
  for (const f of falhas) console.error(`  ${f}`);
  process.exit(1);
}
console.log(`\ncontraste: ${PARES.length} pares em conformidade AA`);
