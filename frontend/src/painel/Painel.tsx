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
import { listarChamados, obterConfig } from "../comum/api";
import type { Chamado, ConfigPublica } from "../comum/tipos";
import { StatusPill } from "../componentes/StatusPill";
import { Wordmark } from "../componentes/Wordmark";
import { ListaChamados } from "./ListaChamados";

type Carga =
  | { estado: "carregando" }
  | { estado: "pronto" }
  | { estado: "erro"; mensagem: string };

export function Painel() {
  const [chamados, setChamados] = useState<Chamado[]>([]);
  const [config, setConfig] = useState<ConfigPublica | null>(null);
  const [carga, setCarga] = useState<Carga>({ estado: "carregando" });

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

  return (
    <div className="poto-painel">
      <header className="poto-painel-topo">
        <div className="poto-painel-marca">
          <Wordmark />
          <span className="poto-painel-subtitulo">
            Plataforma de Orientação, Triagem e Ouvidoria
          </span>
        </div>
        {/* O `StatusPill` do totem serve aqui sem mudança: a pergunta é a
            mesma — "o que estou vendo está atualizado?". */}
        <StatusPill online={carga.estado === "pronto"} />
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
          <ListaChamados
            chamados={chamados}
            onMudou={aplicar}
            sla={config?.sla}
          />
        )}
      </main>
    </div>
  );
}
