<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · **Bahasa Indonesia** · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 Halaman ini diterjemahkan secara otomatis. Bantu kami memperbaikinya: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Versi asli: Русский](../troubleshooting.md).

# Ada yang tidak beres

## 1. Pemeriksaan komputer → Fix

**Settings → Computer check** (Pengaturan → Pemeriksaan komputer) memeriksa semua yang dibutuhkan SMTV dan menyebutkan,
baris demi baris, mana yang beres dan mana yang tidak. Di samping masalah ada tombol **Fix** (Perbaiki): SMTV menginstal
atau memperbaiki apa yang bisa ia tangani sendiri dan menunjukkan apa yang sedang dilakukannya.

<img src="../../images/check.png" alt="Settings → Computer check: setiap baris dengan statusnya dan tombol Fix" width="820">

| Baris menyebutkan | Yang perlu dilakukan |
|---|---|
| **Video (ffmpeg)** tidak ada | Tekan **Fix**: SMTV menginstal ffmpeg, alat video yang dipakainya. |
| **Captions** (Teks) tidak berfungsi | Tekan **Fix**: SMTV menginstal ffmpeg yang bisa menggambar teks. |
| **AI**: belum ada yang terhubung | Pilih satu di **Settings → AI** — [yang mana](connect-ai.md). |
| **Connection to StreamMoment** (Koneksi ke StreamMoment) gagal | Periksa internet; VPN atau firewall mungkin memblokirnya. File tetap bisa dipakai tanpa koneksi ini. |
| **Free space** (Ruang kosong) sedikit | Kosongkan sebagian ruang disk: stream 6 jam butuh sekitar 20 GB selama diproses. |
| **Speech to text** (Ucapan menjadi teks): model belum diunduh | Model terunduh sendiri pada permintaan pertama; atau tekan **Download** di **Settings → Speech to text**. |

Perbaikan yang butuh kata sandi administrator tidak pernah dijalankan diam-diam: SMTV membuka terminal berisi perintahnya,
jadi kamu bisa melihat apa yang dilakukannya.

## 2. Masalah umum

- **Link tidak berfungsi.** Link memerlukan [akun StreamMoment](account.md). Tidak punya akun? Unduh rekamannya sendiri
  dan berikan file-nya ke SMTV.
- **Tidak ada klip, atau sangat sedikit.** SMTV hanya menyimpan momen yang dinilai bagus oleh AI. Stream yang pendek
  atau sepi mungkin menghasilkan sedikit. AI gratis di komputermu menemukan lebih sedikit momen bagus daripada AI cloud.
- **«Too many requests»** (Terlalu banyak permintaan). Paket gratis layanan AI-mu sudah mencapai batas: tunggu, atau
  pakai paket berbayar atau akun.
- **Ponsel tidak bisa membuka SMTV.** Wi-Fi yang sama, tanpa VPN, izinkan SMTV di firewall — lihat [ponsel](phone.md).
- **Windows: terminal menolak `smtv`.** Itu karena Smart App Control; jalankan SMTV dari ikonnya.
- **Jendela kehilangan koneksi ke SMTV.** Tutup jendela dan buka SMTV lagi.

Permintaan yang berhenti bisa dilanjutkan: tekan **Continue** (Lanjutkan) — SMTV meneruskan dari langkah yang sama dan
tidak mengulang yang sudah selesai.

## 3. Laporkan masalah

Masih buntu? Beri tahu kami — itu membantu semua orang.

1. **Settings → Computer check → Report a problem** (Pengaturan → Pemeriksaan komputer → Laporkan masalah; tombol
   **Report…**, juga ada di **Settings → About**), atau tombol di bawah permintaan yang gagal.
2. SMTV menunjukkan apa saja yang masuk ke laporan: versi, hasil pemeriksaan komputer, pengaturan, dan log. **Key dan
   token dihapus**, folder home-mu ditampilkan sebagai `~`. Link dan nama file tidak disertakan kecuali kamu mencentang
   kotaknya.
3. Tekan **Save and open GitHub** (Simpan dan buka GitHub). SMTV menyimpan arsipnya, dan issue baru terbuka di browser
   dengan ringkasan yang sudah terisi. Seret arsip ke sana dan tekan **Submit**.

SMTV tidak mengirim apa pun dengan sendirinya. Tanpa jendela: jalankan `smtv report` di terminal. Kamu juga bisa
[membuka issue](https://github.com/yuriti/clipit/issues/new?template=bug.yml) secara langsung.
