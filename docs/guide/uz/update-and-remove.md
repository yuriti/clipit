<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · **Oʻzbekcha** · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Bu sahifa avtomatik tarjima qilingan. Uni yaxshilashga yordam bering: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Asl nusxa: Русский](../update-and-remove.md).

# Yangilash va oʻchirish

## Yangilash

SMTV kuniga bir marta yangi versiyani tekshiradi (buni oʻchirib qoʻyishingiz mumkin). Yangi versiya boʻlsa, u
**Version … is available** (… versiyasi mavjud) deydi: **Update** (Yangilash) ni bosing.

- SMTV yopiladi, yangilanadi va oʻzi qayta ochiladi, odatda bir daqiqa ichida.
- Soʻrov ishlayotgan boʻlsa, yangilanish u tugashini kutadi — yoki **Stop the jobs and update** (Ishlarni toʻxtatib
  yangilash) ni bosing; **Continue** keyin ularni xuddi shu qadamdan davom ettiradi.
- Yangi versiya ishga tushmasa, oldingisi oʻzi qaytadi.
- Yangi versiyalar SMTV mualliflari tomonidan imzolanadi; SMTV oʻrnatishdan oldin imzoni tekshiradi.

Yangilanishlar haqida hammasi **Settings → Computer check → Updates** (Sozlamalar → Kompyuter tekshiruvi →
Yangilanishlar) boʻlimida.

SMTV’ni Windows yoki Mac uchun yuklab olganmisiz? **Update** (Yangilash) yangi oʻrnatuvchini yuklab oladi, tekshiradi
va ochadi: oʻrnatishni oʻsha yerda yakunlang (Mac’da yangi SMTV’ni Applications’ga sudrab olib boring va **Replace**
(Almashtirish) ni bosing). ZIP arxivdan olingan Windows nusxasi oʻzi yangilanmaydi: yangi ZIP’ni
[reliz sahifasidan](https://github.com/streammomenttv/smtv/releases/latest) yuklab oling.

SMTV’ni boshqa usulda oʻrnatganmisiz? Docker’da yangi versiya — bu yangi image; [tajribali foydalanuvchilar uchun](../../advanced.md#docker) boʻlimiga qarang.

## Oʻchirish

**Settings → Computer check → Remove SMTV from this computer** (SMTV’ni bu kompyuterdan oʻchirish; **Remove…** tugmasi)
dasturni va SMTV belgisini oʻchiradi. Kliplaringiz qoladi — ularni ham oʻchirish uchun **Also remove clips, jobs,
settings and keys** (Kliplar, ishlar, sozlamalar va kalitlarni ham oʻchirish) ga belgi qoʻying.

SMTV’ni Windows yoki Mac uchun yuklab olganmisiz? Dasturning oʻzini tizimdagi odatiy usulda oʻchiring (yuqoridagi
tugma, belgi qoʻysangiz, faqat kliplar va sozlamalarni oʻchiradi):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall** (Sozlamalar → Ilovalar → Oʻrnatilgan ilovalar
  → SMTV → Oʻchirish). ZIP arxivdan olingan nusxa: uning papkasini oʻchiring.
- **Mac:** **SMTV** ni **Applications** papkasidan **Trash** (Savat) ga sudrab olib boring.

Terminalda bitta qator bilan oʻrnatganmisiz? Oynasiz, terminalda:

```bash
smtv uninstall
```

Kliplar va sozlamalarni ham oʻchirish uchun `--data` qoʻshing. Oʻzingiz oʻrnatgan dasturlar (Ollama, LM Studio)
qoladi: ularni boshqa har qanday dastur kabi oʻchiring.
