<!-- languages -->
[English](../install.md) · [Русский](../ru/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · **Azərbaycanca** · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# SMTV-ni quraşdırın

Bir faylı yükləyin, açın və **SMTV** ikonu görünəcək. SMTV-yə lazım olan hər şey içindədir. Administrator parolu
lazım deyil.

| Kompüteriniz | Yükləmə | Ölçü |
|---|---|---|
| **Windows 10 və ya 11** (64-bit) | [Windows üçün SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | təxminən 130 MB |
| **Mac** — Apple silicon (M1 və daha yeni) və ya Intel, macOS 13+ | [Mac üçün SMTV](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | təxminən 270 MB |

Bütün versiyalar və onların yoxlama cəmləri: [buraxılış səhifəsi](https://github.com/streammomenttv/smtv/releases/latest).

**Sistem ilk dəfə niyə xəbərdarlıq edir.** SMTV-nin hələ rəqəmsal imzası yoxdur. Windows üçün imza bir az sonra,
macOS üçün isə imkan olan kimi gələcək və onda bu xəbərdarlıq yox olacaq. SMTV-nin kodu açıqdır: onun nə etdiyini hər
kəs oxuya bilər.

## Windows

1. **Windows üçün SMTV**-ni (`SMTV-…-windows-x64-setup.exe` faylı) yükləyin və açın.
2. Windows **«Windows protected your PC»** yazılı göy pəncərə göstərir. **More info**, sonra **Run anyway** basın.
3. Quraşdırıcı bir-iki sual verir (dil, iş masasında ikon) — **Next** və **Install** basın.
4. Sonda **Launch SMTV** işarəsini saxlayın və **Finish** basın. Növbəti dəfə SMTV-ni **Start** menyusundan (və ya iş
   masasındakı ikondan) başladın.

Quraşdırıcı SMTV-ni öz istifadəçi qovluğunuza qoyur; o, **Settings → Apps** (Parametrlər → Tətbiqlər) bölməsində
görünür və onu oradan silə bilərsiniz.

**Quraşdırmadan:** [ZIP arxivini](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip) yükləyin, istənilən yerə (məsələn, Documents qovluğuna) arxivdən çıxarın və
`SMTV` qovluğundakı **Start SMTV**-ni açın. Bu nüsxə özü yenilənmir: yeni versiya yeni ZIP deməkdir.

### Windows 11: Smart App Control

**Smart App Control** aktivdirsə (Windows Security → App & browser control), Windows imzasız proqramları tamamilə
bloklayır və onları buraxmaq üçün düymə yoxdur. SMTV üçün Smart App Control-u söndürməyə ehtiyac yoxdur. Bunun
əvəzinə SMTV-ni bir sətirlə quraşdırın — o, Smart App Control aktiv olanda da işləyir:
[terminalda bir sətir](#təcrübəli-istifadəçilər-üçün-terminalda-bir-sətir). SMTV imzalandıqda yüklənən fayl da orada işləyəcək.

## Mac

1. **Mac üçün SMTV**-ni yükləyin. Bu, Apple silicon və ya Intel prosessorlu istənilən Mac üçün bir fayldır: SMTV Mac-inizin prosessoru üçün hazırlanmış versiyanı özü işə salır.
2. Yüklənmiş `.dmg` faylını açın. SMTV və **Applications** qovluğu olan pəncərə açılır: **SMTV**-ni **Applications**
   üzərinə sürükləyin.
3. **Applications**-ı açın və **SMTV**-yə iki dəfə klikləyin. macOS SMTV-ni yoxlaya bilmədiyini deyir və onu açmır.
   **Done** basın.
4. **System Settings → Privacy & Security** açın və aşağı sürüşdürün. «SMTV was blocked…» yanında **Open Anyway**
   basın, Mac parolunuzu daxil edin və **Open** basın.
   macOS 14-də daha qısa yol var: Applications-da **SMTV** üzərində sağ klik → **Open** → **Open**.

Bu yalnız ilk dəfə lazımdır: sonra SMTV Applications-dan və ya Launchpad-dən adi kliklə açılır. Eyni addımlar `.dmg`
içindəki «How to open» faylında da var.

## İlk başlanğıc

SMTV kompüterinizi yoxlayır və ilk klipə qədər üç addımı göstərir. Onların altında **diliniz üçün nitqin tanınmasını**
təklif edir — yayımdakı nitqi mətnə çevirən hissə. O, yüklənən faylın içində yoxdur, çünki hər dilə özününkü lazımdır
(0,9–2,5 GB). **Fix** (Düzəlt) basın və gedişatı izləyin və ya keçin: ilk sorğu onu özü yükləyəcək.

**Nə lazımdır:** ən azı 5 GB boş yer, 6 saatlıq yayım üçün 20 GB; internet. Videokart lazım deyil.

## Təcrübəli istifadəçilər üçün: terminalda bir sətir

Eyni SMTV, sadəcə [uv](https://astral.sh/uv) ilə — Python proqramları üçün kiçik rəsmi alət — istifadəçi qovluğunuza
quraşdırılır. Ondan **Linux**-da, **Smart App Control** ilə və ya terminal sizə daha rahatdırsa istifadə edin. O,
yüklənmiş proqram kimi pəncərədən yenilənir.

**Windows:** **Start** basın, `PowerShell` yazın, **Windows PowerShell**-i (göy pəncərəni) açın, bu sətri yapışdırın
(sağ klik və ya Ctrl+V) və **Enter** basın:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Smart App Control aktivdirsə, quraşdırıcı SMTV-ni python.org-dan imzalı Python üzərində quraşdırır (onu quraşdırmağı
soruşa bilər — razılaşın) və SMTV-ni onun vasitəsilə başladır. Terminal `smtv`-ni işə sala bilmədiyini desə, əvəzinə
**SMTV** ikonundan istifadə edin.

**Mac və ya Linux:** **Terminal**-ı açın (Mac-də: Cmd+Space, `Terminal` yazın, Enter), bu sətri yapışdırın və
**Enter** basın:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Bitdiyini deyənə qədər gözləyin (2–10 dəqiqə). SMTV özü açılır; **SMTV** ikonu Windows-da Start menyusunda, Mac-də
Applications qovluğunda, Linux-da proqramlar menyusunda olur. Bu yolla SMTV ilk dəfə **ffmpeg**-i (video aləti)
**Fix** düyməsi ilə quraşdırmağı təklif edir; yuxarıdakı yüklənən faylda o artıq içindədir.

Hər iki quraşdırıcı qısa və açıqdır: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Sistem xəbərdarlıq edərsə

- **Windows: «Windows protected your PC»** (SmartScreen). **More info**, sonra **Run anyway** basın.
- **Windows 11: Smart App Control SMTV-ni bloklayır.** SMTV imzalanana qədər
  [terminalda bir sətirdən](#təcrübəli-istifadəçilər-üçün-terminalda-bir-sətir) istifadə edin.
- **Windows: firewall soruşur** ki, SMTV şəbəkədən istifadə edə bilərmi. **Private** (şəxsi) şəbəkələr üçün icazə
  verin: SMTV-nin telefonunuzda açılması üçün bu lazımdır. Telefona ehtiyacınız yoxdursa, imtina etmək olar.
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» və ya «developer cannot be verified». **System
  Settings → Privacy & Security** açın, aşağı sürüşdürün və SMTV-nin yanında **Open Anyway** basın.
- **Mac: «SMTV would like to accept incoming connections»** — SMTV-ni telefonda istifadə etmək istəyirsinizsə, icazə
  verin.
- **Antivirus** şikayət edir? SMTV yenidir və hələ imzalanmayıb, ona görə bəzi antiviruslar ona ehtiyatla yanaşır.
  Onun kodu açıqdır, hər faylın yoxlama cəmləri isə [buraxılış səhifəsindədir](https://github.com/streammomenttv/smtv/releases/latest) (`SHA256SUMS.txt`).

Növbəti: [ilk klipiniz](first-clip.md).
