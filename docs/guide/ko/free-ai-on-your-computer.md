<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · **한국어** · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/yuriti/clipit/pulls) · [원문: Русский](../free-ai-on-your-computer.md).

# 내 컴퓨터의 무료 AI

AI를 내 컴퓨터에서 바로, 무료로 돌릴 수 있습니다: 아무것도 밖으로 나가지 않고, 낼 돈도 없습니다. AI 모델을 돌리는 프로그램 —
**Ollama** 또는 **LM Studio** — 과 모델(예: **Qwen**)이 필요합니다. SMTV가 그 프로그램을 알아서 찾습니다.

**솔직히 말하면:** 가정용 컴퓨터에서 돌아가는 모델은 클라우드 모델보다 약해서 클립 품질이 떨어지고, 추천 모델 중 어느 것도
아직 SMTV와 함께 테스트하지 않았습니다. 결과가 실망스럽다면 [계정](account.md)이나 [키](get-a-key.md)를 써 보세요.

## 1. 내 컴퓨터에 맞는 모델

중요한 것은 그래픽 카드의 **비디오 메모리**입니다(Apple 실리콘 Mac에서는 전체 메모리).

| 비디오 메모리 | 모델 | 다운로드 | 참고 |
|---|---|---|---|
| 8 GB 미만 | — | — | 너무 적음: 계정이나 키를 쓰세요 |
| 8 GB | `qwen3:8b` | 5.2 GB | 충분히 쓸 만한 것 중 가장 가벼움 |
| 10–12 GB | `qwen3-vl:8b` 또는 `gemma3:12b` | 6.1 / 8.1 GB | 영상 프레임도 봅니다 |
| 16 GB 이상 | `qwen3:14b` | 9.3 GB | 넷 중 최고 |

7B(«70억») 미만 모델은 권장하지 않습니다: SMTV에 필요한 답변 형식을 망가뜨립니다.

**비디오 메모리 확인하는 법:**
- **Windows:** Ctrl+Shift+Esc → **성능**(Performance) → **GPU** → **전용 GPU 메모리**(Dedicated GPU memory).
- **Mac:** Apple 메뉴 → **이 Mac에 관하여**(About This Mac) → **메모리**(Memory). Mac은 메모리를 AI와 나눠 씁니다: 16 GB면 `qwen3:8b`,
  32 GB 이상이면 `qwen3:14b`.

## 2a. Ollama(가장 간단)

1. [ollama.com/download](https://ollama.com/download)에서 Ollama를 받아 다른 프로그램처럼 설치합니다. 저절로 실행되고
   시계 근처에 자리 잡습니다.
2. SMTV에서: **Settings → AI → Free, on this computer → Find on this computer**(설정 → AI → 무료, 이 컴퓨터에서 → 이 컴퓨터에서 찾기). SMTV가 Ollama를 찾습니다.
3. 목록에서 **Ollama**를 엽니다: SMTV가 추천 모델과 크기를 보여 줍니다. 위 표에 맞는 모델 옆의 **Download**(다운로드)를 누르고 기다립니다(5–10 GB).
4. 끝. SMTV가 그 모델을 각 단계에 알아서 씁니다.

SMTV는 요청마다 방송 텍스트 전체가 들어가도록 Ollama의 메모리를 설정합니다. Ollama 설정을 바꿀 필요는 없습니다.

## 2b. LM Studio

1. [lmstudio.ai/download](https://lmstudio.ai/download)에서 LM Studio를 받아 설치합니다.
2. LM Studio에서 **Discover**를 열고 **Qwen3 8B**(표에 따라 14B)를 검색해 **Download**를 누릅니다.
3. **Developer** 탭을 열고 **Start server**를 켭니다(포트 1234에서 대기합니다). 거기서 모델을 불러옵니다.
4. SMTV에서: **Settings → AI → Free, on this computer → Find on this computer**. SMTV가 LM Studio를 찾습니다.

## 3. 클립 만들기

SMTV에 [동영상 파일](first-clip.md)을 넣으세요. 무료 AI를 쓰더라도 Twitch나 YouTube 링크에는 [계정](account.md)이 필요합니다:
녹화본을 가져오는 것이 계정이기 때문입니다.

무료 AI는 클라우드보다 느려서, 긴 방송은 몇 시간이 걸릴 수 있습니다. 컴퓨터를 켜 두세요.
