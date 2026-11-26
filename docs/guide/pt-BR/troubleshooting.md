<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · **Português** · [Deutsch](../de/troubleshooting.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../troubleshooting.md).

# Algo deu errado

## 1. Computer check → Fix

**Settings → Computer check** (Configurações → Verificação do computador) olha tudo de que o SMTV precisa e diz, linha
por linha, o que está bem e o que não está. Ao lado de um problema há um botão **Fix** (Corrigir): o SMTV instala ou
conserta sozinho o que conseguir e mostra o que está fazendo.

<img src="../../images/check.png" alt="Settings → Computer check: cada linha com o seu estado e um botão Fix" width="820">

| A linha diz | O que fazer |
|---|---|
| **Video (ffmpeg)** está faltando | Clique em **Fix**: o SMTV instala o ffmpeg, a ferramenta de vídeo que ele usa. |
| **Captions** (legendas) não funcionam | Clique em **Fix**: o SMTV instala um ffmpeg que consegue desenhar legendas. |
| **AI**: nada conectado | Escolha uma em **Settings → AI** — [qual](connect-ai.md). |
| **Connection to StreamMoment** (conexão com o StreamMoment) falha | Verifique a internet; uma VPN ou um firewall pode bloquear. Arquivos continuam funcionando sem ela. |
| **Free space** (espaço livre) está baixo | Libere espaço em disco: uma live de 6 horas precisa de cerca de 20 GB enquanto é processada. |
| **Speech to text**: um modelo não foi baixado | Ele é baixado sozinho no primeiro pedido; ou clique em **Download** em **Settings → Speech to text**. |

Uma correção que precisa de senha de administrador nunca roda escondida: o SMTV abre um terminal com o comando, para
você ver o que ele faz.

## 2. Problemas comuns

- **Um link não funciona.** Links precisam da [conta StreamMoment](account.md). Sem conta? Baixe a gravação você mesmo
  e dê o arquivo ao SMTV.
- **Nenhum clipe, ou muito poucos.** O SMTV guarda só os momentos que a IA avaliou como bons. Uma live curta ou
  tranquila pode render poucos. Uma IA grátis no seu computador encontra menos momentos bons que uma na nuvem.
- **«Too many requests» (pedidos demais).** O plano grátis do seu serviço de IA atingiu o limite: espere, ou use um
  plano pago ou a conta.
- **O celular não abre o SMTV.** Mesmo Wi-Fi, sem VPN, permita o SMTV no firewall — veja [celular](phone.md).
- **Windows: um terminal recusa `smtv`.** É o Controle Inteligente de Aplicativos (Smart App Control); abra o SMTV
  pelo ícone.
- **A janela perdeu a conexão com o SMTV.** Feche a janela e abra o SMTV de novo.

Um pedido que parou pode continuar: clique em **Continue** (Continuar) — o SMTV retoma da mesma etapa e não refaz o
que já está pronto.

## 3. Relate um problema

Ainda travado? Conte para nós — isso ajuda todo mundo.

1. **Settings → Computer check → Report a problem** (Relatar um problema; o botão **Report…**, que também está em
   **Settings → About**), ou o botão abaixo de um pedido que falhou.
2. O SMTV mostra o que entra no relatório: versões, a verificação do computador, configurações e logs. **Chaves e
   tokens são cortados**, a sua pasta pessoal aparece como `~`. Links e nomes de arquivos ficam de fora, a menos que
   você marque a caixa.
3. Clique em **Save and open GitHub** (salvar e abrir o GitHub). O SMTV salva o arquivo compactado, e uma nova issue
   abre no navegador com o resumo preenchido. Arraste o arquivo para ela e clique em **Submit**.

O SMTV não envia nada sozinho. Sem a janela: rode `smtv report` em um terminal. Você também pode
[abrir uma issue](https://github.com/yuriti/clipit/issues/new?template=bug.yml) diretamente.
