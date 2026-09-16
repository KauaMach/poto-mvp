# Diretrizes do projeto P.O.T.O — MVP

## Autoria de commits e contribuições

Todo commit, script ou instrução de envio para o GitHub deve usar **exclusivamente**
a identidade configurada em `git config user.name` / `git config user.email`.

- **Nunca** usar "Claude", "Claude Code" ou "Anthropic" como autor ou co-autor.
- **Não** acrescentar `Co-Authored-By: Claude <...>` a mensagens de commit.
- **Não** acrescentar "🤖 Generated with Claude Code" a descrições de Pull Request.
- **Não** usar `--author` para sobrescrever o autor com outra identidade.
- Comandos e scripts gerados herdam o `git config` local, sem embutir nome/e-mail.

O histórico deve refletir apenas a identidade do desenvolvedor. Assistência de IA é
ferramenta de trabalho, não contribuinte.

## Escopo

O escopo do MVP está fixado em [PLAN.md §3](PLAN.md). **Nada marcado como P2 entra antes
de todo P0 estar verde.** Se o tempo apertar, corta-se P1 — nunca P0.

## Invariante de segurança

Nenhuma combinação de trilha escolhida + texto livre pode **reduzir** a gravidade que o
roteador determinístico atribuiu. Toda mudança em `app/triagem/` exige rodar
`tests/test_regressao_seguranca.py`.

## Referência

O projeto anterior está em `../poto/` — repositório de terceiro (`gutoportelaa/poto`),
**somente leitura**. Serve como referência de identidade visual e de núcleo de domínio.
Não commitar nele, não renomeá-lo, não tratá-lo como base de implementação.
