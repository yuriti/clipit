<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · **Қазақша** · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Бұл бет автоматты түрде аударылған. Оны жақсартуға көмектесіңіз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Жаңарту және жою

## Жаңарту

SMTV күніне бір рет жаңа нұсқаның бар-жоғын тексереді (мұны өшіруге болады). Жаңа нұсқа болса, **Version … is
available** (… нұсқасы қолжетімді) деп жазады: **Update** (Жаңарту) басыңыз.

- SMTV жабылады, жаңарады және өзі қайта ашылады, әдетте бір минут ішінде.
- Сұрау орындалып жатса, жаңарту ол аяқталғанша күтеді — немесе **Stop the jobs and update** (Тапсырмаларды тоқтатып,
  жаңарту) басыңыз; кейін **Continue** оларды сол қадамнан жалғастырады.
- Жаңа нұсқа іске қосылмаса, алдыңғысы өзі қайтып келеді.
- Жаңа нұсқаларға SMTV авторлары қол қояды; SMTV орнатпас бұрын қолтаңбаны тексереді.

Жаңартуларға қатысты бәрі **Settings → Computer check → Updates** (Баптаулар → Компьютерді тексеру → Жаңартулар)
бөлімінде.

SMTV-ді Windows немесе Mac үшін жүктеп алдыңыз ба? **Update** (Жаңарту) жаңа орнатқышты жүктеп алады, тексереді және
ашады: орнатуды сонда аяқтаңыз (Mac-та жаңа SMTV-ді Applications қалтасына сүйреп, **Replace** (Ауыстыру) басыңыз).
ZIP мұрағатынан алынған Windows көшірмесі өзі жаңармайды: жаңа ZIP-ті [шығарылым бетінен](https://github.com/streammomenttv/smtv/releases/latest) жүктеп алыңыз.

SMTV-ді басқа жолмен орнаттыңыз ба? Docker-де жаңа нұсқа — жаңа образ; [тәжірибелі пайдаланушыларға](../../advanced.md#docker) бетін қараңыз.

## Жою

**Settings → Computer check → Remove SMTV from this computer** (**Remove…** түймесі) бағдарламаны және SMTV белгішесін жояды. Клиптеріңіз қалады — оларды да жою үшін
**Also remove clips, jobs, settings and keys** (Клиптерді, тапсырмаларды, баптаулар мен кілттерді де жою) құсбелгісін
қойыңыз.

SMTV-ді Windows немесе Mac үшін жүктеп алдыңыз ба? Бағдарламаның өзін жүйеде әдеттегідей жойыңыз (жоғарыдағы түйме
құсбелгі қойсаңыз, тек клиптер мен баптауларды жояды):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall** (Параметрлер → Қолданбалар → Орнатылған
  қолданбалар → SMTV → Жою). ZIP мұрағатынан алынған көшірме: оның қалтасын жойыңыз.
- **Mac:** **SMTV**-ді **Applications** қалтасынан **Trash** (Себет) ішіне сүйреңіз.

Терминалда бір жолмен орнаттыңыз ба? Терезесіз, терминалда:

```bash
smtv uninstall
```

Клиптер мен баптауларды да жою үшін `--data` қосыңыз. Өзіңіз орнатқан бағдарламалар (Ollama, LM Studio) қалады:
оларды кез келген басқа бағдарлама сияқты жойыңыз.
