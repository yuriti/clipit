<!-- The source is the Russian README.md; translations: README.<language>.md, the same structure. A change to README.md
     changes README.en.md in the same PR; the other languages follow (each says it was translated automatically from
     the Russian original and links it and Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**Uzun strimni qisqa kliplar va jamlanma videoga aylantiring. Bepul, oʻz kompyuteringizda.**

<!-- languages -->
[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md) · **Oʻzbekcha** · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Deutsch](README.de.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Asl nusxa: Русский](README.md).

[![Soʻnggi versiya](https://img.shields.io/github/v/release/yuriti/clipit?label=release)](https://github.com/yuriti/clipit/releases/latest)
[![Yuklab olishlar](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![Yulduzlar](https://img.shields.io/github/stars/yuriti/clipit?style=flat)](https://github.com/yuriti/clipit/stargazers)
[![Litsenziya: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Weblate’da tarjima qiling](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: strim yozuvi kiradi, SMTV eng yaxshi lahzalarni topadi va birin-ketin vertikal kliplar yasaydi" width="820">

[**SMTV’ni yuklab olish**](#yuklab-olish) · [Qadamma-qadam qoʻllanmalar](docs/guide/uz/README.md) · [Taqqoslash](#smtv-boshqalar-bilan-taqqoslaganda) · [Savollar](#savollar)

</div>

---

Siz olti soat strim qildingiz. Uning ichida joylashga arziydigan oʻnta lahza bor — lekin ularni topish uchun hammasini
qaytadan koʻrib chiqish kerak. **SMTV siz uchun koʻrib chiqadi.** Twitch yoki YouTube yozuvining havolasini qoʻying
yoki video faylni tanlang: SMTV butun strimni tinglaydi, eng yaxshi lahzalarni tanlaydi va sizga TikTok, Shorts va
Reels uchun **joylashga tayyor vertikal kliplar** beradi — subtitrlar va tepada veb-kamera bilan — hamda YouTube uchun
butun strimning **20–30 daqiqalik jamlanma videosini**.

## Nima qiladi

| | |
|---|---|
| 🎬 **Joylashga tayyor kliplar** | Vertikal 9:16, katta subtitrlar, boshida qisqa sarlavha kartasi va oʻyin ustida strimerning veb-kamerasi. |
| ⏱️ **Uzun strimlar muammo emas** | 6–12 soatlik yozuv kiradi, 30 tagacha klip chiqadi. Kliplar birin-ketin paydo boʻladi: qolganlari tayyor boʻlmasdan joylashni boshlang. |
| 📺 **Butun strimning jamlanmasi** | YouTube uchun 20–30 daqiqalik video: strimning oʻzi, koʻrishga arziydigan qismlargacha qisqartirilgan. |
| 🗣️ **Koʻp tillar** | Rus tili, 25 ta Yevropa tili va yana oʻnlab tillar. SMTV nutqni toʻgʻridan-toʻgʻri kompyuteringizda matnga aylantiradi. |
| 🔒 **Fayllaringiz sizda qoladi** | Kliplar kompyuteringizda yasaladi va saqlanadi. Hech narsa saytga yuklanmaydi. |
| 💸 **Bepul va ochiq** | MIT litsenziyasi: foydalaning, ulashing, mijozlar uchun ishlating. Suv belgisi yoʻq, daqiqa cheklovi yoʻq. |

## Ishda koʻring

**Havolani qoʻying yoki faylni tanlang — va qadamlarni kuzating.** Har bir qadam ekranda: nutqni matnga aylantirish,
lahzalarni topish, ularni baholash, har bir klipni montaj qilish.

<img src="docs/images/new-request.gif" alt="Yangi soʻrov: video fayl tanlanadi, SMTV ishga tushadi va har bir qadamni koʻrsatadi" width="820">

**Kliplar birin-ketin paydo boʻladi.** Ularni toʻgʻridan-toʻgʻri SMTV’da koʻring, yuklab oling, joylang.

<img src="docs/images/clips.png" alt="Strimning tayyor kliplari jadval koʻrinishida" width="820">

**Har bir klipning oʻz matni bor.** Nima deyilganini va SMTV bu lahzani nega tanlaganini oʻqing.

<img src="docs/images/viewer.png" alt="Klip oʻz transkripti yonida ijro etilmoqda" width="820">

**Va butun strimning jamlanmasi** YouTube uchun, kliplardan keyin yasaladi.

<img src="docs/images/recap.png" alt="SMTV’dagi strim jamlanmasi" width="820">

**Yorugʻ yoki qorongʻi** — kompyuteringizdagidek.

<img src="docs/images/dark.png" alt="Qorongʻi mavzudagi SMTV" width="820">

<sub>Bu rasmlardagi strim demo uchun oʻylab topilgan: kichik oʻyin, veb-kamera oʻrniga multfilm maskoti va kompyuter
ovozi. Ekranda haqiqiy odam yoʻq.</sub>

## Bepul va ochiq kodli

- **SMTV bepul.** Butun dastur [MIT litsenziyasi](LICENSE) ostida ochiq kodli: uni oʻzingiz, kanalingiz yoki
  mijozlaringiz uchun ishlating, oʻzgartiring va ulashing.
- **Suv belgisi yoʻq, daqiqa cheklovi yoʻq, SMTV’ga obuna yoʻq.**
- **Faqat sunʼiy intellekt uchun toʻlaysiz, u ham xohlasangiz.** SMTV’ga strim matnini oʻqib, lahzalarni tanlaydigan
  sunʼiy intellekt (SI) kerak. Bu oʻz kompyuteringizdagi bepul SI yoki oʻzingiz tanlagan xizmat boʻlishi mumkin —
  pastga qarang.
- **Maʼlumotlaringiz sizda qoladi.** Kliplar kompyuteringizda yasaladi va saqlanadi. Faqat strim matni siz tanlagan
  SI’ga boradi. Kompyuteringizdagi bepul SI bilan esa umuman hech narsa tashqariga chiqmaydi.

## SI’ni tanlang: uchta yoʻl

SMTV nutqni oʻzi kompyuteringizda matnga aylantiradi. Eng yaxshi lahzalarni tanlash uchun esa SI’dan soʻraydi. Bitta
yoʻlni tanlang — bittasi yetarli va uni istalgan vaqtda **Settings → AI** (Sozlamalar → SI) boʻlimida oʻzgartirishingiz
mumkin.

| | Qanday | Narxi | Kimga mos |
|---|---|---|---|
| ⭐ **Akkaunt orqali** | StreamMoment akkauntiga kiring (Google, Twitch yoki Telegram) va balansni toʻldiring. Boʻldi: kalit yoʻq, sozlash yoʻq. | Foydalanishga qarab balansdan toʻlov | Hammaga: eng oddiy yoʻl. Yozuvlarning **havolalarini** qoʻyish uchun ham kerak. [Qoʻllanma](docs/guide/uz/account.md) |
| 🔑 **Oʻz kalitingiz** | OpenAI, Claude, Gemini yoki OpenRouter’dan allaqachon foydalanasizmi? Kalitingizni qoʻying, SMTV undan toʻgʻridan-toʻgʻri foydalanadi. | Oʻsha xizmatga toʻgʻridan-toʻgʻri toʻlaysiz; baʼzilarida bepul tarif bor | SI xizmatidan allaqachon foydalanayotganlarga. [Kalitni qayerdan olish mumkin](docs/guide/uz/get-a-key.md) |
| 💻 **Bepul, kompyuteringizda** | Ollama yoki LM Studio va Qwen modelini oʻrnating; SMTV uni oʻzi topadi. | Bepul | Kuchli videokartali kompyuterga. Kliplar sustroq chiqadi. [Qoʻllanma](docs/guide/uz/free-ai-on-your-computer.md) |

## Yuklab olish

| Kompyuteringiz | Yuklab olish | Hajmi |
|---|---|---|
| **Windows 10 yoki 11** (64-bit) | [**Windows uchun SMTV**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) (oʻrnatuvchi) | taxminan 130 MB |
| **Mac** — Apple silicon (M1 va yangiroq) yoki Intel, macOS 13+ | [**Mac uchun SMTV**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | taxminan 270 MB |

Har qanday Mac uchun bitta fayl: SMTV Mac’ingiz protsessori uchun yaratilgan versiyani oʻzi ishga tushiradi. Windows’da hech narsa oʻrnatmasdan:
[ZIP arxiv](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) — uni arxivdan chiqaring va **Start SMTV** ni oching.

SMTV’ga kerak boʻlgan hamma narsa ichida: dasturning oʻzi, Python va subtitrli ffmpeg. Nutqni tanish birinchi ishga
tushirishda faqat sizning tilingiz uchun yuklanadi (0,9–2,5 GB, bir marta): SMTV uni bitta tugma bilan taklif qiladi —
**Fix** (Tuzatish).

**Birinchi marta tizim ogohlantiradi.** SMTV’da hozircha raqamli imzo yoʻq: Windows uchun imzo biroz keyinroq, macOS
uchun esa imkon boʻlishi bilan paydo boʻladi, shunda bu ogohlantirish yoʻqoladi. Ungacha:

- **Windows** («Windows protected your PC»): **More info** → **Run anyway**.
- **Mac**: SMTV’ni bir marta oching, keyin **System Settings → Privacy & Security** → **Open Anyway**.
- **Smart App Control yoqilgan Windows 11** imzosiz dasturlarni butunlay bloklaydi va ularni oʻtkazib yuboradigan
  tugma yoʻq. Quyidagi bir qatorda oʻrnatishdan foydalaning: u Smart App Control yoqilgan boʻlsa ham ishlaydi. SMTV
  imzolanganda yuklab olingan fayl ham u yerda ishlaydi.

[Har bir qadam rasmlar bilan](docs/guide/uz/install.md).

### Tajribalilar uchun: terminalda bitta qator

Xuddi oʻsha SMTV, faqat [uv](https://astral.sh/uv) yordamida foydalanuvchi papkangizga oʻrnatiladi. U **Linux**’da
ham, **Smart App Control** bilan ham ishlaydi va oynadan xuddi shunday yangilanadi.

**Windows** — Start tugmasini bosing, **PowerShell** deb yozing, uni oching va qoʻying:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

**Mac yoki Linux** — **Terminal**ni oching va qoʻying:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Enter’ni bosing va bir necha daqiqa kuting. Administrator paroli kerak emas. **SMTV** belgisi paydo boʻladi —
Windows’da ish stolida va Start menyusida, Mac’da Applications papkasida, Linux’da dasturlar menyusida.

## Uch qadamda birinchi klipingiz

1. **SI’ni tanlang** — birinchi marta oyna uchta yoʻlni koʻrsatadi ([qaysi biri?](docs/guide/uz/connect-ai.md)).
2. Twitch yoki YouTube yozuvining **havolasini qoʻying** yoki kompyuteringizdan video faylni tanlang.
3. **Kuting.** Kliplar birin-ketin paydo boʻladi: koʻring, yuklab oling, joylang.

Birinchi marta SMTV kompyuteringizni tekshiradi va yetishmayotganini bitta tugma bilan tuzatishni taklif qiladi:
**Fix** (Tuzatish). [Birinchi klip, qadamma-qadam](docs/guide/uz/first-clip.md).

## Qadamma-qadam qoʻllanmalar

Bularning barchasi bilan endi tanishayotganlar uchun — har bir qadam, rasmlar bilan:

| | |
|---|---|
| [Windows, Mac yoki Linux’ga oʻrnatish](docs/guide/uz/install.md) | va tizim ogohlantirsa nima qilish kerak |
| [Birinchi klipingiz](docs/guide/uz/first-clip.md) | havola yoki fayldan tayyor klipgacha |
| [Qaysi SI’ni tanlash kerak](docs/guide/uz/connect-ai.md) | uchta yoʻl yonma-yon |
| [Kompyuteringizda bepul SI](docs/guide/uz/free-ai-on-your-computer.md) | Qwen bilan Ollama yoki LM Studio: videokartangizga qaysi model mos |
| [Kalitni qayerdan olish mumkin](docs/guide/uz/get-a-key.md) | qaysi xizmatlarda bepul yoki arzon tarif bor, qadamma-qadam |
| [StreamMoment akkaunti](docs/guide/uz/account.md) | kirish, balans |
| [Telefonda SMTV](docs/guide/uz/phone.md) | QR kodni skanerlang va kliplarni telefonda koʻring |
| [Nutq va tillar](docs/guide/uz/speech-and-languages.md) | SMTV qaysi tillarni tushunadi |
| [Yangilash va oʻchirish](docs/guide/uz/update-and-remove.md) | |
| [Nimadir notoʻgʻri ketdi](docs/guide/uz/troubleshooting.md) | kompyuter tekshiruvi, **Fix**, **Report a problem** |

## SMTV boshqalar bilan taqqoslaganda

Eng koʻp foydalaniladigan ochiq kodli klip dasturlari, har bir loyihaning oʻz kodi va hujjatlariga koʻra, **2026-yil
noyabr holatiga**. Bular yaxshi loyihalar, har biri oʻz vazifasi uchun yaratilgan; bu jadval faqat SMTV nimasi bilan
farq qilishini koʻrsatadi. Nimadir oʻzgardimi? [Bizga xabar bering](https://github.com/yuriti/clipit/issues/new?template=bug.yml),
jadvalni tuzatamiz.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| Litsenziya | **MIT** | MIT (`cloud/` papkasining oʻz litsenziyasi bor) | Notijorat manba kodi litsenziyasi | MIT | MIT |
| Butun 6–12 soatlik strim | **Ha** | Standart boʻyicha bitta vazifaga 60 daqiqa | Standart boʻyicha 90 daqiqa | Uzunlik cheklovi koʻrsatilmagan | Strimlar uchun moʻljallanmagan |
| Butun strimning uzun jamlanmasi | **Ha, 20–30 daqiqa** | Yoʻq | Yoʻq (uning «recap»i bitta qisqa klip) | Yoʻq | Yoʻq |
| Rus nutqi | **GigaAM-v3, rus tili uchun yaratilgan** | Whisper yoki Parakeet v3 | AssemblyAI yoki Whisper | Yoʻq (Parakeet v2, faqat ingliz tili) | Yoʻq (xitoy va ingliz tillari) |
| Vertikal kadrda strimerning veb-kamerasi | **Ha** | Yoʻq | Oʻyin rejimi, standart boʻyicha oʻchiq | Ha | Vertikal kliplar yoʻq |
| Standart boʻyicha nutqni matnga aylantirish | **Kompyuteringizda, bepul** | Kompyuteringizda | AssemblyAI, pullik xizmat | Kompyuteringizda | Kompyuteringizda |
| Qanday ishga tushiriladi | **Oʻz oynasi va belgisi: Windows va Mac uchun yuklab olinadigan fayl yoki bitta qator** | Docker’dagi veb-sahifa | Docker’dagi veb-sahifa | Veb-sahifa | Veb-sahifa |

## Savollar

<details>
<summary><b>Rostdan ham bepulmi?</b></summary>

Ha. SMTV’ning oʻzi hech narsa turmaydi va cheklovlari yoʻq. Yagona mumkin boʻlgan xarajat — lahzalarni tanlaydigan
SI: oʻz kompyuteringizda bepul yoki siz tanlagan xizmatga pullik (StreamMoment akkaunti yoki oʻz kalitingiz orqali).
</details>

<details>
<summary><b>Kuchli kompyuter kerakmi?</b></summary>

Videokarta kerak emas: SMTV oddiy kompyuterda ishlaydi, faqat sekinroq. NVIDIA kartasi nutqni matnga aylantirishni
tezlashtiradi. Oʻz kompyuteringizdagi bepul SI bundan mustasno — unga kuchli videokarta kerak
([qaysi biri](docs/guide/uz/free-ai-on-your-computer.md)). Diskda boʻsh joy: kamida 5 GB, 6 soatlik strim uchun 20 GB.
</details>

<details>
<summary><b>Qancha vaqt oladi?</b></summary>

Apple silicon protsessorli Mac’da, videokartasiz oʻlchangan: 2,35 soatlik Twitch yozuvida lahzalarni topish taxminan
6 daqiqa, keyin har bir klip taxminan 1 daqiqa oldi; 10,7 daqiqalik jamlanma 6,5 daqiqa oldi. Soʻrov boshlanishidan
oldin SMTV u qancha vaqt olishini koʻrsatadi.
</details>

<details>
<summary><b>Qaysi tizimlarda ishlaydi?</b></summary>

Windows 10 (1809-versiya) yoki yangiroq, 64-bit; Apple silicon’li va Intel’li Mac’da macOS 13 yoki yangiroq (Apple silicon’da SMTV macOS 14 dan boshlab bevosita ishlaydi; macOS 13 da oʻzining Intel versiyasini Rosetta orqali ishga tushiradi, sekinroq); Linux (bir qatorda oʻrnatish). Windows 11 va Apple silicon’li Mac’larda tekshirilgan; Intel
Mac’lar (faqat Rosetta ostida) va Linux ish stollari hali sinovdan oʻtkazilmagan.
</details>

<details>
<summary><b>Qaysi tillarni tushunadi?</b></summary>

Rus tili, 25 ta Yevropa tili va yana oʻnlab tillar. SMTV strim tilini oʻzi aniqlaydi.
[Batafsil](docs/guide/uz/speech-and-languages.md).
</details>

<details>
<summary><b>Kliplardan mijozlarim uchun foydalansam boʻladimi?</b></summary>

Ha. MIT litsenziyasi har qanday foydalanishga, jumladan tijoriy foydalanishga ruxsat beradi: strimerlar, agentliklar,
oʻz kanallaringiz uchun klip yasash. Strimini kesayotgan strimerning huquqlarini hurmat qiling.
</details>

<details>
<summary><b>Kliplarim qayerga ketadi? Biror narsa yuklanadimi?</b></summary>

Kliplar kompyuteringizda qoladi. Oʻzingizning video faylingiz hech qachon undan chiqmaydi. Havola StreamMoment
akkaunti orqali olinadi: uning serveri yozuvni SMTV’ga boʻlakma-boʻlak uzatadi va hech narsa saqlamaydi. Strim matni
faqat siz tanlagan SI’ga boradi. SI xizmatlarining kalitlari kompyuteringizda qoladi va hech qachon loglarda yoki
muammo hisobotlarida koʻrinmaydi.
</details>

<details>
<summary><b>TikTok yoki YouTube’ga oʻzi joylaydimi?</b></summary>

Hozircha yoʻq: kliplarni yuklab olib, oʻzingiz joylaysiz. Settings → About → «Coming» (Sozlamalar → Dastur haqida →
Tez orada) nima rejalashtirilganini koʻrsatadi.
</details>

<details>
<summary><b>Nimadir ishlamayapti.</b></summary>

Settings → **Computer check** → **Fix** (Sozlamalar → Kompyuter tekshiruvi → Tuzatish) koʻp muammolarni hal qiladi.
Baribir chiqmayaptimi? Settings → Computer check → **Report…**: SMTV kalitlaringizsiz hisobot tayyorlaydi va GitHub’da
sahifa ochadi; hech narsa oʻzi yuborilmaydi. [Nimani sinab koʻrish kerak](docs/guide/uz/troubleshooting.md).
</details>

## SMTV’ni tarjima qilishga yordam bering

SMTV oynasi kompyuteringiz tilida gapiradi. Tarjimalarni odamlar [Weblate](https://hosted.weblate.org/engage/smtv/)’da
qiladi — dasturlash kerak emas: sahifani oching, tilingizni tanlang, bir necha qatorni tarjima qiling. Bu sahifaning
tarjimalari avtomatik qilingan; xato koʻrsangiz, uni pull request orqali tuzating.
[Tarjimalar qanday ishlaydi](docs/translations.md).

[![Tarjima holati](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV’ni [StreamMoment](https://streammoment.tv) jamoasi yaratadi. StreamMoment akkaunti SMTV’ga SI berish va
yozuvlarning havolalarini qoʻyishning eng oddiy yoʻli; SMTV usiz ham ishlaydi.

- [Muammo haqida xabar bering](https://github.com/yuriti/clipit/issues/new?template=bug.yml) · [Gʻoya taklif qiling](https://github.com/yuriti/clipit/issues/new?template=feature.yml)
- [Tajribali foydalanuvchilar uchun](docs/advanced.md): Docker, barcha SI xizmatlari, nutq modellari, kalitlar, buyruqlar
- [Oʻzgarishlar](CHANGELOG.md) · [Hissa qoʻshish](CONTRIBUTING.md) · [Xavfsizlik](SECURITY.md)
- SMTV yoqdimi? [Boosty’da qoʻllab-quvvatlang](https://boosty.to/smtv) va repozitoriyga ⭐ bering — bu boshqalarga uni
  topishga yordam beradi.

Litsenziya: [MIT](LICENSE).
