<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · **Azərbaycanca** · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Orijinal: Русский](../free-ai-on-your-computer.md).

# Kompüterinizdə pulsuz Sİ

Süni intellekt (Sİ) birbaşa kompüterinizdə, pulsuz işləyə bilər: heç nə kənara çıxmır və ödəmək lazım deyil. Sİ
modellərini işlədən proqram — **Ollama** və ya **LM Studio** — və model, məsələn **Qwen** lazımdır. SMTV proqramı özü
tapır.

**Düzünü desək:** ev kompüterinə sığan modellər bulud modellərindən zəifdir, ona görə kliplər daha pis alınır, və
tövsiyə olunan modellərin heç biri hələ SMTV ilə test edilməyib. Nəticə sizi məyus etsə, [hesabı](account.md) və ya
[açarı](get-a-key.md) sınayın.

## 1. Kompüterinizə hansı model uyğundur

Əsas olan videokartınızın **video yaddaşıdır** (Apple silicon prosessorlu Mac-də: bütün yaddaş).

| Video yaddaş | Model | Yükləmə | Qeydlər |
|---|---|---|---|
| 8 GB-dan az | — | — | Çox azdır: hesabdan və ya açardan istifadə edin |
| 8 GB | `qwen3:8b` | 5,2 GB | Kifayət qədər yaxşı işləyən ən yüngül model |
| 10–12 GB | `qwen3-vl:8b` və ya `gemma3:12b` | 6,1 / 8,1 GB | Bunlar videonun kadrlarına da baxır |
| 16 GB və daha çox | `qwen3:14b` | 9,3 GB | Dördünün ən yaxşısı |

7B-dən («7 milyard») kiçik modellər tövsiyə olunmur: onlar SMTV-yə lazım olan cavabları pozur.

**Video yaddaşınızı necə öyrənmək olar:**
- **Windows:** Ctrl+Shift+Esc basın → **Performance** → **GPU** → **Dedicated GPU memory**.
- **Mac:** Apple menyusu → **About This Mac** → **Memory**. Mac yaddaşı Sİ ilə bölüşür: 16 GB-da `qwen3:8b`, 32 GB və
  daha çoxda `qwen3:14b` götürün.

## 2a. Ollama (ən sadə)

1. Ollama-nı [ollama.com/download](https://ollama.com/download) ünvanından yükləyin və hər hansı proqram kimi
   quraşdırın. O özü başlayır və saatın yanında yaşayır.
2. SMTV-də: **Settings → AI → Free, on this computer → Find on this computer** (Ayarlar → Sİ → Pulsuz, bu kompüterdə →
   Bu kompüterdə tap). SMTV Ollama-nı tapacaq.
3. Siyahıda **Ollama**-nı açın: SMTV tövsiyə olunan modelləri ölçüləri ilə göstərir. Yuxarıdakı cədvəldən uyğun
   olanın yanında **Download** (Yüklə) basın və gözləyin (5–10 GB).
4. Hazırdır. SMTV öz addımları üçün həmin modeli özü seçir.

SMTV hər sorğu üçün Ollama-nın yaddaşını elə qurur ki, yayımın bütün mətni sığsın; Ollama-nın ayarlarını dəyişmək
lazım deyil.

## 2b. LM Studio

1. LM Studio-nu [lmstudio.ai/download](https://lmstudio.ai/download) ünvanından yükləyin və quraşdırın.
2. LM Studio-da **Discover** açın, **Qwen3 8B** (və ya cədvələ görə 14B) axtarın və **Download** basın.
3. **Developer** tabını açın və **Start server** yandırın (o, 1234 portunu dinləyir). Modeli orada yükləyin.
4. SMTV-də: **Settings → AI → Free, on this computer → Find on this computer**. SMTV LM Studio-nu tapacaq.

## 3. Klip hazırlayın

SMTV-yə [video fayl](first-clip.md) verin. Twitch və ya YouTube linki üçün pulsuz Sİ ilə də [hesab](account.md)
lazımdır: yazını hesab alır.

Pulsuz Sİ buluddakından yavaş işləyir; uzun yayım bir neçə saat çəkə bilər. Kompüteri yanılı saxlayın.
