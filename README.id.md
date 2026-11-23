<!-- Translations: README.<language>.md, the same structure. A change here changes README.ru.md in the same PR;
     the other languages follow (each says it was translated automatically and links Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**Ubah stream panjang menjadi klip pendek dan rangkuman. Gratis, di komputermu sendiri.**

<!-- languages -->
[English](README.md) · [Русский](README.ru.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · **Bahasa Indonesia** · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Deutsch](README.de.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

[![Rilis terbaru](https://img.shields.io/github/v/release/streammomenttv/smtv?label=release)](https://github.com/streammomenttv/smtv/releases/latest)
[![Unduhan](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![Bintang](https://img.shields.io/github/stars/streammomenttv/smtv?style=flat)](https://github.com/streammomenttv/smtv/stargazers)
[![Lisensi: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Terjemahkan di Weblate](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: rekaman stream masuk, SMTV menemukan momen terbaik dan membuat klip vertikal satu per satu" width="820">

[**Unduh SMTV**](#unduh) · [Panduan langkah demi langkah](docs/guide/id/README.md) · [Perbandingan](#perbandingan-smtv-dengan-yang-lain) · [Pertanyaan](#pertanyaan)

</div>

---

Kamu baru saja stream enam jam. Di dalamnya ada sepuluh momen yang layak diunggah — tapi untuk menemukannya kamu harus
menonton semuanya lagi. **SMTV menontonnya untukmu.** Tempel link rekaman Twitch atau YouTube, atau pilih file video,
lalu SMTV akan mendengarkan seluruh stream, memilih momen terbaik, dan memberimu **klip vertikal siap unggah** untuk
TikTok, Shorts, dan Reels, lengkap dengan teks dan webcam di bagian atas, plus **rangkuman 20–30 menit** dari seluruh
stream untuk YouTube.

## Apa yang dilakukan SMTV

| | |
|---|---|
| 🎬 **Klip siap unggah** | Vertikal 9:16, teks besar, kartu judul singkat di awal, dan webcam streamer di atas tampilan game. |
| ⏱️ **Stream panjang tidak masalah** | Masukkan rekaman 6–12 jam, keluar hingga 30 klip. Klip muncul satu per satu: mulai unggah sebelum sisanya selesai. |
| 📺 **Rangkuman seluruh stream** | Video 20–30 menit untuk YouTube: stream itu sendiri, dipangkas hanya ke bagian yang layak ditonton. |
| 🗣️ **Banyak bahasa** | Bahasa Rusia, 25 bahasa Eropa, dan puluhan lainnya. SMTV mengubah ucapan menjadi teks langsung di komputermu. |
| 🔒 **File-mu tetap bersamamu** | Klip dibuat dan disimpan di komputermu. Tidak ada yang diunggah ke situs web mana pun. |
| 💸 **Gratis dan terbuka** | Lisensi MIT: pakai, bagikan, pakai untuk klien. Tanpa watermark, tanpa batas menit. |

## Lihat cara kerjanya

**Tempel link atau pilih file — lalu lihat langkah-langkahnya.** Setiap langkah tampil di layar: ucapan menjadi teks,
mencari momen, menilainya, menyunting setiap klip.

<img src="docs/images/new-request.gif" alt="Permintaan baru: file video dipilih, SMTV mulai dan menampilkan setiap langkah" width="820">

**Klip muncul satu per satu.** Tonton langsung di SMTV, unduh, unggah.

<img src="docs/images/clips.png" alt="Klip-klip selesai dari sebuah stream dalam bentuk grid" width="820">

**Setiap klip dilengkapi teksnya.** Baca apa yang diucapkan dan mengapa SMTV memilih momen itu.

<img src="docs/images/viewer.png" alt="Klip yang diputar di samping transkripnya" width="820">

**Dan rangkuman seluruh stream** untuk YouTube, dibuat setelah klip-klipnya.

<img src="docs/images/recap.png" alt="Rangkuman stream di SMTV" width="820">

**Terang atau gelap** — mengikuti komputermu.

<img src="docs/images/dark.png" alt="SMTV dengan tema gelap" width="820">

<sub>Stream di gambar-gambar ini dibuat khusus untuk demo: sebuah game kecil, maskot kartun sebagai pengganti webcam,
dan suara komputer. Tidak ada orang sungguhan di layar.</sub>

## Gratis dan open source

- **SMTV gratis.** Seluruh program bersifat open source dengan [lisensi MIT](LICENSE): pakai untuk dirimu sendiri,
  untuk channel-mu, atau untuk klien, ubah dan bagikan.
- **Tanpa watermark, tanpa batas menit, tanpa langganan SMTV.**
- **Kamu hanya membayar AI-nya, dan itu pun hanya kalau kamu mau.** SMTV butuh AI untuk membaca teks stream dan memilih
  momen. Bisa AI gratis di komputermu sendiri, atau layanan pilihanmu — lihat di bawah.
- **Datamu tetap bersamamu.** Klip dibuat dan disimpan di komputermu. Hanya teks stream yang dikirim ke AI pilihanmu.
  Dengan AI gratis di komputermu, tidak ada yang keluar sama sekali.

## Pilih AI: tiga cara

SMTV mengubah ucapan menjadi teks di komputermu sendiri. Untuk memilih momen terbaik, SMTV bertanya pada AI. Pilih satu
cara — satu saja cukup, dan kamu bisa menggantinya kapan saja di **Settings → AI** (Pengaturan → AI).

| | Caranya | Biaya | Cocok untuk |
|---|---|---|---|
| ⭐ **Lewat akun** | Masuk ke akun StreamMoment (Google, Twitch, atau Telegram) dan isi saldo. Selesai: tanpa key, tanpa pengaturan. | Bayar sesuai pemakaian dari saldo | Semua orang: cara paling mudah. Juga diperlukan untuk menempel **link** rekaman. [Panduan](docs/guide/id/account.md) |
| 🔑 **Key milikmu sendiri** | Sudah memakai OpenAI, Claude, Gemini, atau OpenRouter? Tempel key-mu, dan SMTV langsung memakainya. | Kamu membayar layanan itu secara langsung; beberapa punya paket gratis | Orang yang sudah memakai layanan AI. [Tempat mendapatkan key](docs/guide/id/get-a-key.md) |
| 💻 **Gratis, di komputermu** | Instal Ollama atau LM Studio dan model Qwen; SMTV menemukannya sendiri. | Gratis | Komputer dengan kartu grafis yang kuat. Hasil klip lebih lemah. [Panduan](docs/guide/id/free-ai-on-your-computer.md) |

## Unduh

| Komputermu | Unduh | Ukuran |
|---|---|---|
| **Windows 10 atau 11** (64-bit) | [**SMTV untuk Windows**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) (penginstal) | sekitar 130 MB |
| **Mac** — Apple silicon (M1 dan yang lebih baru) atau Intel, macOS 13+ | [**SMTV untuk Mac**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | sekitar 270 MB |

Satu file untuk semua Mac: SMTV sendiri menjalankan versi yang dibuat untuk prosesor Mac-mu. Windows tanpa menginstal apa pun:
[file ZIP](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip) — ekstrak dan buka
**Start SMTV**.

Semua yang dibutuhkan SMTV sudah ada di dalamnya: programnya, Python, dan ffmpeg dengan teks (caption). Pengenalan ucapan
diunduh saat pertama kali dijalankan, hanya untuk bahasamu (0.9–2.5 GB, sekali saja): SMTV menawarkannya dengan satu
tombol, **Fix** (Perbaiki).

**Pada kali pertama, sistem memberi peringatan.** SMTV belum punya tanda tangan digital: tanda tangan untuk Windows
menyusul sedikit lebih lambat, untuk macOS secepat mungkin, dan setelah itu peringatan ini hilang. Sampai saat itu:

- **Windows** («Windows melindungi PC Anda»): **Info selengkapnya** (More info) → **Tetap jalankan** (Run anyway).
- **Mac**: buka SMTV sekali, lalu **Pengaturan Sistem → Privasi & Keamanan** (System Settings → Privacy & Security) →
  **Tetap Buka** (Open Anyway).
- **Windows 11 dengan Smart App Control** memblokir program tanpa tanda tangan sepenuhnya, dan tidak ada tombol untuk
  mengizinkannya. Pakai instalasi satu baris di bawah: cara itu berjalan walaupun Smart App Control menyala. Setelah
  SMTV bertanda tangan, file unduhan juga akan berjalan di sana.

[Setiap langkah dengan gambar](docs/guide/id/install.md).

### Untuk pengguna berpengalaman: satu baris di terminal

SMTV yang sama, diinstal dengan [uv](https://astral.sh/uv) ke folder penggunamu. Cara ini juga berjalan di **Linux** dan
dengan **Smart App Control**, dan diperbarui dari jendela dengan cara yang sama.

**Windows** — tekan Start, ketik **PowerShell**, buka, lalu tempel:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

**Mac atau Linux** — buka **Terminal** dan tempel:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Tekan Enter dan tunggu beberapa menit. Tidak perlu kata sandi administrator. Ikon **SMTV** akan muncul — di desktop dan
menu Start di Windows, di Applications di Mac, di menu aplikasi di Linux.

## Klip pertamamu dalam tiga langkah

1. **Pilih AI** — saat pertama kali, jendela menampilkan tiga cara ([yang mana?](docs/guide/id/connect-ai.md)).
2. **Tempel link** rekaman Twitch atau YouTube, atau pilih file video dari komputermu.
3. **Tunggu.** Klip muncul satu per satu: tonton, unduh, unggah.

Saat pertama kali, SMTV memeriksa komputermu dan menawarkan untuk memperbaiki yang kurang dengan satu tombol, **Fix**
(Perbaiki). [Klip pertama, langkah demi langkah](docs/guide/id/first-clip.md).

## Panduan langkah demi langkah

Untuk orang yang baru mengenal semua ini — setiap langkah, dengan gambar:

| | |
|---|---|
| [Instal di Windows, Mac, atau Linux](docs/guide/id/install.md) | dan apa yang harus dilakukan saat sistem memberi peringatan |
| [Klip pertamamu](docs/guide/id/first-clip.md) | dari link atau file sampai klip jadi |
| [AI mana yang dipilih](docs/guide/id/connect-ai.md) | tiga cara, berdampingan |
| [AI gratis di komputermu](docs/guide/id/free-ai-on-your-computer.md) | Ollama atau LM Studio dengan Qwen: model mana yang cocok dengan kartu grafismu |
| [Tempat mendapatkan key](docs/guide/id/get-a-key.md) | layanan mana yang punya paket gratis atau murah, langkah demi langkah |
| [Akun StreamMoment](docs/guide/id/account.md) | masuk, saldo |
| [SMTV di ponselmu](docs/guide/id/phone.md) | pindai kode QR dan tonton klip di ponsel |
| [Ucapan dan bahasa](docs/guide/id/speech-and-languages.md) | bahasa apa saja yang dipahami SMTV |
| [Perbarui dan hapus](docs/guide/id/update-and-remove.md) | |
| [Ada yang tidak beres](docs/guide/id/troubleshooting.md) | pemeriksaan komputer, **Fix**, **Report a problem** (Laporkan masalah) |

## Perbandingan SMTV dengan yang lain

Pemotong klip open source yang paling banyak dipakai, berdasarkan kode dan dokumentasi masing-masing proyek, **per
November 2026**. Semuanya proyek yang bagus, masing-masing dibuat untuk tugasnya sendiri; tabel ini hanya menunjukkan di
mana SMTV berbeda. Ada yang berubah? [Beri tahu kami](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml)
dan kami akan memperbaiki tabelnya.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| Lisensi | **MIT** | MIT (folder `cloud/` punya lisensi sendiri) | Lisensi sumber nonkomersial | MIT | MIT |
| Seluruh stream 6–12 jam | **Ya** | Bawaan 60 menit per tugas | Bawaan 90 menit | Tidak disebutkan batas durasi | Tidak dibuat untuk stream |
| Rangkuman panjang seluruh stream | **Ya, 20–30 menit** | Tidak | Tidak («recap»-nya berupa satu klip pendek) | Tidak | Tidak |
| Ucapan bahasa Rusia | **GigaAM-v3, dibuat untuk bahasa Rusia** | Whisper atau Parakeet v3 | AssemblyAI atau Whisper | Tidak (Parakeet v2, hanya bahasa Inggris) | Tidak (bahasa Mandarin dan Inggris) |
| Webcam streamer dalam bingkai vertikal | **Ya** | Tidak | Mode gaming, mati secara bawaan | Ya | Tidak ada klip vertikal |
| Ucapan menjadi teks secara bawaan | **Di komputermu, gratis** | Di komputermu | AssemblyAI, layanan berbayar | Di komputermu | Di komputermu |
| Cara menjalankannya | **Jendela dan ikon sendiri: unduhan untuk Windows dan Mac, atau satu baris** | Halaman web di Docker | Halaman web di Docker | Halaman web | Halaman web |

## Pertanyaan

<details>
<summary><b>Benar-benar gratis?</b></summary>

Ya. SMTV sendiri tidak memungut biaya apa pun dan tidak punya batasan. Satu-satunya biaya yang mungkin ada adalah AI yang
memilih momen: gratis di komputermu sendiri, atau dibayar ke layanan pilihanmu (lewat akun StreamMoment atau key
milikmu sendiri).
</details>

<details>
<summary><b>Apakah saya butuh komputer yang kuat?</b></summary>

Tidak perlu kartu grafis: SMTV berjalan di komputer biasa, hanya lebih lambat. Kartu NVIDIA membuat proses ucapan
menjadi teks lebih cepat. Pengecualiannya adalah AI gratis di komputermu sendiri — itu butuh kartu grafis yang kuat
([yang mana](docs/guide/id/free-ai-on-your-computer.md)). Ruang disk kosong: minimal 5 GB, 20 GB untuk stream 6 jam.
</details>

<details>
<summary><b>Berapa lama prosesnya?</b></summary>

Diukur di Mac dengan Apple silicon, tanpa kartu grafis: rekaman Twitch 2.35 jam butuh sekitar 6 menit untuk menemukan
momen, lalu sekitar 1 menit per klip; rangkuman 10.7 menit butuh 6.5 menit. Sebelum permintaan dimulai, SMTV
menunjukkan perkiraan lamanya.
</details>

<details>
<summary><b>Berjalan di sistem apa saja?</b></summary>

Windows 10 (versi 1809) atau lebih baru, 64-bit; macOS 13 atau lebih baru di Apple silicon dan Intel (di Apple silicon SMTV berjalan langsung mulai macOS 14; di macOS 13 SMTV menjalankan versi Intel-nya lewat Rosetta, lebih lambat); Linux (instalasi satu baris). Sudah dicek di Windows 11 dan di Mac dengan Apple silicon; Mac Intel (hanya
lewat Rosetta) dan desktop Linux belum diuji.
</details>

<details>
<summary><b>Bahasa apa saja yang dipahami?</b></summary>

Bahasa Rusia, 25 bahasa Eropa, dan puluhan lainnya. SMTV mengenali bahasa stream dengan sendirinya.
[Detail](docs/guide/id/speech-and-languages.md).
</details>

<details>
<summary><b>Bolehkah saya memakai klipnya untuk klien?</b></summary>

Boleh. Lisensi MIT mengizinkan penggunaan apa pun, termasuk komersial: membuat klip untuk streamer, agensi, atau
channel-mu sendiri. Hormati hak streamer yang stream-nya kamu potong.
</details>

<details>
<summary><b>Ke mana klip saya disimpan? Apakah ada yang diunggah?</b></summary>

Klip tetap di komputermu. File video milikmu sendiri tidak pernah keluar dari komputer. Link diambil lewat akun
StreamMoment: server-nya meneruskan rekaman ke SMTV sepotong demi sepotong dan tidak menyimpan apa pun. Teks stream hanya
dikirim ke AI pilihanmu. Key layanan AI tetap di komputermu dan tidak pernah muncul di log atau laporan masalah.
</details>

<details>
<summary><b>Apakah SMTV mengunggah ke TikTok atau YouTube sendiri?</b></summary>

Belum: kamu mengunduh klipnya dan mengunggahnya sendiri. Settings → About → «Coming» (Pengaturan → Tentang → Segera
hadir) menunjukkan apa yang sedang direncanakan.
</details>

<details>
<summary><b>Ada yang tidak berfungsi.</b></summary>

Settings → **Computer check** → **Fix** (Pengaturan → Pemeriksaan komputer → Perbaiki) menyelesaikan sebagian besar
masalah. Masih buntu? Settings → Computer check → **Report…** (Laporkan…): SMTV menyiapkan laporan tanpa key-mu dan
membuka halaman di GitHub; tidak ada yang terkirim dengan sendirinya.
[Apa yang bisa dicoba](docs/guide/id/troubleshooting.md).
</details>

## Bantu terjemahkan SMTV

Jendela SMTV memakai bahasa komputermu. Terjemahannya dibuat oleh orang-orang di
[Weblate](https://hosted.weblate.org/engage/smtv/) — tidak perlu bisa pemrograman: buka halamannya, pilih bahasamu,
terjemahkan beberapa baris. Terjemahan halaman ini dibuat secara otomatis; kalau kamu melihat kesalahan, perbaiki lewat
pull request. [Cara kerja terjemahan](docs/translations.md).

[![Status terjemahan](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV dibuat oleh tim [StreamMoment](https://streammoment.tv). Akun StreamMoment adalah cara paling mudah untuk memberi
SMTV sebuah AI dan untuk menempel link rekaman; SMTV juga tetap berjalan tanpanya.

- [Laporkan masalah](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) · [Usulkan ide](https://github.com/streammomenttv/smtv/issues/new?template=feature.yml)
- [Untuk pengguna mahir](docs/advanced.md): Docker, semua layanan AI, model ucapan, key, perintah
- [Perubahan](CHANGELOG.md) · [Berkontribusi](CONTRIBUTING.md) · [Keamanan](SECURITY.md)
- Suka SMTV? [Dukung di Boosty](https://boosty.to/smtv) dan beri repository ini ⭐ — itu membantu orang lain menemukannya.

Lisensi: [MIT](LICENSE).
