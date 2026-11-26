<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · **Oʻzbekcha** · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Asl nusxa: Русский](../troubleshooting.md).

# Nimadir notoʻgʻri ketdi

## 1. Computer check → Fix

**Settings → Computer check** (Sozlamalar → Kompyuter tekshiruvi) SMTV’ga kerak boʻlgan hamma narsani koʻrib chiqadi
va qatorma-qator nima joyida, nima joyida emasligini aytadi. Muammo yonida **Fix** (Tuzatish) tugmasi bor: SMTV
qoʻlidan kelganini oʻzi oʻrnatadi yoki tuzatadi va nima qilayotganini koʻrsatadi.

<img src="../../images/check.png" alt="Settings → Computer check: har bir qator holati va Fix tugmasi bilan" width="820">

| Qator nima deydi | Nima qilish kerak |
|---|---|
| **Video (ffmpeg)** yoʻq | **Fix** ni bosing: SMTV oʻzi foydalanadigan video vositasi ffmpeg’ni oʻrnatadi. |
| **Captions** (Subtitrlar) ishlamayapti | **Fix** ni bosing: SMTV subtitr chiza oladigan ffmpeg’ni oʻrnatadi. |
| **AI** (SI): hech narsa ulanmagan | **Settings → AI** da bittasini tanlang — [qaysi biri](connect-ai.md). |
| **Connection to StreamMoment** (StreamMoment bilan aloqa) ishlamayapti | Internetni tekshiring; VPN yoki firewall uni bloklashi mumkin. Fayllar usiz ham ishlaydi. |
| **Free space** (Boʻsh joy) kam | Diskda joy boʻshating: 6 soatlik strim qayta ishlanayotganda taxminan 20 GB talab qiladi. |
| **Speech to text** (Nutqdan matnga): model yuklanmagan | U birinchi soʻrovda oʻzi yuklanadi; yoki **Settings → Speech to text** da **Download** ni bosing. |

Administrator paroli kerak boʻlgan tuzatish hech qachon jimgina ishga tushirilmaydi: SMTV buyruq bilan terminal ochadi,
shunda nima qilayotganini koʻrasiz.

## 2. Koʻp uchraydigan muammolar

- **Havola ishlamayapti.** Havolalar uchun [StreamMoment akkaunti](account.md) kerak. Akkaunt yoʻqmi? Yozuvni oʻzingiz
  yuklab oling va SMTV’ga faylni bering.
- **Kliplar yoʻq yoki juda kam.** SMTV faqat SI yaxshi deb baholagan lahzalarni qoldiradi. Qisqa yoki sokin strim kam
  klip berishi mumkin. Kompyuteringizdagi bepul SI bulutdagiga qaraganda kamroq yaxshi lahza topadi.
- **«Too many requests»** (soʻrovlar juda koʻp). SI xizmatingizning bepul tarifi cheklovga yetdi: kuting yoki pullik
  tarif yoxud akkauntdan foydalaning.
- **Telefon SMTV’ni ochmayapti.** Bir xil Wi-Fi, VPN yoʻq, firewall’da SMTV’ga ruxsat bering — [telefon](phone.md)
  qoʻllanmasiga qarang.
- **Windows: terminal `smtv` ni rad etyapti.** Bu Smart App Control; SMTV’ni belgisidan ishga tushiring.
- **Oyna SMTV bilan aloqani yoʻqotdi.** Oynani yoping va SMTV’ni qaytadan oching.

Toʻxtagan soʻrov davom etishi mumkin: **Continue** (Davom etish) ni bosing — SMTV xuddi shu qadamdan davom etadi va
bajarilgan ishni qaytarmaydi.

## 3. Muammo haqida xabar bering

Baribir chiqmayaptimi? Bizga ayting — bu hammaga yordam beradi.

1. **Settings → Computer check → Report a problem** (Muammo haqida xabar berish; **Report…** tugmasi, u
   **Settings → About** da ham bor) yoki muvaffaqiyatsiz soʻrov ostidagi tugma.
2. SMTV hisobotga nima kirishini koʻrsatadi: versiyalar, kompyuter tekshiruvi, sozlamalar va loglar. **Kalitlar va
   tokenlar kesib tashlanadi**, uy papkangiz `~` boʻlib koʻrinadi. Havolalar va fayl nomlari, belgi qoʻymasangiz,
   kiritilmaydi.
3. **Save and open GitHub** (Saqlash va GitHub’ni ochish) ni bosing. SMTV arxivni saqlaydi va brauzerda qisqacha
   mazmuni toʻldirilgan yangi issue ochiladi. Arxivni unga sudrab tashlang va **Submit** ni bosing.

SMTV oʻzi hech narsa yubormaydi. Oynasiz: terminalda `smtv report` ni ishga tushiring. Shuningdek, toʻgʻridan-toʻgʻri
[issue ochishingiz](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) mumkin.
