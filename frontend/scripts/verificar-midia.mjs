/* Verifica que a mídia não aparece onde não deve — MVP-078.
 *
 * O critério da task é "botão só aparece em chamado ativo e com dispositivo
 * disponível". Automatizado pelo mesmo motivo do `verificar-discreto.mjs`: uma
 * inspeção manual protege o dia em que foi feita.
 *
 * A propriedade em jogo é de privacidade, não de layout. Um botão de câmera
 * num chamado **encerrado** transformaria o histórico de chamados numa lista
 * de pretextos para ligar a câmera — e a diferença entre um totem de segurança
 * e um equipamento de vigilância é exatamente essa fronteira.
 *
 * O que se verifica é o **HTML de verdade**, renderizado com `react-dom/server`
 * a partir de um `Chamado` como a API o devolve. Checar o código-fonte — um
 * `grep` por `aberto &&` — passaria com a condição escrita e errada.
 *
 * O que este script **não** cobre: o indicador "AO VIVO" e o `DELETE` ao sair
 * dependem de uma sessão aberta, que exige `useEffect` e `fetch`. Nenhum dos
 * dois roda em renderização de servidor. Ficam para a validação na Pi.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;

/** Um chamado como `GET /chamados` o devolve. `status` é trocado por caso. */
const CHAMADO = {
  chamado_id: "CALL-2026-000044",
  totem_id: "TOTEM-CCS-01",
  tipo_ocorrencia: "seguranca",
  modo: "normal",
  origem_acionamento: "touch",
  gravidade: "risco_imediato",
  canal_roteado: "csv",
  fallback: null,
  status: "notificado",
  texto_livre: "alguém me seguindo no estacionamento",
  observacao: null,
  timestamp_local: null,
  created_at: "2026-09-16T14:00:00+00:00",
  updated_at: "2026-09-16T14:00:00+00:00",
  acked_at: null,
};

/** Como `GET /dispositivos` descreve a câmera CSI da Pi (medido, MVP-073). */
const CAMERA = {
  id: "csi:0",
  tipo: "camera",
  nome: "Câmera CSI (imx219)",
  dono: "RaspPoto",
  status: "disponivel",
  capacidades: { origem: "csi", modelo: "imx219", rotacao: 180, indice: 0 },
};

/* Uma câmera que o backend detectou mas marcou como indisponível. Existe para
 * provar que o filtro olha o `status`, e não só o tamanho da lista. */
const CAMERA_OCUPADA = { ...CAMERA, id: "csi:1", status: "em_uso" };

const CASOS = [
  {
    nome: "chamado ativo, com câmera",
    status: "notificado",
    dispositivos: [CAMERA],
    exige: ["Ver câmera", "Escolher dispositivo"],
    proibe: ["Nenhuma câmera ou microfone"],
  },
  {
    /* O caso central. `encerrado` está fora do conjunto `ABERTOS`, e nada de
     * mídia pode sobrar — nem o seletor, nem a mensagem de vazio, que também
     * ofereceria contexto onde não deve haver nenhum. */
    nome: "chamado ENCERRADO",
    status: "encerrado",
    dispositivos: [CAMERA],
    exige: [],
    proibe: [
      "Ver câmera",
      "Ouvir microfone",
      "Escolher dispositivo",
      "Nenhuma câmera ou microfone",
      "poto-midia",
    ],
  },
  {
    nome: "chamado CANCELADO",
    status: "cancelado",
    dispositivos: [CAMERA],
    exige: [],
    proibe: ["Ver câmera", "Escolher dispositivo", "poto-midia"],
  },
  {
    /* Mensagem clara, não quadro preto — e sem seletor vazio para clicar. */
    nome: "chamado ativo, sem dispositivo",
    status: "notificado",
    dispositivos: [],
    exige: ["Nenhuma câmera ou microfone"],
    proibe: ["Ver câmera", "Escolher dispositivo"],
  },
  {
    /* O filtro é por `status === "disponivel"`, não por lista não-vazia. Sem
     * esta distinção, uma câmera ocupada por outro operador ofereceria um botão
     * que só pode falhar. */
    nome: "chamado ativo, câmera em uso",
    status: "notificado",
    dispositivos: [CAMERA_OCUPADA],
    exige: ["Nenhuma câmera ou microfone"],
    proibe: ["Ver câmera", "Escolher dispositivo"],
  },
];

/* Dentro de `node_modules/.cache` e não em `/tmp`: a resolução de módulos do
 * Node parte da localização do arquivo, e um bundle em `/tmp` não acharia
 * `react-dom`. Mesma razão do `verificar-discreto.mjs`. */
const dir = join(RAIZ, "node_modules/.cache/poto-midia");
mkdirSync(dir, { recursive: true });

let falhas = 0;
try {
  for (const caso of CASOS) {
    const html = renderizar({ ...CHAMADO, status: caso.status }, caso.dispositivos);

    const faltando = caso.exige.filter((t) => !html.includes(t));
    const vazados = caso.proibe.filter((t) => html.includes(t));

    if (faltando.length || vazados.length) {
      falhas += 1;
      console.error(`✗ ${caso.nome}`);
      for (const t of faltando) console.error(`    faltou: "${t}"`);
      for (const t of vazados) console.error(`    vazou:  "${t}"`);
      continue;
    }
    console.log(`✓ ${caso.nome}`);
  }

  /* A verificação inversa, e ela é necessária.
   *
   * Se `CardChamado` não renderizasse nada — um erro de import, um retorno
   * antecipado — todos os casos de "proibe" passariam de graça e o script diria
   * que está tudo bem. O protocolo tem que estar lá nos dois estados.
   */
  for (const status of ["notificado", "encerrado"]) {
    const html = renderizar({ ...CHAMADO, status }, [CAMERA]);
    if (!html.includes(CHAMADO.chamado_id)) {
      falhas += 1;
      console.error(
        `✗ o cartão de "${status}" não renderizou o protocolo — ` +
          "a ausência dos termos proibidos não prova nada",
      );
    }
  }

  if (falhas) {
    console.error(`\n${falhas} caso(s) de mídia falharam.`);
    process.exit(1);
  }
  console.log(`mídia no painel: ${CASOS.length} casos conferidos`);
} finally {
  rmSync(dir, { recursive: true, force: true });
}

function renderizar(chamado, dispositivos) {
  const entrada = join(dir, "entrada.tsx");
  writeFileSync(
    entrada,
    `import { renderToStaticMarkup } from "react-dom/server";
     import { CardChamado } from "${RAIZ}src/painel/CardChamado";
     process.stdout.write(renderToStaticMarkup(
       <CardChamado
         chamado={${JSON.stringify(chamado)}}
         dispositivos={${JSON.stringify(dispositivos)}}
         onMudou={() => {}}
         slaSegundos={120}
       />
     ));`,
  );

  const saida = join(dir, "saida.mjs");
  execFileSync(
    join(RAIZ, "node_modules/.bin/rolldown"),
    [entrada, "-o", saida, "--format", "esm", "--platform", "node",
     "--external", "react", "--external", "react-dom",
     "--external", "react/jsx-runtime",
     /* `CardChamado` importa `api.ts`, que lê `import.meta.env` no topo do
      * módulo — e fora do Vite isso é `undefined`, então o bundle morre antes
      * de renderizar. O `rolldown` não tem `--define`, mas o banner é inserido
      * acima do corpo do módulo e roda antes dele; os externos (react) não
      * leem `import.meta.env`, então definí-lo aqui é suficiente.
      *
      * `DEV: false` é deliberado: é o valor de produção, e é nele que a
      * garantia importa. */
     "--banner",
     'import.meta.env = { VITE_POTO_TOTEM_ID: "TOTEM-VERIFICACAO", DEV: false };'],
    { stdio: ["ignore", "ignore", "inherit"] },
  );

  return execFileSync(process.execPath, [saida], {
    encoding: "utf8",
    cwd: RAIZ,
  });
}
