<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · **Кыргызча** · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Бул барак автоматтык түрдө которулган. Аны жакшыртууга жардам бериңиз: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Жаңыртуу жана өчүрүү

## Жаңыртуу

SMTV күнүнө бир жолу жаңы версия бар-жогун текшерет (муну өчүрсөңүз болот). Жаңы версия болсо, **Version … is
available** (… версиясы жеткиликтүү) деп жазат: **Update** (Жаңыртуу) басыңыз.

- SMTV жабылат, жаңырат жана өзү кайра ачылат, адатта бир мүнөттүн ичинде.
- Суроо аткарылып жатса, жаңыртуу ал бүткөнчө күтөт — же **Stop the jobs and update** (Тапшырмаларды токтотуп,
  жаңыртуу) басыңыз; кийин **Continue** аларды ошол эле кадамдан улантат.
- Жаңы версия иштебей калса, мурункусу өзү кайтып келет.
- Жаңы версияларга SMTVнин авторлору кол коюшат; SMTV орнотуудан мурун колтамганы текшерет.

Жаңыртууларга тиешелүүнүн баары **Settings → Computer check → Updates** (Жөндөөлөр → Компьютерди текшерүү →
Жаңыртуулар) бөлүмүндө.

SMTVни Windows же Mac үчүн жүктөп алдыңызбы? **Update** (Жаңыртуу) жаңы орноткучту жүктөп алат, текшерет жана ачат:
орнотууну ошол жерде аяктаңыз (Mac'та жаңы SMTVни Applications'ка сүйрөп барып, **Replace** (Алмаштыруу) басыңыз).
ZIP архивинен алынган Windows көчүрмөсү өзү жаңырбайт: жаңы ZIP'ти [чыгаруу барагынан](https://github.com/streammomenttv/smtv/releases/latest) жүктөп алыңыз.

SMTVни башка жол менен орноттуңузбу? Docker'де жаңы версия — жаңы образ; [тажрыйбалуу колдонуучуларга](../../advanced.md#docker) барагын караңыз.

## Өчүрүү

**Settings → Computer check → Remove SMTV from this computer** (**Remove…** баскычы) программаны жана SMTV сөлөкөтүн өчүрөт. Клиптериңиз калат — аларды да өчүрүү үчүн
**Also remove clips, jobs, settings and keys** (Клиптерди, тапшырмаларды, жөндөөлөрдү жана ачкычтарды да өчүрүү)
белгисин коюңуз.

SMTVни Windows же Mac үчүн жүктөп алдыңызбы? Программанын өзүн системада адаттагыдай өчүрүңүз (жогорудагы баскыч,
белги коюлса, клиптерди жана жөндөөлөрдү гана өчүрөт):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall** (Параметрлер → Колдонмолор → Орнотулган
  колдонмолор → SMTV → Өчүрүү). ZIP архивинен алынган көчүрмө: анын папкасын өчүрүңүз.
- **Mac:** **SMTV**ни **Applications** папкасынан **Trash** (Себет) ичине сүйрөп барыңыз.

Терминалда бир сап менен орноттуңузбу? Терезесиз, терминалда:

```bash
smtv uninstall
```

Клиптерди жана жөндөөлөрдү да өчүрүү үчүн `--data` кошуңуз. Өзүңүз орноткон программалар (Ollama, LM Studio) калат:
аларды башка программалар сыяктуу эле өчүрүңүз.
