/* Verifica que a tela discreta não deixa rastro — MVP-053.
 *
 * O critério da task é "inspecionar o DOM — nenhuma dessas palavras presente".
 * Automatizado, porque esta é a propriedade mais crítica da interface: se o
 * agressor está a três metros, uma palavra errada na tela transforma o socorro
 * em risco. Uma inspeção manual protege o dia em que foi feita; um script
 * protege todos os dias depois.
 *
 * O que se verifica é o **HTML de verdade**: o componente é renderizado com
 * `react-dom/server` a partir de uma resposta real do backend, e o resultado é
 * varrido por palavra proibida. Checar o código-fonte em vez do resultado
 * deixaria passar a palavra chegando por um caminho indireto — uma mensagem
 * vinda da API, um rótulo herdado, um `aria-label`.
 *
 * `rolldown` já vem com o Vite 8, então não há dependência nova.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;

/* Palavras que não podem aparecer na tela discreta.
 *
 * As três primeiras são as do critério. `CALL-` cobre o protocolo, que a
 * variante recebe e **não** deve mostrar. `csv` e `180` cobrem o canal
 * acionado chegando por acidente.
 */
const PROIBIDAS = [
  "Sala Lilás",
  "Lilás",
  "denúncia",
  "denuncia",
  "assédio",
  "assedio",
  "CALL-",
  "sala_lilas",
  "central_180",
];

/* Resposta real do backend para a trilha `mulher`, capturada da suíte de
 * contrato (MVP-039). Fixa aqui de propósito: o script não deve depender de um
 * backend rodando para verificar uma propriedade da interface.
 */
const RESPOSTA = {
  chamado_id: "CALL-2026-000044",
  status: "notificado",
  canal_roteado: "central_180",
  gravidade: "risco_potencial",
  instrucao_totem: {
    mensagem_tela: "Seu pedido foi registrado. Aguarde atendimento.",
    feedback_sonoro: false,
    tela_neutra: true,
  },
  duplicado: false,
};

/* Dentro de `node_modules/.cache` e não em `/tmp`: a resolução de módulos do
 * Node parte da localização do **arquivo**, não do diretório de trabalho, e um
 * bundle em `/tmp` não acharia `react-dom`. */
const dir = join(RAIZ, "node_modules/.cache/poto-verificacao");
mkdirSync(dir, { recursive: true });
try {
  const entrada = join(dir, "entrada.tsx");
  writeFileSync(
    entrada,
    `import { renderToStaticMarkup } from "react-dom/server";
     import { Confirm } from "${RAIZ}src/componentes/Confirm";
     const r = ${JSON.stringify(RESPOSTA)};
     process.stdout.write(renderToStaticMarkup(
       <Confirm
         variante="neutral"
         mensagem={r.instrucao_totem.mensagem_tela}
         protocolo={r.chamado_id}
       />
     ));`,
  );

  const saida = join(dir, "saida.mjs");
  execFileSync(
    join(RAIZ, "node_modules/.bin/rolldown"),
    [entrada, "-o", saida, "--format", "esm", "--platform", "node",
     "--external", "react", "--external", "react-dom",
     "--external", "react/jsx-runtime"],
    { stdio: ["ignore", "ignore", "inherit"] },
  );

  const html = execFileSync(process.execPath, [saida], {
    encoding: "utf8",
    cwd: RAIZ,
  });

  const vazadas = PROIBIDAS.filter((p) =>
    html.toLowerCase().includes(p.toLowerCase()),
  );

  if (vazadas.length) {
    console.error("tela discreta vazou informação:");
    for (const p of vazadas) console.error(`  "${p}"`);
    console.error(`\nHTML:\n${html}`);
    process.exit(1);
  }

  /* A verificação inversa: se o HTML não contivesse **nada**, o teste passaria
   * de graça. A mensagem genérica precisa estar lá. */
  if (!html.includes("Seu pedido foi registrado")) {
    console.error("a tela discreta não renderizou a mensagem genérica —");
    console.error("a ausência das palavras proibidas não prova nada aqui.");
    process.exit(1);
  }

  console.log(
    `tela discreta: ${PROIBIDAS.length} termos proibidos ausentes, ` +
      "mensagem genérica presente",
  );
} finally {
  rmSync(dir, { recursive: true, force: true });
}
