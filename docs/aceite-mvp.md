# Aceite do MVP — roteiro de resiliência

O que este documento prova: **o conjunto Pi + tablet se recupera sozinho**. Não
que o código funciona — isso a suíte de testes cobre — mas que ninguém precisa
estar por perto quando algo cai.

Cada item tem um número esperado e um espaço para o medido. Preencher é parte do
aceite: *"reiniciou rápido"* não é um resultado.

---

## Estado desta execução

| | |
|---|---|
| Data | *(preencher)* |
| Pi | Raspberry Pi 5 · `RaspPoto` · aarch64 |
| Tablet | Galaxy Tab A11 8,7" |
| build-id no ar | *(`make build-id`)* |

> **O que já foi verificado e o que não foi.** O item 3 (integridade do banco)
> foi executado e tem número real. Os demais exigem a Pi e o tablet, que não
> estavam alcançáveis quando este roteiro foi escrito — estão marcados
> `⏳ pendente` e o espaço "medido" está vazio de propósito.

---

## 1. Reboot da Pi

```bash
sudo reboot
# de outra máquina, cronometrando:
time until curl -sf http://RaspPoto.local:8000/api/v1/health >/dev/null; do sleep 1; done
```

| critério | esperado | medido |
|---|---|---|
| API respondendo após reboot | **< 60 s** | ⏳ |
| Tablet reconecta **sem toque** | automático | ⏳ |

O tablet reconecta porque o WebSocket tem reconexão de espera crescente
(MVP-054) e o dreno da fila roda a cada 15 s (MVP-058) — não porque alguém
recarrega a página.

---

## 2. `kill -9` no serviço

```bash
sudo systemctl status poto-api          # anote o PID
sudo kill -9 <PID>
time until curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null; do sleep 1; done
```

| critério | esperado | medido |
|---|---|---|
| systemd reergue | **< 10 s** | ⏳ |

`RestartSec=3` mais o tempo de subida do uvicorn. Se passar de 10 s, o suspeito
é a carga do classificador — o `/health` diz se ele está sendo carregado.

---

## 3. Corte de energia → banco íntegro ✅

**Executado.** Simulado com `SIGKILL` no meio de escritas contínuas, que é o que
um cabo arrancado faz: sem flush, sem rollback, sem chance de encerramento
gracioso.

| critério | esperado | **medido** |
|---|---|---|
| `PRAGMA integrity_check` | `ok` | **`ok`** |
| `journal_mode` | `wal` | **`wal`** |
| Chamados recuperados | ≥ os confirmados | **103** (≥100 confirmados) |
| Linhas órfãs em `estado_log` | 0 | **0** |
| Protocolos com marcador `pendente:` | 0 | **0** |
| `evento_id` duplicado | 0 | **0** |

As duas últimas linhas são as que importam mais do que a integridade do arquivo.
O `criar_chamado` insere com um marcador e corrige o protocolo **na mesma
transação** (MVP-016); se o WAL não fosse atômico, um `SIGKILL` no meio deixaria
`pendente:<uuid>` visível no painel. E o `estado_log` sem órfãs prova que a
linha de histórico e o chamado entram juntos ou não entram.

O que o WAL com `synchronous=NORMAL` promete é exatamente isto: o pior caso é
**perder as últimas transações**, nunca corromper. Foi o que aconteceu.

---

## 4. Operação contínua

Deixar o totem aberto no tablet, no carregador, por 30 minutos.

| critério | esperado | medido |
|---|---|---|
| Tela não apaga | acesa | ⏳ |
| Aplicação responde ao toque no fim | sim | ⏳ |
| Memória do serviço estável | sem crescer | ⏳ |

```bash
# na Pi, durante:
watch -n 30 'systemctl show poto-api -p MemoryCurrent; vcgencmd measure_temp'
```

---

## 5. WiFi do tablet desligado — **o que prova a premissa**

Este é o item que justifica a fila offline. Com o wifi do tablet desligado:

| critério | esperado | medido |
|---|---|---|
| Acionar uma trilha **confirma na hora** | sem espera | ⏳ |
| Badge mostra `· 1 na fila` | aparece | ⏳ |
| Nenhuma mensagem de erro técnico | nenhuma | ⏳ |
| Religar o wifi → fila esvazia | **≤ 15 s** | ⏳ |
| Chamados no painel | **1**, não 2 | ⏳ |

A última linha é a que o `evento_id` gerado no cliente garante (MVP-048): o
reenvio carrega o mesmo id e o backend devolve o chamado existente. Se aparecer
duplicado, a idempotência quebrou — e o teste de contrato que cobre isso é
`test_dreno_repetido_nao_duplica`.

---

## 6. Pi desligada com o tablet aberto

| critério | esperado | medido |
|---|---|---|
| Totem **não trava** | responde | ⏳ |
| Sem erro técnico na tela | mensagem humana | ⏳ |
| Acionamento vai para a fila | enfileira | ⏳ |
| Pi de volta → fila drena | automático | ⏳ |

É o mesmo caminho do item 5 visto do outro lado: lá a rede do tablet caiu, aqui
o servidor sumiu. O cliente não distingue os dois, e não precisa — `ErroRede`
enfileira em ambos.

---

## 7. Tablet reiniciado

Seguir `docs/setup-tablet.md` §5.

| critério | esperado | medido |
|---|---|---|
| Volta à aplicação | **≤ 5 toques** | ⏳ |
| Fixação de tela reativada | sim | ⏳ |

Os 5 toques incluem dois só para refixar: a fixação **não sobrevive ao reboot**,
e isso é limitação do Android.

---

## Como reproduzir o item 3

O script usado está registrado aqui porque o resultado depende de *como* o
processo morre:

```python
# escreve chamados em laço num banco temporário, imprime a contagem
# → SIGKILL no meio de uma escrita (não SIGTERM: este daria chance de flush)
# → reabre e roda integrity_check, conta órfãs e marcadores
```

O ponto é usar **SIGKILL**. Um `SIGTERM` deixaria o SQLite fechar
ordenadamente, e o teste passaria sem provar nada sobre corte de energia — foi
uma armadilha real durante a escrita deste roteiro.
