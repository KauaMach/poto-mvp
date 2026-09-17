/* Verifica o mapa de rotas do frontend — MEL-003.
 *
 * O backend serve o mesmo `index.html` para qualquer caminho fora de `/api`, e
 * por isso ele **não sabe** distinguir `/totem` de `/rota-qualquer`. Quem
 * decide qual tela aparece é o `rotaAtual()`, no cliente — então a garantia tem
 * que ser verificada aqui.
 *
 * O que motivou este script: antes da MEL-003, `/totem` respondia com o totem
 * **por acidente** — o `rotaAtual` só checava `/painel` e `/galeria` e devolvia
 * `"totem"` para todo o resto. Um `grep` por `"/totem"` no código não acharia
 * nada, e a rota "funcionava". Um teste que só verificasse `/totem → totem`
 * continuaria passando com a linha explícita removida, porque o fallback cobre.
 *
 * Daí a tabela abaixo incluir os dois lados: o que **tem** que ser cada rota, e
 * o que cai no fallback. A mutação que apaga `if (limpo === CAMINHO_TOTEM)` é
 * pega pelo caso `/totem` com `explicito: true` — ver o final do arquivo.
 *
 * `rotaAtual` recebe o caminho como argumento e não lê `window.location`, então
 * roda direto no Node, sem navegador e sem bundler para a lógica em si. O
 * `rolldown` entra só para apagar os tipos do TypeScript.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;

/* `dev` é o `import.meta.env.DEV` que o `App.tsx` repassa. Os dois valores são
 * testados: em produção a galeria não existe nem digitando a URL (MVP-047). */
const CASOS = [
  // caminho              dev      esperado    explícito?
  ["/totem", false, "totem", true],
  ["/totem/", false, "totem", true],

  /* A sub-ação "Descrever por voz" tem rota própria, para poder ser aberta
   * direto. **A ordem no `rotaAtual` importa**: um `startsWith(CAMINHO_TOTEM)`
   * antes desta linha engoliria `/totem/voz`. O caso `/totem/vozes` abaixo é o
   * inverso — caminho parecido não é a rota de voz. */
  ["/totem/voz", false, "voz", true],
  ["/totem/voz/", false, "voz", true],
  ["/totem/vozes", false, "totem", false],
  ["/painel", false, "painel", true],
  ["/painel/", false, "painel", true],
  ["/painel//", false, "painel", true],

  /* A raiz cai no fallback do totem, e isso é rede de segurança: o redirect de
   * `/` para `/totem` vive no backend, mas se ele falhar ou alguém servir o
   * build sem ele, a tela certa ainda aparece. */
  ["/", false, "totem", false],

  /* Fallback deliberado: num aparelho de corredor, URL digitada errado deve
   * terminar na tela de pedir ajuda, não num 404. */
  ["/rota-inventada", false, "totem", false],
  ["/painelx", false, "totem", false],
  ["/api/v1/health", false, "totem", false],

  /* A galeria só existe em desenvolvimento. */
  ["/galeria", true, "galeria", true],
  ["/galeria", false, "totem", false],
  ["/galeria/", true, "galeria", true],
];

const dir = join(RAIZ, "node_modules/.cache/poto-rotas");
mkdirSync(dir, { recursive: true });

let falhas = 0;
try {
  const entrada = join(dir, "entrada.ts");
  writeFileSync(
    entrada,
    `import { rotaAtual, CAMINHO_TOTEM, CAMINHO_VOZ } from "${RAIZ}src/rotas";
     const casos = ${JSON.stringify(CASOS)};
     const saida = casos.map(([caminho, dev, esperado]) => ({
       caminho, dev, esperado, obtido: rotaAtual(caminho, dev),
     }));
     process.stdout.write(JSON.stringify({
       caminhoTotem: CAMINHO_TOTEM, caminhoVoz: CAMINHO_VOZ, saida,
     }));`,
  );

  const saida = join(dir, "saida.mjs");
  execFileSync(
    join(RAIZ, "node_modules/.bin/rolldown"),
    [entrada, "-o", saida, "--format", "esm", "--platform", "node"],
    { stdio: ["ignore", "ignore", "inherit"] },
  );

  const { caminhoTotem, caminhoVoz, saida: resultados } = JSON.parse(
    execFileSync(process.execPath, [saida], { encoding: "utf8", cwd: RAIZ }),
  );

  for (const r of resultados) {
    const ok = r.obtido === r.esperado;
    if (!ok) falhas += 1;
    const marca = ok ? "✓" : "✗";
    const modo = r.dev ? "dev " : "prod";
    console.log(
      `  ${marca} ${modo} ${r.caminho.padEnd(18)} → ${r.obtido}` +
        (ok ? "" : `   ESPERADO: ${r.esperado}`),
    );
  }

  /* O caminho canônico não pode divergir do que o backend redireciona para.
   * Se alguém mudar um dos dois, o outro fica apontando para o vazio. */
  if (caminhoVoz !== "/totem/voz") {
    falhas += 1;
    console.error(`✗ CAMINHO_VOZ é "${caminhoVoz}", esperado "/totem/voz"`);
  }

  if (caminhoTotem !== "/totem") {
    falhas += 1;
    console.error(
      `✗ CAMINHO_TOTEM é "${caminhoTotem}", mas o redirect do backend ` +
        `(app/main.py) aponta para "/totem"`,
    );
  }

  /* A verificação que pega a mutação que importa.
   *
   * Apagar `if (limpo === CAMINHO_TOTEM) return "totem"` **não** quebra nenhum
   * caso acima — o fallback devolve "totem" de qualquer jeito. O que distingue
   * uma rota explícita de um fallback é o comportamento do *código-fonte*, não
   * da saída: então aqui a asserção é sobre a fonte, e é honesto dizer isso em
   * vez de fingir que a saída prova.
   */
  const fonte = execFileSync("cat", [join(RAIZ, "src/rotas.ts")], {
    encoding: "utf8",
  });
  if (!/if\s*\(\s*limpo\s*===\s*CAMINHO_TOTEM\s*\)/.test(fonte)) {
    falhas += 1;
    console.error(
      '✗ `rotas.ts` não tem a checagem explícita de CAMINHO_TOTEM — o totem\n' +
        "  voltou a ser apenas o fallback, que é exatamente o que a MEL-003\n" +
        "  existe para corrigir (a saída continua igual; só a intenção morreu)",
    );
  }

  if (falhas) {
    console.error(`\n${falhas} verificação(ões) de rota falharam.`);
    process.exit(1);
  }
  console.log(`rotas: ${CASOS.length} casos + caminho canônico + rota explícita`);
} finally {
  rmSync(dir, { recursive: true, force: true });
}
