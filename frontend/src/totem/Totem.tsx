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
import { enfileirar } from "../comum/fila";
import { useFila } from "../comum/useFila";
import type { EventoOut, PanicoOut } from "../comum/tipos";
import { useOnline } from "../comum/useOnline";
import { Panic, PanicAjuda } from "../componentes/Panic";
import { Shell } from "./Shell";
import { AlertaAtivo } from "./telas/AlertaAtivo";
import { Confirmacao } from "./telas/Confirmacao";
import { Home } from "./telas/Home";
import { Voz } from "./telas/Voz";
import type { Trilha } from "./trilhas";

type Estado =
  | { tela: "inicio" }
  /* A sub-ação do blueprint de design. Ainda não funciona — a tela diz isso.
   * Ver `telas/Voz.tsx`. */
  | { tela: "voz" }
  | { tela: "enviando" }
  | { tela: "confirmado"; resultado: EventoOut; offline: boolean }
  /* O pânico tem tela própria: persistente, com cronômetro e escalonamento
   * (MVP-054). `desde` guarda o instante do acionamento — o cronômetro conta a
   * partir dele, não de quando o componente montou. */
  | { tela: "alerta"; alerta: PanicoOut; desde: Date; offline?: boolean }
  | { tela: "erro"; mensagem: string };

type Props = {
  /** Tela em que abrir. Só `/totem/voz` usa isto; o padrão é a inicial. */
  telaInicial?: "inicio" | "voz";
};

export function Totem({ telaInicial = "inicio" }: Props) {
  const online = useOnline();
  const [estado, setEstado] = useState<Estado>({ tela: telaInicial });
  /* O intervalo vem do `/config` (`totem_offline_seg`, MVP-037). Até o totem
   * buscá-lo — e offline ele nunca busca — vale o mesmo default do backend, que
   * é a razão de a constante existir num lugar só. */
  const { naFila, recontar } = useFila(INTERVALO_DRENO_SEG);

  const voltar = useCallback(() => setEstado({ tela: "inicio" }), []);

  const acionar = useCallback(async (trilha: Trilha) => {
    /* `enviando` desabilita os botões antes de qualquer `await`: dois toques
     * rápidos gerariam **dois** `evento_id` distintos, e a idempotência do
     * backend só protege reenvios do mesmo id. */
    /* O evento é montado **antes** do try: se o envio falhar, é este mesmo
     * objeto — com este mesmo `evento_id` — que vai para a fila. Montar dentro
     * do `catch` geraria um id novo e quebraria a idempotência. */
    const evento = novoEvento(trilha.tipo, { modo: trilha.modo });
    setEstado({ tela: "enviando" });
    try {
      const resultado = await enviarEvento(evento);
      setEstado({ tela: "confirmado", resultado, offline: false });
    } catch (erro) {
      /* **Falha de rede não é falha do acionamento.** O evento vai para a fila
       * e a pessoa recebe confirmação imediata — ela não pode ficar sabendo que
       * o wi-fi da universidade caiu, nem decidir o que fazer a respeito.
       *
       * `ErroApi` é outra coisa: o envio chegou e foi **recusado** (payload
       * inválido, rota errada). Reenfileirar entraria em laço com um payload
       * que vai falhar igual, então aí a tela admite o erro.
       */
      if (erro instanceof Error && erro.name === "ErroRede") {
        const guardado = enfileirar("evento", evento);
        /* Reconta na hora: o badge tem que aparecer no mesmo quadro da
         * confirmação, não no próximo ciclo de dreno. */
        recontar();
        setEstado({
          tela: "confirmado",
          offline: true,
          resultado: confirmacaoLocal(guardado),
        });
        return;
      }
      setEstado({
        tela: "erro",
        mensagem: "Não foi possível registrar agora. Tente novamente.",
      });
    }
  }, [recontar]);

  const acionarPanico = useCallback(async () => {
    /* O instante é capturado **antes** do envio: o cronômetro conta desde o
     * toque, não desde a resposta. Num webhook lento a diferença chega a
     * segundos, e é o tempo de espera real que a pessoa precisa ver. */
    const desde = new Date();
    const panico = novoPanico();
    setEstado({ tela: "enviando" });
    try {
      const alerta = await enviarPanico(panico);
      beep();
      setEstado({ tela: "alerta", alerta, desde });
    } catch (erro) {
      if (erro instanceof Error && erro.name === "ErroRede") {
        /* Um pânico offline continua sendo um pânico. A tela de alerta ativo
         * aparece igual, com o protocolo local, e o alerta real sai quando a
         * rede voltar. O que **não** existe ainda é o status ao vivo — sem
         * WebSocket não há como saber se a central recebeu. */
        const guardado = enfileirar("panico", panico);
        recontar();
        setEstado({
          tela: "alerta",
          desde,
          offline: true,
          alerta: {
            chamado_id: guardado ? "aguardando envio" : "não registrado",
            status: "alerta_ativo",
            gravidade: "risco_imediato",
            resultados: [],
            escalonamento_disponivel: ESCALONAMENTO_OFFLINE,
            duplicado: false,
          },
        });
        return;
      }
      setEstado({
        tela: "erro",
        mensagem: "Não foi possível registrar agora. Tente novamente.",
      });
    }
  }, [recontar]);

  if (estado.tela === "alerta") {
    /* `semCromo`: o alerta ativo ocupa a tela inteira. Um header com o
     * wordmark clicável ali daria um jeito acidental de sair de um estado que
     * é persistente de propósito. */
    return (
      <Shell online={online} fundo="var(--rust)" semCromo>
        <AlertaAtivo
          alerta={estado.alerta}
          desde={estado.desde}
          offline={estado.offline}
          onVoltar={voltar}
        />
      </Shell>
    );
  }

  if (estado.tela === "confirmado") {
    return (
      <Shell online={online} naFila={naFila} onInicio={voltar}>
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
      naFila={naFila}
      onInicio={voltar}
      rodape={
        <>
          <Panic onAcionar={acionarPanico} desabilitado={estado.tela === "enviando"} />
          <PanicAjuda />
        </>
      }
    >
      {estado.tela === "voz" ? (
        <Voz onVoltar={voltar} />
      ) : (
        <Home
          onEscolher={(t) => void acionar(t)}
          onDescreverPorVoz={() => setEstado({ tela: "voz" })}
          enviando={estado.tela === "enviando"}
        />
      )}
      {estado.tela === "erro" && (
        <p role="alert" className="poto-erro">
          {estado.mensagem}
        </p>
      )}
    </Shell>
  );
}

/** Intervalo do dreno, em segundos.
 *
 * Espelha `POTO_TOTEM_OFFLINE_SEG` do backend (MVP-037). Duplicado aqui porque
 * offline **não há `/config`** para consultar — e é justamente offline que o
 * dreno importa. O `/config` continua sendo a fonte quando há rede; esta
 * constante é o piso.
 */
const INTERVALO_DRENO_SEG = 15;

/** Confirmação montada **no cliente**, para quando o envio não chegou.
 *
 * É a única vez em que o frontend decide o conteúdo de uma tela de
 * confirmação — e dói, porque contradiz a regra de que só o backend decide.
 * A alternativa seria pior: sem resposta do servidor não há `instrucao_totem`,
 * e deixar a tela em branco ou em erro é justamente o que a fila existe para
 * evitar.
 *
 * Não recebe o evento de propósito: a função não deve ter acesso a nada que
 * possa vazar para a tela. Duas salvaguardas mantêm a contradição contida:
 *
 * - **Não há protocolo.** Inventar um `CALL-` local seria pior que não ter: a
 *   pessoa anotaria um número que a central não reconhece.
 * - **Sem som**, e a mensagem é genérica. Sem `tela_neutra` do servidor o
 *   cliente não sabe se o caso é discreto, e um beep na trilha errada é tão
 *   revelador quanto um protocolo na tela. O silêncio é o default seguro.
 */
function confirmacaoLocal(guardado: boolean): EventoOut {
  return {
    chamado_id: "",
    status: "recebido",
    canal_roteado: "",
    /* `risco_potencial` e não a gravidade real: o cliente não roteia. É o
     * suficiente para a tela não mentir em nenhuma direção. */
    gravidade: "risco_potencial",
    instrucao_totem: {
      mensagem_tela: guardado
        ? "Pedido registrado. Aguarde atendimento."
        : "Não foi possível registrar. Procure ajuda presencialmente.",
      feedback_sonoro: false,
      tela_neutra: true,
    },
    duplicado: false,
  };
}

/* Autoridades oferecidas quando o pânico está offline.
 *
 * Fixas aqui de propósito: elas normalmente vêm do `/config` (MVP-037), e
 * offline não há `/config`. São exatamente as quatro de `config.CANAIS_ESTADO`,
 * e é a única duplicação da lista no cliente — o alternativo seria uma tela de
 * pânico sem nenhum caminho de escalonamento, que é o pior momento possível
 * para não oferecer nada.
 */
const ESCALONAMENTO_OFFLINE = [
  { canal: "pm_190", nome: "Polícia Militar" },
  { canal: "samu_192", nome: "SAMU" },
  { canal: "bombeiros_193", nome: "Corpo de Bombeiros" },
  { canal: "central_180", nome: "Central de Atendimento à Mulher" },
];
