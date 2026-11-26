<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · **Bahasa Indonesia** · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Versi asli: Русский](../install.md).

# Instal SMTV

Unduh satu file, buka, dan ikon **SMTV** muncul. Semua yang dibutuhkan SMTV sudah ada di dalamnya. Kamu tidak perlu
kata sandi administrator.

| Komputermu | Unduh | Ukuran |
|---|---|---|
| **Windows 10 atau 11** (64-bit) | [SMTV untuk Windows](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | sekitar 130 MB |
| **Mac** — Apple silicon (M1 dan yang lebih baru) atau Intel, macOS 13+ | [SMTV untuk Mac](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | sekitar 270 MB |

Semua versi dan checksum-nya: [halaman rilis](https://github.com/streammomenttv/smtv/releases/latest).

**Kenapa sistem memberi peringatan pada kali pertama.** SMTV belum punya tanda tangan digital. Tanda tangan untuk Windows
menyusul sedikit lebih lambat, untuk macOS secepat mungkin, dan setelah itu peringatan ini hilang. Kode SMTV terbuka:
siapa pun bisa membaca apa yang dilakukannya.

## Windows

1. Unduh **SMTV untuk Windows** (file `SMTV-…-windows-x64-setup.exe`) dan buka.
2. Windows menampilkan jendela biru **«Windows melindungi PC Anda»** («Windows protected your PC»). Tekan **Info
   selengkapnya** (More info), lalu **Tetap jalankan** (Run anyway).
3. Penginstal menanyakan beberapa hal (bahasa, ikon di desktop) — tekan **Next** dan **Install**.
4. Di akhir, biarkan **Launch SMTV** tetap dicentang dan tekan **Finish**. Lain kali, jalankan SMTV dari menu **Start**
   (atau dari ikon di desktop).

Penginstal menaruh SMTV di folder penggunamu sendiri; SMTV muncul di **Pengaturan → Aplikasi** (Settings → Apps), dan
dari sana kamu bisa menghapusnya.

**Tanpa menginstal:** unduh [file ZIP](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip),
ekstrak di mana saja (misalnya ke Documents) dan buka **Start SMTV** di folder `SMTV`. Salinan ini tidak memperbarui
dirinya sendiri: versi baru berarti ZIP baru.

### Windows 11: Smart App Control

Jika **Smart App Control** menyala (Keamanan Windows → Kontrol aplikasi & browser), Windows memblokir program tanpa
tanda tangan sepenuhnya, dan tidak ada tombol untuk mengizinkannya. Kamu tidak perlu mematikan Smart App Control demi
SMTV. Instal SMTV dengan satu baris saja — cara itu berjalan walaupun Smart App Control menyala:
[satu baris di terminal](#untuk-pengguna-berpengalaman-satu-baris-di-terminal). Setelah SMTV bertanda tangan, file
unduhan juga akan berjalan di sana.

## Mac

1. Unduh **SMTV untuk Mac**. Ini satu file untuk semua Mac, dengan Apple silicon atau Intel: SMTV sendiri menjalankan versi yang dibuat untuk prosesor Mac-mu.
2. Buka file `.dmg` yang sudah diunduh. Sebuah jendela terbuka berisi SMTV dan folder **Aplikasi** (Applications): seret
   **SMTV** ke **Aplikasi**.
3. Buka **Aplikasi** dan klik dua kali **SMTV**. macOS bilang tidak bisa memeriksa SMTV dan tidak membukanya. Tekan
   **Selesai** (Done).
4. Buka **Pengaturan Sistem → Privasi & Keamanan** (System Settings → Privacy & Security) dan gulir ke bawah. Di samping
   «SMTV diblokir…» tekan **Tetap Buka** (Open Anyway), masukkan kata sandi Mac-mu dan tekan **Buka** (Open).
   Di macOS 14 ada cara yang lebih singkat: klik kanan **SMTV** di Aplikasi → **Buka** (Open) → **Buka**.

Hanya pada kali pertama: setelah itu SMTV terbuka dengan klik biasa, dari Aplikasi atau Launchpad. Langkah yang sama
ada di file «How to open» di dalam `.dmg`.

## Saat pertama kali dijalankan

SMTV memeriksa komputermu dan menampilkan tiga langkah menuju klip pertama. Di bawahnya SMTV menawarkan **pengenalan
ucapan untuk bahasamu** — bagian yang mengubah ucapan di stream menjadi teks. Bagian ini tidak ada di file unduhan,
karena setiap bahasa butuh yang berbeda (0.9–2.5 GB). Tekan **Fix** (Perbaiki) dan lihat kemajuannya, atau lewati saja:
permintaan pertama akan mengunduhnya sendiri.

**Yang kamu butuhkan:** ruang kosong minimal 5 GB, 20 GB untuk stream 6 jam; internet. Tidak perlu kartu grafis.

## Untuk pengguna berpengalaman: satu baris di terminal

SMTV yang sama, diinstal dengan [uv](https://astral.sh/uv) — alat resmi kecil untuk program Python — ke folder
penggunamu. Pakai cara ini di **Linux**, dengan **Smart App Control**, atau kalau kamu lebih suka terminal. SMTV
diperbarui dari jendela, sama seperti aplikasi yang diunduh.

**Windows:** tekan **Start**, ketik `PowerShell`, buka **Windows PowerShell** (jendela biru), tempel baris ini (klik
kanan atau Ctrl+V) dan tekan **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Jika Smart App Control menyala, penginstal menginstal SMTV di atas Python bertanda tangan dari python.org (mungkin akan
meminta izin untuk menginstalnya — setujui) dan menjalankan SMTV lewat Python itu. Jika terminal bilang tidak bisa
menjalankan `smtv`, pakai ikon **SMTV** saja.

**Mac atau Linux:** buka **Terminal** (di Mac: Cmd+Space, ketik `Terminal`, Enter), tempel baris ini dan tekan
**Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Tunggu sampai penginstal bilang sudah selesai (2–10 menit). SMTV terbuka sendiri; ikon **SMTV** ada di menu Start di
Windows, di Applications di Mac, di menu aplikasi di Linux. Dengan cara ini, saat pertama kali SMTV menawarkan untuk
menginstal **ffmpeg** (alat video) dengan **Fix**; file unduhan di atas sudah berisi ffmpeg.

Kedua penginstal itu pendek dan terbuka: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Jika sistem memberi peringatan

- **Windows: «Windows melindungi PC Anda»** («Windows protected your PC», SmartScreen). Tekan **Info selengkapnya**
  (More info), lalu **Tetap jalankan** (Run anyway).
- **Windows 11: Smart App Control memblokir SMTV.** Pakai
  [satu baris di terminal](#untuk-pengguna-berpengalaman-satu-baris-di-terminal) sampai SMTV bertanda tangan.
- **Windows: firewall bertanya** apakah SMTV boleh memakai jaringan. Izinkan untuk jaringan **pribadi** (private): SMTV
  membutuhkannya agar bisa dibuka di ponselmu. Menolak juga tidak apa-apa kalau kamu tidak butuh ponsel.
- **Mac: «SMTV tidak dapat dibuka»** («SMTV cannot be opened»), «Apple tidak dapat memverifikasi…» atau «pengembang
  tidak dapat diverifikasi». Buka **Pengaturan Sistem → Privasi & Keamanan** (System Settings → Privacy & Security),
  gulir ke bawah, dan tekan **Tetap Buka** (Open Anyway) di samping SMTV.
- **Mac: «SMTV ingin menerima koneksi masuk»** («SMTV would like to accept incoming connections») — izinkan kalau kamu
  ingin memakai SMTV di ponsel.
- **Antivirus** mengeluh? SMTV masih baru dan belum bertanda tangan, jadi sebagian antivirus berhati-hati terhadapnya.
  Kodenya terbuka, dan checksum setiap file ada di [halaman rilis](https://github.com/streammomenttv/smtv/releases/latest)
  (`SHA256SUMS.txt`).

Berikutnya: [klip pertamamu](first-clip.md).
