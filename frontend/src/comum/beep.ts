/* Realimentação sonora — MVP-051.
 *
 * 660 Hz por 0,12 s, gerado pela Web Audio API em vez de um arquivo de áudio.
 * Dois motivos: um `.mp3` é mais um recurso para carregar (e para faltar
 * offline), e um oscilador não tem latência de decodificação — o som sai no
 * mesmo quadro do toque, que é o que faz a realimentação parecer resposta e
 * não eco.
 *
 * **Nunca levanta.** Navegadores bloqueiam áudio sem gesto do usuário, o
 * contexto pode estar suspenso, e no tablet o volume pode estar em zero. Um
 * pedido de socorro não pode falhar porque o beep não pôde tocar.
 */

const FREQUENCIA_HZ = 660;
const DURACAO_S = 0.12;

/* Um contexto só, criado na primeira vez. Criar um por beep esgota o limite do
 * navegador (Chrome permite poucas dezenas) e o som pararia de sair depois de
 * algumas dezenas de acionamentos — numa demonstração, exatamente no meio. */
let contexto: AudioContext | null = null;

function obterContexto(): AudioContext | null {
  if (contexto) return contexto;
  const Ctor = window.AudioContext ?? window.webkitAudioContext;
  if (!Ctor) return null;
  try {
    contexto = new Ctor();
    return contexto;
  } catch {
    return null;
  }
}

export function beep(): void {
  try {
    const ctx = obterContexto();
    if (!ctx) return;

    /* O contexto nasce suspenso quando criado sem gesto do usuário. Retomar é
     * assíncrono; ignorar a promessa é proposital — se falhar, não há beep, e
     * isso não é um erro que interesse a quem está usando o totem. */
    if (ctx.state === "suspended") void ctx.resume();

    const osc = ctx.createOscillator();
    const ganho = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = FREQUENCIA_HZ;

    /* Envelope curto em vez de ligar e desligar seco: um corte abrupto produz
     * um clique audível (descontinuidade na forma de onda), que soa como
     * defeito. */
    const agora = ctx.currentTime;
    ganho.gain.setValueAtTime(0, agora);
    ganho.gain.linearRampToValueAtTime(0.3, agora + 0.01);
    ganho.gain.linearRampToValueAtTime(0, agora + DURACAO_S);

    osc.connect(ganho).connect(ctx.destination);
    osc.start(agora);
    osc.stop(agora + DURACAO_S);
  } catch {
    /* Som é realimentação, não requisito. */
  }
}
