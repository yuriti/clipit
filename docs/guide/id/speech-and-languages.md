<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · **Bahasa Indonesia** · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Versi asli: Русский](../speech-and-languages.md).

# Ucapan dan bahasa

Pertama, SMTV mengubah ucapan di stream menjadi teks, lengkap dengan waktu setiap kata — dengan begitu AI memahami apa
yang terjadi. Ini berjalan **di komputermu, gratis**. SMTV mengenali bahasa stream dengan sendirinya.

| Bahasa | Model | Unduhan (sekali) | Kecepatan di prosesor 12 inti |
|---|---|---|---|
| Bahasa Rusia | GigaAM-v3, dibuat untuk bahasa Rusia | 0.9 GB | 54× lebih cepat dari waktu nyata |
| 25 bahasa Eropa: Inggris, Spanyol, Jerman, Prancis, Italia, Portugis, Polandia, Ukraina, dan lainnya | Parakeet-TDT v3 | 2.4 GB | 33× lebih cepat dari waktu nyata |
| Semua bahasa lain: Mandarin, Jepang, Korea, Hindi, Bengali, Kazakh, Uzbek, Azerbaijan, Vietnam, Indonesia, dan puluhan lainnya | Whisper large-v3-turbo | 1.6 GB | Belum diukur |

Model terunduh sendiri saat pertama kali ada stream dalam bahasanya. Kartu grafis tidak diperlukan; kartu NVIDIA
membuatnya lebih cepat. Di Mac, Whisper berjalan di prosesor dan lebih lambat.

**Settings → Speech to text** (Pengaturan → Ucapan menjadi teks) menampilkan setiap model: di mana model berjalan,
bahasanya, ukuran, dan kecepatannya, dengan tombol **Download** (Unduh) dan **Remove** (Hapus). Di sana setiap bahasa bisa
memakai model lain, termasuk **Whisper in the cloud** (Whisper di cloud) dengan key milikmu sendiri (Groq atau OpenAI)
— lebih cepat di komputer yang lemah, tapi suaranya jadi keluar dari komputermu.

<img src="../../images/speech.png" alt="Settings → Speech to text: model-model dan bahasa yang ditanganinya" width="820">

**Bahasa jendela** adalah hal terpisah: SMTV memakai bahasa komputermu; **Settings → Language and theme** (Pengaturan →
Bahasa dan tema) untuk memilih bahasa lain. Bahasamu belum ada atau baru setengah diterjemahkan?
[Bantu terjemahkan](../../translations.md) — tidak perlu bisa pemrograman.
