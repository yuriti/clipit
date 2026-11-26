<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · **Қазақша** · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Бұл бет автоматты түрде аударылған. Оны жақсартуға көмектесіңіз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Түпнұсқа: Русский](../free-ai-on-your-computer.md).

# Компьютеріңіздегі тегін ЖИ

ЖИ тікелей компьютеріңізде, тегін жұмыс істей алады: ешнәрсе сыртқа шықпайды және төлейтін ештеңе жоқ. Сізге ЖИ
модельдерін іске қосатын бағдарлама — **Ollama** немесе **LM Studio** — және модель, мысалы **Qwen** керек. SMTV
бағдарламаны өзі табады.

**Шынын айтсақ:** үй компьютеріне сыятын модельдер бұлттық модельдерден әлсіздеу, сондықтан клиптер нашарлау шығады,
әрі ұсынылған модельдердің ешқайсысы SMTV-мен әлі тексерілмеген. Нәтиже көңіліңізден шықпаса,
[аккаунтты](account.md) немесе [кілтті](get-a-key.md) байқап көріңіз.

## 1. Компьютеріңізге қай модель сай келеді

Ең маңыздысы — бейнекартаңыздың **бейнежады** (Apple silicon негізіндегі Mac-та — бүкіл жад).

| Бейнежад | Модель | Жүктеу көлемі | Ескертпе |
|---|---|---|---|
| 8 ГБ-тан аз | — | — | Тым аз: аккаунтты немесе кілтті пайдаланыңыз |
| 8 ГБ | `qwen3:8b` | 5,2 ГБ | Жеткілікті жақсы жұмыс істейтіндердің ең жеңілі |
| 10–12 ГБ | `qwen3-vl:8b` немесе `gemma3:12b` | 6,1 / 8,1 ГБ | Бұлар бейненің кадрларына да қарайды |
| 16 ГБ және одан көп | `qwen3:14b` | 9,3 ГБ | Төртеуінің ең жақсысы |

7B-дан («7 миллиард») кіші модельдерді ұсынбаймыз: олар SMTV-ге керек жауаптарды бұзады.

**Бейнежадыңызды қалай білуге болады:**
- **Windows:** Ctrl+Shift+Esc басыңыз → **Performance** → **GPU** → **Dedicated GPU memory**.
- **Mac:** Apple мәзірі → **About This Mac** → **Memory**. Mac жадты ЖИ-мен бөліседі: 16 ГБ болса `qwen3:8b`, 32 ГБ
  немесе одан көп болса `qwen3:14b` алыңыз.

## 2a. Ollama (ең оңайы)

1. Ollama-ны [ollama.com/download](https://ollama.com/download) сайтынан жүктеп алып, кез келген бағдарлама сияқты
   орнатыңыз. Ол өзі іске қосылады және сағаттың қасында тұрады.
2. SMTV-де: **Settings → AI → Free, on this computer → Find on this computer** (Баптаулар → ЖИ → Тегін, осы
   компьютерде → Осы компьютерден табу). SMTV Ollama-ны табады.
3. Тізімде **Ollama**-ны ашыңыз: SMTV ұсынылған модельдерді өлшемімен көрсетеді. Жоғарыдағы кестедегі модельдің
   қасындағы **Download** (Жүктеп алу) түймесін басып, күтіңіз (5–10 ГБ).
4. Дайын. SMTV өз қадамдары үшін сол модельді өзі таңдайды.

SMTV бүкіл стрим мәтіні сыятындай етіп әр сұрауға Ollama жадын өзі баптайды; Ollama баптауларын өзгертудің қажеті жоқ.

## 2b. LM Studio

1. LM Studio-ны [lmstudio.ai/download](https://lmstudio.ai/download) сайтынан жүктеп алып, орнатыңыз.
2. LM Studio-да **Discover** ашып, **Qwen3 8B** (немесе кесте бойынша 14B) іздеп, **Download** басыңыз.
3. **Developer** қойындысын ашып, **Start server** қосыңыз (ол 1234 портын тыңдайды). Модельді сол жерде жүктеңіз.
4. SMTV-де: **Settings → AI → Free, on this computer → Find on this computer**. SMTV LM Studio-ны табады.

## 3. Клип жасаңыз

SMTV-ге [бейнефайл](first-clip.md) беріңіз. Twitch немесе YouTube сілтемесі үшін тегін ЖИ болса да
[аккаунт](account.md) керек: жазбаны аккаунт алып береді.

Тегін ЖИ бұлттықтан баяуырақ жұмыс істейді; ұзақ стрим бірнеше сағат алуы мүмкін. Компьютерді өшірмеңіз.
