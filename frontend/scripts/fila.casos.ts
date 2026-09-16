/* Casos de verificação da fila offline — MVP-057 / MVP-058.
 *
 * Arquivo `.ts` de verdade, não string dentro de script: o conteúdo é código e
 * precisa de destaque de sintaxe, checagem de tipo e diff legível.
 *
 * Os casos que importam não são os do caminho felizes. São os três modos como
 * `localStorage` falha de verdade — cota, bloqueio, corrupção — e o
 * comportamento do dreno sob falha, que é onde uma fila mal feita perde
 * pedidos ou entope.
 *
 * Rodado por `scripts/verificar-fila.mjs`, que empacota com rolldown e fornece
 * um `localStorage` de mentira.
 */
import * as fila from "../src/comum/fila";
import type { EventoIn } from "../src/comum/tipos";

const ev = (id: string, tipo = "seguranca"): EventoIn => ({
  evento_id: id,
  totem_id: "T1",
  tipo_ocorrencia: tipo as EventoIn["tipo_ocorrencia"],
});

const armazenamento = () => globalThis.localStorage;

function erroRede(): never {
  const e = new Error("rede");
  e.name = "ErroRede";
  throw e;
}

function erroApi(): never {
  const e = new Error("422");
  e.name = "ErroApi";
  throw e;
}

// --- Fila (MVP-057) --------------------------------------------------------

const sincronos: [string, () => boolean][] = [
  ["fila nasce vazia", () => {
    fila.limpar();
    return fila.pendentes().length === 0;
  }],

  ["enfileira 3 trilhas", () => {
    fila.limpar();
    fila.enfileirar("evento", ev("a", "saude"));
    fila.enfileirar("evento", ev("b", "seguranca"));
    fila.enfileirar("evento", ev("c", "mulher"));
    return fila.quantosPendentes() === 3;
  }],

  ["preserva o evento_id original", () => {
    const ids = fila.pendentes().map((i) => i.corpo.evento_id);
    return ids.join(",") === "a,b,c";
  }],

  ["ordem é do mais antigo para o mais novo", () => {
    const tipos = fila
      .pendentes()
      .map((i) => (i.corpo as EventoIn).tipo_ocorrencia);
    return tipos.join(",") === "saude,seguranca,mulher";
  }],

  ["mesmo evento_id não duplica", () => {
    fila.enfileirar("evento", ev("a"));
    return fila.quantosPendentes() === 3;
  }],

  ["remover tira só o item pedido", () => {
    fila.remover("b");
    return fila.pendentes().map((i) => i.corpo.evento_id).join(",") === "a,c";
  }],

  ["marcarTentativa incrementa", () => {
    fila.marcarTentativa("a");
    fila.marcarTentativa("a");
    return fila.pendentes().find((i) => i.corpo.evento_id === "a")?.tentativas === 2;
  }],

  ["limite descarta o MAIS ANTIGO", () => {
    // Entre um pedido de dez dias atrás e um de agora, o de agora é o que
    // ainda pode ser atendido.
    fila.limpar();
    for (let i = 0; i < fila.FILA_LIMITE + 5; i++) {
      fila.enfileirar("evento", ev(`e${i}`));
    }
    const ids = fila.pendentes().map((i) => i.corpo.evento_id);
    return (
      ids.length === fila.FILA_LIMITE &&
      ids[0] === "e5" &&
      ids[ids.length - 1] === `e${fila.FILA_LIMITE + 4}`
    );
  }],

  ["persiste o pânico também", () => {
    fila.limpar();
    fila.enfileirar("panico", { evento_id: "p1", totem_id: "T1" });
    return fila.pendentes()[0].tipo === "panico";
  }],

  // Os três modos de falha reais de localStorage.
  ["cota estourada não levanta", () => {
    fila.limpar();
    const real = armazenamento().setItem;
    armazenamento().setItem = () => {
      const e = new Error("quota");
      e.name = "QuotaExceededError";
      throw e;
    };
    const ok = fila.enfileirar("evento", ev("x")) === false;
    armazenamento().setItem = real;
    return ok;
  }],

  ["acesso bloqueado não levanta", () => {
    const real = armazenamento().getItem;
    armazenamento().getItem = () => {
      throw new Error("blocked");
    };
    const ok = fila.pendentes().length === 0 && fila.quantosPendentes() === 0;
    armazenamento().getItem = real;
    return ok;
  }],

  ["conteúdo corrompido não levanta", () => {
    const casos = ['{isto não é json', '{"nao":"array"}', '[1, null, "x"]'];
    const ok = casos.every((v) => {
      armazenamento().setItem(fila.FILA_CHAVE, v);
      return fila.pendentes().length === 0;
    });
    fila.limpar();
    return ok;
  }],

  ["item de forma antiga é descartado, não quebra", () => {
    armazenamento().setItem(
      fila.FILA_CHAVE,
      JSON.stringify([
        { versao_velha: true },
        { tipo: "evento", corpo: { evento_id: "z" } },
      ]),
    );
    const ids = fila.pendentes().map((i) => i.corpo.evento_id);
    fila.limpar();
    return ids.length === 1 && ids[0] === "z";
  }],
];

// --- Dreno (MVP-058) -------------------------------------------------------

const assincronos: [string, () => Promise<boolean>][] = [
  ["dreno esvazia a fila em caso de sucesso", async () => {
    fila.limpar();
    fila.enfileirar("evento", ev("a"));
    fila.enfileirar("evento", ev("b"));
    const r = await fila.drenar(async () => {}, async () => {});
    return r.enviados === 2 && r.restantes === 0 && !r.interrompido;
  }],

  ["item enviado sai; o que falhou fica", async () => {
    fila.limpar();
    fila.enfileirar("evento", ev("a"));
    fila.enfileirar("evento", ev("b"));
    let n = 0;
    const r = await fila.drenar(
      async () => {
        if (++n === 2) erroRede();
      },
      async () => {},
    );
    const ids = fila.pendentes().map((i) => i.corpo.evento_id);
    return r.enviados === 1 && r.interrompido && ids.join(",") === "b";
  }],

  ["dreno é SERIAL, não paralelo", async () => {
    // 50 itens em paralelo abrem 50 conexões de um totem que acabou de
    // recuperar uma rede instável, e a primeira coisa que acontece é a rede
    // cair de novo.
    fila.limpar();
    for (let i = 0; i < 5; i++) fila.enfileirar("evento", ev(`s${i}`));
    let simultaneos = 0;
    let pico = 0;
    await fila.drenar(
      async () => {
        pico = Math.max(pico, ++simultaneos);
        await new Promise((r) => setTimeout(r, 1));
        simultaneos--;
      },
      async () => {},
    );
    return pico === 1;
  }],

  ["falha de rede PARA o dreno, não insiste item a item", async () => {
    fila.limpar();
    for (let i = 0; i < 5; i++) fila.enfileirar("evento", ev(`f${i}`));
    let tentativas = 0;
    const r = await fila.drenar(
      async () => {
        tentativas++;
        erroRede();
      },
      async () => {},
    );
    // Se o primeiro não passou, o próximo também não vai.
    return tentativas === 1 && r.enviados === 0 && r.restantes === 5;
  }],

  ["ErroApi DESCARTA o item e segue", async () => {
    // Um payload recusado travaria a fila para sempre, bloqueando os pedidos
    // atrás dele — que podem ser válidos.
    fila.limpar();
    fila.enfileirar("evento", ev("ruim"));
    fila.enfileirar("evento", ev("bom"));
    let n = 0;
    const r = await fila.drenar(
      async () => {
        if (++n === 1) erroApi();
      },
      async () => {},
    );
    return r.enviados === 1 && r.restantes === 0;
  }],

  ["dreno concorrente não envia duas vezes", async () => {
    // O timer de 15 s e o evento `online` podem disparar juntos.
    fila.limpar();
    fila.enfileirar("evento", ev("a"));
    let envios = 0;
    const lento = async () => {
      envios++;
      await new Promise((r) => setTimeout(r, 5));
    };
    await Promise.all([
      fila.drenar(lento, async () => {}),
      fila.drenar(lento, async () => {}),
    ]);
    return envios === 1;
  }],

  ["acionamento novo durante o dreno também é enviado", async () => {
    fila.limpar();
    fila.enfileirar("evento", ev("a"));
    let n = 0;
    const r = await fila.drenar(
      async () => {
        if (++n === 1) fila.enfileirar("evento", ev("no-meio"));
      },
      async () => {},
    );
    return r.enviados === 2 && r.restantes === 0;
  }],

  ["pânico é drenado pelo enviador de pânico", async () => {
    fila.limpar();
    fila.enfileirar("panico", { evento_id: "p", totem_id: "T1" });
    let porPanico = 0;
    let porEvento = 0;
    await fila.drenar(
      async () => {
        porEvento++;
      },
      async () => {
        porPanico++;
      },
    );
    return porPanico === 1 && porEvento === 0;
  }],

  ["tentativas são contadas nas falhas", async () => {
    fila.limpar();
    fila.enfileirar("evento", ev("t"));
    await fila.drenar(async () => erroRede(), async () => {});
    await fila.drenar(async () => erroRede(), async () => {});
    return fila.pendentes()[0].tentativas === 2;
  }],
];

// --- Execução --------------------------------------------------------------

let falhas = 0;

for (const [nome, caso] of sincronos) {
  let ok = false;
  try {
    ok = caso();
  } catch (e) {
    console.error("  exceção:", e);
  }
  console.log(`  ${ok ? "✓" : "✗"} ${nome}`);
  if (!ok) falhas++;
}

for (const [nome, caso] of assincronos) {
  let ok = false;
  try {
    ok = await caso();
  } catch (e) {
    console.error("  exceção:", e);
  }
  console.log(`  ${ok ? "✓" : "✗"} ${nome}`);
  if (!ok) falhas++;
}

if (falhas) {
  console.error(`\n${falhas} caso(s) falharam`);
  process.exit(1);
}
console.log(
  `\nfila: ${sincronos.length + assincronos.length} casos — ` +
    "3 modos de falha de localStorage, dreno serial, ErroApi descartado",
);
