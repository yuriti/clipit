<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · **Oʻzbekcha** · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Asl nusxa: Русский](../free-ai-on-your-computer.md).

# Kompyuteringizda bepul SI

Sunʼiy intellekt (SI) toʻgʻridan-toʻgʻri kompyuteringizda, bepul ishlashi mumkin: hech narsa tashqariga chiqmaydi va
hech narsa toʻlash kerak emas. Sizga SI modellarini ishga tushiradigan dastur — **Ollama** yoki **LM Studio** — va
model, masalan **Qwen** kerak. SMTV dasturni oʻzi topadi.

**Rostini aytsak:** uy kompyuteriga sigʻadigan modellar bulutdagilardan kuchsizroq, shuning uchun kliplar yomonroq
chiqadi, va tavsiya etilgan modellarning hech biri hali SMTV bilan sinovdan oʻtkazilmagan. Natija sizni xafa qilsa,
[akkaunt](account.md) yoki [kalitni](get-a-key.md) sinab koʻring.

## 1. Kompyuteringizga qaysi model mos keladi

Asosiysi — videokartangizning **video xotirasi** (Apple silicon protsessorli Mac’da: butun xotira).

| Video xotira | Model | Yuklab olish | Izohlar |
|---|---|---|---|
| 8 GB dan kam | — | — | Juda kam: akkaunt yoki kalitdan foydalaning |
| 8 GB | `qwen3:8b` | 5,2 GB | Yetarlicha yaxshi ishlaydigan eng yengili |
| 10–12 GB | `qwen3-vl:8b` yoki `gemma3:12b` | 6,1 / 8,1 GB | Bular video kadrlariga ham qaraydi |
| 16 GB va undan koʻp | `qwen3:14b` | 9,3 GB | Toʻrttasining eng yaxshisi |

7B («7 milliard») dan kichik modellar tavsiya etilmaydi: ular SMTV’ga kerakli javoblarni buzadi.

**Video xotirangizni qanday bilish mumkin:**
- **Windows:** Ctrl+Shift+Esc ni bosing → **Performance** → **GPU** → **Dedicated GPU memory**.
- **Mac:** Apple menyusi → **About This Mac** → **Memory**. Mac xotirani SI bilan boʻlishadi: 16 GB boʻlsa `qwen3:8b`,
  32 GB yoki undan koʻp boʻlsa `qwen3:14b` ni oling.

## 2a. Ollama (eng oddiysi)

1. Ollama’ni [ollama.com/download](https://ollama.com/download) dan yuklab oling va boshqa dasturlar kabi oʻrnating.
   U oʻzi ishga tushadi va soat yonida turadi.
2. SMTV’da: **Settings → AI → Free, on this computer → Find on this computer** (Sozlamalar → SI → Bepul, bu
   kompyuterda → Bu kompyuterdan topish). SMTV Ollama’ni topadi.
3. Roʻyxatda **Ollama**ni oching: SMTV tavsiya etilgan modellarni hajmi bilan koʻrsatadi. Yuqoridagi jadvaldagi
   modelning yonidagi **Download** (Yuklab olish) tugmasini bosing va kuting (5–10 GB).
4. Tayyor. SMTV oʻz qadamlari uchun oʻsha modelni oʻzi tanlaydi.

SMTV har bir soʻrov uchun Ollama xotirasini butun strim matni sigʻadigan qilib sozlaydi; Ollama sozlamalarini
oʻzgartirishingiz shart emas.

## 2b. LM Studio

1. LM Studio’ni [lmstudio.ai/download](https://lmstudio.ai/download) dan yuklab oling va oʻrnating.
2. LM Studio’da **Discover** ni oching, **Qwen3 8B** ni (yoki jadvalga koʻra 14B ni) qidiring va **Download** ni
   bosing.
3. **Developer** yorligʻini oching va **Start server** ni yoqing (u 1234-portni tinglaydi). Modelni oʻsha yerda
   yuklang.
4. SMTV’da: **Settings → AI → Free, on this computer → Find on this computer**. SMTV LM Studio’ni topadi.

## 3. Klip yasang

SMTV’ga [video fayl](first-clip.md) bering. Twitch yoki YouTube havolasi uchun bepul SI bilan ham [akkaunt](account.md)
kerak: yozuvni akkaunt oladi.

Bepul SI bulutdagidan sekinroq ishlaydi; uzun strim bir necha soat olishi mumkin. Kompyuterni yoqiq qoldiring.
