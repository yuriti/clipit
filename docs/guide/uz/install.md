<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · **Oʻzbekcha** · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Asl nusxa: Русский](../install.md).

# SMTV’ni oʻrnatish

Bitta faylni yuklab oling, uni oching — va **SMTV** belgisi paydo boʻladi. SMTV’ga kerak boʻlgan hamma narsa ichida.
Administrator paroli kerak emas.

| Kompyuteringiz | Yuklab olish | Hajmi |
|---|---|---|
| **Windows 10 yoki 11** (64-bit) | [Windows uchun SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | taxminan 130 MB |
| **Mac** — Apple silicon (M1 va yangiroq) yoki Intel, macOS 13+ | [Mac uchun SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | taxminan 270 MB |

Barcha versiyalar va ularning nazorat yigʻindilari: [reliz sahifasi](https://github.com/streammomenttv/smtv/releases/latest).

**Nega tizim birinchi marta ogohlantiradi.** SMTV’da hozircha raqamli imzo yoʻq. Windows uchun imzo biroz keyinroq,
macOS uchun esa imkon boʻlishi bilan paydo boʻladi, shunda bu ogohlantirish yoʻqoladi. SMTV kodi ochiq: uning nima
qilishini istalgan odam oʻqib koʻrishi mumkin.

## Windows

1. **Windows uchun SMTV** ni (`SMTV-…-windows-x64-setup.exe` fayli) yuklab oling va oching.
2. Windows **«Windows protected your PC»** degan koʻk oyna koʻrsatadi. **More info**, keyin **Run anyway** ni bosing.
3. Oʻrnatuvchi bir-ikkita savol beradi (til, ish stolidagi belgi) — **Next** va **Install** ni bosing.
4. Oxirida **Launch SMTV** belgisini qoldiring va **Finish** ni bosing. Keyingi safar SMTV’ni **Start** menyusidan
   (yoki ish stolidagi belgidan) ishga tushiring.

Oʻrnatuvchi SMTV’ni oʻz foydalanuvchi papkangizga qoʻyadi; u **Settings → Apps** (Sozlamalar → Ilovalar) boʻlimida
paydo boʻladi, uni oʻsha yerdan oʻchirish mumkin.

**Oʻrnatmasdan:** [ZIP arxivni](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip) yuklab oling, istalgan joyga (masalan, Documents papkasiga) arxivdan chiqaring
va `SMTV` papkasidagi **Start SMTV** ni oching. Bu nusxa oʻzi yangilanmaydi: yangi versiya — bu yangi ZIP.

### Windows 11: Smart App Control

Agar **Smart App Control** yoqilgan boʻlsa (Windows Security → App & browser control), Windows imzosiz dasturlarni
butunlay bloklaydi va ularni oʻtkazib yuboradigan tugma yoʻq. SMTV uchun Smart App Control’ni oʻchirish shart emas.
Buning oʻrniga SMTV’ni bitta qator bilan oʻrnating — u Smart App Control yoqilgan boʻlsa ham ishlaydi:
[terminalda bitta qator](#tajribalilar-uchun-terminalda-bitta-qator). SMTV imzolanganda yuklab olingan fayl ham u yerda ishlaydi.

## Mac

1. **Mac uchun SMTV** ni yuklab oling. Bu Apple silicon’li yoki Intel’li har qanday Mac uchun bitta fayl: SMTV Mac’ingiz protsessori uchun yaratilgan versiyani oʻzi ishga tushiradi.
2. Yuklab olingan `.dmg` ni oching. SMTV va **Applications** papkasi bor oyna ochiladi: **SMTV** ni **Applications**
   ustiga sudrab olib boring.
3. **Applications** ni oching va **SMTV** ni ikki marta bosing. macOS SMTV’ni tekshira olmasligini aytadi va uni
   ochmaydi. **Done** ni bosing.
4. **System Settings → Privacy & Security** ni oching va pastga aylantiring. «SMTV was blocked…» yonidagi **Open
   Anyway** ni bosing, Mac parolingizni kiriting va **Open** ni bosing.
   macOS 14’da qisqaroq yoʻl bor: Applications’dagi **SMTV** ustida oʻng tugmani bosing → **Open** → **Open**.

Bu faqat birinchi marta kerak: keyin SMTV Applications yoki Launchpad’dan oddiy bosish bilan ochiladi. Xuddi shu
qadamlar `.dmg` ichidagi «How to open» faylida ham bor.

## Birinchi ishga tushirish

SMTV kompyuteringizni tekshiradi va birinchi klipgacha uchta qadamni koʻrsatadi. Ularning ostida u **sizning tilingiz
uchun nutqni tanishni** taklif qiladi — strimdagi nutqni matnga aylantiradigan qism. U yuklab olinadigan fayl ichida
yoʻq, chunki har bir tilga oʻziniki kerak (0,9–2,5 GB). **Fix** (Tuzatish) ni bosing va jarayonni kuzating yoki
oʻtkazib yuboring: birinchi soʻrov uni oʻzi yuklab oladi.

**Nima kerak:** kamida 5 GB boʻsh joy, 6 soatlik strim uchun 20 GB; internet. Videokarta kerak emas.

## Tajribalilar uchun: terminalda bitta qator

Xuddi oʻsha SMTV, faqat [uv](https://astral.sh/uv) — Python dasturlari uchun kichik rasmiy vosita — yordamida
foydalanuvchi papkangizga oʻrnatiladi. Undan **Linux**’da, **Smart App Control** bilan yoki terminal sizga qulayroq
boʻlsa foydalaning. U yuklab olingan ilova kabi oynadan yangilanadi.

**Windows:** **Start** ni bosing, `PowerShell` deb yozing, **Windows PowerShell**ni (koʻk oynani) oching, bu qatorni
qoʻying (oʻng tugma yoki Ctrl+V) va **Enter**ni bosing:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Smart App Control yoqilgan boʻlsa, oʻrnatuvchi SMTV’ni python.org’dagi imzolangan Python ustiga oʻrnatadi (uni
oʻrnatishni soʻrashi mumkin — rozi boʻling) va SMTV’ni u orqali ishga tushiradi. Agar terminal `smtv` ni ishga tushira
olmasligini aytsa, oʻrniga **SMTV** belgisidan foydalaning.

**Mac yoki Linux:** **Terminal**ni oching (Mac’da: Cmd+Space, `Terminal` deb yozing, Enter), bu qatorni qoʻying va
**Enter**ni bosing:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Tugaganini aytguncha kuting (2–10 daqiqa). SMTV oʻzi ochiladi; **SMTV** belgisi Windows’da Start menyusida, Mac’da
Applications’da, Linux’da dasturlar menyusida boʻladi. Bu yoʻlda SMTV birinchi marta **ffmpeg** ni (video vositasi)
**Fix** tugmasi bilan oʻrnatishni taklif qiladi; yuqoridagi yuklab olinadigan faylda u allaqachon ichida.

Ikkala oʻrnatuvchi ham qisqa va ochiq: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Tizim ogohlantirsa

- **Windows: «Windows protected your PC»** (SmartScreen). **More info**, keyin **Run anyway** ni bosing.
- **Windows 11: Smart App Control SMTV’ni bloklaydi.** SMTV imzolanmaguncha
  [terminalda bitta qator](#tajribalilar-uchun-terminalda-bitta-qator) usulidan foydalaning.
- **Windows: firewall soʻraydi**, SMTV tarmoqdan foydalanishi mumkinmi. **Private** (xususiy) tarmoqlar uchun ruxsat
  bering: SMTV telefoningizda ochilishi uchun bu kerak. Telefon kerak boʻlmasa, rad etsangiz ham boʻladi.
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» yoki «developer cannot be verified». **System
  Settings → Privacy & Security** ni oching, pastga aylantiring va SMTV yonidagi **Open Anyway** ni bosing.
- **Mac: «SMTV would like to accept incoming connections»** — SMTV’dan telefonda foydalanmoqchi boʻlsangiz, ruxsat
  bering.
- **Antivirus** shikoyat qilyaptimi? SMTV yangi va hali imzolanmagan, shuning uchun baʼzi antiviruslar unga ehtiyotkor
  munosabatda boʻladi. Uning kodi ochiq, har bir faylning nazorat yigʻindilari esa [reliz sahifasida](https://github.com/streammomenttv/smtv/releases/latest)
  (`SHA256SUMS.txt`).

Keyingisi: [birinchi klipingiz](first-clip.md).
