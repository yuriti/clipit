<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · **Português** · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Uma IA grátis no seu computador

A IA pode rodar direto no seu computador, de graça: nada sai dele e não há nada para pagar. Você precisa de um
programa que rode modelos de IA — **Ollama** ou **LM Studio** — e de um modelo, por exemplo **Qwen**. O SMTV encontra
o programa sozinho.

**Sendo sincero:** os modelos que cabem em um computador doméstico são mais fracos que os da nuvem, então os clipes
saem piores, e nenhum dos modelos recomendados foi testado com o SMTV ainda. Se o resultado decepcionar, experimente a
[conta](account.md) ou [uma chave](get-a-key.md).

## 1. Qual modelo cabe no seu computador

O que importa é a **memória de vídeo** da sua placa de vídeo (em um Mac com Apple silicon: a memória inteira).

| Memória de vídeo | Modelo | Download | Observações |
|---|---|---|---|
| menos de 8 GB | — | — | Pouco demais: use a conta ou uma chave |
| 8 GB | `qwen3:8b` | 5,2 GB | O mais leve que funciona bem o suficiente |
| 10–12 GB | `qwen3-vl:8b` ou `gemma3:12b` | 6,1 / 8,1 GB | Estes também olham quadros do vídeo |
| 16 GB ou mais | `qwen3:14b` | 9,3 GB | O melhor dos quatro |

Modelos menores que 7B («7 bilhões») não são recomendados: eles estragam as respostas de que o SMTV precisa.

**Como descobrir a sua memória de vídeo:**
- **Windows:** aperte Ctrl+Shift+Esc → **Desempenho** (Performance) → **GPU** → **Memória dedicada da GPU**
  (Dedicated GPU memory).
- **Mac:** menu Apple → **Sobre Este Mac** (About This Mac) → **Memória** (Memory). O Mac divide a memória com a IA:
  com 16 GB escolha `qwen3:8b`, com 32 GB ou mais `qwen3:14b`.

## 2a. Ollama (o mais simples)

1. Baixe o Ollama em [ollama.com/download](https://ollama.com/download) e instale como qualquer programa. Ele abre
   sozinho e fica perto do relógio.
2. No SMTV: **Settings → AI → Free, on this computer → Find on this computer** (Configurações → IA → Grátis, neste
   computador → Encontrar neste computador). O SMTV encontra o Ollama.
3. Abra **Ollama** na lista: o SMTV mostra os modelos recomendados com o tamanho de cada um. Clique em **Download**
   (Baixar) ao lado do modelo da tabela acima e espere (5–10 GB).
4. Pronto. O SMTV escolhe esse modelo para as etapas dele sozinho.

O SMTV ajusta a memória do Ollama para cada pedido, para que o texto da live inteira caiba; você não precisa mudar as
configurações do Ollama.

## 2b. LM Studio

1. Baixe o LM Studio em [lmstudio.ai/download](https://lmstudio.ai/download) e instale.
2. No LM Studio, abra **Discover**, procure **Qwen3 8B** (ou 14B, conforme a tabela) e clique em **Download**.
3. Abra a aba **Developer** e ligue **Start server** (ele escuta na porta 1234). Carregue o modelo ali.
4. No SMTV: **Settings → AI → Free, on this computer → Find on this computer**. O SMTV encontra o LM Studio.

## 3. Faça um clipe

Dê ao SMTV um [arquivo de vídeo](first-clip.md). Um link da Twitch ou do YouTube precisa da [conta](account.md) mesmo
com uma IA grátis: é a conta que baixa a gravação.

A IA grátis trabalha mais devagar que uma na nuvem; uma live longa pode levar algumas horas. Deixe o computador ligado.
