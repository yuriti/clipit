<!-- languages -->
[Русский](../get-a-key.md) · **English** · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 This page was translated automatically from the [Russian original](../get-a-key.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Where to get a key

A **key** (an «API key») is a long password that lets SMTV use an AI service on your behalf. You get it on the
service's site after you sign up. SMTV keeps it only on your computer and sends it only to that service; it never
shows up in logs or problem reports.

> Prices and free plans change. What is written here was checked on the services' own pages on **23.11.2026** — check
> the service's page before you start.

## Which service

| Service | Free plan | Where to get the key | Good to know |
|---|---|---|---|
| **Google Gemini** | Yes, with limits per minute and per day; the free models are listed on Google's pricing page | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | The easiest free start; billing is set up only for the paid plan. On the free plan Google may use what you send to improve its products and people may read it — except in the EEA, Switzerland and the UK. Not available in every country (not in Russia, for example): see Google's list of regions. |
| **Groq** | Yes, with limits shown in its console | [console.groq.com/keys](https://console.groq.com/keys) | Very fast. Also turns speech into text in the cloud, cheaply (about $0.04 per hour of audio with Whisper large-v3 turbo). |
| **OpenRouter** | Models whose name ends in `:free`: 20 requests a minute, 50 a day (1,000 a day once you have bought $10 of credit) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | One key for hundreds of models from different companies. 50 requests a day is not enough for a long stream. |
| **Mistral** | Check on its site: its pages did not state free terms for the API | [console.mistral.ai](https://console.mistral.ai) | A European company. |
| **DeepSeek** | No | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Paid from a balance you top up first. |
| **OpenAI** | No free credit is promised: a new account pays in advance, from $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | The models behind ChatGPT. A ChatGPT subscription is not the same as a key: the key is paid separately. Only in supported countries (not in Russia). |
| **Claude (Anthropic)** | No | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | A Claude subscription is not the same as a key. Only in supported regions (not in Russia). |

SMTV also knows xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras and any OpenAI-compatible address — see
[for advanced users](../../advanced.md#ai-services-and-keys).

**A free plan has limits.** A long stream sends many requests; when the limit is reached the service answers «too
many requests» and SMTV waits or stops. For a 6–12 hour stream a paid plan or the [account](account.md) works better.

## Example: a free Gemini key, step by step

1. Open [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and sign in with a Google account.
2. Accept the terms if asked.
3. Press **Create API key**. Copy the key (it starts with `AIza…`). Keep it secret, like a password.
4. In SMTV: **Settings → AI → Your own key → Add a key**.
5. Choose **Gemini**, paste the key, press **Check**. SMTV says whether the key works.
6. Done. Every step of the AI now uses Gemini with a suitable model; **Settings → AI steps** shows which.

Other services work the same way: sign up, find **API keys**, create one, paste it into SMTV, press **Check**.
Paid services first ask you to add a card or top up a balance.

## Your key is safe

- Kept on your computer, encrypted.
- Sent only to the service it belongs to. StreamMoment never sees it.
- Lost or leaked? Delete it on the service's site and create a new one.
