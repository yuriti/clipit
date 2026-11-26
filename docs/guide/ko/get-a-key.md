<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · **한국어** · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/yuriti/clipit/pulls) · [원문: Русский](../get-a-key.md).

# 키 받는 곳

**키**(«API 키»)는 SMTV가 나 대신 AI 서비스를 쓸 수 있게 해 주는 긴 비밀번호입니다. 서비스에 가입하면 그 사이트에서 받을 수 있습니다.
SMTV는 키를 내 컴퓨터에만 보관하고 그 서비스에만 보냅니다. 로그나 문제 보고서에는 절대 나타나지 않습니다.

> 가격과 무료 요금제는 바뀝니다. 여기 적힌 내용은 각 서비스의 공식 페이지에서 **23.11.2026**에 확인한 것입니다 — 시작하기 전에 서비스 페이지를 확인하세요.

## 어떤 서비스로

| 서비스 | 무료 요금제 | 키 받는 곳 | 알아 두면 좋은 점 |
|---|---|---|---|
| **Google Gemini** | 있음, 분당·일일 한도 있음. 무료 모델은 Google 가격 페이지에 나와 있음 | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 무료로 시작하기 가장 쉬움. 결제는 유료 요금제에서만 설정합니다. 무료 요금제에서는 Google이 보낸 내용을 자사 제품 개선에 쓸 수 있고 사람이 읽을 수도 있습니다 — 유럽경제지역, 스위스, 영국은 제외입니다. 모든 나라에서 쓸 수 있는 것은 아닙니다(예: 러시아에서는 안 됨): Google의 지원 지역 목록을 보세요. |
| **Groq** | 있음, 한도 있음. 한도는 콘솔에 표시됨 | [console.groq.com/keys](https://console.groq.com/keys) | 매우 빠름. 클라우드에서 음성 텍스트 변환도 저렴하게 할 수 있습니다(Whisper large-v3 turbo 기준 오디오 1시간에 약 $0.04). |
| **OpenRouter** | 이름이 `:free`로 끝나는 모델: 분당 20회, 하루 50회 요청(크레딧 $10어치를 구매하면 하루 1,000회) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | 키 하나로 여러 회사의 모델 수백 개를 쓸 수 있습니다. 긴 방송에는 하루 50회 요청으로는 부족합니다. |
| **Mistral** | 사이트에서 확인하세요: 해당 페이지에는 API의 무료 조건이 적혀 있지 않았습니다 | [console.mistral.ai](https://console.mistral.ai) | 유럽 회사입니다. |
| **DeepSeek** | 없음 | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | 먼저 충전한 잔액에서 결제됩니다. |
| **OpenAI** | 무료 크레딧은 약속되지 않음: 새 계정은 선결제, $5부터 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ChatGPT 뒤에 있는 모델. ChatGPT 구독과 키는 다릅니다: 키는 따로 결제합니다. 지원되는 국가에서만 가능(러시아는 불가). |
| **Claude (Anthropic)** | 없음 | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Claude 구독과 키는 다릅니다. 지원되는 지역에서만 가능(러시아는 불가). |

SMTV는 xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras, 그리고 OpenAI 호환 주소라면 무엇이든 지원합니다 —
[고급 사용자용](../../advanced.md#ai-services-and-keys)을 보세요.

**무료 요금제에는 한도가 있습니다.** 긴 방송은 요청을 많이 보냅니다. 한도에 닿으면 서비스가 "요청이 너무 많음"(«too many requests»)이라고 답하고
SMTV는 기다리거나 멈춥니다. 6–12시간 방송이라면 유료 요금제나 [계정](account.md)이 더 잘 맞습니다.

## 예시: 무료 Gemini 키, 단계별로

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey)를 열고 Google 계정으로 로그인합니다.
2. 요청하면 약관에 동의합니다.
3. **Create API key**를 누릅니다. 키를 복사합니다(`AIza…`로 시작). 비밀번호처럼 비밀로 지키세요.
4. SMTV에서: **Settings → AI → Your own key → Add a key**(설정 → AI → 내 키 → 키 추가).
5. **Gemini**를 고르고 키를 붙여 넣은 뒤 **Check**(확인)를 누릅니다. 키가 작동하는지 SMTV가 알려 줍니다.
6. 끝. 이제 AI의 모든 단계가 알맞은 모델로 Gemini를 씁니다. 어떤 모델인지는 **Settings → AI steps**(설정 → AI 단계)에서 볼 수 있습니다.

다른 서비스도 똑같습니다: 가입하고, **API keys**를 찾아 키를 만들고, SMTV에 붙여 넣고, **Check**를 누릅니다.
유료 서비스는 먼저 카드를 등록하거나 잔액을 충전하라고 합니다.

## 내 키는 안전합니다

- 암호화되어 내 컴퓨터에 보관됩니다.
- 그 키의 서비스에만 전송됩니다. StreamMoment는 절대 볼 수 없습니다.
- 잃어버렸거나 유출됐나요? 서비스 사이트에서 삭제하고 새로 만드세요.
