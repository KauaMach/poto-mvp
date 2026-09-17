/* Detalhe do chamado — MEL-009.
 *
 * O painel mostrava uma lista e nada mais. `GET /chamados/{id}` existe desde a
 * MVP-032 e devolve **a história inteira** — a triagem que a máquina fez, cada
 * canal acionado com resultado, e cada transição de estado — e nada disso
 * chegava à tela. Era a lacuna que eu mesmo documentei no roteiro de teste.
 *
 * Duas coisas acontecem aqui, e a segunda é consequência da primeira:
 *
 * 1. **Mais informação.** É o que responde "por que este chamado foi para o
 *    CSV?" meses depois — e a resposta é auditável, não uma reconstituição de
 *    memória.
 * 2. **Mais opções, num lugar que as comporta.** Câmera, microfone e
 *    videochamada moravam no cartão, competindo com vinte outros cartões por
 *    espaço. A videochamada, que é a ação mais importante de um pânico, ficava
 *    como um botão apagado no pé do cartão. Aqui elas têm largura.
 *
 * **Painel lateral e não modal.** Um modal bloqueia o resto da tela, e numa
 * central a lista **precisa** continuar visível: outro chamado pode entrar
 * enquanto o operador lê este, e o WebSocket vai acendê-lo atrás. Um overlay
 * que esconde isso troca contexto por foco no pior momento.
 */
import { useEffect, useState } from "react";
import { auditoriaDeMidia, detalharChamado } from "../comum/api";
import type {
  AuditoriaMidia,
  Chamado,
  ChamadoDetalhe,
  Dispositivo,
} from "../comum/tipos";
import { Sym } from "../componentes/Sym";
import { AcoesChamado } from "./AcoesChamado";
import { ChamadaChamado } from "./ChamadaChamado";
import { ContadorSLA } from "./ContadorSLA";
import { MidiaChamado } from "./MidiaChamado";
import {
  ABERTOS,
  COR_GRAVIDADE,
  ROTULO_GRAVIDADE,
  ROTULO_STATUS,
  TITULO_TIPO,
} from "./rotulos";

type Props = {
  chamado: Chamado;
  dispositivos: Dispositivo[];
  slaSegundos: number | null;
  onMudou: (chamado: Chamado) => void;
  onFechar: () => void;
};

export function DetalheChamado({
  chamado,
  dispositivos,
  slaSegundos,
  onMudou,
  onFechar,
}: Props) {
  const [detalhe, setDetalhe] = useState<ChamadoDetalhe | null>(null);
  const [auditoria, setAuditoria] = useState<AuditoriaMidia[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const aberto = ABERTOS.has(chamado.status);

  /* **Um efeito só, com `updated_at` na dependência.**
   *
   * A primeira versão tinha dois: um para carregar e outro que comparava
   * `detalhe.updated_at` com `chamado.updated_at` para recarregar quando o
   * WebSocket mudasse o estado por fora. O oxlint acusou `set-state-in-effect`
   * e estava certo — aquele segundo efeito dependia do próprio `detalhe` que
   * ele mesmo escrevia, e a condição de recarga era **derivável**, não estado.
   *
   * Com `chamado.updated_at` na dependência, o efeito reexecuta exatamente
   * quando o chamado muda: mesma intenção, sem comparação e sem o risco de
   * laço. O padrão de `vivo` é o mesmo do `Painel.tsx` — uma resposta que chega
   * depois de a gaveta fechar não deve escrever em estado desmontado.
   */
  useEffect(() => {
    let vivo = true;

    void (async () => {
      try {
        /* Em paralelo: a auditoria não depende do detalhe, e serializar somaria
         * dois tempos de ida e volta antes de a gaveta mostrar algo. */
        const [d, a] = await Promise.all([
          detalharChamado(chamado.chamado_id),
          /* A auditoria pode falhar sem derrubar o detalhe: ela é complementar,
           * e um chamado sem mídia nenhuma devolve lista vazia — não erro. */
          auditoriaDeMidia(chamado.chamado_id).catch(() => []),
        ]);
        if (!vivo) return;
        setDetalhe(d);
        setAuditoria(a);
        setErro(null);
      } catch {
        if (vivo) setErro("Não foi possível carregar o detalhe deste chamado.");
      }
    })();

    return () => {
      vivo = false;
    };
  }, [chamado.chamado_id, chamado.updated_at]);

  /* `Escape` fecha. Num painel operado por teclado durante um plantão, ter que
   * achar o botão de fechar com o mouse é atrito desnecessário. */
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") onFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  return (
    <aside
      className="poto-detalhe"
      aria-label={`Detalhe de ${chamado.chamado_id}`}
    >
      <header
        className="poto-detalhe-topo"
        style={{ borderLeftColor: COR_GRAVIDADE[chamado.gravidade] }}
      >
        <div>
          <span
            className="poto-chip-gravidade"
            style={{ color: COR_GRAVIDADE[chamado.gravidade] }}
          >
            <span aria-hidden="true" className="poto-ponto" />
            {ROTULO_GRAVIDADE[chamado.gravidade]}
          </span>
          <h2 className="poto-detalhe-titulo">
            {TITULO_TIPO[chamado.tipo_ocorrencia]}
          </h2>
          <p className="poto-protocolo tabular">{chamado.chamado_id}</p>
        </div>
        <button
          type="button"
          className="poto-detalhe-fechar"
          onClick={onFechar}
          aria-label="Fechar detalhe"
        >
          <Sym nome="arrow_back" tamanho="sm" />
        </button>
      </header>

      <div className="poto-detalhe-corpo">
        {erro && (
          <p className="poto-midia-erro" role="alert">
            {erro}
          </p>
        )}

        <Linha rotulo="Situação" valor={ROTULO_STATUS[chamado.status]} />
        <Linha rotulo="Totem" valor={chamado.totem_id} />
        <Linha rotulo="Canal acionado" valor={chamado.canal_roteado || "—"} />
        {chamado.fallback && (
          <Linha rotulo="Fallback" valor={chamado.fallback} />
        )}
        <Linha rotulo="Origem" valor={chamado.origem_acionamento} />
        <Linha rotulo="Recebido" valor={horaCompleta(chamado.created_at)} />
        {chamado.acked_at && (
          <Linha
            rotulo="Reconhecido"
            valor={`${horaCompleta(chamado.acked_at)} · ${
              Math.round(
                (Date.parse(chamado.acked_at) -
                  Date.parse(chamado.created_at)) / 1000,
              )
            }s depois`}
          />
        )}

        {aberto && slaSegundos !== null && (
          <ContadorSLA chamado={chamado} segundos={slaSegundos} />
        )}

        {chamado.texto_livre && (
          <section className="poto-detalhe-secao">
            <h3>Relato</h3>
            {/* Entre aspas e em itálico: é a voz de quem pediu ajuda, não texto
                do sistema. A distinção importa quando se lê rápido. */}
            <p className="poto-card-relato">“{chamado.texto_livre}”</p>
          </section>
        )}

        {chamado.observacao && (
          <section className="poto-detalhe-secao">
            <h3>Observação da central</h3>
            <p className="poto-detalhe-texto">{chamado.observacao}</p>
          </section>
        )}

        {/* --- Ações. Aqui, e não no cartão. ---------------------------- */}
        <section className="poto-detalhe-secao">
          <h3>Ações</h3>
          <AcoesChamado chamado={chamado} onMudou={onMudou} />
          {aberto && (
            <MidiaChamado chamado={chamado} dispositivos={dispositivos} />
          )}
          {/* Videochamada só em pânico ativo: `alerta_ativo` é o único estado
              com tela persistente no totem, então é o único onde há para onde
              mandar o vídeo (MEL-005). */}
          {aberto && chamado.origem_acionamento === "panico" && (
            <ChamadaChamado chamado={chamado} />
          )}
        </section>

        {/* --- A história, que a lista nunca mostrou ------------------- */}
        {detalhe?.triagem && (
          <section className="poto-detalhe-secao">
            <h3>Triagem</h3>
            <p className="poto-detalhe-nota">
              O que a máquina inferiu <strong>e</strong> qual trilha a pessoa
              tocou. É o que responde “por que foi para este canal?”.
            </p>
            <Linha
              rotulo="Trilha tocada"
              valor={detalhe.triagem.trilha_escolhida ?? "—"}
            />
            <Linha rotulo="Tipo inferido" valor={detalhe.triagem.tipo ?? "—"} />
            <Linha
              rotulo="Gravidade inferida"
              valor={detalhe.triagem.gravidade ?? "—"}
            />
            <Linha
              rotulo="Confiança"
              valor={
                detalhe.triagem.confianca === undefined
                  ? "—"
                  : `${Math.round(detalhe.triagem.confianca * 100)}%`
              }
            />
            <Linha rotulo="Fonte" valor={detalhe.triagem.fonte ?? "—"} />
          </section>
        )}

        {detalhe && detalhe.notificacoes.length > 0 && (
          <section className="poto-detalhe-secao">
            <h3>Acionamentos ({detalhe.notificacoes.length})</h3>
            <ul className="poto-detalhe-lista">
              {detalhe.notificacoes.map((n, i) => (
                <li key={`${n.canal}-${i}`}>
                  <span
                    className={
                      n.sucesso ? "poto-pastilha-ok" : "poto-pastilha-falha"
                    }
                  >
                    {n.sucesso ? "enviado" : "falhou"}
                  </span>
                  <strong>{n.nome}</strong>
                  {/* `destino` vem mascarado do backend: só os últimos
                      dígitos. O contato completo fica no banco. */}
                  <span className="poto-detalhe-meta tabular">{n.destino}</span>
                  {n.escalonamento && (
                    <span className="poto-detalhe-meta">escalonamento</span>
                  )}
                  {n.detalhe && (
                    <span className="poto-detalhe-meta">{n.detalhe}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {detalhe && detalhe.estados.length > 0 && (
          <section className="poto-detalhe-secao">
            <h3>Linha do tempo</h3>
            <ol className="poto-detalhe-tempo">
              {detalhe.estados.map((e, i) => (
                <li key={i}>
                  <span className="poto-detalhe-meta tabular">
                    {hora(e.created_at)}
                  </span>
                  <span>
                    {e.de ? `${ROTULO_STATUS[e.de]} → ` : ""}
                    <strong>{ROTULO_STATUS[e.para]}</strong>
                  </span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {auditoria.length > 0 && (
          <section className="poto-detalhe-secao">
            <h3>Auditoria de mídia ({auditoria.length})</h3>
            <p className="poto-detalhe-nota">
              Cada ativação de câmera ou microfone deixa rastro. É o que separa
              um totem de segurança de um equipamento de vigilância.
            </p>
            <ol className="poto-detalhe-tempo">
              {auditoria.map((a, i) => (
                <li key={i}>
                  <span className="poto-detalhe-meta tabular">
                    {hora(a.created_at)}
                  </span>
                  <span>
                    <strong>{a.acao}</strong> · {a.dispositivo ?? a.dispositivo_id}
                    {a.duracao_seg !== null && ` · ${a.duracao_seg}s`}
                    {a.motivo && ` · ${a.motivo}`}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {!detalhe && !erro && (
          <p className="poto-detalhe-nota">Carregando a história do chamado…</p>
        )}
      </div>
    </aside>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <p className="poto-detalhe-linha">
      <span className="poto-card-rotulo">{rotulo}</span>
      <span>{valor}</span>
    </p>
  );
}

function hora(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function horaCompleta(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
