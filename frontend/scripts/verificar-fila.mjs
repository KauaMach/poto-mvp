/* Verifica a fila offline — MVP-057.
 *
 * O critério é "desligar o backend, acionar 3 trilhas, conferir 3 itens". Isto
 * automatiza a parte que não precisa de navegador: a fila em si, com um
 * `localStorage` de mentira.
 *
 * Os casos que importam não são os do caminho felizes — são os três jeitos como
 * `localStorage` falha de verdade: cota estourada, acesso bloqueado e conteúdo
 * corrompido. Em todos, perder a fila é ruim; **derrubar a tela do totem é
 * pior**, e é isso que se verifica.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;
const dir = join(RAIZ, "node_modules/.cache/poto-verificacao");
mkdirSync(dir, { recursive: true });

const entrada = join(dir, "fila.ts");
writeFileSync(
  entrada,
  `import * as fila from "${RAIZ}src/comum/fila";

  const ev = (id: string, tipo = "seguranca") => ({
    evento_id: id, totem_id: "T1", tipo_ocorrencia: tipo as never,
  });

  const casos: [string, () => boolean][] = [
    ["fila nasce vazia", () => fila.pendentes().length === 0],

    ["enfileira 3 trilhas", () => {
      fila.limpar();
      fila.enfileirar("evento", ev("a", "saude"));
      fila.enfileirar("evento", ev("b", "seguranca"));
      fila.enfileirar("evento", ev("c", "mulher"));
      return fila.quantosPendentes() === 3;
    }],

    ["preserva o evento_id original", () => {
      const ids = fila.pendentes().map((i) => i.corpo.evento_id);
      return JSON.stringify(ids) === JSON.stringify(["a", "b", "c"]);
    }],

    ["ordem é do mais antigo para o mais novo", () => {
      const tipos = fila.pendentes().map((i) => (i.corpo as never as {tipo_ocorrencia: string}).tipo_ocorrencia);
      return JSON.stringify(tipos) === JSON.stringify(["saude", "seguranca", "mulher"]);
    }],

    ["mesmo evento_id não duplica", () => {
      fila.enfileirar("evento", ev("a"));
      return fila.quantosPendentes() === 3;
    }],

    ["remover tira só o item pedido", () => {
      fila.remover("b");
      return JSON.stringify(fila.pendentes().map((i) => i.corpo.evento_id)) ===
        JSON.stringify(["a", "c"]);
    }],

    ["marcarTentativa incrementa", () => {
      fila.marcarTentativa("a");
      fila.marcarTentativa("a");
      return fila.pendentes().find((i) => i.corpo.evento_id === "a")?.tentativas === 2;
    }],

    ["limite descarta o MAIS ANTIGO", () => {
      fila.limpar();
      for (let i = 0; i < fila.FILA_LIMITE + 5; i++) fila.enfileirar("evento", ev(\`e\${i}\`));
      const ids = fila.pendentes().map((i) => i.corpo.evento_id);
      // Entre um pedido de dez dias atrás e um de agora, o de agora é o que
      // ainda pode ser atendido.
      return ids.length === fila.FILA_LIMITE &&
        ids[0] === "e5" && ids[ids.length - 1] === \`e\${fila.FILA_LIMITE + 4}\`;
    }],

    ["persiste o pânico também", () => {
      fila.limpar();
      fila.enfileirar("panico", { evento_id: "p1", totem_id: "T1" });
      return fila.pendentes()[0].tipo === "panico";
    }],

    // --- Os três modos de falha reais de localStorage --------------------
    ["cota estourada não levanta", () => {
      fila.limpar();
      const real = globalThis.localStorage.setItem;
      globalThis.localStorage.setItem = () => {
        const e = new Error("quota"); e.name = "QuotaExceededError"; throw e;
      };
      const ok = fila.enfileirar("evento", ev("x")) === false;
      globalThis.localStorage.setItem = real;
      return ok;
    }],

    ["acesso bloqueado não levanta", () => {
      const real = globalThis.localStorage.getItem;
      globalThis.localStorage.getItem = () => { throw new Error("blocked"); };
      const ok = fila.pendentes().length === 0 && fila.quantosPendentes() === 0;
      globalThis.localStorage.getItem = real;
      return ok;
    }],

    ["conteúdo corrompido não levanta", () => {
      globalThis.localStorage.setItem(fila.FILA_CHAVE, "{isto não é json");
      const a = fila.pendentes().length === 0;
      globalThis.localStorage.setItem(fila.FILA_CHAVE, '{"nao":"array"}');
      const b = fila.pendentes().length === 0;
      globalThis.localStorage.setItem(fila.FILA_CHAVE, '[1, null, "x"]');
      const c = fila.pendentes().length === 0;
      fila.limpar();
      return a && b && c;
    }],

    ["item de forma antiga é descartado, não quebra", () => {
      globalThis.localStorage.setItem(fila.FILA_CHAVE,
        JSON.stringify([{ versao_velha: true }, { tipo: "evento", corpo: { evento_id: "z" } }]));
      const ids = fila.pendentes().map((i) => i.corpo.evento_id);
      fila.limpar();
      return ids.length === 1 && ids[0] === "z";
    }],
  ];

  let falhas = 0;
  for (const [nome, caso] of casos) {
    let ok = false;
    try { ok = caso(); } catch (e) { console.error("  exceção:", e); }
    console.log(\`  \${ok ? "✓" : "✗"} \${nome}\`);
    if (!ok) falhas++;
  }
  if (falhas) { console.error(\`\\n\${falhas} caso(s) falharam\`); process.exit(1); }
  console.log(\`\\nfila: \${casos.length} casos, incluindo os 3 modos de falha de localStorage\`);`,
);

const saida = join(dir, "fila.mjs");
execFileSync(
  join(RAIZ, "node_modules/.bin/rolldown"),
  [entrada, "-o", saida, "--format", "esm", "--platform", "node"],
  { stdio: ["ignore", "ignore", "inherit"] },
);

/* `localStorage` de mentira: o Node não tem um, e jsdom seria uma dependência
 * grande para simular um Map com quota. */
const prelúdio = join(dir, "prelúdio.mjs");
writeFileSync(
  prelúdio,
  `const m = new Map();
   globalThis.localStorage = {
     getItem: (k) => (m.has(k) ? m.get(k) : null),
     setItem: (k, v) => void m.set(k, String(v)),
     removeItem: (k) => void m.delete(k),
   };
   globalThis.window = globalThis;
   await import("${saida}");`,
);

execFileSync(process.execPath, [prelúdio], { stdio: "inherit" });
