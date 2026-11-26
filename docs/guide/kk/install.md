<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · **Қазақша** · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Бұл бет автоматты түрде аударылған. Оны жақсартуға көмектесіңіз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Түпнұсқа: Русский](../install.md).

# SMTV орнату

Бір файлды жүктеп алып, ашыңыз — **SMTV** белгішесі пайда болады. SMTV-ге керектің бәрі ішінде. Әкімші құпиясөзі
керек емес.

| Компьютеріңіз | Жүктеп алу | Көлемі |
|---|---|---|
| **Windows 10 немесе 11** (64-биттік) | [Windows-қа арналған SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | шамамен 130 МБ |
| **Mac** — Apple silicon (M1 және жаңарағы) немесе Intel, macOS 13+ | [Mac-қа арналған SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | шамамен 270 МБ |

Барлық нұсқалар мен олардың бақылау сомалары: [шығарылым беті](https://github.com/streammomenttv/smtv/releases/latest).

**Неліктен жүйе алғаш рет ескерту береді.** SMTV-де әзірге цифрлық қолтаңба жоқ. Windows-қа арналған қолтаңба сәл
кейінірек, macOS-қа арналғаны мүмкіндігінше тезірек пайда болады, сонда бұл ескерту жоғалады. SMTV коды ашық: оның не
істейтінін кез келген адам оқи алады.

## Windows

1. **Windows-қа арналған SMTV** жүктеп алыңыз (`SMTV-…-windows-x64-setup.exe` файлы) және оны ашыңыз.
2. Windows **«Windows protected your PC»** деген көк терезе көрсетеді. **More info**, содан кейін **Run anyway**
   басыңыз.
3. Орнатқыш бір-екі сұрақ қояды (тіл, жұмыс үстеліндегі белгіше) — **Next** және **Install** басыңыз.
4. Соңында **Launch SMTV** белгісін қалдырып, **Finish** басыңыз. Келесі жолы SMTV-ді **Start** (Бастау) мәзірінен
   (немесе жұмыс үстеліндегі белгішеден) іске қосыңыз.

Орнатқыш SMTV-ді өз пайдаланушы қалтаңызға қояды; ол **Settings → Apps** (Параметрлер → Қолданбалар) бөлімінде пайда
болады, сол жерден оны жоюға болады.

**Орнатпай:** [ZIP мұрағатын](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip) жүктеп алып, кез келген жерге (мысалы, Documents қалтасына) мұрағаттан
шығарыңыз да, `SMTV` қалтасындағы **Start SMTV** ашыңыз. Бұл көшірме өзі жаңармайды: жаңа нұсқа — жаңа ZIP.

### Windows 11: Smart App Control

**Smart App Control** қосулы болса (Windows Security → App & browser control), Windows қолтаңбасыз бағдарламаларды
толықтай бұғаттайды, оларды өткізетін түйме жоқ. SMTV үшін Smart App Control-ды өшірудің қажеті жоқ. Оның орнына
SMTV-ді бір жолмен орнатыңыз — ол Smart App Control қосулы болса да жұмыс істейді:
[терминалда бір жол](#тәжірибелі-пайдаланушыларға-терминалда-бір-жол). SMTV-ге қол қойылғанда, жүктеп алынған файл да онда жұмыс істейтін болады.

## Mac

1. **Mac-қа арналған SMTV** жүктеп алыңыз. Бұл Apple silicon немесе Intel негізіндегі кез келген Mac-қа арналған бір файл: SMTV Mac-ыңыздың процессорына арналған нұсқаны өзі іске қосады.
2. Жүктеп алынған `.dmg` файлын ашыңыз. SMTV және **Applications** (Бағдарламалар) қалтасы бар терезе ашылады:
   **SMTV**-ді **Applications** үстіне сүйреңіз.
3. **Applications** қалтасын ашып, **SMTV**-ді екі рет басыңыз. macOS SMTV-ді тексере алмайтынын айтады және оны
   ашпайды. **Done** басыңыз.
4. **System Settings → Privacy & Security** ашып, төмен айналдырыңыз. «SMTV was blocked…» жолының қасындағы **Open
   Anyway** басыңыз, Mac құпиясөзін енгізіп, **Open** басыңыз.
   macOS 14-те қысқарақ жол бар: Applications ішіндегі **SMTV**-ді тінтуірдің оң жақ түймесімен басыңыз → **Open** →
   **Open**.

Бұл тек алғашқы рет керек: одан кейін SMTV Applications немесе Launchpad ішінен кәдімгі басумен ашылады. Дәл осы
қадамдар `.dmg` ішіндегі «How to open» файлында да бар.

## Алғашқы іске қосу

SMTV компьютеріңізді тексеріп, алғашқы клипке дейінгі үш қадамды көрсетеді. Олардың астында **сіздің тіліңізге
арналған сөзді тануды** ұсынады — стримдегі сөзді мәтінге айналдыратын бөлік. Ол жүктеп алынатын файлдың ішінде жоқ,
өйткені әр тілге өзінікі керек (0,9–2,5 ГБ). **Fix** (Түзету) басып, барысын бақылаңыз немесе өткізіп жіберіңіз:
алғашқы сұрау оны өзі жүктеп алады.

**Не керек:** кемінде 5 ГБ бос орын, 6 сағаттық стрим үшін 20 ГБ; интернет. Бейнекарта керек емес.

## Тәжірибелі пайдаланушыларға: терминалда бір жол

Сол SMTV, тек [uv](https://astral.sh/uv) арқылы — Python бағдарламаларына арналған шағын ресми құрал — пайдаланушы
қалтаңызға орнатылады. Оны **Linux**-та, **Smart App Control** қосулы болғанда немесе терминал сізге ыңғайлырақ
болса пайдаланыңыз. Ол жүктеп алынған қолданба сияқты терезеден жаңарады.

**Windows:** **Start** (Бастау) басып, `PowerShell` деп теріңіз, **Windows PowerShell** (көк терезе) ашыңыз, мына
жолды қойыңыз (тінтуірдің оң жақ түймесі немесе Ctrl+V) және **Enter** басыңыз:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Smart App Control қосулы болса, орнатқыш SMTV-ді python.org сайтындағы қолтаңбалы Python-ға орнатады (оны орнатуды
сұрауы мүмкін — келісіңіз) және SMTV-ді сол арқылы іске қосады. Егер терминал `smtv` іске қосылмайтынын жазса, оның
орнына **SMTV** белгішесін пайдаланыңыз.

**Mac немесе Linux:** **Terminal** ашыңыз (Mac-та: Cmd+Space, `Terminal` деп теріп, Enter), мына жолды қойып,
**Enter** басыңыз:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Дайын болғанын айтқанша күтіңіз (2–10 минут). SMTV өзі ашылады; **SMTV** белгішесі Windows-та Start мәзірінде, Mac-та
Applications қалтасында, Linux-та қолданбалар мәзірінде болады. Бұл жолмен SMTV алғаш рет **ffmpeg** (бейнемен жұмыс
істейтін құрал) орнатуды **Fix** түймесімен ұсынады; жоғарыдағы жүктеп алынатын файлда ол ішінде бар.

Екі орнатқыш та қысқа әрі ашық: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Жүйе ескерту берсе

- **Windows: «Windows protected your PC»** (SmartScreen). **More info**, содан кейін **Run anyway** басыңыз.
- **Windows 11: Smart App Control SMTV-ді бұғаттайды.** SMTV-ге қол қойылғанша
  [терминалда бір жолды](#тәжірибелі-пайдаланушыларға-терминалда-бір-жол) пайдаланыңыз.
- **Windows: брандмауэр** SMTV-ге желіні пайдалануға рұқсат беру-бермеуді сұрайды. **Жеке** (private) желілер үшін
  рұқсат етіңіз: SMTV-ді телефонда ашу үшін бұл керек. Телефон керек болмаса, бас тартуға болады.
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» немесе «developer cannot be verified». **System
  Settings → Privacy & Security** ашып, төмен айналдырып, SMTV қасындағы **Open Anyway** басыңыз.
- **Mac: «SMTV would like to accept incoming connections»** — SMTV-ді телефонда пайдаланғыңыз келсе, рұқсат етіңіз.
- **Антивирус** шағымданады ма? SMTV жаңа әрі әлі қолтаңбасыз, сондықтан кейбір антивирустар оған сақтықпен
  қарайды. Оның коды ашық, ал әр файлдың бақылау сомалары [шығарылым бетінде](https://github.com/streammomenttv/smtv/releases/latest) тұр (`SHA256SUMS.txt`).

Келесі: [алғашқы клипіңіз](first-clip.md).
