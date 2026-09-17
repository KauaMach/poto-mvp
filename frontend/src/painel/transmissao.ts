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

/** Uma transmissão em curso. `parar()` encerra e **libera a câmera**. */
export type Transmissao = { parar: () => void };

/**
 * Captura a webcam e envia quadros para `envioUrl` até alguém chamar `parar()`.
 *
 * @param envioUrl  vem pronta do backend (`ChamadaOut.envio_url`).
 * @param aoFalhar  chamado uma vez, se a transmissão morrer sozinha.
 */
export async function transmitir(
  envioUrl: string,
  aoFalhar?: (erro: unknown) => void,
): Promise<Transmissao> {
  const motivo = indisponivel();
  if (motivo) throw new Error(EXPLICACAO[motivo]);

  const midia = await navigator.mediaDevices.getUserMedia({
    video: { width: LARGURA, height: ALTURA },
    /* Sem áudio: é a MEL-007, e separá-la é deliberado — áudio ao vivo por
     * quadros tem problemas próprios (sincronia, continuidade) que não devem
     * atrasar o vídeo. */
    audio: false,
  });

  /* `<video>` e `<canvas>` fora do DOM: eles são só o caminho de
   * captura → desenho → JPEG. Anexá-los à página mostraria o operador para o
   * próprio operador, o que não é o ponto, e ocuparia espaço no painel. */
  const video = document.createElement("video");
  video.srcObject = midia;
  video.muted = true;
  await video.play();

  const tela = document.createElement("canvas");
  tela.width = LARGURA;
  tela.height = ALTURA;
  const pincel = tela.getContext("2d");

  let vivo = true;
  let relogio: number | null = null;

  const encerrar = () => {
    vivo = false;
    if (relogio !== null) window.clearInterval(relogio);
    /* A linha que apaga a luz da webcam. Sem ela, a câmera do operador
     * continua ligada depois de a chamada acabar. */
    for (const faixa of midia.getTracks()) faixa.stop();
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
