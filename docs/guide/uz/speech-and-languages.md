<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · **Oʻzbekcha** · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Asl nusxa: Русский](../speech-and-languages.md).

# Nutq va tillar

Avval SMTV strim nutqini har bir soʻzning vaqti bilan matnga aylantiradi — SI nima boʻlganini shu orqali tushunadi. Bu
**kompyuteringizda, bepul** ishlaydi. SMTV strim tilini oʻzi aniqlaydi.

| Til | Model | Yuklab olish (bir marta) | 12 yadroli protsessordagi tezlik |
|---|---|---|---|
| Rus tili | GigaAM-v3, rus tili uchun yaratilgan | 0,9 GB | Real vaqtdan 54 marta tez |
| 25 ta Yevropa tili: ingliz, ispan, nemis, fransuz, italyan, portugal, polyak, ukrain va boshqalar | Parakeet-TDT v3 | 2,4 GB | Real vaqtdan 33 marta tez |
| Qolgan barcha tillar: xitoy, yapon, koreys, hind, bengal, qozoq, oʻzbek, ozarbayjon, vyetnam, indonez va yana oʻnlab tillar | Whisper large-v3-turbo | 1,6 GB | Hali oʻlchanmagan |

Model oʻz tilidagi strim birinchi marta kelganda oʻzi yuklanadi. Videokarta kerak emas; NVIDIA kartasi uni
tezlashtiradi. Mac’da Whisper protsessorda ishlaydi va sekinroq.

**Settings → Speech to text** (Sozlamalar → Nutqdan matnga) har bir modelni koʻrsatadi: qayerda ishlashi, tillari,
hajmi va tezligi, **Download** (Yuklab olish) va **Remove** (Oʻchirish) tugmalari bilan. U yerda har bir tilga boshqa
model berish mumkin, jumladan oʻz kalitingiz (Groq yoki OpenAI) bilan **Whisper in the cloud** (Bulutdagi Whisper) —
kuchsiz kompyuterda tezroq, lekin unda ovoz kompyuteringizdan chiqib ketadi.

<img src="../../images/speech.png" alt="Settings → Speech to text: modellar va ular qabul qiladigan tillar" width="820">

**Oyna tili** alohida: SMTV kompyuteringiz tilida gapiradi; **Settings → Language and theme** (Sozlamalar → Til va
mavzu) boshqasini tanlaydi. Tilingiz yoʻqmi yoki yarim tarjima qilinganmi? [Tarjima qilishga yordam bering](../../translations.md)
— dasturlash kerak emas.
