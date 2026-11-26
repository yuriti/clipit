<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · **Қазақша** · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Бұл бет автоматты түрде аударылған. Оны жақсартуға көмектесіңіз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Түпнұсқа: Русский](../speech-and-languages.md).

# Сөз және тілдер

Алдымен SMTV стримдегі сөзді әр сөздің уақытымен бірге мәтінге айналдырады — ЖИ не болғанын осылай түсінеді. Бұл
**компьютеріңізде, тегін** жұмыс істейді. SMTV стримнің тілін өзі анықтайды.

| Тіл | Модель | Жүктеу (бір рет) | 12 ядролы процессордағы жылдамдық |
|---|---|---|---|
| Орыс тілі | GigaAM-v3, орыс тіліне арналған | 0,9 ГБ | Нақты уақыттан 54 есе жылдам |
| 25 еуропа тілі: ағылшын, испан, неміс, француз, итальян, португал, поляк, украин және басқалар | Parakeet-TDT v3 | 2,4 ГБ | Нақты уақыттан 33 есе жылдам |
| Қалған барлық тілдер: қытай, жапон, корей, хинди, бенгал, қазақ, өзбек, әзербайжан, вьетнам, индонезия және тағы ондаған тіл | Whisper large-v3-turbo | 1,6 ГБ | Әлі өлшенбеген |

Модель өз тіліндегі стрим алғаш келгенде өзі жүктеледі. Бейнекарта керек емес; NVIDIA бейнекартасымен тезірек.
Mac-та Whisper процессорда жұмыс істейді және баяуырақ.

**Settings → Speech to text** (Баптаулар → Сөзді мәтінге айналдыру) барлық модельді көрсетеді: қайда жұмыс істейді,
қай тілдер, өлшемі мен жылдамдығы, **Download** (Жүктеп алу) және **Remove** (Жою) түймелерімен. Сол жерде әр тілге
басқа модель беруге болады, соның ішінде өз кілтіңізбен (Groq немесе OpenAI) **Whisper in the cloud** (бұлттағы
Whisper) — әлсіз компьютерде тезірек, бірақ онда дыбыс компьютеріңізден шығады.

<img src="../../images/speech.png" alt="Settings → Speech to text: модельдер және олар қабылдайтын тілдер" width="820">

**Терезенің тілі** — бөлек баптау: SMTV компьютеріңіздің тілінде сөйлейді; басқасын **Settings → Language and theme**
(Баптаулар → Тіл және тақырып) бөлімінде таңдауға болады. Тіліңіз жоқ па немесе жартылай аударылған ба?
[Аударуға көмектесіңіз](../../translations.md) — бағдарламалау керек емес.
