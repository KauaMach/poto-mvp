/* Painel da central — MVP-060.
 *
 * O contraponto do totem. Lá a tela tem um propósito e dois toques; aqui ela é
 * uma superfície de trabalho: alguém de plantão olhando uma lista que muda
 * sozinha, por horas.
 *
 * Duas decisões moldam o arquivo:
 *
 * - **A lista é estado local, atualizada por WebSocket** (MVP-062), não
 *   recarregada em laço. Um `setInterval` buscando `/chamados` a cada 5 s
 *   custaria tráfego constante e ainda chegaria até 5 s atrasado — num painel
 *   de emergência, "acende em menos de 1 s" é requisito.
 * - **O `GET /chamados` acontece uma vez, no mount.** Ele é o ponto de partida;
 *   o WebSocket cuida do resto. Se a conexão cair e voltar, uma recarga
 *   reconcilia.
 */
import { useCallback, useEffect, useState } from "react";
import { listarChamados, listarDispositivos, obterConfig } from "../comum/api";
import type {
  Chamado,
  ConfigPublica,
  Dispositivo,
  EventoWS,
} from "../comum/tipos";
import { useEventosWS } from "../comum/useEventosWS";
import { Wordmark } from "../componentes/Wordmark";
import { BarraFiltros } from "./BarraFiltros";
import { aplicarFiltros, FILTROS_VAZIOS, temFiltro, type Filtros } from "./filtros";
import { IndicadorTempoReal } from "./IndicadorTempoReal";
import { ListaChamados } from "./ListaChamados";

type Carga =
  | { estado: "carregando" }
  | { estado: "pronto" }
  | { estado: "erro"; mensagem: string };

export function Painel() {
  const [chamados, setChamados] = useState<Chamado[]>([]);
  const [config, setConfig] = useState<ConfigPublica | null>(null);
  const [carga, setCarga] = useState<Carga>({ estado: "carregando" });
  /* Buscado **uma vez, aqui**, e passado para baixo (MVP-078). Com vinte
   * cartões na tela, cada um pedindo `/dispositivos`, seriam vinte requisições
   * para a mesma resposta. */
  const [dispositivos, setDispositivos] = useState<Dispositivo[]>([]);
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VAZIOS);

  /* Insere ou substitui **no lugar**, indexando por `chamado_id`.
   *
   * É o que permite o WebSocket (MVP-062) atualizar um cartão sem reconstruir
   * a lista — e sem isto um `atualizado` faria a lista piscar inteira, perdendo
   * a posição de rolagem de quem está lendo.
   */
  const aplicar = useCallback((chamado: Chamado) => {
    setChamados((atuais) => {
      const i = atuais.findIndex((c) => c.chamado_id === chamado.chamado_id);
      if (i === -1) return [chamado, ...atuais];
      const copia = [...atuais];
      copia[i] = chamado;
      return copia;
    });
  }, []);

  /* O hub transmite `{evento, dados}` com o mesmo contrato do REST — é a
   * garantia da MVP-033, que unificou `para_painel()` nos cinco pontos de
   * broadcast. Sem ela, este handler precisaria de um segundo formato de
   * `Chamado` e o tipo declarado mentiria sobre um dos dois. */
  const aoEvento = useCallback(
    (evento: EventoWS) => {
      if (evento.evento === "novo_chamado" || evento.evento === "atualizado") {
        aplicar(evento.dados);
      }
      /* `conectado` e `ping` não mexem na lista: o primeiro é boas-vindas, o
       * segundo é keepalive. O estado da conexão vem do próprio hook. */
    },
    [aplicar],
  );

  const estadoWS = useEventosWS(aoEvento);

  useEffect(() => {
    let vivo = true;

    void (async () => {
      try {
        /* Em paralelo: o `/config` não depende da lista, e serializar somaria
         * dois tempos de ida e volta antes de a tela aparecer. */
        const [lista, cfg] = await Promise.all([
          listarChamados(),
          obterConfig(),
        ]);
        if (!vivo) return;
        setChamados(lista);
        setConfig(cfg);
        setCarga({ estado: "pronto" });
      } catch (erro) {
        if (!vivo) return;
        setCarga({
          estado: "erro",
          mensagem:
            erro instanceof Error && erro.name === "ErroApi"
              ? "Sem permissão para ver os chamados. Confira o token do painel."
              : "Não foi possível carregar os chamados.",
        });
      }
    })();

    return () => {
      vivo = false;
    };
  }, []);

  /* Os dispositivos vêm num efeito **separado**, e isso não é desorganização.
   *
   * Se `/dispositivos` entrasse no `Promise.all` acima, uma falha na detecção
   * de hardware — câmera arrancada, `v4l2-ctl` ausente, `arecord` travado —
   * levaria a tela inteira para o estado de erro e o operador não veria
   * chamado nenhum. A mídia é acessório; **a lista é o trabalho**.
   *
   * Falhar aqui é silencioso de propósito: sem dispositivos, o cartão mostra
   * "nenhuma câmera ou microfone disponível", que é a mesma coisa que o
   * operador precisa saber em ambos os casos.
   */
  useEffect(() => {
    let vivo = true;
    void listarDispositivos()
      .then((lista) => {
        if (vivo) setDispositivos(lista);
      })
      .catch(() => {
        /* Lista vazia é o estado inicial e a degradação correta. */
      });
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <div className="poto-painel">
      <header className="poto-painel-topo">
        <div className="poto-painel-marca">
          <Wordmark />
          <span className="poto-painel-subtitulo">
            Plataforma de Orientação, Triagem e Ouvidoria
          </span>
        </div>
        {/* Não é o `StatusPill` do totem: a pergunta ali é "o que eu tocar
            chega agora?", e aqui é "o que está na tela é ao vivo?". Num painel
            onde nada acontece por vinte minutos, silêncio e conexão morta
            parecem idênticos e significam o oposto. */}
        <IndicadorTempoReal estado={estadoWS} />
      </header>

      <main className="poto-painel-corpo">
        {carga.estado === "carregando" && (
          <p className="poto-vazio">Carregando chamados…</p>
        )}

        {carga.estado === "erro" && (
          <p className="poto-vazio" role="alert">
            {carga.mensagem}
          </p>
        )}

        {carga.estado === "pronto" && (
          <>
            <BarraFiltros
              chamados={chamados}
              filtros={filtros}
              onMudar={setFiltros}
              onLimpar={() => setFiltros(FILTROS_VAZIOS)}
            />
            <ListaChamados
              chamados={aplicarFiltros(chamados, filtros)}
              onMudou={aplicar}
              sla={config?.sla}
              dispositivos={dispositivos}
              filtrado={temFiltro(filtros)}
            />
          </>
        )}
      </main>
    </div>
  );
}
