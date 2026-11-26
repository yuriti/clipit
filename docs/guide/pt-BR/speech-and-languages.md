<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · **Português** · [Deutsch](../de/speech-and-languages.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../speech-and-languages.md).

# Fala e idiomas

Primeiro o SMTV transforma a fala da live em texto, com o tempo de cada palavra — é assim que a IA entende o que
aconteceu. Isso roda **no seu computador, de graça**. O SMTV descobre o idioma da live sozinho.

| Idioma | Modelo | Download (uma vez) | Velocidade em um processador de 12 núcleos |
|---|---|---|---|
| Russo | GigaAM-v3, feito para o russo | 0,9 GB | 54× mais rápido que o tempo real |
| 25 idiomas europeus: inglês, espanhol, alemão, francês, italiano, português, polonês, ucraniano e outros | Parakeet-TDT v3 | 2,4 GB | 33× mais rápido que o tempo real |
| Todos os outros idiomas: chinês, japonês, coreano, hindi, bengali, cazaque, uzbeque, azerbaijano, vietnamita, indonésio e dezenas de outros | Whisper large-v3-turbo | 1,6 GB | Ainda não medido |

Um modelo é baixado sozinho na primeira vez que chega uma live no idioma dele. Não precisa de placa de vídeo; uma
placa NVIDIA deixa mais rápido. No Mac, o Whisper roda no processador e é mais lento.

**Settings → Speech to text** (Configurações → Fala em texto) mostra todos os modelos: onde rodam, os idiomas,
tamanho e velocidade, com **Download** (Baixar) e **Remove** (Remover). Ali cada idioma pode usar outro modelo,
inclusive o **Whisper in the cloud** (Whisper na nuvem) com a sua própria chave (Groq ou OpenAI) — mais rápido em um
computador fraco, mas aí o áudio sai do seu computador.

<img src="../../images/speech.png" alt="Settings → Speech to text: os modelos e os idiomas que eles atendem" width="820">

**O idioma da janela** é outra coisa: o SMTV fala o idioma do seu computador; **Settings → Language and theme**
(idioma e tema) escolhe outro. Seu idioma está faltando ou pela metade? [Ajude a traduzir](../../translations.md) —
não precisa saber programar.
