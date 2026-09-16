/* Roda os casos de `fila.casos.ts` — MVP-057 / MVP-058.
 *
 * O script só empacota e executa; os casos vivem num `.ts` de verdade, porque
 * código dentro de string perde destaque de sintaxe, checagem de tipo e diff
 * legível — e a primeira versão deste arquivo, com os casos embutidos, gerou
 * JavaScript inválido por escaping de template aninhado.
 *
 * `localStorage` é fornecido por um `Map`: o Node não tem um, e jsdom seria uma
 * dependência grande para simular três métodos.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;
const dir = join(RAIZ, "node_modules/.cache/poto-verificacao");
mkdirSync(dir, { recursive: true });

const saida = join(dir, "fila.mjs");
execFileSync(
  join(RAIZ, "node_modules/.bin/rolldown"),
  [join(RAIZ, "scripts/fila.casos.ts"), "-o", saida,
   "--format", "esm", "--platform", "node"],
  { stdio: ["ignore", "ignore", "inherit"] },
);

const entrada = join(dir, "fila.entrada.mjs");
writeFileSync(
  entrada,
  [
    "const m = new Map();",
    "globalThis.localStorage = {",
    "  getItem: (k) => (m.has(k) ? m.get(k) : null),",
    "  setItem: (k, v) => void m.set(k, String(v)),",
    "  removeItem: (k) => void m.delete(k),",
    "};",
    "globalThis.window = globalThis;",
    `await import(${JSON.stringify(saida)});`,
  ].join("\n"),
);

execFileSync(process.execPath, [entrada], { stdio: "inherit" });
