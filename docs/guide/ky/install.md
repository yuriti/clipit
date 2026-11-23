<!-- languages -->
[English](../install.md) · [Русский](../ru/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · **Кыргызча** · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Бул барак автоматтык түрдө которулган. Аны жакшыртууга жардам бериңиз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# SMTV орнотуу

Бир файлды жүктөп алып, ачыңыз — жана **SMTV** сөлөкөтү пайда болот. SMTVге керектин баары ичинде. Администратордун
сырсөзү керек эмес.

| Компьютериңиз | Жүктөп алуу | Көлөмү |
|---|---|---|
| **Windows 10 же 11** (64-биттик) | [Windows үчүн SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | болжол менен 130 МБ |
| **Mac** — Apple silicon (M1 жана жаңыраагы) же Intel, macOS 13+ | [Mac үчүн SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | болжол менен 270 МБ |

Бардык версиялар жана алардын текшерүү суммалары: [чыгаруу барагы](https://github.com/streammomenttv/smtv/releases/latest).

**Эмне үчүн система биринчи жолу эскертет.** SMTVде азырынча санариптик колтамга жок. Windows үчүн колтамга бир аз
кийинчерээк, macOS үчүн мүмкүн болушунча тезирээк пайда болот, ошондо бул эскертүү жоголот. SMTVнин коду ачык: анын
эмне кыларын ар ким окуп көрө алат.

## Windows

1. **Windows үчүн SMTV** жүктөп алып (`SMTV-…-windows-x64-setup.exe` файлы), аны ачыңыз.
2. Windows **«Windows protected your PC»** деген көк терезени көрсөтөт. **More info**, андан кийин **Run anyway**
   басыңыз.
3. Орноткуч бир-эки суроо берет (тил, иш столундагы сөлөкөт) — **Next** жана **Install** басыңыз.
4. Аягында **Launch SMTV** белгисин калтырып, **Finish** басыңыз. Кийинки жолу SMTVни **Start** (Баштоо) менюсунан
   (же иш столундагы сөлөкөттөн) иштетиңиз.

Орноткуч SMTVни өз колдонуучу папкаңызга коёт; ал **Settings → Apps** (Параметрлер → Колдонмолор) бөлүмүндө пайда
болот, аны ошол жерден өчүрсөңүз болот.

**Орнотпостон:** [ZIP архивин](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip) жүктөп алып, каалаган жерге (мисалы, Documents папкасына) архивден чыгарыңыз
жана `SMTV` папкасындагы **Start SMTV** ачыңыз. Бул көчүрмө өзү жаңырбайт: жаңы версия — жаңы ZIP.

### Windows 11: Smart App Control

**Smart App Control** күйүк болсо (Windows Security → App & browser control), Windows кол коюлбаган программаларды
толугу менен бөгөттөйт, аларды өткөрүүчү баскыч жок. SMTV үчүн Smart App Control'ду өчүрүүнүн кереги жок. Анын ордуна
SMTVни бир сап менен орнотуңуз — ал Smart App Control күйүк болсо да иштейт: [терминалда бир сап](#тажрыйбалуулар-үчүн-терминалда-бир-сап). SMTVге
кол коюлганда, жүктөлүп алынган файл да ал жерде иштеп калат.

## Mac

1. **Mac үчүн SMTV** жүктөп алыңыз. Бул Apple silicon же Intel негизиндеги ар кандай Mac үчүн бир файл: SMTV Mac'ыңыздын процессоруна жасалган версияны өзү ишке киргизет.
2. Жүктөлүп алынган `.dmg` файлын ачыңыз. SMTV жана **Applications** (Программалар) папкасы бар терезе ачылат:
   **SMTV**ни **Applications** үстүнө сүйрөп барыңыз.
3. **Applications** ачып, **SMTV**ни эки жолу басыңыз. macOS SMTVни текшере албай турганын айтат жана аны ачпайт.
   **Done** басыңыз.
4. **System Settings → Privacy & Security** ачып, ылдый жылдырыңыз. «SMTV was blocked…» сабынын жанындагы **Open
   Anyway** басыңыз, Mac сырсөзүңүздү киргизип, **Open** басыңыз.
   macOS 14тө кыскараак жол бар: Applications ичиндеги **SMTV**ни чычкандын оң баскычы менен басыңыз → **Open** →
   **Open**.

Бул биринчи жолу гана керек: андан кийин SMTV Applications же Launchpad'дан кадимки басуу менен ачылат. Дал ушул
кадамдар `.dmg` ичиндеги «How to open» файлында да бар.

## Биринчи иштетүү

SMTV компьютериңизди текшерип, биринчи клипке чейинки үч кадамды көрсөтөт. Алардын астында **сиздин тилиңиз үчүн
кепти таанууну** сунуштайт — стримдеги кепти текстке айландыруучу бөлүк. Ал жүктөлүүчү файлдын ичинде жок, анткени ар
бир тилге өзүнүкү керек (0,9–2,5 ГБ). **Fix** (Оңдоо) басып, жүрүшүн карап туруңуз же өткөрүп жибериңиз: биринчи
суроо аны өзү жүктөп алат.

**Эмне керек:** кеминде 5 ГБ бош орун, 6 сааттык стрим үчүн 20 ГБ; интернет. Видеокарта керек эмес.

## Тажрыйбалуулар үчүн: терминалда бир сап

Ошол эле SMTV, болгону [uv](https://astral.sh/uv) аркылуу — Python программалары үчүн кичинекей расмий курал —
колдонуучу папкаңызга орнотулат. Аны **Linux**'та, **Smart App Control** менен же терминал сизге ыңгайлуураак болсо
колдонуңуз. Ал жүктөлүп алынган колдонмо сыяктуу эле терезеден жаңырат.

**Windows:** **Start** (Баштоо) басып, `PowerShell` деп терип, **Windows PowerShell** (көк терезе) ачыңыз, бул сапты
коюп (чычкандын оң баскычы же Ctrl+V), **Enter** басыңыз:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Smart App Control күйүк болсо, орноткуч SMTVни python.org сайтындагы кол коюлган Python'го орнотот (аны орнотууну
сурашы мүмкүн — макул болуңуз) жана SMTVни ал аркылуу иштетет. Эгер терминал `smtv` иштетилбей турганын жазса, анын
ордуна **SMTV** сөлөкөтүн колдонуңуз.

**Mac же Linux:** **Terminal** ачыңыз (Mac'та: Cmd+Space, `Terminal` деп терип, Enter), бул сапты коюп, **Enter**
басыңыз:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Даяр болгонун айтканга чейин күтүңүз (2–10 мүнөт). SMTV өзү ачылат; **SMTV** сөлөкөтү Windows'то Start менюсунда,
Mac'та Applications папкасында, Linux'та колдонмолор менюсунда болот. Бул жол менен SMTV биринчи жолу **ffmpeg**
(видео менен иштеген курал) орнотууну **Fix** баскычы менен сунуштайт; жогорудагы жүктөлүүчү файлда ал ичинде бар.

Эки орноткуч тең кыска жана ачык: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Система эскертсе

- **Windows: «Windows protected your PC»** (SmartScreen). **More info**, андан кийин **Run anyway** басыңыз.
- **Windows 11: Smart App Control SMTVни бөгөттөйт.** SMTVге кол коюлганга чейин
  [терминалда бир сапты](#тажрыйбалуулар-үчүн-терминалда-бир-сап) колдонуңуз.
- **Windows: брандмауэр** SMTVге тармакты колдонууга уруксат берүү керекпи деп сурайт. **Жеке** (private) тармактар
  үчүн уруксат бериңиз: SMTVни телефондо ачуу үчүн бул керек. Телефон керек болбосо, баш тартсаңыз болот.
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» же «developer cannot be verified». **System Settings →
  Privacy & Security** ачып, ылдый жылдырып, SMTVнин жанындагы **Open Anyway** басыңыз.
- **Mac: «SMTV would like to accept incoming connections»** — SMTVни телефондо колдонгуңуз келсе, уруксат бериңиз.
- **Антивирус** нааразы болуп жатабы? SMTV жаңы жана азырынча кол коюлган эмес, ошондуктан айрым антивирустар ага
  сак мамиле кылат. Анын коду ачык, ал эми ар бир файлдын текшерүү суммалары [чыгаруу барагында](https://github.com/streammomenttv/smtv/releases/latest) турат
  (`SHA256SUMS.txt`).

Кийинкиси: [биринчи клибиңиз](first-clip.md).
