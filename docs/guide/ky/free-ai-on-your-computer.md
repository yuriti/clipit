<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · **Кыргызча** · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Бул барак автоматтык түрдө которулган. Аны жакшыртууга жардам бериңиз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Түп нуска: Русский](../free-ai-on-your-computer.md).

# Компьютериңиздеги акысыз ЖИ

ЖИ түздөн-түз компьютериңизде, акысыз иштей алат: эч нерсе сыртка чыкпайт жана төлөй турган эч нерсе жок. Сизге ЖИ
моделдерин иштеткен программа — **Ollama** же **LM Studio** — жана модель, мисалы **Qwen** керек. SMTV программаны
өзү табат.

**Чынын айтсак:** үй компьютерине батчу моделдер булут моделдеринен алсызыраак, ошондуктан клиптер начарыраак чыгат,
анын үстүнө сунушталган моделдердин бири да SMTV менен али текшериле элек. Натыйжа көңүлүңүздөн чыкпаса,
[аккаунтту](account.md) же [ачкычты](get-a-key.md) сынап көрүңүз.

## 1. Компьютериңизге кайсы модель туура келет

Эң негизгиси — видеокартаңыздын **видеоэси** (Apple silicon негизиндеги Mac'та — бүт эс).

| Видеоэс | Модель | Жүктөө көлөмү | Эскертүү |
|---|---|---|---|
| 8 ГБдан аз | — | — | Өтө аз: аккаунтту же ачкычты колдонуңуз |
| 8 ГБ | `qwen3:8b` | 5,2 ГБ | Жетиштүү жакшы иштегендердин эң жеңили |
| 10–12 ГБ | `qwen3-vl:8b` же `gemma3:12b` | 6,1 / 8,1 ГБ | Булар видеонун кадрларын да карайт |
| 16 ГБ жана андан көп | `qwen3:14b` | 9,3 ГБ | Төртөөнүн эң мыктысы |

7Bдан («7 миллиард») кичине моделдерди сунуштабайбыз: алар SMTVге керектүү жоопторду бузат.

**Видеоэсиңизди кантип билсе болот:**
- **Windows:** Ctrl+Shift+Esc басыңыз → **Performance** → **GPU** → **Dedicated GPU memory**.
- **Mac:** Apple менюсу → **About This Mac** → **Memory**. Mac эсти ЖИ менен бөлүшөт: 16 ГБ болсо `qwen3:8b`, 32 ГБ же
  андан көп болсо `qwen3:14b` алыңыз.

## 2a. Ollama (эң жөнөкөйү)

1. Ollama'ны [ollama.com/download](https://ollama.com/download) сайтынан жүктөп алып, башка программалар сыяктуу
   орнотуңуз. Ал өзү иштеп баштайт жана сааттын жанында турат.
2. SMTVде: **Settings → AI → Free, on this computer → Find on this computer** (Жөндөөлөр → ЖИ → Акысыз, бул
   компьютерде → Бул компьютерден табуу). SMTV Ollama'ны табат.
3. Тизмеден **Ollama**'ны ачыңыз: SMTV сунушталган моделдерди өлчөмү менен көрсөтөт. Жогорудагы таблицадагы моделдин
   жанындагы **Download** (Жүктөп алуу) баскычын басып, күтүңүз (5–10 ГБ).
4. Даяр. SMTV өз кадамдары үчүн ошол моделди өзү тандайт.

SMTV бүт стримдин тексти батышы үчүн ар бир суроого Ollama'нын эсин өзү жөндөйт; Ollama'нын жөндөөлөрүн өзгөртүүнүн
кереги жок.

## 2b. LM Studio

1. LM Studio'ну [lmstudio.ai/download](https://lmstudio.ai/download) сайтынан жүктөп алып, орнотуңуз.
2. LM Studio'до **Discover** ачып, **Qwen3 8B** (же таблица боюнча 14B) издеп, **Download** басыңыз.
3. **Developer** өтмөгүн ачып, **Start server** күйгүзүңүз (ал 1234 портун угат). Моделди ошол жерде жүктөңүз.
4. SMTVде: **Settings → AI → Free, on this computer → Find on this computer**. SMTV LM Studio'ну табат.

## 3. Клип жасаңыз

SMTVге [видеофайл](first-clip.md) бериңиз. Twitch же YouTube шилтемеси үчүн акысыз ЖИ болсо да [аккаунт](account.md)
керек: жазууну аккаунт алып берет.

Акысыз ЖИ булуттагыдан жайыраак иштейт; узун стрим бир нече саат алышы мүмкүн. Компьютерди өчүрбөңүз.
