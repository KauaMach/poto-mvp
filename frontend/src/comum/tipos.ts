/* Tipos da API — espelho dos contratos de `backend/app/models.py`.
 *
 * Escritos à mão e não gerados do OpenAPI de propósito: gerar exigiria um passo
 * de build acoplado a um backend rodando, e a Pi **não compila** o frontend
 * (ARCHITECTURE.md D1c). A superfície é pequena e estável.
 *
 * O preço é que uma divergência entre este arquivo e o backend só aparece em
 * tempo de execução. A mitigação é os testes de contrato da MVP-039, que
 * cobram a forma das respostas pelo lado do servidor.
 */

/** As quatro trilhas do totem. */
export type TipoOcorrencia = "seguranca" | "mulher" | "saude" | "ouvidoria";

/** `discreto` é decisão do roteador, não preferência de quem usa. */
export type Modo = "normal" | "discreto";

export type OrigemAcionamento = "touch" | "botao_fisico" | "panico";

/** Ordem de proteção: orientacao < risco_potencial < risco_imediato. */
export type Gravidade = "risco_imediato" | "risco_potencial" | "orientacao";

export type StatusChamado =
  | "recebido"
  | "roteado"
  | "notificado"
  | "alerta_ativo"
  | "reconhecido"
  | "em_atendimento"
  | "escalonado"
  | "encerrado"
  | "falha_notificacao"
  | "cancelado";

/** O que a tela deve mostrar. **Decidido pelo backend**, nunca pelo cliente. */
export type InstrucaoTotem = {
  mensagem_tela: string;
  feedback_sonoro: boolean;
  tela_neutra: boolean;
};

export type EventoIn = {
  /** UUID gerado no totem **antes** do envio — é a chave de idempotência. */
  evento_id: string;
  totem_id: string;
  tipo_ocorrencia: TipoOcorrencia;
  modo?: Modo;
  origem_acionamento?: OrigemAcionamento;
  texto_livre?: string | null;
  timestamp_local?: string | null;
};

export type EventoOut = {
  chamado_id: string;
  status: StatusChamado;
  canal_roteado: string;
  gravidade: Gravidade;
  instrucao_totem: InstrucaoTotem;
  duplicado: boolean;
};

export type PanicoIn = {
  evento_id: string;
  totem_id: string;
  modo?: Modo;
  timestamp_local?: string | null;
};

/* Nem `CanalResultado` nem `CanalOpcao` têm `destino`: `/panico` é aberto, e
 * devolver o telefone do CSV ali entregaria os contatos institucionais a
 * qualquer um que alcance a API. */
export type CanalResultado = {
  canal: string;
  nome: string;
  sucesso: boolean;
  detalhe: string | null;
};

export type CanalOpcao = { canal: string; nome: string };

export type PanicoOut = {
  chamado_id: string;
  status: StatusChamado;
  gravidade: Gravidade;
  resultados: CanalResultado[];
  escalonamento_disponivel: CanalOpcao[];
  duplicado: boolean;
};

export type Chamado = {
  chamado_id: string;
  totem_id: string;
  tipo_ocorrencia: TipoOcorrencia;
  modo: Modo;
  origem_acionamento: OrigemAcionamento;
  gravidade: Gravidade;
  canal_roteado: string;
  fallback: string | null;
  status: StatusChamado;
  texto_livre: string | null;
  observacao: string | null;
  timestamp_local: string | null;
  created_at: string;
  updated_at: string;
  acked_at: string | null;
};

export type ConfigPublica = {
  /** Prazos por gravidade. `orientacao` é `null` — aquele nível não escalona. */
  sla: Record<Gravidade, number | null>;
  canais_estado: CanalOpcao[];
  totem_offline_seg: number;
};

/** Eventos do WebSocket do painel. */
export type EventoWS =
  | { evento: "conectado"; dados: { paineis: number; servidor: string } }
  | { evento: "ping"; dados: Record<string, never> }
  | { evento: "novo_chamado"; dados: Chamado }
  | { evento: "atualizado"; dados: Chamado }
  /* MEL-006. No canal do totem (`/ws/chamado/{id}`) estes chegam projetados —
   * só `chamado_id`, `status` e `stream_url` (`CAMPOS_TOTEM`). É assim que a
   * tela de alerta descobre onde buscar o vídeo do operador. */
  | {
      evento: "chamada_iniciada";
      dados: { chamado_id: string; stream_url: string; audio_url: string };
    }
  | { evento: "chamada_encerrada"; dados: { chamado_id: string } };

/* --- Mídia (MVP-073 / MVP-077) ------------------------------------------- */

export type TipoDispositivo = "camera" | "microfone";

/** Um dispositivo de captura, como `GET /dispositivos` o descreve.
 *
 * `capacidades` fica como `Record<string, unknown>`: o conteúdo depende da
 * origem (CSI traz `indice` e `rotacao`, ALSA traz `device` e `taxa_hz`), e
 * tipar cada variante aqui obrigaria a mexer no frontend a cada hardware novo
 * — sem que nenhuma tela use esses campos.
 */
export type Dispositivo = {
  id: string;
  tipo: TipoDispositivo;
  nome: string;
  dono: string;
  status: string;
  capacidades: Record<string, unknown>;
};

/** Autorização de captura concedida por `POST /chamados/{id}/midia`.
 *
 * `stream_url` **já vem montada**, com a sessão embutida. O painel não compõe
 * essa URL: o formato do token é assunto do backend, e duplicá-lo aqui faria
 * duas implementações divergirem no dia em que ele mudasse.
 */
export type MidiaSessao = {
  sessao_id: string;
  stream_url: string;
  /** Segundos até expirar. O backend encerra sozinho ao fim do prazo. */
  expira_em: number;
  dispositivo_id: string;
  tipo: TipoDispositivo;
};

/** Videochamada autorizada da central para o totem (MEL-004).
 *
 * Duas URLs porque são dois papéis: a central **envia** quadros por
 * `envio_url`, o totem **consome** de `stream_url`. Vêm montadas pelo backend.
 */
export type ChamadaSessao = {
  sessao_id: string;
  envio_url: string;
  stream_url: string;
  /** Uma URL só: a central publica com `POST`, o totem consome com `GET`. */
  audio_url: string;
  expira_em: number;
};
