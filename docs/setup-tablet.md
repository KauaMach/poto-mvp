# Preparar o tablet como totem

Aparelho: **Samsung Galaxy Tab A11, 8,7"** · Android com One UI · Chrome

O objetivo não é "abrir a aplicação". É deixar o tablet num estado em que
**alguém que não conhece o projeto não consiga sair dela por acidente** — e em
que ele volte sozinho ao totem depois de um reinício.

> O que este documento **não** faz: MDM, root, ou aplicativo dedicado. Tudo
> abaixo usa recursos do próprio Android. É o suficiente para um totem em
> ambiente supervisionado, e reversível em um minuto.

---

## 0. Antes de começar

A Pi precisa estar servindo. Do tablet, no Chrome:

```
http://RaspPoto.local:8000/api/v1/health
```

Se responder JSON, siga. Se não, use a URL de IP que o `install-pi.sh` imprimiu
— wifi de universidade costuma bloquear multicast, e aí o `.local` não resolve
(MVP-067b).

**Anote qual das duas funcionou.** É a base que vai no atalho — e o atalho
aponta para **`/totem`**:

```
http://RaspPoto.local:8000/totem      (ou o IP equivalente)
```

> A raiz (`http://…:8000/`) também funciona: ela **redireciona** para `/totem`
> (MEL-003). O atalho usa o caminho canônico para o aparelho não pagar um salto
> de HTTP a cada abertura, mas um tablet já configurado na raiz continua
> chegando na tela certa — não precisa refazer nada.

---

## 1. Instalar a aplicação na tela inicial

1. Abra a URL que funcionou, com `/totem` no fim, no **Chrome**.
2. Menu **⋮** → **Adicionar à tela inicial**.
3. Nome: `P.O.T.O`. Confirme.
4. Feche o Chrome **por completo** (Recentes → fechar tudo).
5. Abra pelo ícone novo.

**Confira:** não deve haver barra de endereço. Se houver, o manifest não foi
lido — recarregue a página no Chrome uma vez e repita.

> Por que pelo ícone e não por um atalho de navegador: o manifest declara
> `display: fullscreen` (MVP-055b), e só o atalho instalado o respeita. Aberto
> como aba comum, a barra de endereço fica — e ela é uma porta para sair da
> aplicação.

---

## 2. Fixar a tela (o passo que de fato tranca)

Sem isto, todo o resto é decoração: qualquer pessoa desliza de baixo para cima
e sai.

1. **Configurações** → **Segurança e privacidade** → **Outras configurações de
   segurança** → **Fixar aplicativos** (ou **Fixação de tela**).
2. Ligue **Fixar aplicativos**.
3. Ligue **Solicitar PIN para liberar** — *este item é o que importa*.
   Sem ele, o desafixar é um toque longo e a fixação não protege nada.
4. Volte ao P.O.T.O, abra **Recentes**, toque no ícone do app no topo do cartão
   e escolha **Fixar**.

**Confira:** deslizar para sair deve pedir o PIN.

Para sair de propósito: **Recentes + Voltar** juntos (ou deslizar de baixo e
segurar), depois o PIN.

---

## 3. A tela não pode apagar

Um totem com a tela preta é um totem que ninguém percebe que existe.

- **Configurações** → **Tela** → **Tempo de espera da tela** → **10 minutos**
  (o máximo do One UI).
- Para **nunca apagar**, ligue o modo desenvolvedor:
  1. **Configurações** → **Sobre o tablet** → **Informações de software** →
     toque **7×** em **Número de compilação**.
  2. **Configurações** → **Opções do desenvolvedor** → ligue **Permanecer
     ativo** ("Stay awake").
  3. Isso mantém a tela acesa **enquanto carregando** — então o totem fica
     permanentemente no carregador, que é o que se quer de um aparelho de
     parede.
- **Brilho**: fixo em ~70%, com **Brilho adaptativo desligado**. O automático
  escurece a tela num corredor à noite, que é quando ela mais precisa ser vista.

---

## 4. Silenciar o que interrompe

Cada item aqui é uma coisa que pode aparecer **por cima** da tela de socorro.

- **Não perturbe**: ligado, com exceções desativadas.
- **Notificações**: desative para todos os apps que sobrarem.
- **Assistente de voz** (Google Assistant / Bixby): desativado — segurar o
  botão de início abriria o assistente sobre a aplicação.
- **Gestos de navegação**: se possível, use **Botões de navegação** em vez de
  gestos. Gesto de deslizar é mais fácil de disparar por acidente ao tocar um
  cartão perto da borda.
- **Rotação automática**: pode deixar ligada. O layout se adapta às duas
  orientações (MVP-055) e travar criaria um estado pior — alguém segurando o
  tablet no eixo errado veria a tela de lado.

---

## 5. Retomar depois de um reinício — **5 toques**

O critério da task é este, e vale cronometrar:

| # | Toque |
|---|---|
| 1 | Desbloquear (deslizar) |
| 2 | PIN, se houver bloqueio de tela |
| 3 | Ícone **P.O.T.O** na tela inicial |
| 4 | **Recentes** |
| 5 | Ícone do app no cartão → **Fixar** |

> Os toques 4 e 5 existem porque a **fixação não sobrevive ao reboot** — é
> limitação do Android, não do projeto. Se o totem for reiniciado com
> frequência, vale considerar um app de kiosk dedicado; para a operação e a
> demonstração do MVP, cinco toques documentados bastam.

Para reduzir a 3 toques: desligue o bloqueio de tela (**Configurações** →
**Tela de bloqueio** → **Nenhum**). **Só faça isso se o tablet estiver fisicamente
seguro** — sem bloqueio, quem pegar o aparelho tem acesso a tudo.

---

## 6. Conferência final

Entregue o tablet a alguém que não leu este documento e peça para **sair da
aplicação**. Se conseguir sem o PIN, algo acima não foi aplicado.

Depois, com o tablet pronto:

- [ ] Abre no ícone, sem barra de endereço
- [ ] Deslizar para sair pede PIN
- [ ] Tela não apaga no carregador
- [ ] As quatro trilhas respondem ao toque
- [ ] O botão de pânico exige **1 segundo** de pressão (MVP-046)
- [ ] Rodar o tablet: a grade se adapta e **nada rola** (MVP-055)
- [ ] Desligar o wifi, acionar uma trilha: confirma na hora e aparece
      `· 1 na fila` no topo (MVP-057)
- [ ] Religar o wifi: a fila esvazia sozinha em ≤ 15 s (MVP-058)

Os dois últimos são os que provam que o totem não depende da rede — e são os
que a demonstração mostra.
