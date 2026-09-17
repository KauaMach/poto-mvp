/* "Iniciar videochamada" no painel — MEL-005.
 *
 * O operador recebe um pânico, decide, e aparece na tela de quem está
 * esperando. O propósito não é vigilância nem diagnóstico: é **a pessoa não se
 * sentir sozinha** enquanto o socorro não chega.
 *
 * **Só em chamado de pânico**, e a razão é estrutural, não preferência: o
 * `alerta_ativo` é o único estado com **tela persistente** no totem. As outras
 * trilhas mostram a confirmação por 9 segundos e voltam para a Home — não há
 * onde o vídeo aparecer. Widenar isso exigiria uma tela nova no totem, não um
 * `if` diferente aqui.
 *
 * O contraponto da `MidiaChamado`: lá a central pede para **ver** o local; aqui
 * pede para **aparecer** nele. Mesma sessão, mesmo prazo, mesma auditoria,
 * direção invertida.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  abrirChamada,
  fecharChamada,
  fecharChamadaAoSair,
} from "../comum/api";
import type { Chamado, ChamadaSessao } from "../comum/tipos";
import {
  EXPLICACAO,
  indisponivel,
  transmitir,
  type Transmissao,
} from "./transmissao";

type Props = { chamado: Chamado };

export function ChamadaChamado({ chamado }: Props) {
  const [sessao, setSessao] = useState<ChamadaSessao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  /* A transmissão num `ref` e não em estado: ela não é renderizada, e guardá-la
   * em estado provocaria um render a cada troca sem nada mudar na tela. */
  const transmissao = useRef<Transmissao | null>(null);

  const encerrar = useCallback(async () => {
    /* Para a câmera **primeiro**. É o que apaga a luz da webcam do operador, e
     * esperar a resposta do `DELETE` para isso deixaria a câmera ligada por
     * todo o tempo de ida e volta. */
    transmissao.current?.parar();
    transmissao.current = null;
    const id = sessao?.sessao_id;
    setSessao(null);
    await fecharChamada(chamado.chamado_id, id).catch(() => {
      /* O backend expira a sessão em 10 min e a varre no worker de SLA. Uma
       * falha aqui atrasa o registro do fechamento, não a liberação da
       * câmera — essa já aconteceu na linha de cima. */
    });
  }, [chamado.chamado_id, sessao?.sessao_id]);

  const iniciar = useCallback(async () => {
    setOcupado(true);
    setErro(null);
    let aberta: ChamadaSessao | null = null;
    try {
      aberta = await abrirChamada(chamado.chamado_id);
      /* A captura vem **depois** de a sessão existir: sem `envio_url` não há
       * para onde mandar quadro, e pedir a câmera antes acenderia a luz da
       * webcam para uma chamada que pode ser recusada com 409. */
      transmissao.current = await transmitir(aberta.envio_url, (falha) => {
        setErro(mensagem(falha));
        setSessao(null);
      });
      setSessao(aberta);
    } catch (falha) {
      setErro(mensagem(falha));
      /* Se a sessão abriu e a câmera não, fecha a sessão: deixá-la aberta
       * registraria na auditoria uma chamada que nunca transmitiu nada. */
      if (aberta) await fecharChamada(chamado.chamado_id, aberta.sessao_id).catch(() => {});
    } finally {
      setOcupado(false);
    }
  }, [chamado.chamado_id]);

  /* Sair da tela encerra: chamado resolvido, filtro mudado, painel fechado. */
  useEffect(() => {
    if (!sessao) return;
    return () => {
      transmissao.current?.parar();
      transmissao.current = null;
      void fecharChamada(chamado.chamado_id).catch(() => {});
    };
  }, [sessao, chamado.chamado_id]);

  /* Fechar a aba, que o `useEffect` não cobre. `pagehide` e não
   * `beforeunload` — o segundo não dispara em iOS nem em aba descartada por
   * memória. Ver a nota em `api.ts`. */
  useEffect(() => {
    if (!sessao) return;
    const aoSair = () => {
      transmissao.current?.parar();
      fecharChamadaAoSair(chamado.chamado_id);
    };
    window.addEventListener("pagehide", aoSair);
    return () => window.removeEventListener("pagehide", aoSair);
  }, [sessao, chamado.chamado_id]);

  const bloqueio = indisponivel();

  return (
    <section
      className="poto-chamada"
      aria-label={`Videochamada de ${chamado.chamado_id}`}
    >
      {sessao ? (
        <div className="poto-chamada-ativa">
          <span className="poto-ao-vivo">
            <span aria-hidden="true" className="poto-ponto poto-ponto-vivo" />
            TRANSMITINDO
          </span>
          <span className="poto-chamada-nota">
            Sua câmera está na tela do totem
          </span>
          <button
            type="button"
            className="poto-botao-texto"
            onClick={() => void encerrar()}
          >
            Encerrar chamada
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="poto-botao-secundario"
          disabled={ocupado || bloqueio !== null}
          onClick={() => void iniciar()}
          /* Com a captura bloqueada, o motivo vai no `title` **e** no texto
           * abaixo: um botão desabilitado sem explicação faz o operador achar
           * que o sistema travou. */
          title={bloqueio ? EXPLICACAO[bloqueio] : undefined}
        >
          {ocupado ? "Abrindo…" : "Iniciar videochamada"}
        </button>
      )}

      {bloqueio && !sessao && (
        <p className="poto-chamada-nota">{EXPLICACAO[bloqueio]}</p>
      )}

      {erro && (
        <p className="poto-midia-erro" role="alert">
          {erro}
        </p>
      )}
    </section>
  );
}

function mensagem(falha: unknown): string {
  if (falha instanceof Error && falha.name === "ErroApi") {
    const status = (falha as Error & { status: number }).status;
    if (status === 409) return "Este chamado já foi encerrado.";
    if (status === 401) return "Sem permissão. Confira o token do painel.";
  }
  /* `NotAllowedError` é o operador negando a câmera no navegador — é escolha
   * dele, e a mensagem não deve soar como defeito. */
  if (falha instanceof Error && falha.name === "NotAllowedError") {
    return "Permissão de câmera negada no navegador.";
  }
  if (falha instanceof Error && falha.message) return falha.message;
  return "Não foi possível iniciar a videochamada.";
}
