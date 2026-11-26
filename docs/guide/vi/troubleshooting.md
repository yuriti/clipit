<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · **Tiếng Việt** · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 Trang này được dịch tự động. Hãy giúp cải thiện bản dịch: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Bản gốc: Русский](../troubleshooting.md).

# Có lỗi xảy ra

## 1. Kiểm tra máy tính → Fix

**Settings → Computer check** (Cài đặt → Kiểm tra máy tính) xem xét mọi thứ SMTV cần và cho biết, từng dòng một, cái
gì ổn và cái gì không. Bên cạnh mỗi vấn đề có một nút **Fix** (Sửa): SMTV tự cài hoặc sửa những gì nó làm được và cho
bạn thấy nó đang làm gì.

<img src="../../images/check.png" alt="Settings → Computer check: từng dòng với trạng thái và nút Fix" width="820">

| Dòng báo | Cần làm gì |
|---|---|
| **Video (ffmpeg)** bị thiếu | Bấm **Fix**: SMTV cài ffmpeg, công cụ xử lý video mà nó dùng. |
| **Captions** (Phụ đề) không hoạt động | Bấm **Fix**: SMTV cài một bản ffmpeg có thể vẽ phụ đề. |
| **AI**: chưa kết nối gì | Chọn một cách trong **Settings → AI** — [cách nào](connect-ai.md). |
| **Connection to StreamMoment** (Kết nối tới StreamMoment) bị lỗi | Kiểm tra internet; VPN hoặc tường lửa có thể chặn nó. File vẫn dùng được khi không có kết nối này. |
| **Free space** (Dung lượng trống) còn ít | Giải phóng bớt ổ đĩa: một buổi stream 6 tiếng cần khoảng 20 GB trong lúc xử lý. |
| **Speech to text** (Lời nói thành văn bản): model chưa được tải | Nó tự tải về ở yêu cầu đầu tiên; hoặc bấm **Download** trong **Settings → Speech to text**. |

Một bản sửa cần mật khẩu quản trị viên sẽ không bao giờ chạy ngầm: SMTV mở terminal kèm lệnh đó để bạn thấy nó làm gì.

## 2. Các vấn đề thường gặp

- **Link không hoạt động.** Link cần [tài khoản StreamMoment](account.md). Không có tài khoản? Hãy tự tải bản ghi về
  và đưa file cho SMTV.
- **Không có clip, hoặc rất ít.** SMTV chỉ giữ những khoảnh khắc mà AI chấm là hay. Một buổi stream ngắn hoặc ít sôi
  động có thể cho ít clip. AI miễn phí trên máy tính của bạn tìm được ít khoảnh khắc hay hơn AI đám mây.
- **«Too many requests»** (Quá nhiều yêu cầu). Gói miễn phí của dịch vụ AI bạn dùng đã chạm giới hạn: hãy chờ, hoặc dùng
  gói trả phí hay tài khoản.
- **Điện thoại không mở được SMTV.** Cùng Wi-Fi, không VPN, cho phép SMTV qua tường lửa — xem [điện thoại](phone.md).
- **Windows: terminal từ chối `smtv`.** Đó là do Smart App Control; hãy mở SMTV từ biểu tượng của nó.
- **Cửa sổ mất kết nối với SMTV.** Đóng cửa sổ và mở lại SMTV.

Một yêu cầu đã dừng có thể chạy tiếp: bấm **Continue** (Tiếp tục) — SMTV làm tiếp từ đúng bước đó và không làm lại những
gì đã xong.

## 3. Báo cáo sự cố

Vẫn chưa được? Hãy báo cho chúng tôi — điều đó giúp ích cho tất cả mọi người.

1. **Settings → Computer check → Report a problem** (Cài đặt → Kiểm tra máy tính → Báo cáo sự cố; nút **Report…**, cũng
   có trong **Settings → About**), hoặc nút bên dưới một yêu cầu bị lỗi.
2. SMTV hiện những gì sẽ có trong báo cáo: phiên bản, kết quả kiểm tra máy tính, cài đặt và log. **Key và token được cắt
   bỏ**, thư mục home của bạn hiện thành `~`. Link và tên file không được đưa vào trừ khi bạn đánh dấu ô chọn.
3. Bấm **Save and open GitHub** (Lưu và mở GitHub). SMTV lưu file nén, và một issue mới mở ra trong trình duyệt với phần
   tóm tắt đã được điền sẵn. Kéo file nén vào đó và bấm **Submit**.

SMTV không tự gửi gì cả. Không có cửa sổ: chạy `smtv report` trong terminal. Bạn cũng có thể
[mở issue](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) trực tiếp.
