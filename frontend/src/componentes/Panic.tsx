/* Botão de pânico — MVP-046.
 *
 * Sempre o elemento de maior peso visual da tela. Como é **virtual** e não
 * físico, precisa de intenção deliberada: dispara só depois de **1000 ms de
 * pressão contínua**.
 *
 * A razão não é cerimônia. Um toque simples numa tela pública dispara com um
 * roçar de mão, uma mochila apoiada, uma criança passando — e cada disparo faz
 * broadcast **real** para o CSV e a Sala Lilás, com status `alerta_ativo`, que
 * não fecha sozinho. O custo de um falso positivo é uma equipe despachada e a
 * confiança da central no sistema.
 *
 * O custo do desenho oposto — exigir confirmação — seria pior: uma tela de
 * "tem certeza?" pede uma decisão de quem está em pânico. Daí a escolha:
 * **esforço físico em vez de decisão cognitiva.** Segurar é algo que o corpo
 * faz; confirmar é algo que a cabeça faz, e a cabeça é o que está ocupado.
 *
 * O anel de progresso não é enfeite: sem realimentação, quem segura por 400 ms
 * e não vê nada acontecer conclui que o botão não funciona e solta.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useMovimentoReduzido } from "../comum/useMovimentoReduzido";
import { Sym } from "./Sym";

/** Pressão necessária, em milissegundos. */
export const DURACAO_PRESSAO = 1000;

/** Passo da animação do anel. ~60 fps sem depender de requestAnimationFrame. */
const PASSO_MS = 16;

/** Degraus do progresso quando o movimento é reduzido. */
const DEGRAUS = 4;

type Props = {
  onAcionar: () => void;
  desabilitado?: boolean;
};

export function Panic({ onAcionar, desabilitado = false }: Props) {
  const [progresso, setProgresso] = useState(0); // 0..1
  const [pressionando, setPressionando] = useState(false);
  const movimentoReduzido = useMovimentoReduzido();
  const inicio = useRef<number | null>(null);
  const timer = useRef<number | null>(null);
  /* Guarda o callback mais recente sem reiniciar o timer: sem isto, um
   * `onAcionar` recriado a cada render do pai cancelaria a pressão em curso. */
  const acionar = useRef(onAcionar);
  acionar.current = onAcionar;

  const limpar = useCallback(() => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
    inicio.current = null;
    setPressionando(false);
    setProgresso(0);
  }, []);

  const comecar = useCallback(() => {
    if (desabilitado || timer.current !== null) return;
    inicio.current = performance.now();
    setPressionando(true);

    timer.current = window.setInterval(() => {
      if (inicio.current === null) return;
      const decorrido = performance.now() - inicio.current;
      const fracao = Math.min(decorrido / DURACAO_PRESSAO, 1);
      setProgresso(fracao);

      if (fracao >= 1) {
        /* Limpa **antes** de acionar: se `onAcionar` levantar, o botão não pode
         * ficar preso em "pressionando" com um timer rodando. */
        limpar();
        /* Guarda porque a API não existe em iOS nem em desktop, e em alguns
         * navegadores lança se chamada sem gesto do usuário. */
        try {
          navigator.vibrate?.(200);
        } catch {
          /* Vibração é conforto, não requisito. */
        }
        acionar.current();
      }
    }, PASSO_MS);
  }, [desabilitado, limpar]);

  /* Solta antes de completar: **cancela e não envia nada**. É o critério que
   * torna o toque acidental inofensivo. */
  const cancelar = useCallback(() => {
    if (timer.current !== null) limpar();
  }, [limpar]);

  /* O timer precisa morrer se o componente sair da árvore no meio da pressão —
   * caso real, porque a tela troca ao acionar qualquer trilha. */
  useEffect(() => limpar, [limpar]);

  const rotulo = pressionando ? "Segure para acionar" : "Pânico";

  /* Com movimento reduzido a barra salta de 25 em 25% em vez de correr: quatro
   * degraus são percebidos como progresso sem movimento contínuo. */
  const preenchimento = movimentoReduzido
    ? Math.floor(progresso * DEGRAUS) / DEGRAUS
    : progresso;

  return (
    <button
      type="button"
      className="poto-panic"
      disabled={desabilitado}
      /* `pointer*` cobre toque, mouse e caneta com um só conjunto de eventos.
       * `pointercancel` é o que dispara quando o sistema toma o gesto (uma
       * notificação chegando, o navegador decidindo que é rolagem) — sem
       * tratá-lo, o botão ficaria preso em "pressionando" para sempre. */
      onPointerDown={comecar}
      onPointerUp={cancelar}
      onPointerLeave={cancelar}
      onPointerCancel={cancelar}
      /* Enter e Espaço **mantidos** têm o mesmo efeito. O navegador repete
       * `keydown` enquanto a tecla está pressionada, e o `comecar` ignora
       * repetição porque só age se não houver timer. */
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault(); /* impede o clique sintético do navegador */
          comecar();
        }
      }}
      onKeyUp={(e) => {
        if (e.key === "Enter" || e.key === " ") cancelar();
      }}
      onBlur={cancelar}
      aria-describedby="poto-panic-ajuda"
      style={{
        position: "relative",
        overflow: "hidden",
        width: "100%",
        minHeight: 64,
        borderRadius: "var(--r-pill)",
        background: "var(--rust)",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-sm)",
        fontFamily: "var(--font-display)",
        fontWeight: 400,
        fontSize: 14,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        opacity: desabilitado ? 0.5 : 1,
      }}
    >
      {/* Barra de progresso por baixo do conteúdo. `scaleX` em vez de `width`
          porque transforma na GPU e não provoca relayout a cada 16 ms. */}
      <span
        aria-hidden="true"
        className="poto-panic-barra"
        style={{
          position: "absolute",
          inset: 0,
          background: "var(--rust-d)",
          transformOrigin: "left center",
          transform: `scaleX(${preenchimento})`,
        }}
      />
      <span
        style={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          gap: "var(--space-sm)",
        }}
      >
        <Sym nome="emergency" tamanho="md" cor="#fff" />
        {rotulo}
      </span>

      {/* Progresso também como número, para leitor de tela: a barra é visual e
          `aria-hidden`. */}
      <span className="visually-hidden" aria-live="off">
        {pressionando ? `${Math.round(progresso * 100)}%` : ""}
      </span>
    </button>
  );
}

/** Texto de apoio. Fica fora do botão para não ser lido como parte do rótulo. */
export function PanicAjuda() {
  return (
    <p
      id="poto-panic-ajuda"
      style={{
        fontFamily: "var(--font-ui)",
        fontSize: 13,
        color: "var(--muted)",
        textAlign: "center",
        marginTop: "var(--space-xs)",
      }}
    >
      Segure por 1 segundo para acionar
    </p>
  );
}
