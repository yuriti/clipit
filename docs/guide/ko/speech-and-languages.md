<!-- languages -->
[English](../speech-and-languages.md) · [Русский](../ru/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · **한국어** · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/streammomenttv/smtv/pulls).

# 음성과 언어

SMTV는 먼저 방송의 음성을 단어마다 시간과 함께 텍스트로 바꿉니다 — 그래야 AI가 무슨 일이 있었는지 이해합니다. 이 작업은
**내 컴퓨터에서, 무료로** 이루어집니다. 방송의 언어는 SMTV가 알아서 찾아냅니다.

| 언어 | 모델 | 다운로드(한 번) | 12코어 프로세서에서의 속도 |
|---|---|---|---|
| 러시아어 | GigaAM-v3, 러시아어 전용 | 0.9 GB | 실시간보다 54배 빠름 |
| 유럽 25개 언어: 영어, 스페인어, 독일어, 프랑스어, 이탈리아어, 포르투갈어, 폴란드어, 우크라이나어 등 | Parakeet-TDT v3 | 2.4 GB | 실시간보다 33배 빠름 |
| 그 밖의 모든 언어: 중국어, 일본어, 한국어, 힌디어, 벵골어, 카자흐어, 우즈베크어, 아제르바이잔어, 베트남어, 인도네시아어 외 수십 개 | Whisper large-v3-turbo | 1.6 GB | 아직 측정하지 않음 |

모델은 그 언어의 방송이 처음 들어올 때 저절로 다운로드됩니다. 그래픽 카드는 필요 없고, NVIDIA 카드가 있으면 더 빠릅니다.
Mac에서는 Whisper가 프로세서에서 돌아가서 더 느립니다.

**Settings → Speech to text**(설정 → 음성을 텍스트로)에는 모든 모델이 표시됩니다: 어디서 돌아가는지, 언어, 크기와 속도, 그리고
**Download**(다운로드)와 **Remove**(삭제). 거기서 언어마다 다른 모델을 고를 수 있고, 내 키(Groq 또는 OpenAI)로 **Whisper in the cloud**
(클라우드 Whisper)도 쓸 수 있습니다 — 성능이 낮은 컴퓨터에서는 더 빠르지만, 그 경우 소리가 내 컴퓨터 밖으로 나갑니다.

<img src="../../images/speech.png" alt="Settings → Speech to text: 모델과 각 모델이 맡는 언어" width="820">

**창의 언어**는 별개입니다: SMTV는 내 컴퓨터의 언어로 표시되고, **Settings → Language and theme**(설정 → 언어와 테마)에서
다른 언어를 고를 수 있습니다. 내 언어가 없거나 절반만 번역됐나요? [번역을 도와주세요](../../translations.md) — 프로그래밍은 필요 없습니다.
