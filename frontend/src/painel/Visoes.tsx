/* As visões de "Totens" e "Análises" — MEL-009.
 *
 * Tudo aqui é derivado de `GET /chamados`, que o painel já busca. Nenhuma
 * requisição nova, nenhum endpoint novo — e nenhuma tela de "em breve".
 *
 * As barras são `<div>` com largura proporcional, e não um gráfico de
 * biblioteca: uma dependência de charts para desenhar sete barras horizontais
 * custaria mais que o problema que resolve, e num painel de plantão o número
 * escrito ao lado é o que se lê de verdade — a barra só dá a proporção.
 */
import type { Chamado } from "../comum/tipos";
import { analisar, resumirTotens } from "./abas";
import { COR_GRAVIDADE, ROTULO_GRAVIDADE, ROTULO_STATUS, TITULO_TIPO } from "./rotulos";

export function VisaoTotens({ chamados }: { chamados: Chamado[] }) {
  const totens = resumirTotens(chamados);

  if (totens.length === 0) {
    return <p className="poto-vazio">Nenhum totem registrou chamado ainda.</p>;
  }

  return (
    <div className="poto-totens">
      {totens.map((t) => (
        <article key={t.totem_id} className="poto-totem-card">
          <header>
            <h3 className="tabular">{t.totem_id}</h3>
            {/* Um totem com chamado aberto é onde alguém está esperando. É a
                informação que a aba existe para dar, então ela vem primeiro e
                em ferrugem. */}
            {t.abertos > 0 ? (
              <span className="poto-totem-abertos">
                <span aria-hidden="true" className="poto-ponto poto-ponto-vivo" />
                {t.abertos} aberto{t.abertos > 1 ? "s" : ""}
              </span>
            ) : (
              <span className="poto-totem-quieto">sem pendência</span>
            )}
          </header>

          <p className="poto-detalhe-linha">
            <span className="poto-card-rotulo">Total</span>
            <span className="tabular">{t.total}</span>
          </p>
          <p className="poto-detalhe-linha">
            <span className="poto-card-rotulo">Último</span>
            <span className="tabular">{quando(t.ultimo)}</span>
          </p>

          <div className="poto-barras">
            {(["risco_imediato", "risco_potencial", "orientacao"] as const).map(
              (g) =>
                t.porGravidade[g] > 0 && (
                  <Barra
                    key={g}
                    rotulo={ROTULO_GRAVIDADE[g]}
                    valor={t.porGravidade[g]}
                    total={t.total}
                    cor={COR_GRAVIDADE[g]}
                  />
                ),
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

export function VisaoAnalises({
  chamados,
  sla,
}: {
  chamados: Chamado[];
  sla?: Record<string, number | null>;
}) {
  const a = analisar(chamados, sla);

  if (a.total === 0) {
    return <p className="poto-vazio">Sem dados para analisar ainda.</p>;
  }

  return (
    <div className="poto-analises">
      <div className="poto-numeros">
        <Numero rotulo="Chamados" valor={String(a.total)} />
        <Numero rotulo="Em aberto" valor={String(a.abertos)} destaque={a.abertos > 0} />
        <Numero
          rotulo="Reconhecidos"
          valor={`${a.reconhecidos}/${a.total}`}
        />
        <Numero
          rotulo="Tempo até reconhecer"
          valor={a.medianaAck === null ? "—" : duracao(a.medianaAck)}
          /* Mediana, não média: um chamado esquecido a noite inteira puxaria a
             média para horas e faria o número mentir sobre a operação. */
          nota="mediana"
        />
        <Numero
          rotulo="Prazo estourado"
          valor={String(a.semAckNoPrazo)}
          destaque={a.semAckNoPrazo > 0}
          nota="sem reconhecimento"
        />
      </div>

      <section className="poto-detalhe-secao">
        <h3>Por trilha</h3>
        <div className="poto-barras">
          {(["seguranca", "mulher", "saude", "ouvidoria"] as const).map((t) => (
            <Barra
              key={t}
              rotulo={TITULO_TIPO[t]}
              valor={a.porTipo[t]}
              total={a.total}
              cor="var(--ink)"
            />
          ))}
        </div>
      </section>

      <section className="poto-detalhe-secao">
        <h3>Por gravidade</h3>
        <div className="poto-barras">
          {(["risco_imediato", "risco_potencial", "orientacao"] as const).map(
            (g) => (
              <Barra
                key={g}
                rotulo={ROTULO_GRAVIDADE[g]}
                valor={a.porGravidade[g]}
                total={a.total}
                cor={COR_GRAVIDADE[g]}
              />
            ),
          )}
        </div>
      </section>

      <section className="poto-detalhe-secao">
        <h3>Por situação</h3>
        <div className="poto-barras">
          {Object.entries(a.porStatus)
            .sort(([, x], [, y]) => (y ?? 0) - (x ?? 0))
            .map(([status, n]) => (
              <Barra
                key={status}
                rotulo={ROTULO_STATUS[status as keyof typeof ROTULO_STATUS]}
                valor={n ?? 0}
                total={a.total}
                cor="var(--muted)"
              />
            ))}
        </div>
      </section>
    </div>
  );
}

function Barra({
  rotulo,
  valor,
  total,
  cor,
}: {
  rotulo: string;
  valor: number;
  total: number;
  cor: string;
}) {
  const pct = total > 0 ? Math.round((valor / total) * 100) : 0;
  return (
    <div className="poto-barra">
      <span className="poto-barra-rotulo">{rotulo}</span>
      <span className="poto-barra-trilho">
        {/* `aria-hidden`: o número ao lado já informa. Uma barra anunciada
            como "72 por cento" duplicaria a leitura. */}
        <span
          aria-hidden="true"
          className="poto-barra-preenchimento"
          style={{ width: `${pct}%`, background: cor }}
        />
      </span>
      <span className="poto-barra-valor tabular">{valor}</span>
    </div>
  );
}

function Numero({
  rotulo,
  valor,
  nota,
  destaque = false,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  destaque?: boolean;
}) {
  return (
    <div className={destaque ? "poto-numero poto-numero-destaque" : "poto-numero"}>
      <span className="poto-numero-valor tabular">{valor}</span>
      <span className="poto-numero-rotulo">{rotulo}</span>
      {nota && <span className="poto-numero-nota">{nota}</span>}
    </div>
  );
}

function duracao(segundos: number): string {
  if (segundos < 60) return `${Math.round(segundos)}s`;
  const min = Math.floor(segundos / 60);
  if (min < 60) return `${min}min`;
  return `${Math.floor(min / 60)}h ${min % 60}min`;
}

function quando(iso: string): string {
  const d = new Date(iso);
  const agora = Date.now();
  const minutos = Math.floor((agora - d.getTime()) / 60000);
  if (minutos < 1) return "agora";
  if (minutos < 60) return `${minutos} min atrás`;
  /* Acima de um dia, a hora sozinha seria ambígua — "14:32" de quando? */
  if (agora - d.getTime() < 86_400_000) {
    return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}
