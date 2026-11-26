<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · **Azərbaycanca** · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Orijinal: Русский](../update-and-remove.md).

# Yeniləmə və silmə

## Yeniləmə

SMTV gündə bir dəfə yeni versiya yoxlayır (bunu söndürə bilərsiniz). Yeni versiya olanda **Version … is available**
(Versiya … mövcuddur) deyir: **Update** (Yenilə) basın.

- SMTV bağlanır, yenilənir və özü yenidən açılır, adətən bir dəqiqə ərzində.
- Sorğu işləyirsə, yeniləmə onun bitməsini gözləyir — və ya **Stop the jobs and update** (İşləri dayandır və yenilə)
  basın; **Continue** sonra onları eyni addımdan davam etdirir.
- Yeni versiya başlamasa, əvvəlki özü geri qayıdır.
- Yeni versiyalar SMTV müəllifləri tərəfindən imzalanır; SMTV quraşdırmadan əvvəl imzanı yoxlayır.

Yeniləmələr haqqında hər şey **Settings → Computer check → Updates** (Ayarlar → Kompüter yoxlaması → Yeniləmələr)
bölməsindədir.

SMTV-ni Windows və ya Mac üçün yükləmisiniz? **Update** (Yenilə) yeni quraşdırıcını yükləyir, yoxlayır və açır:
quraşdırmanı orada başa çatdırın (Mac-də yeni SMTV-ni Applications-a sürükləyin və **Replace** (Əvəz et) basın). ZIP
arxivindən olan Windows nüsxəsi özü yenilənmir: yeni ZIP-i [buraxılış səhifəsindən](https://github.com/yuriti/clipit/releases/latest) yükləyin.

SMTV-ni başqa yolla quraşdırmısınız? Docker-də yeni versiya yeni image deməkdir; [təcrübəli istifadəçilər üçün](../../advanced.md#docker) bölməsinə baxın.

## Silmə

**Settings → Computer check → Remove SMTV from this computer** (SMTV-ni bu kompüterdən sil; **Remove…** düyməsi)
proqramı və SMTV ikonunu silir. Klipləriniz qalır — onları da silmək üçün **Also remove clips, jobs, settings and
keys** (Klipləri, işləri, ayarları və açarları da sil) qutusunu işarələyin.

SMTV-ni Windows və ya Mac üçün yükləmisiniz? Proqramın özünü sistemdə adət olunduğu kimi silin (yuxarıdakı düymə,
işarələsəniz, yalnız klipləri və ayarları silir):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall** (Parametrlər → Tətbiqlər → Quraşdırılmış
  tətbiqlər → SMTV → Sil). ZIP arxivindən olan nüsxə: onun qovluğunu silin.
- **Mac:** **SMTV**-ni **Applications** qovluğundan **Trash** (Zibil qutusu) içinə sürükləyin.

Terminalda bir sətirlə quraşdırmısınız? Pəncərəsiz, terminalda:

```bash
smtv uninstall
```

Klipləri və ayarları da silmək üçün `--data` əlavə edin. Özünüz quraşdırdığınız proqramlar (Ollama, LM Studio) qalır:
onları hər hansı başqa proqram kimi silin.
