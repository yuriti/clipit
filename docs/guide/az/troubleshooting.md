<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · **Azərbaycanca** · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Orijinal: Русский](../troubleshooting.md).

# Nəsə alınmadı

## 1. Computer check → Fix

**Settings → Computer check** (Ayarlar → Kompüter yoxlaması) SMTV-yə lazım olan hər şeyə baxır və sətir-sətir nəyin
qaydasında olduğunu, nəyin olmadığını deyir. Problemin yanında **Fix** (Düzəlt) düyməsi var: SMTV bacardığını özü
quraşdırır və ya düzəldir və nə etdiyini göstərir.

<img src="../../images/check.png" alt="Settings → Computer check: hər sətir öz vəziyyəti və Fix düyməsi ilə" width="820">

| Sətir deyir | Nə etməli |
|---|---|
| **Video (ffmpeg)** yoxdur | **Fix** basın: SMTV istifadə etdiyi video aləti ffmpeg-i quraşdırır. |
| **Captions** (Altyazılar) işləmir | **Fix** basın: SMTV altyazı çəkə bilən ffmpeg quraşdırır. |
| **AI** (Sİ): heç nə qoşulmayıb | **Settings → AI**-da birini seçin — [hansını](connect-ai.md). |
| **Connection to StreamMoment** (StreamMoment ilə əlaqə) alınmır | İnterneti yoxlayın; VPN və ya firewall onu bloklaya bilər. Fayllar onsuz da işləyir. |
| **Free space** (Boş yer) azdır | Diskdə yer boşaldın: 6 saatlıq yayım emal olunarkən təxminən 20 GB tələb edir. |
| **Speech to text** (Nitqdən mətnə): model yüklənməyib | İlk sorğuda özü yüklənir; və ya **Settings → Speech to text**-də **Download** basın. |

Administrator parolu tələb edən düzəliş heç vaxt xəbərsiz işə salınmır: SMTV əmrlə terminal açır ki, nə etdiyini
görəsiniz.

## 2. Tez-tez rast gəlinən problemlər

- **Link işləmir.** Linklər üçün [StreamMoment hesabı](account.md) lazımdır. Hesab yoxdur? Yazını özünüz yükləyin və
  SMTV-yə fayl verin.
- **Klip yoxdur və ya çox azdır.** SMTV yalnız Sİ-nin yaxşı qiymətləndirdiyi anları saxlayır. Qısa və ya sakit yayım az
  klip verə bilər. Kompüterinizdəki pulsuz Sİ buluddakından daha az yaxşı an tapır.
- **«Too many requests»** (həddindən çox sorğu). Sİ xidmətinizin pulsuz planı limitə çatıb: gözləyin, ya da ödənişli
  plan və ya hesabdan istifadə edin.
- **Telefon SMTV-ni açmır.** Eyni Wi-Fi, VPN yoxdur, firewall-da SMTV-yə icazə verin — [telefon](phone.md) bölməsinə
  baxın.
- **Windows: terminal `smtv`-dən imtina edir.** Bu, Smart App Control-dur; SMTV-ni ikonundan başladın.
- **Pəncərə SMTV ilə əlaqəni itirdi.** Pəncərəni bağlayın və SMTV-ni yenidən açın.

Dayanmış sorğu davam edə bilər: **Continue** (Davam et) basın — SMTV eyni addımdan davam edir və görülmüş işi təkrar
etmir.

## 3. Problem barədə bildirin

Yenə də alınmır? Bizə deyin — bu hamıya kömək edir.

1. **Settings → Computer check → Report a problem** (Problem barədə bildir; **Report…** düyməsi, o həm də
   **Settings → About**-dadır), və ya uğursuz sorğunun altındakı düymə.
2. SMTV hesabata nəyin daxil olduğunu göstərir: versiyalar, kompüter yoxlaması, ayarlar və loglar. **Açarlar və
   tokenlər kəsilib çıxarılır**, ev qovluğunuz `~` kimi görünür. Linklər və fayl adları, qutunu işarələməsəniz, daxil
   edilmir.
3. **Save and open GitHub** (Saxla və GitHub-ı aç) basın. SMTV arxivi saxlayır və brauzerdə xülasəsi doldurulmuş yeni
   issue açılır. Arxivi ora sürükləyin və **Submit** basın.

SMTV özbaşına heç nə göndərmir. Pəncərəsiz: terminalda `smtv report` işə salın. Həmçinin birbaşa
[issue aça](https://github.com/yuriti/clipit/issues/new?template=bug.yml) bilərsiniz.
