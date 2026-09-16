/* Galeria de componentes — MVP-047.
 *
 * Quatro tasks desta fase pedem validação visual: "conferir contra
 * Tela-Totem.png", "comparação lado a lado", "renderizar as três variantes
 * lado a lado", "segurar 1 s e tocar 5× rápido". Sem um lugar onde tudo
 * apareça junto, cada uma dessas conferências exigiria montar uma tela
 * descartável — e nenhuma ficaria repetível.
 *
 * Fica numa rota **só de desenvolvimento** (`/galeria`). Não é uma tela do
 * produto: o totem não deve ter como chegar aqui, e num kiosk em modo quiosque
 * ninguém digita URL. A rota existe enquanto o design system estiver em
 * construção.
 */
import { useState } from "react";
import { Choice } from "./componentes/Choice";
import { Confirm } from "./componentes/Confirm";
import { Panic, PanicAjuda } from "./componentes/Panic";
import { StatusPill } from "./componentes/StatusPill";
import { Sym, TAMANHOS_SYM, type GlifoSym } from "./componentes/Sym";
import { Wordmark } from "./componentes/Wordmark";

const GLIFOS: GlifoSym[] = [
  "stethoscope",
  "shield",
  "female",
  "info",
  "emergency",
  "check",
  "arrow_back",
];

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: "var(--space-xxl)" }}>
      <h2
        style={{
          fontFamily: "var(--font-ui)",
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--muted)",
          marginBottom: "var(--space-md)",
          paddingBottom: "var(--space-xs)",
          borderBottom: "1.5px solid var(--line)",
        }}
      >
        {titulo}
      </h2>
      {children}
    </section>
  );
}

export function Galeria() {
  const [acionamentos, setAcionamentos] = useState<string[]>([]);

  return (
    <main
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        padding: "var(--space-xl) var(--space-lg)",
      }}
    >
      <p
        style={{
          fontFamily: "var(--font-ui)",
          fontSize: 13,
          color: "var(--muted)",
          marginBottom: "var(--space-xl)",
        }}
      >
        Galeria do design system — rota de desenvolvimento, não faz parte do
        produto.
      </p>

      <Secao titulo="Wordmark e StatusPill (MVP-044)">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "var(--space-lg)",
            flexWrap: "wrap",
            padding: "var(--space-md)",
            border: "1.5px solid var(--line)",
            borderRadius: "var(--r-md)",
            background: "var(--bg)",
          }}
        >
          <Wordmark onInicio={() => window.scrollTo(0, 0)} />
          <div style={{ display: "flex", gap: "var(--space-lg)", flexWrap: "wrap" }}>
            <StatusPill online />
            <StatusPill online={false} />
            <StatusPill online={false} naFila={3} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Ícones · os 7 glifos do subset (MVP-041, MVP-043)">
        <div style={{ display: "flex", gap: "var(--space-lg)", flexWrap: "wrap" }}>
          {GLIFOS.map((nome) => (
            <div key={nome} style={{ textAlign: "center", minWidth: 96 }}>
              <Sym nome={nome} tamanho="lg" cor="var(--rust)" />
              <p
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: 11,
                  color: "var(--muted)",
                  marginTop: "var(--space-xs)",
                }}
              >
                {nome}
              </p>
            </div>
          ))}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: "var(--space-lg)",
            marginTop: "var(--space-lg)",
          }}
        >
          {Object.keys(TAMANHOS_SYM).map((t) => (
            <div key={t} style={{ textAlign: "center" }}>
              <Sym
                nome="shield"
                tamanho={t as keyof typeof TAMANHOS_SYM}
                cor="var(--ink)"
              />
              <p
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: 11,
                  color: "var(--muted)",
                }}
              >
                {t} · {TAMANHOS_SYM[t as keyof typeof TAMANHOS_SYM]}px
              </p>
            </div>
          ))}
        </div>
      </Secao>

      <Secao titulo="Choice · as 4 trilhas, grade 2×2 (MVP-045)">
        <div className="poto-grid" style={{ maxWidth: 780 }}>
          <Choice
            icone="stethoscope"
            rotulo="Emergência médica"
            onClick={() => setAcionamentos((a) => [...a, "saude"])}
          />
          <Choice
            icone="shield"
            rotulo="Segurança"
            onClick={() => setAcionamentos((a) => [...a, "seguranca"])}
          />
          <Choice
            icone="female"
            rotulo="Assédio / Sala Lilás"
            onClick={() => setAcionamentos((a) => [...a, "mulher"])}
          />
          <Choice
            icone="info"
            rotulo="Outros"
            variante="muted"
            onClick={() => setAcionamentos((a) => [...a, "ouvidoria"])}
          />
        </div>
        <div style={{ marginTop: "var(--space-lg)", maxWidth: 380 }}>
          <Choice
            icone="shield"
            rotulo="Desabilitado (envio em curso)"
            onClick={() => {}}
            desabilitado
          />
        </div>
      </Secao>

      <Secao titulo="Panic · segure 1 s (MVP-046)">
        <div style={{ maxWidth: 780 }}>
          <Panic onAcionar={() => setAcionamentos((a) => [...a, "PÂNICO"])} />
          <PanicAjuda />
        </div>
        <p
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: 13,
            color: "var(--muted)",
            marginTop: "var(--space-md)",
          }}
        >
          Validação da task: toque rápido 5× e confirme que a lista abaixo
          continua sem "PÂNICO".
        </p>
        <pre
          className="tabular"
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: 13,
            background: "var(--bg)",
            border: "1.5px solid var(--line)",
            borderRadius: "var(--r-sm)",
            padding: "var(--space-sm) var(--space-md)",
            marginTop: "var(--space-xs)",
            minHeight: 44,
          }}
        >
          {acionamentos.length ? acionamentos.join("\n") : "(nenhum acionamento)"}
        </pre>
      </Secao>

      <Secao titulo="Confirm · as três variantes (MVP-047)">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "var(--space-md)",
          }}
        >
          {(
            [
              ["padrao", "Pedido registrado. Aguarde atendimento.", "CALL-2026-000042"],
              [
                "critico",
                "Pedido de segurança enviado. Mantenha a calma, ajuda a caminho.",
                "CALL-2026-000043",
              ],
              ["neutral", "Seu pedido foi registrado. Aguarde atendimento.", "CALL-2026-000044"],
            ] as const
          ).map(([variante, mensagem, protocolo]) => (
            <div
              key={variante}
              style={{
                border: "1.5px solid var(--line)",
                borderRadius: "var(--r-md)",
                overflow: "hidden",
                minHeight: 380,
              }}
            >
              <Confirm
                variante={variante}
                mensagem={mensagem}
                protocolo={protocolo}
              />
            </div>
          ))}
        </div>
        <p
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: 13,
            color: "var(--muted)",
            marginTop: "var(--space-md)",
          }}
        >
          A variante <strong>neutral</strong> recebe protocolo e{" "}
          <strong>não o mostra</strong> — é a trilha discreta.
        </p>
        <div
          style={{
            marginTop: "var(--space-md)",
            maxWidth: 420,
            border: "1.5px solid var(--line)",
            borderRadius: "var(--r-md)",
            overflow: "hidden",
          }}
        >
          <Confirm
            mensagem="Pedido registrado."
            protocolo="CALL-2026-000045"
            offline
          />
        </div>
      </Secao>
    </main>
  );
}
