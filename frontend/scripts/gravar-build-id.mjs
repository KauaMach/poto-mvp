/* Grava o build-id dentro de `dist/` — MVP-066b.
 *
 * O build-id é a mitigação do único risco real de separar build e execução
 * (ARCHITECTURE.md D1c): **artefato velho**. Alterar o código, esquecer de
 * reconstruir e enviar a versão antiga é um bug silencioso — a tela parece
 * certa, o comportamento é o de ontem, e a depuração começa procurando no
 * lugar errado.
 *
 * O identificador é um **hash do conteúdo do próprio `dist/`**, não a data nem
 * o commit. A diferença importa:
 *
 * - data mudaria a cada build mesmo sem nenhuma alteração, e um identificador
 *   que sempre muda não distingue nada;
 * - o hash do commit não veria alterações não commitadas, que é exatamente o
 *   estado de quem está testando algo na Pi.
 *
 * Fica **dentro** de `dist/` porque o deploy envia essa pasta por rsync. Um
 * build-id ao lado dela não viajaria com o artefato, e daria para ter um
 * `dist/` velho servindo com build-id novo — precisamente o engano que ele
 * existe para detectar. (Correção ao plano original, feita na MVP-036.)
 */
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const DIST = new URL("../dist/", import.meta.url).pathname;
const ARQUIVO = "build-id";

/** Todos os arquivos de `dist/`, em ordem estável. */
function arquivos(dir) {
  return readdirSync(dir, { withFileTypes: true })
    .flatMap((e) => {
      const caminho = join(dir, e.name);
      if (e.isDirectory()) return arquivos(caminho);
      /* O próprio build-id fica fora do hash: incluí-lo o faria depender de si
       * mesmo e mudar a cada execução. */
      return relative(DIST, caminho) === ARQUIVO ? [] : [caminho];
    })
    .sort();
}

const hash = createHash("sha256");
for (const caminho of arquivos(DIST)) {
  /* O **nome** entra no hash junto com o conteúdo: sem ele, renomear um
   * arquivo sem mudar bytes daria o mesmo build-id — e o Vite renomeia os
   * bundles por hash de conteúdo, então o nome carrega informação. */
  hash.update(relative(DIST, caminho));
  hash.update(readFileSync(caminho));
}

/* 12 caracteres: o suficiente para não colidir na prática e curto o bastante
 * para alguém comparar dois de olho, que é como o build-id é usado — `/health`
 * da Pi contra a saída deste script. */
const id = hash.digest("hex").slice(0, 12);
writeFileSync(join(DIST, ARQUIVO), `${id}\n`, "utf8");

const total = arquivos(DIST).reduce((n, c) => n + statSync(c).size, 0);
console.log(`build-id ${id}  (${arquivos(DIST).length} arquivos, ${(total / 1024).toFixed(0)} KB)`);
