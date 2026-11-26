<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · **Bahasa Indonesia** · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Versi asli: Русский](../update-and-remove.md).

# Perbarui dan hapus

## Perbarui

SMTV memeriksa versi baru sekali sehari (kamu bisa mematikannya). Jika ada, SMTV menampilkan **Version … is available**
(Versi … tersedia): tekan **Update** (Perbarui).

- SMTV menutup, memperbarui, dan membuka lagi dengan sendirinya, biasanya dalam satu menit.
- Jika ada permintaan yang sedang berjalan, pembaruan menunggu sampai selesai — atau tekan **Stop the jobs and update**
  (Hentikan pekerjaan dan perbarui); setelahnya **Continue** meneruskannya dari langkah yang sama.
- Jika versi baru tidak bisa berjalan, versi sebelumnya kembali dengan sendirinya.
- Versi baru ditandatangani oleh pembuat SMTV; SMTV memeriksa tanda tangannya sebelum menginstal.

Semua tentang pembaruan ada di **Settings → Computer check → Updates** (Pengaturan → Pemeriksaan komputer → Pembaruan).

Mengunduh SMTV untuk Windows atau Mac? **Update** (Perbarui) mengunduh penginstal baru, memeriksanya, dan
membukanya: selesaikan instalasinya di sana (di Mac, seret SMTV yang baru ke Applications dan tekan **Ganti**
(Replace)). Salinan Windows dari ZIP tidak memperbarui dirinya sendiri: unduh ZIP baru dari
[halaman rilis](https://github.com/streammomenttv/smtv/releases/latest).

Menginstal SMTV dengan cara lain? Di Docker, versi baru berarti image baru; lihat [untuk pengguna mahir](../../advanced.md#docker).

## Hapus

**Settings → Computer check → Remove SMTV from this computer** (Hapus SMTV dari komputer ini; tombol **Remove…**)
menghapus program dan ikon SMTV. Klipmu tetap ada — centang **Also remove clips, jobs, settings and keys** (Hapus juga
klip, pekerjaan, pengaturan, dan key) untuk menghapusnya juga.

Mengunduh SMTV untuk Windows atau Mac? Hapus programnya dengan cara sistem (tombol di atas hanya menghapus klip dan
pengaturan, jika kamu mencentangnya):

- **Windows:** **Pengaturan → Aplikasi → Aplikasi yang diinstal → SMTV → Hapus instalan** (Settings → Apps →
  Installed apps → SMTV → Uninstall). Salinan dari ZIP: hapus foldernya.
- **Mac:** seret **SMTV** dari **Aplikasi** (Applications) ke **Tempat Sampah** (Trash).

Menginstal dengan satu baris di terminal? Tanpa jendela, di terminal:

```bash
smtv uninstall
```

Tambahkan `--data` untuk menghapus klip dan pengaturan juga. Program yang kamu instal sendiri (Ollama, LM Studio) tetap
ada: hapus seperti program lainnya.
