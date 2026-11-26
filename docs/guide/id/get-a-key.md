<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · **Bahasa Indonesia** · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Versi asli: Русский](../get-a-key.md).

# Tempat mendapatkan key

**Key** (sebuah «API key») adalah kata sandi panjang yang memungkinkan SMTV memakai layanan AI atas namamu. Kamu
mendapatkannya di situs layanan setelah mendaftar. SMTV hanya menyimpannya di komputermu dan hanya mengirimkannya ke
layanan itu; key tidak pernah muncul di log atau laporan masalah.

> Harga dan paket gratis bisa berubah. Yang tertulis di sini sudah dicocokkan dengan halaman resmi layanannya pada **23.11.2026** — cek halaman layanannya sebelum mulai.

## Layanan yang mana

| Layanan | Paket gratis | Tempat mendapatkan key | Perlu diketahui |
|---|---|---|---|
| **Google Gemini** | Ya, dengan batas per menit dan per hari; model gratisnya tercantum di halaman harga Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Awal gratis yang paling mudah; penagihan baru disiapkan hanya untuk paket berbayar. Di paket gratis, Google bisa memakai apa yang kamu kirim untuk meningkatkan produknya dan orang bisa membacanya — kecuali di Wilayah Ekonomi Eropa, Swiss, dan Inggris. Tidak tersedia di semua negara (misalnya tidak di Rusia): lihat daftar wilayah Google. |
| **Groq** | Ya, dengan batasan yang terlihat di konsolnya | [console.groq.com/keys](https://console.groq.com/keys) | Sangat cepat. Juga bisa mengubah ucapan menjadi teks di cloud, dengan murah (sekitar $0.04 per jam audio dengan Whisper large-v3 turbo). |
| **OpenRouter** | Model yang namanya berakhiran `:free`: 20 permintaan per menit, 50 per hari (1.000 per hari setelah kamu membeli kredit $10) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Satu key untuk ratusan model dari berbagai perusahaan. 50 permintaan per hari tidak cukup untuk stream yang panjang. |
| **Mistral** | Cek di situsnya: halamannya tidak menyebutkan ketentuan gratis untuk API | [console.mistral.ai](https://console.mistral.ai) | Perusahaan Eropa. |
| **DeepSeek** | Tidak | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Dibayar dari saldo yang diisi dulu. |
| **OpenAI** | Tidak ada kredit gratis yang dijanjikan: akun baru membayar di muka, mulai $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Model di balik ChatGPT. Langganan ChatGPT tidak sama dengan key: key dibayar terpisah. Hanya di negara yang didukung (tidak di Rusia). |
| **Claude (Anthropic)** | Tidak | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Langganan Claude tidak sama dengan key. Hanya di wilayah yang didukung (tidak di Rusia). |

SMTV juga mengenal xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras, dan alamat apa pun yang kompatibel dengan
OpenAI — lihat [untuk pengguna mahir](../../advanced.md#ai-services-and-keys).

**Paket gratis punya batas.** Stream panjang mengirim banyak permintaan; saat batas tercapai, layanan menjawab «too
many requests» (terlalu banyak permintaan) dan SMTV menunggu atau berhenti. Untuk stream 6–12 jam, paket berbayar atau
[akun](account.md) lebih cocok.

## Contoh: key Gemini gratis, langkah demi langkah

1. Buka [aistudio.google.com/apikey](https://aistudio.google.com/apikey) dan masuk dengan akun Google.
2. Setujui ketentuannya jika diminta.
3. Tekan **Create API key**. Salin key-nya (diawali dengan `AIza…`). Rahasiakan, seperti kata sandi.
4. Di SMTV: **Settings → AI → Your own key → Add a key** (Pengaturan → AI → Key milikmu sendiri → Tambah key).
5. Pilih **Gemini**, tempel key-nya, tekan **Check** (Periksa). SMTV memberi tahu apakah key-nya berfungsi.
6. Selesai. Setiap langkah AI sekarang memakai Gemini dengan model yang sesuai; **Settings → AI steps** (Pengaturan →
   Langkah AI) menunjukkan model yang mana.

Layanan lain bekerja dengan cara yang sama: daftar, cari **API keys**, buat satu, tempel ke SMTV, tekan **Check**.
Layanan berbayar akan meminta kamu menambahkan kartu atau mengisi saldo terlebih dahulu.

## Key-mu aman

- Disimpan di komputermu, terenkripsi.
- Hanya dikirim ke layanan pemiliknya. StreamMoment tidak pernah melihatnya.
- Hilang atau bocor? Hapus di situs layanannya dan buat yang baru.
