/* Confere os prazos de retorno automático contra TASKS.md (MVP-052).
 *
 * Mesmo princípio do `verificar-tokens.mjs`: os números vivem no documento e o
 * script lê de lá em vez de duplicá-los. Um prazo que derive — alguém
 * "arredondando" os 12 s do crítico para 8 — passaria despercebido, e é
 * justamente o crítico que precisa dos 12: o protocolo tem que ser lido e
 * anotado, possivelmente por quem está com a mão tremendo.
 */
import { readFileSync } from "node:fs";

const RAIZ = new URL("..", import.meta.url).pathname;

/* A fonte é a linha de critério da MVP-052:
 *   - **5 s** discreto · **12 s** crítico · **9 s** demais              */
const tasks = readFileSync(`${RAIZ}../TASKS.md`, "utf8");
const linha = tasks.match(
  /\*\*(\d+) s\*\* discreto · \*\*(\d+) s\*\* crítico · \*\*(\d+) s\*\* demais/,
);
if (!linha) {
  console.error("MVP-052: linha de prazos não encontrada em TASKS.md");
  process.exit(1);
}
const esperado = {
  discreto: Number(linha[1]) * 1000,
  critico: Number(linha[2]) * 1000,
  padrao: Number(linha[3]) * 1000,
};

/* Lê a tabela do componente sem executá-lo: importar o .tsx exigiria um
 * bundler, e o objetivo aqui é só comparar números. */
const fonte = readFileSync(
  `${RAIZ}src/totem/telas/retorno.ts`,
  "utf8",
);
const bloco = fonte.match(/export const RETORNO_MS = \{([\s\S]*?)\} as const;/);
if (!bloco) {
  console.error("RETORNO_MS não encontrado em retorno.ts");
  process.exit(1);
}
const nosso = Object.fromEntries(
  [...bloco[1].matchAll(/(\w+):\s*(\d+)/g)].map(([, k, v]) => [k, Number(v)]),
);

const problemas = [];
for (const [chave, ms] of Object.entries(esperado)) {
  if (nosso[chave] !== ms) {
    problemas.push(`${chave}: ${nosso[chave]}ms != ${ms}ms (TASKS.md MVP-052)`);
  }
}
if (problemas.length) {
  console.error("prazos de retorno divergentes:");
  for (const p of problemas) console.error(`  ${p}`);
  process.exit(1);
}
console.log(
  `prazos: discreto ${esperado.discreto}ms · crítico ${esperado.critico}ms · ` +
    `demais ${esperado.padrao}ms conferem com TASKS.md`,
);
