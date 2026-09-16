/* Cliente da API — camada única de acesso ao backend (MVP-048).
 *
 * Nenhum componente faz `fetch` direto. O motivo não é organização: é que
 * **todo envio precisa poder cair na fila offline** (MVP-057), e isso só é
 * possível se existir um lugar por onde tudo passa.
 *
 * A base vem de `location.origin`. Em produção o backend serve a aplicação da
 * mesma origem, então não há endpoint para configurar — a decisão de servir
 * tudo de um processo (MVP-026) é o que torna isto possível. Em
 * desenvolvimento o Vite faz proxy de `/api`, então a mesma expressão
 * funciona.
 */
import type {
  Chamado,
  ConfigPublica,
  Dispositivo,
  EventoIn,
  EventoOut,
  MidiaSessao,
  PanicoIn,
  PanicoOut,
  TipoOcorrencia,
} from "./tipos";

const BASE = "/api/v1";

/** Teto de cada requisição. Um totem não pode ficar preso num fetch pendurado:
 * `fetch` sem sinal de abortar espera o timeout do sistema operacional, que
 * pode ser mais de um minuto. */
const TIMEOUT_MS = 8000;

/** Falha de transporte — rede caiu, DNS, timeout, servidor inalcançável.
 *
 * Distinguida de `ErroApi` porque o tratamento é **oposto**: erro de rede é
 * candidato a enfileirar e reenviar; erro da API (422, 404) significa que o
 * envio chegou e foi rejeitado, e reenviar o mesmo payload falharia de novo. */
export class ErroRede extends Error {
  constructor(causa?: unknown) {
    super("falha de rede");
    this.name = "ErroRede";
    this.cause = causa;
  }
}

/** Resposta de erro **do servidor**. Chegou, foi processada, foi recusada. */
export class ErroApi extends Error {
  /* Campos declarados, não propriedades de construtor: o `tsconfig` liga
   * `erasableSyntaxOnly`, que proíbe sintaxe de TypeScript sem equivalente em
   * JavaScript — a garantia de que apagar os tipos basta para rodar. */
  readonly status: number;
  readonly detalhe: string;

  constructor(status: number, detalhe: string) {
    super(`HTTP ${status}: ${detalhe}`);
    this.name = "ErroApi";
    this.status = status;
    this.detalhe = detalhe;
  }
}

async function requisitar<T>(caminho: string, init?: RequestInit): Promise<T> {
  const controle = new AbortController();
  const prazo = window.setTimeout(() => controle.abort(), TIMEOUT_MS);

  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      ...init,
      signal: controle.signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (erro) {
    /* `fetch` só rejeita por falha de transporte ou abort. Status de erro vem
     * como resposta resolvida — é o tratamento abaixo. */
    throw new ErroRede(erro);
  } finally {
    window.clearTimeout(prazo);
  }

  if (!resposta.ok) {
    /* O corpo pode não ser JSON (um 502 de proxy devolve HTML). Ler como texto
     * e tentar decodificar evita que um erro de servidor vire um erro de
     * parsing, que confundiria o diagnóstico. */
    const texto = await resposta.text().catch(() => "");
    let detalhe = texto;
    try {
      detalhe = JSON.parse(texto).detail ?? texto;
    } catch {
      /* Não era JSON; o texto cru serve. */
    }
    throw new ErroApi(resposta.status, detalhe || resposta.statusText);
  }

  return (await resposta.json()) as T;
}

/** Monta um evento com `evento_id` **antes** do envio.
 *
 * É o ponto mais importante deste arquivo. O id nasce no totem, não no
 * servidor, porque é ele que garante a idempotência: um evento que falhou,
 * ficou na fila e foi reenviado carrega o **mesmo** id, e o backend devolve o
 * chamado que já existe em vez de criar um segundo alarme para a mesma
 * emergência.
 *
 * Gerar o id no envio, e não aqui, quebraria isso: cada tentativa teria um id
 * novo e a fila multiplicaria o chamado.
 */
export function novoEvento(
  tipo: TipoOcorrencia,
  extra: Partial<Omit<EventoIn, "evento_id" | "tipo_ocorrencia">> = {},
): EventoIn {
  return {
    evento_id: gerarId(),
    totem_id: TOTEM_ID,
    tipo_ocorrencia: tipo,
    origem_acionamento: "touch",
    /* Diagnóstico apenas: o horário autoritativo é o `created_at` do servidor.
     * O backend aceita este campo como string livre de propósito — um tablet
     * com a hora dessincronizada não pode fazer um pedido de socorro falhar. */
    timestamp_local: new Date().toISOString(),
    ...extra,
  };
}

export function novoPanico(modo: PanicoIn["modo"] = "normal"): PanicoIn {
  return {
    evento_id: gerarId(),
    totem_id: TOTEM_ID,
    modo,
    timestamp_local: new Date().toISOString(),
  };
}

/** UUID v4. `crypto.randomUUID` exige contexto seguro (HTTPS ou localhost).
 *
 * Na rede local da universidade o totem roda em **HTTP**, e ali a API não
 * existe. O fallback com `crypto.getRandomValues` mantém a idempotência
 * funcionando — que é o que de fato importa; unicidade criptográfica não é
 * requisito, unicidade é.
 */
function gerarId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();

  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40; // versão 4
  b[8] = (b[8] & 0x3f) | 0x80; // variante RFC 4122
  const hex = [...b].map((n) => n.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Identificação deste totem.
 *
 * Vem de `VITE_POTO_TOTEM_ID` no build. Um valor fixo no código impediria dois
 * totens de coexistirem — e o painel precisa saber **de onde** veio o chamado
 * para despachar a equipe ao lugar certo.
 */
export const TOTEM_ID = import.meta.env.VITE_POTO_TOTEM_ID ?? "TOTEM-DEV-01";

export function enviarEvento(evento: EventoIn): Promise<EventoOut> {
  return requisitar<EventoOut>("/eventos", {
    method: "POST",
    body: JSON.stringify(evento),
  });
}

export function enviarPanico(panico: PanicoIn): Promise<PanicoOut> {
  return requisitar<PanicoOut>("/panico", {
    method: "POST",
    body: JSON.stringify(panico),
  });
}

export function listarChamados(filtros: {
  tipo?: string;
  status?: string;
  gravidade?: string;
} = {}): Promise<Chamado[]> {
  const busca = new URLSearchParams(
    Object.entries(filtros).filter(([, v]) => v) as [string, string][],
  );
  const consulta = busca.toString();
  return requisitar<Chamado[]>(`/chamados${consulta ? `?${consulta}` : ""}`);
}

export function ackChamado(chamadoId: string): Promise<Chamado> {
  return requisitar<Chamado>(
    `/chamados/${encodeURIComponent(chamadoId)}/ack`,
    { method: "POST" },
  );
}

export function atualizarChamado(
  chamadoId: string,
  mudanca: { status?: string; observacao?: string },
): Promise<Chamado> {
  return requisitar<Chamado>(`/chamados/${encodeURIComponent(chamadoId)}`, {
    method: "PATCH",
    body: JSON.stringify(mudanca),
  });
}

export function escalonarChamado(
  chamadoId: string,
  canal: string,
): Promise<CanalResultadoResposta> {
  return requisitar<CanalResultadoResposta>(
    `/chamados/${encodeURIComponent(chamadoId)}/escalonar`,
    { method: "POST", body: JSON.stringify({ canal }) },
  );
}

type CanalResultadoResposta = {
  canal: string;
  nome: string;
  sucesso: boolean;
  detalhe: string | null;
};

export function obterConfig(): Promise<ConfigPublica> {
  return requisitar<ConfigPublica>("/config");
}

/* --- Mídia (MVP-078) ------------------------------------------------------
 *
 * Três funções e uma assimetria proposital: `fecharMidia` tem um caminho
 * separado para o descarregamento da página. Ver a nota nela.
 */

export function listarDispositivos(): Promise<Dispositivo[]> {
  return requisitar<Dispositivo[]>("/dispositivos");
}

export function abrirMidia(
  chamadoId: string,
  dispositivoId: string,
): Promise<MidiaSessao> {
  return requisitar<MidiaSessao>(
    `/chamados/${encodeURIComponent(chamadoId)}/midia`,
    { method: "POST", body: JSON.stringify({ dispositivo_id: dispositivoId }) },
  );
}

/** Encerra a sessão. Sem `sessaoId`, encerra **todas** as do chamado.
 *
 * Devolve `204` sem corpo, então não passa pelo `requisitar` — ele faz
 * `resposta.json()` e um 204 não tem JSON para decodificar.
 */
export async function fecharMidia(
  chamadoId: string,
  sessaoId?: string,
): Promise<void> {
  const busca = sessaoId ? `?sessao=${encodeURIComponent(sessaoId)}` : "";
  await fetch(
    `${BASE}/chamados/${encodeURIComponent(chamadoId)}/midia${busca}`,
    { method: "DELETE" },
  );
}

/** A mesma coisa, para quando a página está sendo descarregada.
 *
 * `keepalive` é o que faz a requisição sobreviver ao descarregamento: um
 * `fetch` normal disparado em `pagehide` é **cancelado** junto com a página, e
 * a sessão ficaria aberta até expirar — dez minutos de câmera ligada na
 * auditoria, sem ninguém assistindo.
 *
 * `sendBeacon` seria o caminho natural, mas ele só faz `POST`. Daí o `fetch`
 * com `keepalive`, que aceita qualquer método.
 *
 * Não é garantia: o navegador pode matar a aba antes. A rede de segurança é do
 * backend, que expira a sessão sozinho e varre as vencidas no worker de SLA.
 */
export function fecharMidiaAoSair(chamadoId: string): void {
  void fetch(`${BASE}/chamados/${encodeURIComponent(chamadoId)}/midia`, {
    method: "DELETE",
    keepalive: true,
  }).catch(() => {
    /* A página está indo embora; não há a quem reportar. */
  });
}
