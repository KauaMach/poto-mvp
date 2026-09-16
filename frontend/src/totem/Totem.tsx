/* Contêiner do totem — fluxo de acionamento (MVP-051).
 *
 * Máquina de estados de três posições: `inicio` → `enviando` → `confirmado`,
 * com volta automática ao `inicio` (MVP-052).
 *
 * A regra que organiza o arquivo: **o cliente não decide nada sobre a
 * ocorrência.** Ele coleta o toque, manda, e obedece ao `instrucao_totem` que
 * volta. Gravidade, canal, mensagem de tela, som e discrição são todos do
 * backend — é o que garante que a proteção não dependa de o frontend lembrar
 * de aplicá-la.
 */
import { useCallback, useState } from "react";
import { enviarEvento, enviarPanico, novoEvento, novoPanico } from "../comum/api";
import { beep } from "../comum/beep";
import type { EventoOut, PanicoOut } from "../comum/tipos";
import { useOnline } from "../comum/useOnline";
import { Panic, PanicAjuda } from "../componentes/Panic";
import { Shell } from "./Shell";
import { AlertaAtivo } from "./telas/AlertaAtivo";
import { Confirmacao } from "./telas/Confirmacao";
import { Home } from "./telas/Home";
import type { Trilha } from "./trilhas";

type Estado =
  | { tela: "inicio" }
  | { tela: "enviando" }
  | { tela: "confirmado"; resultado: EventoOut; offline: boolean }
  /* O pânico tem tela própria: persistente, com cronômetro e escalonamento
   * (MVP-054). `desde` guarda o instante do acionamento — o cronômetro conta a
   * partir dele, não de quando o componente montou. */
  | { tela: "alerta"; alerta: PanicoOut; desde: Date }
  | { tela: "erro"; mensagem: string };

export function Totem() {
  const online = useOnline();
  const [estado, setEstado] = useState<Estado>({ tela: "inicio" });

  const voltar = useCallback(() => setEstado({ tela: "inicio" }), []);

  const acionar = useCallback(async (trilha: Trilha) => {
    /* `enviando` desabilita os botões antes de qualquer `await`: dois toques
     * rápidos gerariam **dois** `evento_id` distintos, e a idempotência do
     * backend só protege reenvios do mesmo id. */
    setEstado({ tela: "enviando" });
    try {
      const resultado = await enviarEvento(
        novoEvento(trilha.tipo, { modo: trilha.modo }),
      );
      setEstado({ tela: "confirmado", resultado, offline: false });
    } catch (erro) {
      /* A fila offline entra aqui na MVP-057. Até então, a tela não pode
       * travar: mostra o erro e volta, porque um totem preso numa tela de
       * carregamento é pior do que um totem que admite a falha. */
      setEstado({
        tela: "erro",
        mensagem:
          erro instanceof Error && erro.name === "ErroRede"
            ? "Sem conexão. Tente novamente."
            : "Não foi possível registrar agora. Tente novamente.",
      });
    }
  }, []);

  const acionarPanico = useCallback(async () => {
    /* O instante é capturado **antes** do envio: o cronômetro conta desde o
     * toque, não desde a resposta. Num webhook lento a diferença chega a
     * segundos, e é o tempo de espera real que a pessoa precisa ver. */
    const desde = new Date();
    setEstado({ tela: "enviando" });
    try {
      const alerta = await enviarPanico(novoPanico());
      beep();
      setEstado({ tela: "alerta", alerta, desde });
    } catch {
      setEstado({
        tela: "erro",
        mensagem: "Sem conexão. O alerta será reenviado automaticamente.",
      });
    }
  }, []);

  if (estado.tela === "alerta") {
    /* `semCromo`: o alerta ativo ocupa a tela inteira. Um header com o
     * wordmark clicável ali daria um jeito acidental de sair de um estado que
     * é persistente de propósito. */
    return (
      <Shell online={online} fundo="var(--rust)" semCromo>
        <AlertaAtivo
          alerta={estado.alerta}
          desde={estado.desde}
          onVoltar={voltar}
        />
      </Shell>
    );
  }

  if (estado.tela === "confirmado") {
    return (
      <Shell online={online} onInicio={voltar}>
        <Confirmacao
          resultado={estado.resultado}
          offline={estado.offline}
          onVoltar={voltar}
        />
      </Shell>
    );
  }

  return (
    <Shell
      online={online}
      onInicio={voltar}
      rodape={
        <>
          <Panic onAcionar={acionarPanico} desabilitado={estado.tela === "enviando"} />
          <PanicAjuda />
        </>
      }
    >
      <Home
        onEscolher={(t) => void acionar(t)}
        enviando={estado.tela === "enviando"}
      />
      {estado.tela === "erro" && (
        <p role="alert" className="poto-erro">
          {estado.mensagem}
        </p>
      )}
    </Shell>
  );
}
