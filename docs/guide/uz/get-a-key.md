<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · **Oʻzbekcha** · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Asl nusxa: Русский](../get-a-key.md).

# Kalitni qayerdan olish mumkin

**Kalit** («API kalit») — SMTV’ga sizning nomingizdan SI xizmatidan foydalanish imkonini beradigan uzun parol. Uni
roʻyxatdan oʻtganingizdan keyin xizmat saytida olasiz. SMTV uni faqat kompyuteringizda saqlaydi va faqat oʻsha
xizmatga yuboradi; u hech qachon loglarda yoki muammo hisobotlarida koʻrinmaydi.

> Narxlar va bepul tariflar oʻzgaradi. Bu yerda yozilganlar xizmatlarning oʻz sahifalarida **23.11.2026** sanasida tekshirilgan — boshlashdan oldin xizmat sahifasini tekshiring.

## Qaysi xizmat

| Xizmat | Bepul tarif | Kalitni qayerdan olish | Bilib qoʻyish foydali |
|---|---|---|---|
| **Google Gemini** | Ha, daqiqalik va kunlik cheklovlar bilan; bepul modellar Google narxlar sahifasida koʻrsatilgan | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Eng oson bepul boshlanish; toʻlov faqat pullik tarif uchun ulanadi. Bepul tarifda Google siz yuborganlarni oʻz mahsulotlarini yaxshilash uchun ishlatishi va odamlar oʻqishi mumkin — Yevropa iqtisodiy hududi, Shveytsariya va Buyuk Britaniyadan tashqari. Har bir mamlakatda mavjud emas (masalan, Rossiyada yoʻq): Google hududlar roʻyxatiga qarang. |
| **Groq** | Ha, cheklovlar bilan, ular konsolda koʻrsatilgan | [console.groq.com/keys](https://console.groq.com/keys) | Juda tez. Bulutda nutqni matnga ham arzon aylantira oladi (Whisper large-v3 turbo bilan bir soat audio uchun taxminan $0.04). |
| **OpenRouter** | Nomi `:free` bilan tugaydigan modellar: daqiqasiga 20 soʻrov, kuniga 50 (siz $10 kredit sotib olsangiz, kuniga 1,000) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Turli kompaniyalarning yuzlab modellari uchun bitta kalit. Uzun strim uchun kuniga 50 soʻrov yetarli emas. |
| **Mistral** | Saytidan aniqlang: uning sahifalarida API uchun bepul shartlar koʻrsatilmagan | [console.mistral.ai](https://console.mistral.ai) | Yevropa kompaniyasi. |
| **DeepSeek** | Yoʻq | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Avval toʻldiriladigan balansdan toʻlanadi. |
| **OpenAI** | Bepul kredit vaʼda qilinmaydi: yangi hisob oldindan toʻlaydi, $5 dan | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ChatGPT ortidagi modellar. ChatGPT obunasi kalit bilan bir xil emas: kalit alohida toʻlanadi. Faqat qoʻllab-quvvatlanadigan mamlakatlarda (Rossiyada yoʻq). |
| **Claude (Anthropic)** | Yoʻq | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Claude obunasi kalit bilan bir xil emas. Faqat qoʻllab-quvvatlanadigan hududlarda (Rossiyada yoʻq). |

SMTV xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras va har qanday OpenAI bilan mos manzilni ham biladi —
[tajribali foydalanuvchilar uchun](../../advanced.md#ai-services-and-keys) boʻlimiga qarang.

**Bepul tarifning cheklovlari bor.** Uzun strim koʻp soʻrov yuboradi; cheklovga yetganda xizmat «too many requests»
(soʻrovlar juda koʻp) deb javob beradi va SMTV kutadi yoki toʻxtaydi. 6–12 soatlik strim uchun pullik tarif yoki
[akkaunt](account.md) yaxshiroq ishlaydi.

## Misol: bepul Gemini kaliti, qadamma-qadam

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) ni oching va Google akkaunti bilan kiring.
2. Soʻralsa, shartlarni qabul qiling.
3. **Create API key** ni bosing. Kalitni nusxalang (u `AIza…` bilan boshlanadi). Uni parol kabi sir saqlang.
4. SMTV’da: **Settings → AI → Your own key → Add a key** (Sozlamalar → SI → Oʻz kalitingiz → Kalit qoʻshish).
5. **Gemini** ni tanlang, kalitni qoʻying, **Check** (Tekshirish) ni bosing. SMTV kalit ishlashini aytadi.
6. Tayyor. Endi SI’ning har bir qadami mos model bilan Gemini’dan foydalanadi; qaysi biri ekanini **Settings → AI
   steps** (Sozlamalar → SI qadamlari) koʻrsatadi.

Boshqa xizmatlar ham xuddi shunday ishlaydi: roʻyxatdan oʻting, **API keys** boʻlimini toping, kalit yarating, uni
SMTV’ga qoʻying, **Check** ni bosing. Pullik xizmatlar avval karta qoʻshishni yoki balansni toʻldirishni soʻraydi.

## Kalitingiz xavfsiz

- Kompyuteringizda, shifrlangan holda saqlanadi.
- Faqat u tegishli boʻlgan xizmatga yuboriladi. StreamMoment uni hech qachon koʻrmaydi.
- Yoʻqotdingizmi yoki sizib chiqdimi? Uni xizmat saytida oʻchiring va yangisini yarating.
