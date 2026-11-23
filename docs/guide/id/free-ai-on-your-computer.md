<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · **Bahasa Indonesia** · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# AI gratis di komputermu

AI bisa berjalan langsung di komputermu, gratis: tidak ada yang keluar, dan tidak ada yang perlu dibayar. Kamu butuh
program yang menjalankan model AI — **Ollama** atau **LM Studio** — dan sebuah model, misalnya **Qwen**. SMTV menemukan
program itu sendiri.

**Terus terang:** model yang muat di komputer rumahan lebih lemah daripada model cloud, jadi klipnya lebih jelek, dan
belum ada satu pun model yang direkomendasikan yang sudah diuji dengan SMTV. Kalau hasilnya mengecewakan, coba
[akun](account.md) atau [key](get-a-key.md).

## 1. Model mana yang cocok dengan komputermu

Yang penting adalah **memori video** kartu grafismu (di Mac dengan Apple silicon: seluruh memori).

| Memori video | Model | Ukuran unduhan | Catatan |
|---|---|---|---|
| kurang dari 8 GB | — | — | Terlalu sedikit: pakai akun atau key |
| 8 GB | `qwen3:8b` | 5.2 GB | Yang paling ringan namun cukup baik |
| 10–12 GB | `qwen3-vl:8b` atau `gemma3:12b` | 6.1 / 8.1 GB | Model ini juga melihat frame video |
| 16 GB atau lebih | `qwen3:14b` | 9.3 GB | Yang terbaik dari keempatnya |

Model yang lebih kecil dari 7B («7 miliar») tidak disarankan: model itu merusak jawaban yang dibutuhkan SMTV.

**Cara mengetahui memori videomu:**
- **Windows:** tekan Ctrl+Shift+Esc → **Kinerja** (Performance) → **GPU** → **Memori GPU khusus** (Dedicated GPU memory).
- **Mac:** menu Apple → **Tentang Mac Ini** (About This Mac) → **Memori** (Memory). Mac berbagi memori dengan AI: dengan
  16 GB pilih `qwen3:8b`, dengan 32 GB atau lebih pilih `qwen3:14b`.

## 2a. Ollama (paling mudah)

1. Unduh Ollama dari [ollama.com/download](https://ollama.com/download) dan instal seperti program lain. Ollama berjalan
   sendiri dan tinggal di dekat jam.
2. Di SMTV: **Settings → AI → Free, on this computer → Find on this computer** (Pengaturan → AI → Gratis, di komputer
   ini → Cari di komputer ini). SMTV menemukan Ollama.
3. Buka **Ollama** di daftar: SMTV menampilkan model yang direkomendasikan beserta ukurannya. Tekan **Download** (Unduh)
   di samping model dari tabel di atas dan tunggu (5–10 GB).
4. Selesai. SMTV memilih model itu untuk langkah-langkahnya dengan sendirinya.

SMTV mengatur memori Ollama untuk setiap permintaan agar seluruh teks stream muat; kamu tidak perlu mengubah pengaturan
Ollama.

## 2b. LM Studio

1. Unduh LM Studio dari [lmstudio.ai/download](https://lmstudio.ai/download) dan instal.
2. Di LM Studio buka **Discover**, cari **Qwen3 8B** (atau 14B, sesuai tabel) dan tekan **Download**.
3. Buka tab **Developer** dan nyalakan **Start server** (mendengarkan di port 1234). Muat modelnya di sana.
4. Di SMTV: **Settings → AI → Free, on this computer → Find on this computer**. SMTV menemukan LM Studio.

## 3. Buat klip

Berikan SMTV sebuah [file video](first-clip.md). Link ke Twitch atau YouTube tetap memerlukan [akun](account.md) meskipun
memakai AI gratis: akunlah yang mengambil rekamannya.

AI gratis bekerja lebih lambat daripada AI cloud; stream yang panjang bisa memakan waktu beberapa jam. Biarkan komputer
tetap menyala.
