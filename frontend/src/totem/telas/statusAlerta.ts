import type { StatusChamado } from "../../comum/tipos";

/* Texto do status ao vivo do alerta — MVP-054.
 *
 * Em arquivo próprio para não quebrar o fast refresh do `AlertaAtivo`: um
 * módulo que exporta componente e função perde a recarga a quente.
 */
/** Texto do status ao vivo, a partir do status do chamado.
 *
 * Escrito do ponto de vista de **quem espera**, não do sistema: "Central
 * recebeu" e não "reconhecido". A pessoa quer saber o que está acontecendo com
 * ela, não em que estado está a linha do banco.
 */
export function textoDoStatus(status: StatusChamado): string {
  switch (status) {
    case "alerta_ativo":
    case "notificado":
    case "roteado":
    case "recebido":
      return "Aguardando central";
    case "reconhecido":
      return "Central recebeu";
    case "em_atendimento":
    case "escalonado":
      return "Atendimento a caminho";
    case "encerrado":
      return "Atendimento concluído";
    case "cancelado":
      return "Chamado cancelado";
    case "falha_notificacao":
      /* Não diz "falhou". A pessoa não pode fazer nada sobre isso, e a
       * informação acionável é outra: os botões de escalonamento abaixo. */
      return "Aguardando central";
  }
}
