<!-- The source is the Russian README.md; translations: README.<language>.md, the same structure. A change to README.md
     changes README.en.md in the same PR; the other languages follow (each says it was translated automatically from
     the Russian original and links it and Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**Transforme uma live longa em clipes curtos e um resumo. De graça, no seu próprio computador.**

<!-- languages -->
[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · **Português** · [Deutsch](README.de.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](README.md).

[![Última versão](https://img.shields.io/github/v/release/yuriti/clipit?label=release)](https://github.com/yuriti/clipit/releases/latest)
[![Downloads](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![Estrelas](https://img.shields.io/github/stars/yuriti/clipit?style=flat)](https://github.com/yuriti/clipit/stargazers)
[![Licença: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Traduza no Weblate](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: entra a gravação de uma live, o SMTV encontra os melhores momentos e faz clipes verticais um por um" width="820">

[**Baixar o SMTV**](#baixar) · [Guias passo a passo](docs/guide/pt-BR/README.md) · [Comparação](#como-o-smtv-se-compara) · [Perguntas](#perguntas)

</div>

---

Você fez live por seis horas. Em algum lugar ali estão os dez momentos que valem a pena postar — mas, para achá-los,
seria preciso assistir tudo de novo. **O SMTV assiste por você.** Cole o link de uma gravação da Twitch ou do YouTube,
ou escolha um arquivo de vídeo, e o SMTV escuta a live inteira, escolhe os melhores momentos e entrega **clipes
verticais prontos para postar** no TikTok, Shorts e Reels, com legendas e a webcam em cima, além de um **resumo de
20–30 minutos** da live inteira para o YouTube.

## O que ele faz

| | |
|---|---|
| 🎬 **Clipes prontos para postar** | Vertical 9:16, com legendas grandes, um cartão de título curto no começo e a webcam do streamer em cima do jogo. |
| ⏱️ **Lives longas não são problema** | Entra uma gravação de 6–12 horas, saem até 30 clipes. Os clipes aparecem um por um: comece a postar antes de o resto ficar pronto. |
| 📺 **Um resumo da live inteira** | Um vídeo de 20–30 minutos para o YouTube: a própria live, cortada só nas partes que valem a pena. |
| 🗣️ **Muitos idiomas** | Russo, 25 idiomas europeus e dezenas de outros. O SMTV transforma a fala em texto no seu próprio computador. |
| 🔒 **Seus arquivos ficam com você** | Os clipes são feitos e guardados no seu computador. Nada é enviado para um site. |
| 💸 **Grátis e aberto** | Licença MIT: use, compartilhe, use para clientes. Sem marca d'água, sem limite de minutos. |

## Veja funcionando

**Cole um link ou escolha um arquivo — e acompanhe as etapas.** Cada etapa aparece na tela: fala em texto, busca de
momentos, avaliação, edição de cada clipe.

<img src="docs/images/new-request.gif" alt="Um novo pedido: um arquivo de vídeo é escolhido, o SMTV começa e mostra cada etapa" width="820">

**Os clipes aparecem um por um.** Assista direto no SMTV, baixe, poste.

<img src="docs/images/clips.png" alt="Clipes prontos de uma live em uma grade" width="820">

**Cada clipe vem com o seu texto.** Leia o que foi dito e por que o SMTV escolheu o momento.

<img src="docs/images/viewer.png" alt="Um clipe tocando ao lado da sua transcrição" width="820">

**E um resumo da live inteira** para o YouTube, feito depois dos clipes.

<img src="docs/images/recap.png" alt="O resumo da live no SMTV" width="820">

**Claro ou escuro** — como no seu computador.

<img src="docs/images/dark.png" alt="O SMTV no tema escuro" width="820">

<sub>A live destas imagens foi inventada para a demonstração: um joguinho, um mascote de desenho no lugar da webcam e
uma voz de computador. Nenhuma pessoa real aparece na tela.</sub>

## Grátis e de código aberto

- **O SMTV é grátis.** O programa inteiro é de código aberto sob a [licença MIT](LICENSE): use para você, para o seu
  canal ou para clientes, modifique e compartilhe.
- **Sem marca d'água, sem limite de minutos, sem assinatura do SMTV.**
- **Você paga só pela IA, e só se quiser.** O SMTV precisa de uma IA para ler o texto da live e escolher os momentos.
  Pode ser uma IA grátis no seu próprio computador ou um serviço que você escolher — veja abaixo.
- **Seus dados ficam com você.** Os clipes são feitos e guardados no seu computador. Só o texto da live vai para a IA
  que você escolheu. Com uma IA grátis no seu computador, nada sai dele.

## Escolha a sua IA: três jeitos

O SMTV transforma a fala em texto no seu computador sozinho. Para escolher os melhores momentos, ele pergunta a uma
IA. Escolha um jeito — um basta, e você pode trocar a qualquer momento em **Settings → AI** (Configurações → IA).

| | Como | Custo | Bom para |
|---|---|---|---|
| ⭐ **Pela conta** | Entre em uma conta StreamMoment (Google, Twitch ou Telegram) e coloque saldo. Só isso: sem chaves, sem configuração. | Paga conforme usa, do saldo | Todo mundo: o jeito mais simples. Também é necessária para colar **links** de gravações. [Guia](docs/guide/pt-BR/account.md) |
| 🔑 **Sua própria chave** | Já usa OpenAI, Claude, Gemini ou OpenRouter? Cole a sua chave, e o SMTV a usa diretamente. | Você paga direto ao serviço; alguns têm plano grátis | Quem já usa um serviço de IA. [Onde conseguir uma chave](docs/guide/pt-BR/get-a-key.md) |
| 💻 **Grátis, no seu computador** | Instale o Ollama ou o LM Studio e um modelo Qwen; o SMTV o encontra sozinho. | Grátis | Um computador com uma placa de vídeo forte. Os clipes saem mais fracos. [Guia](docs/guide/pt-BR/free-ai-on-your-computer.md) |

## Baixar

| Seu computador | Download | Tamanho |
|---|---|---|
| **Windows 10 ou 11** (64 bits) | [**SMTV para Windows**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) (instalador) | cerca de 130 MB |
| **Mac** — Apple silicon (M1 e mais novos) ou Intel, macOS 13+ | [**SMTV para Mac**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | cerca de 270 MB |

Um só arquivo para qualquer Mac: o SMTV inicia sozinho a versão feita para o processador do seu Mac. Windows sem instalar nada:
[o ZIP](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) — descompacte e abra
**Start SMTV**.

Tudo de que o SMTV precisa já vem dentro: o programa, o Python e o ffmpeg com legendas. O reconhecimento de fala é
baixado na primeira vez que você abre o SMTV, só para o seu idioma (0,9–2,5 GB, uma vez só): o SMTV oferece isso com um
botão, **Fix** (Corrigir).

**Na primeira vez, o sistema mostra um aviso.** O SMTV ainda não tem assinatura digital: a do Windows vem um pouco mais
tarde, a do macOS assim que possível, e aí esse aviso some. Até lá:

- **Windows** («O Windows protegeu o computador»): **Mais informações** (More info) → **Executar assim mesmo** (Run
  anyway).
- **Mac**: abra o SMTV uma vez e depois vá em **Ajustes do Sistema → Privacidade e Segurança** (System Settings →
  Privacy & Security) → **Abrir Mesmo Assim** (Open Anyway).
- **Windows 11 com Smart App Control** bloqueia por completo programas sem assinatura, e não existe botão para liberar.
  Use a instalação com uma linha logo abaixo: ela funciona com o Smart App Control ligado. Quando o SMTV for assinado, o
  download também vai funcionar lá.

[Cada passo, com imagens](docs/guide/pt-BR/install.md).

### Para usuários experientes: uma linha no terminal

O mesmo SMTV, instalado com o [uv](https://astral.sh/uv) na sua pasta de usuário. Também funciona no **Linux** e com o
**Smart App Control**, e se atualiza pela janela do mesmo jeito.

**Windows** — clique em Iniciar, digite **PowerShell**, abra e cole:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

**Mac ou Linux** — abra o **Terminal** e cole:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Aperte Enter e espere alguns minutos. Não precisa de senha de administrador. Aparece um ícone do **SMTV** — na área de
trabalho e no menu Iniciar no Windows, em Aplicativos no Mac, no menu de aplicativos no Linux.

## Seu primeiro clipe em três passos

1. **Escolha uma IA** — na primeira vez, a janela mostra os três jeitos ([qual escolher?](docs/guide/pt-BR/connect-ai.md)).
2. **Cole um link** de uma gravação da Twitch ou do YouTube, ou escolha um arquivo de vídeo do seu computador.
3. **Espere.** Os clipes aparecem um por um: assista, baixe, poste.

Na primeira vez, o SMTV verifica o seu computador e oferece consertar o que falta com um botão, **Fix** (Corrigir).
[O primeiro clipe, passo a passo](docs/guide/pt-BR/first-clip.md).

## Guias passo a passo

Para quem é novo em tudo isso — cada passo, com imagens:

| | |
|---|---|
| [Instalar no Windows, Mac ou Linux](docs/guide/pt-BR/install.md) | e o que fazer quando o sistema mostra um aviso |
| [Seu primeiro clipe](docs/guide/pt-BR/first-clip.md) | de um link ou arquivo até o clipe pronto |
| [Qual IA escolher](docs/guide/pt-BR/connect-ai.md) | os três jeitos, lado a lado |
| [Uma IA grátis no seu computador](docs/guide/pt-BR/free-ai-on-your-computer.md) | Ollama ou LM Studio com Qwen: qual modelo cabe na sua placa de vídeo |
| [Onde conseguir uma chave](docs/guide/pt-BR/get-a-key.md) | quais serviços têm plano grátis ou barato, passo a passo |
| [A conta StreamMoment](docs/guide/pt-BR/account.md) | entrar, saldo |
| [O SMTV no seu celular](docs/guide/pt-BR/phone.md) | escaneie um QR code e assista aos clipes no celular |
| [Fala e idiomas](docs/guide/pt-BR/speech-and-languages.md) | quais idiomas o SMTV entende |
| [Atualizar e remover](docs/guide/pt-BR/update-and-remove.md) | |
| [Algo deu errado](docs/guide/pt-BR/troubleshooting.md) | verificação do computador, **Fix**, **Report a problem** (Relatar um problema) |

## Como o SMTV se compara

Os clipadores de código aberto mais usados, segundo o código e a documentação de cada projeto, **em novembro de
2026**. São bons projetos, cada um feito para o seu propósito; esta tabela só mostra onde o SMTV é diferente. Algo
mudou? [Conte para nós](https://github.com/yuriti/clipit/issues/new?template=bug.yml) e corrigimos a tabela.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| Licença | **MIT** | MIT (a pasta `cloud/` tem licença própria) | Licença de código não comercial | MIT | MIT |
| Uma live inteira de 6–12 horas | **Sim** | 60 minutos por tarefa por padrão | 90 minutos por padrão | Nenhum limite de duração informado | Não foi feito para lives |
| Um resumo longo da live inteira | **Sim, 20–30 minutos** | Não | Não (o «recap» dele é um clipe curto) | Não | Não |
| Fala em russo | **GigaAM-v3, feito para o russo** | Whisper ou Parakeet v3 | AssemblyAI ou Whisper | Não (Parakeet v2, só inglês) | Não (chinês e inglês) |
| Webcam do streamer no quadro vertical | **Sim** | Não | Modo gaming, desligado por padrão | Sim | Sem clipes verticais |
| Fala em texto por padrão | **No seu computador, grátis** | No seu computador | AssemblyAI, um serviço pago | No seu computador | No seu computador |
| Como você abre | **Janela e ícone próprios: download para Windows e Mac, ou uma linha** | Página web no Docker | Página web no Docker | Página web | Página web |

## Perguntas

<details>
<summary><b>É grátis mesmo?</b></summary>

Sim. O SMTV em si não custa nada e não tem limites. O único custo possível é a IA que escolhe os momentos: grátis no
seu próprio computador, ou pago ao serviço que você escolher (pela conta StreamMoment ou pela sua própria chave).
</details>

<details>
<summary><b>Preciso de um computador potente?</b></summary>

Não precisa de placa de vídeo: o SMTV funciona em um computador comum, só que mais devagar. Uma placa NVIDIA deixa a
fala em texto mais rápida. A exceção é uma IA grátis no seu próprio computador — ela precisa de uma placa de vídeo
forte ([qual](docs/guide/pt-BR/free-ai-on-your-computer.md)). Espaço livre em disco: 5 GB no mínimo, 20 GB para uma
live de 6 horas.
</details>

<details>
<summary><b>Quanto tempo demora?</b></summary>

Medido em um Mac com Apple silicon, sem placa de vídeo: uma gravação da Twitch de 2,35 horas levou cerca de 6 minutos
para encontrar os momentos, depois cerca de 1 minuto por clipe; um resumo de 10,7 minutos levou 6,5 minutos. Antes de
um pedido começar, o SMTV mostra quanto tempo ele deve levar.
</details>

<details>
<summary><b>Em quais sistemas ele roda?</b></summary>

Windows 10 (versão 1809) ou mais novo, 64 bits; macOS 13 ou mais novo em Apple silicon e Intel (em Apple silicon o SMTV roda nativamente a partir do macOS 14; no macOS 13 ele roda a sua versão para Intel pelo Rosetta, mais lenta); Linux (instalação com uma linha). Testado no Windows 11 e em Macs com Apple silicon; Macs com Intel (só pelo
Rosetta) e desktops Linux ainda não foram testados.
</details>

<details>
<summary><b>Quais idiomas ele entende?</b></summary>

Russo, 25 idiomas europeus e dezenas de outros. O SMTV descobre o idioma da live sozinho.
[Detalhes](docs/guide/pt-BR/speech-and-languages.md).
</details>

<details>
<summary><b>Posso usar os clipes para os meus clientes?</b></summary>

Sim. A licença MIT permite qualquer uso, inclusive comercial: clipes para streamers, agências, seus próprios canais.
Respeite os direitos do streamer cuja live você clipa.
</details>

<details>
<summary><b>Para onde vão os meus clipes? Alguma coisa é enviada?</b></summary>

Os clipes ficam no seu computador. Um arquivo de vídeo seu nunca sai dele. Um link é baixado pela conta StreamMoment:
o servidor dela passa a gravação para o SMTV em pedaços e não guarda nada. O texto da live vai só para a IA que você
escolheu. As chaves de serviços de IA ficam no seu computador e nunca aparecem em logs nem em relatórios de problema.
</details>

<details>
<summary><b>Ele posta no TikTok ou no YouTube sozinho?</b></summary>

Ainda não: você baixa os clipes e posta você mesmo. Settings → About → «Coming» (Configurações → Sobre → Em breve)
mostra o que está planejado.
</details>

<details>
<summary><b>Alguma coisa não funciona.</b></summary>

Settings → **Computer check** → **Fix** (Configurações → Verificação do computador → Corrigir) resolve a maioria dos
problemas. Ainda travado? Settings → Computer check → **Report…**: o SMTV prepara um relatório sem as suas chaves e
abre uma página no GitHub; nada é enviado sozinho.
[O que tentar](docs/guide/pt-BR/troubleshooting.md).
</details>

## Ajude a traduzir o SMTV

A janela do SMTV fala o idioma do seu computador. As traduções são feitas por pessoas no
[Weblate](https://hosted.weblate.org/engage/smtv/) — não precisa saber programar: abra a página, escolha o seu idioma,
traduza algumas linhas. As traduções desta página foram feitas automaticamente; se você vir um erro, corrija em um pull
request. [Como funcionam as traduções](docs/translations.md).

[![Status da tradução](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

O SMTV é feito pela equipe do [StreamMoment](https://streammoment.tv). A conta StreamMoment é o jeito mais simples de
dar uma IA ao SMTV e de colar links de gravações; o SMTV também funciona sem ela.

- [Relatar um problema](https://github.com/yuriti/clipit/issues/new?template=bug.yml) · [Sugerir uma ideia](https://github.com/yuriti/clipit/issues/new?template=feature.yml)
- [Para usuários avançados](docs/advanced.md): Docker, todos os serviços de IA, modelos de fala, chaves, comandos
- [Mudanças](CHANGELOG.md) · [Como contribuir](CONTRIBUTING.md) · [Segurança](SECURITY.md)
- Gostou do SMTV? [Apoie no Boosty](https://boosty.to/smtv) e dê uma ⭐ ao repositório — isso ajuda outras pessoas a
  encontrá-lo.

Licença: [MIT](LICENSE).
