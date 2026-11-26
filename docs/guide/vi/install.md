<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · **Tiếng Việt** · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Trang này được dịch tự động. Hãy giúp cải thiện bản dịch: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Bản gốc: Русский](../install.md).

# Cài đặt SMTV

Tải về một file, mở nó ra, và biểu tượng **SMTV** sẽ xuất hiện. Mọi thứ SMTV cần đều có sẵn bên trong. Bạn không cần
mật khẩu quản trị viên.

| Máy tính của bạn | Tải về | Dung lượng |
|---|---|---|
| **Windows 10 hoặc 11** (64-bit) | [SMTV cho Windows](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) | khoảng 130 MB |
| **Mac** — chip Apple (M1 trở về sau) hoặc Intel, macOS 13+ | [SMTV cho Mac](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | khoảng 270 MB |

Tất cả các phiên bản và mã kiểm tra (checksum) của chúng: [trang phát hành](https://github.com/streammomenttv/smtv/releases/latest).

**Vì sao lần đầu hệ thống cảnh báo bạn.** SMTV chưa có chữ ký số. Chữ ký cho Windows sẽ có muộn hơn một chút, chữ ký cho
macOS sẽ có sớm nhất có thể, và khi đó cảnh báo này sẽ biến mất. Mã nguồn của SMTV là công khai: ai cũng có thể đọc xem nó
làm gì.

## Windows

1. Tải **SMTV cho Windows** (file `SMTV-…-windows-x64-setup.exe`) và mở nó.
2. Windows hiện một cửa sổ màu xanh **«Windows đã bảo vệ PC của bạn»** (Windows protected your PC). Bấm **Thông tin thêm**
   (More info), rồi **Vẫn chạy** (Run anyway).
3. Trình cài đặt hỏi vài câu (ngôn ngữ, có đặt biểu tượng trên desktop không) — bấm **Next** (Tiếp) và **Install** (Cài đặt).
4. Ở cuối, để nguyên dấu chọn **Launch SMTV** (Mở SMTV) và bấm **Finish** (Xong). Lần sau, mở SMTV từ menu **Start**
   (hoặc biểu tượng trên desktop).

Trình cài đặt đặt SMTV vào thư mục người dùng của riêng bạn; nó xuất hiện trong **Cài đặt → Ứng dụng** (Settings → Apps),
nơi bạn có thể gỡ nó.

**Không cần cài:** tải [file ZIP](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip),
giải nén ở đâu cũng được (ví dụ vào Documents) và mở **Start SMTV** trong thư mục `SMTV`. Bản này không tự cập nhật:
phiên bản mới là một file ZIP mới.

### Windows 11: Smart App Control

Nếu **Smart App Control** đang bật (Bảo mật Windows → Kiểm soát ứng dụng và trình duyệt, tức Windows Security → App &
browser control), Windows chặn hoàn toàn các chương trình không có chữ ký, và không có nút nào để cho qua. Bạn không cần tắt
Smart App Control vì SMTV. Thay vào đó, hãy cài SMTV bằng một dòng lệnh — cách này chạy được ngay cả khi Smart App Control
đang bật: [một dòng lệnh trong terminal](#dành-cho-người-dùng-có-kinh-nghiệm-một-dòng-lệnh-trong-terminal). Khi SMTV có chữ ký, bản tải về cũng sẽ chạy được ở đó.

## Mac

1. Tải **SMTV cho Mac**. Đây là một file cho mọi máy Mac, chip Apple hay Intel: SMTV tự chạy phiên bản được làm cho bộ xử lý của máy Mac của bạn.
2. Mở file `.dmg` vừa tải. Một cửa sổ mở ra với SMTV và thư mục **Ứng dụng** (Applications): kéo **SMTV** thả vào
   **Ứng dụng**.
3. Mở **Ứng dụng** và nhấp đúp vào **SMTV**. macOS báo không thể kiểm tra SMTV và không mở nó. Bấm **Xong** (Done).
4. Mở **Cài đặt hệ thống → Quyền riêng tư & Bảo mật** (System Settings → Privacy & Security) và cuộn xuống. Bên cạnh
   «SMTV đã bị chặn…» bấm **Vẫn mở** (Open Anyway), nhập mật khẩu máy Mac và bấm **Mở** (Open).
   Trên macOS 14 có cách ngắn hơn: bấm chuột phải vào **SMTV** trong Ứng dụng → **Mở** → **Mở**.

Chỉ lần đầu thôi: sau đó SMTV mở bằng một cú nhấp bình thường, từ Ứng dụng hoặc Launchpad. Các bước này cũng có trong file
«How to open» bên trong `.dmg`.

## Lần khởi động đầu tiên

SMTV kiểm tra máy tính của bạn và hiện ba bước để có clip đầu tiên. Bên dưới, nó đề nghị **nhận dạng giọng nói cho ngôn ngữ
của bạn** — phần biến lời nói trong buổi stream thành văn bản. Phần này không có trong bản tải về, vì mỗi ngôn ngữ cần một
phần riêng (0.9–2.5 GB). Bấm **Fix** (Sửa) và theo dõi tiến trình, hoặc bỏ qua: yêu cầu đầu tiên sẽ tự tải nó về.

**Bạn cần:** ít nhất 5 GB dung lượng trống, 20 GB cho một buổi stream 6 tiếng; có internet. Không cần card đồ họa.

## Dành cho người dùng có kinh nghiệm: một dòng lệnh trong terminal

Vẫn là SMTV đó, được cài bằng [uv](https://astral.sh/uv) — một công cụ chính thức nhỏ dùng để cài các chương trình Python —
vào thư mục người dùng của bạn. Hãy dùng cách này trên **Linux**, khi bật **Smart App Control**, hoặc nếu bạn thích terminal
hơn. Nó cập nhật từ cửa sổ giống như ứng dụng tải về.

**Windows:** bấm **Start**, gõ `PowerShell`, mở **Windows PowerShell** (cửa sổ màu xanh), dán dòng này (chuột phải hoặc
Ctrl+V) và bấm **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

Khi Smart App Control đang bật, trình cài đặt cài SMTV trên bản Python có chữ ký từ python.org (có thể nó sẽ hỏi để cài
Python — hãy đồng ý) và mở SMTV thông qua đó. Nếu terminal báo không chạy được `smtv`, hãy dùng biểu tượng **SMTV** thay thế.

**Mac hoặc Linux:** mở **Terminal** (trên Mac: Cmd+Space, gõ `Terminal`, Enter), dán dòng này và bấm **Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Chờ đến khi nó báo đã xong (2–10 phút). SMTV tự mở; biểu tượng **SMTV** nằm trong menu Start trên Windows, trong
Applications trên Mac, trong menu ứng dụng trên Linux. Theo cách này, lần đầu SMTV sẽ đề nghị cài **ffmpeg** (công cụ xử lý
video) bằng **Fix** (Sửa); bản tải về ở trên đã có sẵn nó.

Cả hai trình cài đặt đều ngắn và công khai: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Nếu hệ thống cảnh báo

- **Windows: «Windows đã bảo vệ PC của bạn»** («Windows protected your PC», SmartScreen). Bấm **Thông tin thêm** (More
  info), rồi **Vẫn chạy** (Run anyway).
- **Windows 11: Smart App Control chặn SMTV.** Hãy dùng [một dòng lệnh trong terminal](#dành-cho-người-dùng-có-kinh-nghiệm-một-dòng-lệnh-trong-terminal) cho đến khi SMTV
  có chữ ký.
- **Windows: tường lửa hỏi** SMTV có được dùng mạng không. Hãy cho phép với mạng **riêng tư** (private): SMTV cần quyền
  này để mở được trên điện thoại của bạn. Từ chối cũng không sao nếu bạn không cần dùng điện thoại.
- **Mac: «Không thể mở SMTV»** («SMTV cannot be opened»), «Apple không thể xác minh…» hoặc «không thể xác minh nhà phát
  triển». Mở **Cài đặt hệ thống → Quyền riêng tư & Bảo mật** (System Settings → Privacy & Security), cuộn xuống và bấm
  **Vẫn mở** (Open Anyway) bên cạnh SMTV.
- **Mac: «SMTV muốn chấp nhận các kết nối đến»** («SMTV would like to accept incoming connections») — hãy cho phép nếu
  bạn muốn dùng SMTV trên điện thoại.
- **Phần mềm diệt virus** phàn nàn? SMTV còn mới và chưa có chữ ký, nên một số phần mềm diệt virus dè chừng với nó. Mã nguồn
  của SMTV là công khai, và mã kiểm tra của từng file có trên [trang phát hành](https://github.com/streammomenttv/smtv/releases/latest)
  (`SHA256SUMS.txt`).

Tiếp theo: [clip đầu tiên của bạn](first-clip.md).
