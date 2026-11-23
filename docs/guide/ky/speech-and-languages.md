<!-- languages -->
[English](../speech-and-languages.md) · [Русский](../ru/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · **Кыргызча** · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Бул барак автоматтык түрдө которулган. Аны жакшыртууга жардам бериңиз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Кеп жана тилдер

Адегенде SMTV стримдеги кепти ар бир сөздүн убактысы менен кошо текстке айландырат — ЖИ эмне болгонун ушундайча
түшүнөт. Бул **компьютериңизде, акысыз** иштейт. SMTV стримдин тилин өзү аныктайт.

| Тил | Модель | Жүктөө (бир жолу) | 12 ядролуу процессордогу ылдамдык |
|---|---|---|---|
| Орус тили | GigaAM-v3, орус тили үчүн жасалган | 0,9 ГБ | Чыныгы убакыттан 54 эсе ылдам |
| 25 европа тили: англис, испан, немис, француз, италия, португал, поляк, украин жана башкалар | Parakeet-TDT v3 | 2,4 ГБ | Чыныгы убакыттан 33 эсе ылдам |
| Калган бардык тилдер: кытай, жапон, корей, хинди, бенгал, казак, өзбек, азербайжан, вьетнам, индонезия жана дагы ондогон тилдер | Whisper large-v3-turbo | 1,6 ГБ | Азырынча өлчөнө элек |

Модель өз тилиндеги стрим биринчи жолу келгенде өзү жүктөлөт. Видеокарта керек эмес; NVIDIA видеокартасы менен
тезирээк. Mac'та Whisper процессордо иштейт жана жайыраак.

**Settings → Speech to text** (Жөндөөлөр → Кепти текстке айландыруу) бардык моделдерди көрсөтөт: кайда иштейт, кайсы
тилдер, өлчөмү жана ылдамдыгы, **Download** (Жүктөп алуу) жана **Remove** (Өчүрүү) баскычтары менен. Ошол жерде ар бир
тилге башка модель берсе болот, анын ичинде өз ачкычыңыз менен (Groq же OpenAI) **Whisper in the cloud** (булуттагы
Whisper) — алсыз компьютерде тезирээк, бирок анда үн компьютериңизден чыгат.

<img src="../../images/speech.png" alt="Settings → Speech to text: моделдер жана алар кабыл алган тилдер" width="820">

**Терезенин тили** — өзүнчө жөндөө: SMTV компьютериңиздин тилинде сүйлөйт; башкасын **Settings → Language and theme**
(Жөндөөлөр → Тил жана тема) бөлүмүндө тандаса болот. Тилиңиз жокпу же жарым-жартылай которулганбы?
[Которууга жардам бериңиз](../../translations.md) — программалоо керек эмес.
