<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · **Português** · [Deutsch](../de/install.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../install.md).

# Instalar o SMTV

Baixe um arquivo, abra e aparece um ícone do **SMTV**. Tudo de que o SMTV precisa já vem dentro. Você não precisa de
senha de administrador.

| Seu computador | Download | Tamanho |
|---|---|---|
| **Windows 10 ou 11** (64 bits) | [SMTV para Windows](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) | cerca de 130 MB |
| **Mac** — Apple silicon (M1 e mais novos) ou Intel, macOS 13+ | [SMTV para Mac](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | cerca de 270 MB |

Todas as versões e suas somas de verificação: [a página da versão](https://github.com/yuriti/clipit/releases/latest).

**Por que o sistema mostra um aviso na primeira vez.** O SMTV ainda não tem assinatura digital. A assinatura para o
Windows vem um pouco mais tarde, a do macOS assim que possível, e aí esse aviso some. O código do SMTV é aberto:
qualquer pessoa pode ler o que ele faz.

## Windows

1. Baixe o **SMTV para Windows** (o arquivo `SMTV-…-windows-x64-setup.exe`) e abra.
2. O Windows mostra uma janela azul **«O Windows protegeu o computador»** («Windows protected your PC»). Clique em
   **Mais informações** (More info) e depois em **Executar assim mesmo** (Run anyway).
3. O instalador faz algumas perguntas (idioma, um ícone na área de trabalho) — clique em **Avançar** (Next) e
   **Instalar** (Install).
4. No final, deixe marcado **Abrir o SMTV** (Launch SMTV) e clique em **Concluir** (Finish). Da próxima vez, abra o
   SMTV pelo menu **Iniciar** (ou pelo ícone na área de trabalho).

O instalador coloca o SMTV na sua própria pasta de usuário; ele aparece em **Configurações → Aplicativos** (Settings →
Apps), onde você pode removê-lo.

**Sem instalar:** baixe [o ZIP](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip),
descompacte onde quiser (por exemplo em Documentos) e abra **Start SMTV** na pasta `SMTV`. Essa cópia não se atualiza
sozinha: uma versão nova é um ZIP novo.

### Windows 11: Smart App Control

Se o **Smart App Control** (Controle Inteligente de Aplicativos) estiver ligado (Segurança do Windows → Controle de
aplicativos e do navegador), o Windows bloqueia por completo programas sem assinatura, e não existe botão para liberar.
Você não precisa desligar o Smart App Control por causa do SMTV. Em vez disso, instale o SMTV com uma linha — funciona
com o Smart App Control ligado: [uma linha no terminal](#para-usuários-experientes-uma-linha-no-terminal). Quando o
SMTV for assinado, o download também vai funcionar lá.

## Mac

1. Baixe o **SMTV para Mac**. É um só arquivo para qualquer Mac, com Apple silicon ou Intel: o SMTV inicia sozinho a versão feita para o processador do seu Mac.
2. Abra o `.dmg` baixado. Abre uma janela com o SMTV e a pasta **Aplicativos** (Applications): arraste o **SMTV** para
   **Aplicativos**.
3. Abra **Aplicativos** e clique duas vezes no **SMTV**. O macOS diz que não consegue verificar o SMTV e não abre.
   Clique em **OK** (Done).
4. Abra **Ajustes do Sistema → Privacidade e Segurança** (System Settings → Privacy & Security) e role para baixo. Ao
   lado de «O SMTV foi bloqueado…» clique em **Abrir Mesmo Assim** (Open Anyway), digite a senha do seu Mac e clique
   em **Abrir** (Open).
   No macOS 14 há um jeito mais curto: clique com o botão direito no **SMTV** em Aplicativos → **Abrir** → **Abrir**.

Só na primeira vez: depois disso o SMTV abre com um clique normal, por Aplicativos ou pelo Launchpad. Os mesmos passos
estão no arquivo «How to open» dentro do `.dmg`.

## A primeira vez que você abre

O SMTV verifica o seu computador e mostra três passos até o primeiro clipe. Abaixo deles, ele oferece o
**reconhecimento de fala para o seu idioma** — a parte que transforma a fala da live em texto. Ele não vem no download,
porque cada idioma precisa do seu (0,9–2,5 GB). Clique em **Fix** (Corrigir) e acompanhe o progresso, ou pule: o
primeiro pedido baixa sozinho.

**Do que você precisa:** 5 GB de espaço livre no mínimo, 20 GB para uma live de 6 horas; internet. Não precisa de
placa de vídeo.

## Para usuários experientes: uma linha no terminal

O mesmo SMTV, instalado com o [uv](https://astral.sh/uv) — uma pequena ferramenta oficial para programas em Python —
na sua pasta de usuário. Use no **Linux**, com o **Smart App Control** ou se preferir o terminal. Ele se atualiza pela
janela como o aplicativo baixado.

**Windows:** clique em **Iniciar**, digite `PowerShell`, abra o **Windows PowerShell** (a janela azul), cole esta linha
(botão direito ou Ctrl+V) e aperte **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

Com o Smart App Control ligado, o instalador coloca o SMTV sobre o Python assinado do python.org (pode pedir para
instalá-lo — aceite) e abre o SMTV por meio dele. Se um terminal disser que não consegue executar `smtv`, use o ícone
do **SMTV**.

**Mac ou Linux:** abra o **Terminal** (no Mac: Cmd+Espaço, digite `Terminal`, Enter), cole esta linha e aperte
**Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Espere até ele dizer que terminou (2–10 minutos). O SMTV abre sozinho; o ícone do **SMTV** fica no menu Iniciar no
Windows, em Aplicativos no Mac, no menu de aplicativos no Linux. Por esse caminho, na primeira vez o SMTV oferece
instalar o **ffmpeg** (a ferramenta de vídeo) com **Fix**; o download acima já vem com ele.

Os dois instaladores são curtos e abertos: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Se o sistema mostrar um aviso

- **Windows: «O Windows protegeu o computador»** («Windows protected your PC», SmartScreen). Clique em **Mais
  informações** (More info) e depois em **Executar assim mesmo** (Run anyway).
- **Windows 11: o Smart App Control bloqueia o SMTV.** Use [uma linha no terminal](#para-usuários-experientes-uma-linha-no-terminal)
  até o SMTV ser assinado.
- **Windows: o firewall pergunta** se o SMTV pode usar a rede. Permita em redes **privadas**: o SMTV precisa disso
  para abrir no seu celular. Pode recusar se não for usar o celular.
- **Mac: «Não é possível abrir o SMTV»**, «A Apple não pôde verificar…» ou «não é possível verificar o
  desenvolvedor». Abra **Ajustes do Sistema → Privacidade e Segurança** (System Settings → Privacy & Security), role
  para baixo e clique em **Abrir Mesmo Assim** (Open Anyway) ao lado do SMTV.
- **Mac: «O SMTV deseja aceitar conexões de entrada»** — permita se quiser usar o SMTV no celular.
- O **antivírus** reclama? O SMTV é novo e ainda não é assinado, então alguns antivírus tomam cuidado com ele. O código
  é aberto, e as somas de verificação de cada arquivo estão na [página da versão](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`).

Próximo: [seu primeiro clipe](first-clip.md).
