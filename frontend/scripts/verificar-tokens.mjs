/* Confere `tokens.css` contra PLAN.md §6, valor a valor — MVP-042.
 *
 * O critério da task é literalmente "comparar valor a valor". Fazer isso à mão
 * uma vez não protege nada: o risco real é a **deriva**, alguém ajustando um
 * hex meses depois e a interface deixando de ser a identidade aprovada sem que
 * ninguém note.
 *
 * O PLAN.md é lido como fonte da verdade em vez de os valores serem copiados
 * para dentro deste script. Uma cópia teria o mesmo problema que ela existe
 * para resolver.
 *
 * Sem dependência nova: o projeto não tem — nem planeja — runner de teste no
 * frontend, e acrescentar um por causa de 30 linhas seria desproporcional.
 */
import { readFileSync } from "node:fs";

const RAIZ = new URL("..", import.meta.url).pathname;

/** Normaliza um valor CSS para comparação **semântica**, não textual.
 *
 * `rgba(20,15,5,.05)` e `rgba(20, 15, 5, 0.05)` são a mesma cor para o
 * navegador, e travar nessa diferença faria o script cobrar a formatação do
 * documento em vez da identidade visual — o que ele existe para proteger.
 *
 * A normalização é deliberadamente pequena: espaço, caixa, e zero à esquerda
 * de decimal. Nada além disso, para que uma divergência de valor continue
 * sendo divergência.
 */
function normalizar(valor) {
  return valor
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/\s*,\s*/g, ",")
    .replace(/(^|[\s,(])0\.(\d)/g, "$1.$2");
}

/** Extrai `--nome: valor` de um texto CSS. */
function extrairTokens(texto) {
  const tokens = new Map();
  for (const [, nome, valor] of texto.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    tokens.set(nome, normalizar(valor));
  }
  return tokens;
}

const plano = readFileSync(`${RAIZ}../PLAN.md`, "utf8");
const secao = plano.match(/## 6\. Identidade visual[\s\S]*?```css([\s\S]*?)```/);
if (!secao) {
  console.error("PLAN.md §6 não encontrada — o bloco css canônico sumiu?");
  process.exit(1);
}

const canonicos = extrairTokens(secao[1]);
const nossos = extrairTokens(readFileSync(`${RAIZ}src/estilos/tokens.css`, "utf8"));

const problemas = [];
for (const [nome, esperado] of canonicos) {
  const nosso = nossos.get(nome);
  if (nosso === undefined) problemas.push(`${nome}: ausente em tokens.css`);
  else if (nosso !== esperado) {
    problemas.push(`${nome}: "${nosso}" != "${esperado}" (PLAN.md §6)`);
  }
}

if (problemas.length) {
  console.error(`tokens divergentes de PLAN.md §6 (${problemas.length}):`);
  for (const p of problemas) console.error(`  ${p}`);
  process.exit(1);
}
console.log(`tokens: ${canonicos.size} valores conferem com PLAN.md §6`);
