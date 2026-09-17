/* Captura da webcam do operador e envio dos quadros — MEL-005.
 *
 * O lado difícil da videochamada. Do outro lado (o totem) é um `<img>`
 * consumindo MJPEG, sem nada de novo; aqui é preciso **capturar**, e captura no
 * navegador tem uma exigência que o resto do sistema não tem.
 *
 * **`getUserMedia` só existe em contexto seguro.** HTTPS, ou
 * `localhost`/`127.0.0.1`. O P.O.T.O serve em HTTP puro na rede local, por
 * decisão registrada (`PLAN.md §8`), então em `http://<ip-da-pi>:8000/painel` o
 * `navigator.mediaDevices` vem **`undefined`** — não é permissão negada, a API
 * não está lá.
 *
 * Três caminhos para destravar, e o código aqui funciona nos três sem mudança:
 *
 *   C) `chrome://flags/#unsafely-treat-insecure-origin-as-secure` com a origem
 *      da Pi, **na máquina da central**. Uma configuração, num computador
 *      controlado, reversível. É o caminho recomendado para começar.
 *   A) um agente local na central capturando fora do navegador (aí este arquivo
 *      não é usado).
 *   B) HTTPS de verdade, que exige certificado em todos os aparelhos.
 *
 * Por isso `indisponivel()` existe e é explícito: sem contexto seguro, a tela
 * tem que dizer **o que fazer**, não mostrar um erro de JavaScript.
 *
 * Duas decisões de captura:
 *
 * - **320×240 a 10 fps, qualidade 0,6.** É um rosto numa tela de 8,7" — não é
 *   inspeção de imagem. Resolução menor é menos CPU no tablet que está
 *   *tocando* o vídeo, menos banda na rede local e menos trabalho no navegador
 *   da central, que precisa desenhar e comprimir cada quadro.
 * - **Liberar a câmera ao parar é obrigatório.** Um `MediaStreamTrack` que não
 *   é parado mantém a webcam ligada, com a luz acesa, depois de a chamada
 *   acabar. É a mesma lição da câmera da Pi (MVP-075), com agravante: aqui é a
 *   câmera **pessoal** de quem atende.
 */

/** Largura e altura pedidas à câmera. Ver a nota no topo. */
export const LARGURA = 320;
export const ALTURA = 240;

/** Quadros por segundo. O mesmo da câmera da Pi, por simetria. */
export const FPS = 10;

/** Qualidade do JPEG. 0,6 é suficiente para um rosto nesse tamanho. */
export const QUALIDADE = 0.6;

/* --- Áudio (MEL-007) ------------------------------------------------------
 *
 * **16 kHz, mono, 16 bit** — e os três valores não são escolha nossa: são o que
 * o `microfone.py` da Pi já declara no cabeçalho WAV desde a MVP-076, e é esse
 * mecanismo que o totem reaproveita para tocar. Divergir aqui tocaria o áudio
 * na velocidade errada, que é pior que não tocar (parece defeito de microfone).
 */
export const TAXA_AUDIO = 16000;

/* Tamanho do bloco de captura, em amostras. 2048 a 16 kHz = 128 ms.
 *
 * É o piso da latência do áudio: a voz só sai depois de o bloco encher. Blocos
 * menores dão menos atraso e mais requisições; 2048 é a potência de dois mais
 * próxima dos 100 ms que o `microfone.py` usa do outro lado. */
export const BLOCO_AUDIO = 2048;

export type MotivoIndisponivel = "contexto-inseguro" | "sem-suporte";

/**
 * Por que a captura não é possível aqui, ou `null` se é.
 *
 * Distingue os dois casos porque a saída é diferente: contexto inseguro se
 * resolve com uma configuração na máquina da central; falta de suporte, não.
 */
export function indisponivel(): MotivoIndisponivel | null {
  /* `typeof window` e não `window` direto: esta função é chamada **durante o
   * render** do `ChamadaChamado`, e fora do navegador `window` não existe — a
   * verificação de rotas renderiza os componentes no Node e estourava com
   * `ReferenceError: window is not defined`. Foi ela que encontrou isto.
   *
   * Não é só conveniência de teste: uma função que toca global do navegador no
   * caminho de render é frágil por natureza. Tratar a ausência é o correto. */
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return "sem-suporte";
  }
  if (!window.isSecureContext) return "contexto-inseguro";
  if (!navigator.mediaDevices?.getUserMedia) return "sem-suporte";
  return null;
}

export const EXPLICACAO: Record<MotivoIndisponivel, string> = {
  "contexto-inseguro":
    "O navegador só libera a câmera em HTTPS ou localhost. Nesta máquina, " +
    "libere a origem da Pi em chrome://flags/#unsafely-treat-insecure-origin-as-secure.",
  "sem-suporte": "Este navegador não expõe câmera. Tente pelo Chrome.",
};

/** Uma transmissão em curso. `parar()` encerra e **libera o dispositivo**. */
export type Transmissao = { parar: () => void };

/** Vídeo e áudio de uma chamada, com a mídia que os dois compartilham.
 *
 * O `MediaStream` é **um só** para os dois: `getUserMedia` é chamado uma vez,
 * então o navegador pede permissão uma vez e acende um indicador só. Pedir
 * separado mostraria dois avisos de permissão para a mesma chamada.
 */
export type Canal = {
  parar: () => void;
  /** `true` se o áudio subiu. `false` = vídeo sem voz, e a tela deve dizer. */
  comAudio: boolean;
};

/**
 * Captura a webcam e envia quadros para `envioUrl` até alguém chamar `parar()`.
 *
 * @param envioUrl  vem pronta do backend (`ChamadaOut.envio_url`).
 * @param aoFalhar  chamado uma vez, se a transmissão morrer sozinha.
 */
export function transmitirVideo(
  envioUrl: string,
  midia: MediaStream,
  aoFalhar?: (erro: unknown) => void,
): Transmissao {
  /* `<video>` e `<canvas>` fora do DOM: eles são só o caminho de
   * captura → desenho → JPEG. Anexá-los à página mostraria o operador para o
   * próprio operador, o que não é o ponto, e ocuparia espaço no painel. */
  const video = document.createElement("video");
  video.srcObject = midia;
  video.muted = true;
  /* `play()` sem `await`: esta função é síncrona de propósito, para o chamador
   * poder iniciar vídeo e áudio sem duas esperas. O `drawImage` do primeiro
   * quadro pode sair preto se a reprodução ainda não começou — a 10 fps isso é
   * um quadro, e o seguinte já vem certo. */
  void video.play();

  const tela = document.createElement("canvas");
  tela.width = LARGURA;
  tela.height = ALTURA;
  const pincel = tela.getContext("2d");

  let vivo = true;
  let relogio: number | null = null;

  const encerrar = () => {
    vivo = false;
    if (relogio !== null) window.clearInterval(relogio);
    /* As faixas são paradas pelo `abrirCanal`, que é quem as criou — aqui só
     * solta a referência. Quem apaga a luz da webcam é o `stop()` de lá. */
    video.srcObject = null;
  };

  const enviarUm = async () => {
    if (!vivo || !pincel) return;
    pincel.drawImage(video, 0, 0, LARGURA, ALTURA);
    const quadro = await new Promise<Blob | null>((resolver) =>
      tela.toBlob(resolver, "image/jpeg", QUALIDADE),
    );
    if (!quadro || !vivo) return;
    const r = await fetch(envioUrl, {
      method: "POST",
      headers: { "Content-Type": "image/jpeg" },
      body: quadro,
    });
    /* 403 significa que a sessão morreu — expirou, ou o chamado foi encerrado
     * por outro operador. Insistir manteria a webcam ligada contra um destino
     * que não existe mais. */
    if (r.status === 403) throw new Error("a sessão da chamada terminou");
  };

  relogio = window.setInterval(() => {
    void enviarUm().catch((erro) => {
      encerrar();
      aoFalhar?.(erro);
    });
  }, 1000 / FPS);

  return { parar: encerrar };
}

/**
 * Abre o canal completo: vídeo **e** áudio, com uma permissão só (MEL-007).
 *
 * **Um `getUserMedia` para os dois**, e isso importa para quem opera: o
 * navegador pede permissão uma vez e acende um indicador só. Duas chamadas
 * mostrariam dois avisos para a mesma ação, e o segundo pareceria suspeito.
 *
 * Se o áudio falhar mas o vídeo subir, **a chamada continua** com `comAudio:
 * false` — e a tela tem que dizer isso. Meia conversa é melhor que nenhuma,
 * desde que ninguém pense que está sendo ouvido quando não está.
 */
export async function abrirCanal(
  envioUrl: string,
  audioUrl: string,
  aoFalhar?: (erro: unknown) => void,
): Promise<Canal> {
  const motivo = indisponivel();
  if (motivo) throw new Error(EXPLICACAO[motivo]);

  const midia = await navigator.mediaDevices.getUserMedia({
    video: { width: LARGURA, height: ALTURA },
    /* `echoCancellation` e `noiseSuppression` porque o operador está num
     * ambiente com outras pessoas falando. */
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const video = transmitirVideo(envioUrl, midia, aoFalhar);

  let audio: Transmissao | null = null;
  try {
    audio = transmitirAudio(audioUrl, midia, aoFalhar);
  } catch (erro) {
    /* Vídeo sem voz é degradação aceitável; vídeo nenhum não é. Registra e
     * segue — o `comAudio: false` faz a tela avisar. */
    console.warn("áudio da chamada não subiu:", erro);
  }

  return {
    parar: () => {
      video.parar();
      audio?.parar();
      /* As faixas são paradas aqui, e não em cada um: elas são compartilhadas,
       * e parar duas vezes é inofensivo mas confuso de ler. */
      for (const faixa of midia.getTracks()) faixa.stop();
    },
    comAudio: audio !== null,
  };
}

/**
 * Captura o microfone do operador e envia PCM para `audioUrl` (MEL-007).
 *
 * Separado do vídeo porque o transporte é outro: vídeo são JPEGs independentes
 * (perder um não quebra nada), áudio é fluxo contínuo (um buraco é audível).
 *
 * **PCM cru, e não `MediaRecorder`.** O `MediaRecorder` daria WebM/Opus
 * comprimido, que o navegador do totem só tocaria via MSE — mais código, mais
 * API, mais coisa para falhar. Em PCM, a Pi monta o **mesmo WAV em streaming**
 * que o microfone dela já serve desde a MVP-076, e o totem toca num `<audio>`
 * sem uma linha de JavaScript. Numa rede local, 16 kHz mono são 32 KB/s — não
 * vale trocar simplicidade por compressão.
 *
 * **`ScriptProcessorNode`, apesar de estar deprecado.** A alternativa correta é
 * o `AudioWorklet`, que roda fora da thread principal — mas exige carregar um
 * módulo por URL, o que significa **outro arquivo em `public/` sem hash no
 * nome**, e acabei de aprender o preço disso (ver a nota de versão em
 * `fontes.css`: a fonte nova não alcançou quem tinha cache, e o botão mostrou a
 * palavra "mic"). Para um fluxo mono de 16 kHz numa máquina só, o custo de
 * thread é desprezível e o `ScriptProcessorNode` não traz asset novo. É troca
 * consciente, e o caminho de upgrade está nomeado aqui.
 */
export function transmitirAudio(
  audioUrl: string,
  midia: MediaStream,
  aoFalhar?: (erro: unknown) => void,
): Transmissao {
  /* `sampleRate` no construtor: sem isto o contexto abre na taxa do sistema
   * (tipicamente 48 kHz) e o PCM sairia 3× mais rápido do que o cabeçalho WAV
   * da Pi declara — a voz ficaria aguda e acelerada. */
  const contexto = new AudioContext({ sampleRate: TAXA_AUDIO });
  const origem = contexto.createMediaStreamSource(midia);
  const processador = contexto.createScriptProcessor(BLOCO_AUDIO, 1, 1);

  let vivo = true;

  const encerrar = () => {
    vivo = false;
    processador.onaudioprocess = null;
    origem.disconnect();
    processador.disconnect();
    void contexto.close();
  };

  processador.onaudioprocess = (evento) => {
    if (!vivo) return;
    const amostras = evento.inputBuffer.getChannelData(0);

    /* Float32 (−1..1) → Int16 little-endian, que é o que o WAV declara.
     * O `Math.max/min` antes da multiplicação **não é zelo excessivo**: o Web
     * Audio pode entregar valores levemente fora de −1..1, e sem o corte eles
     * dão a volta no inteiro de 16 bit — o sintoma é um estalo alto justamente
     * nos picos da voz. */
    const pcm = new Int16Array(amostras.length);
    for (let i = 0; i < amostras.length; i += 1) {
      const v = Math.max(-1, Math.min(1, amostras[i]));
      pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }

    void fetch(audioUrl, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: pcm.buffer,
    })
      .then((r) => {
        if (r.status === 403) throw new Error("a sessão da chamada terminou");
      })
      .catch((erro) => {
        encerrar();
        aoFalhar?.(erro);
      });
  };

  origem.connect(processador);
  /* Conectar ao destino é necessário para o `ScriptProcessorNode` rodar em
   * alguns navegadores — mas com ganho zero, senão o operador ouviria a própria
   * voz de volta pelos alto-falantes. */
  const silencio = contexto.createGain();
  silencio.gain.value = 0;
  processador.connect(silencio);
  silencio.connect(contexto.destination);

  return { parar: encerrar };
}
