<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · **Azərbaycanca** · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 Bu səhifə avtomatik tərcümə olunub. Onu yaxşılaşdırmağa kömək edin: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Orijinal: Русский](../get-a-key.md).

# Açarı haradan almaq olar

**Açar** («API açarı») SMTV-yə sizin adınızdan Sİ xidmətindən istifadə etməyə imkan verən uzun paroldur. Onu
qeydiyyatdan keçdikdən sonra xidmətin saytında alırsınız. SMTV onu yalnız kompüterinizdə saxlayır və yalnız həmin
xidmətə göndərir; o heç vaxt loglarda və ya problem hesabatlarında görünmür.

> Qiymətlər və pulsuz planlar dəyişir. Burada yazılanlar xidmətlərin öz səhifələrində **23.11.2026** tarixində yoxlanılıb — başlamazdan əvvəl xidmətin səhifəsini yoxlayın.

## Hansı xidmət

| Xidmət | Pulsuz plan | Açarı haradan almaq olar | Bilməyə dəyər |
|---|---|---|---|
| **Google Gemini** | Bəli, dəqiqəlik və gündəlik limitlərlə; pulsuz modellər Google-un qiymət səhifəsində sadalanıb | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Ən asan pulsuz başlanğıc; ödəniş yalnız pullu plan üçün qoşulur. Pulsuz planda Google göndərdiklərinizi öz məhsullarını yaxşılaşdırmaq üçün istifadə edə bilər və insanlar onu oxuya bilər — Avropa İqtisadi Bölgəsi, İsveçrə və Birləşmiş Krallıq istisna olmaqla. Hər ölkədə əlçatan deyil (məsələn, Rusiyada yoxdur): Google-un regionlar siyahısına baxın. |
| **Groq** | Bəli, limitlərlə, onlar konsolda göstərilir | [console.groq.com/keys](https://console.groq.com/keys) | Çox sürətlidir. Buludda nitqi mətnə də ucuz çevirə bilir (Whisper large-v3 turbo ilə bir saatlıq səs üçün təxminən $0.04). |
| **OpenRouter** | Adı `:free` ilə bitən modellər: dəqiqədə 20 sorğu, gündə 50 (siz $10 kredit aldıqdan sonra gündə 1,000) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Müxtəlif şirkətlərin yüzlərlə modeli üçün bir açar. Uzun yayım üçün gündə 50 sorğu azdır. |
| **Mistral** | Saytında dəqiqləşdirin: səhifələrində API üçün pulsuz şərtlər göstərilməyib | [console.mistral.ai](https://console.mistral.ai) | Avropa şirkəti. |
| **DeepSeek** | Xeyr | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Əvvəlcə artırdığınız balansdan ödənilir. |
| **OpenAI** | Pulsuz kredit vəd edilmir: yeni hesab əvvəlcədən ödəyir, $5-dan başlayaraq | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ChatGPT-nin arxasındakı modellər. ChatGPT abunəsi açarla eyni şey deyil: açar ayrıca ödənilir. Yalnız dəstəklənən ölkələrdə (Rusiyada yoxdur). |
| **Claude (Anthropic)** | Xeyr | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Claude abunəsi açarla eyni şey deyil. Yalnız dəstəklənən regionlarda (Rusiyada yoxdur). |

SMTV həmçinin xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras və istənilən OpenAI-uyğun ünvanı tanıyır —
[təcrübəli istifadəçilər üçün](../../advanced.md#ai-services-and-keys) bölməsinə baxın.

**Pulsuz planın limitləri var.** Uzun yayım çoxlu sorğu göndərir; limit dolanda xidmət «too many requests» (həddindən
çox sorğu) cavabı verir və SMTV gözləyir və ya dayanır. 6–12 saatlıq yayım üçün ödənişli plan və ya [hesab](account.md)
daha yaxşı işləyir.

## Nümunə: pulsuz Gemini açarı, addım-addım

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) açın və Google hesabı ilə daxil olun.
2. Soruşulsa, şərtləri qəbul edin.
3. **Create API key** basın. Açarı kopyalayın (`AIza…` ilə başlayır). Onu parol kimi gizli saxlayın.
4. SMTV-də: **Settings → AI → Your own key → Add a key** (Ayarlar → Sİ → Öz açarınız → Açar əlavə et).
5. **Gemini** seçin, açarı yapışdırın, **Check** (Yoxla) basın. SMTV açarın işləyib-işləmədiyini deyəcək.
6. Hazırdır. İndi Sİ-nin hər addımı uyğun modellə Gemini-dən istifadə edir; hansı olduğunu **Settings → AI steps**
   (Ayarlar → Sİ addımları) göstərir.

Digər xidmətlər də eyni cür işləyir: qeydiyyatdan keçin, **API keys** bölməsini tapın, açar yaradın, SMTV-yə
yapışdırın, **Check** basın. Ödənişli xidmətlər əvvəlcə kart əlavə etməyi və ya balansı artırmağı istəyir.

## Açarınız təhlükəsizdir

- Kompüterinizdə, şifrələnmiş şəkildə saxlanılır.
- Yalnız aid olduğu xidmətə göndərilir. StreamMoment onu heç vaxt görmür.
- İtirdiniz və ya sızdı? Onu xidmətin saytında silin və yenisini yaradın.
