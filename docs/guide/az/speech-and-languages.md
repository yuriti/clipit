<!-- languages -->
[English](../speech-and-languages.md) · [Русский](../ru/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · **Azərbaycanca** · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Nitq və dillər

Əvvəlcə SMTV yayımın nitqini hər sözün vaxtı ilə birlikdə mətnə çevirir — Sİ nə baş verdiyini belə başa düşür. Bu,
**kompüterinizdə, pulsuz** işləyir. SMTV yayımın dilini özü müəyyən edir.

| Dil | Model | Yükləmə (bir dəfə) | 12 nüvəli prosessorda sürət |
|---|---|---|---|
| Rus dili | GigaAM-v3, rus dili üçün hazırlanıb | 0,9 GB | Real vaxtdan 54 dəfə sürətli |
| 25 Avropa dili: ingilis, ispan, alman, fransız, italyan, portuqal, polyak, ukrayna və başqaları | Parakeet-TDT v3 | 2,4 GB | Real vaxtdan 33 dəfə sürətli |
| Bütün digər dillər: Çin, yapon, koreya, hind, benqal, qazax, özbək, Azərbaycan, vyetnam, indoneziya və onlarla başqası | Whisper large-v3-turbo | 1,6 GB | Hələ ölçülməyib |

Model onun dilində ilk yayım gələndə özü yüklənir. Videokart lazım deyil; NVIDIA kartı onu sürətləndirir. Mac-də
Whisper prosessorda işləyir və daha yavaşdır.

**Settings → Speech to text** (Ayarlar → Nitqdən mətnə) hər modeli göstərir: harada işlədiyini, dillərini, ölçüsünü və
sürətini, **Download** (Yüklə) və **Remove** (Sil) düymələri ilə. Orada hər dilə başqa model vermək olar, həmçinin öz
açarınızla (Groq və ya OpenAI) **Whisper in the cloud** (Buludda Whisper) — zəif kompüterdə daha sürətlidir, amma bu
zaman səs kompüterinizdən çıxır.

<img src="../../images/speech.png" alt="Settings → Speech to text: modellər və onların götürdüyü dillər" width="820">

**Pəncərənin dili** ayrıdır: SMTV kompüterinizin dilində danışır; **Settings → Language and theme** (Ayarlar → Dil və
mövzu) başqasını seçir. Diliniz yoxdur və ya yarımçıq tərcümə olunub? [Tərcüməyə kömək edin](../../translations.md) —
proqramlaşdırma lazım deyil.
