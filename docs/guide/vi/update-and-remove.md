<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · **Tiếng Việt** · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Trang này được dịch tự động. Hãy giúp cải thiện bản dịch: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Bản gốc: Русский](../update-and-remove.md).

# Cập nhật và gỡ cài đặt

## Cập nhật

SMTV kiểm tra phiên bản mới mỗi ngày một lần (bạn có thể tắt việc này). Khi có, nó báo **Version … is available**
(Đã có phiên bản …): bấm **Update** (Cập nhật).

- SMTV tự đóng, cập nhật và mở lại, thường trong vòng một phút.
- Nếu một yêu cầu đang chạy, việc cập nhật sẽ chờ đến khi nó xong — hoặc bấm **Stop the jobs and update** (Dừng công
  việc và cập nhật); sau đó **Continue** sẽ chạy tiếp chúng từ đúng bước cũ.
- Nếu phiên bản mới không khởi động được, phiên bản trước sẽ tự quay lại.
- Các phiên bản mới được tác giả SMTV ký; SMTV kiểm tra chữ ký trước khi cài.

Mọi thứ về cập nhật nằm trong **Settings → Computer check → Updates** (Cài đặt → Kiểm tra máy tính → Cập nhật).

Bạn tải SMTV cho Windows hoặc Mac? **Update** (Cập nhật) sẽ tải trình cài đặt mới, kiểm tra nó và mở nó: hãy cài nốt ở đó
(trên Mac, kéo SMTV mới thả vào Applications và bấm **Thay thế** (Replace)). Bản Windows từ file ZIP không tự cập nhật: hãy tải
file ZIP mới từ [trang phát hành](https://github.com/yuriti/clipit/releases/latest).

Cài SMTV theo cách khác? Trong Docker, phiên bản mới là một image mới; xem [dành cho người dùng nâng cao](../../advanced.md#docker).

## Gỡ cài đặt

**Settings → Computer check → Remove SMTV from this computer** (Gỡ SMTV khỏi máy tính này; nút **Remove…**) sẽ gỡ chương
trình và biểu tượng SMTV. Clip của bạn vẫn còn — đánh dấu **Also remove clips, jobs, settings and keys** (Gỡ cả clip,
công việc, cài đặt và key) để gỡ luôn chúng.

Bạn tải SMTV cho Windows hoặc Mac? Hãy gỡ chính chương trình theo cách của hệ thống (nút ở trên chỉ gỡ clip và cài đặt, nếu
bạn đánh dấu chúng):

- **Windows:** **Cài đặt → Ứng dụng → Ứng dụng đã cài đặt → SMTV → Gỡ cài đặt** (Settings → Apps → Installed apps → SMTV →
  Uninstall). Bản từ file ZIP: xóa thư mục của nó.
- **Mac:** kéo **SMTV** từ **Ứng dụng** (Applications) vào **Thùng rác** (Trash).

Cài bằng một dòng lệnh trong terminal? Không có cửa sổ, trong terminal:

```bash
smtv uninstall
```

Thêm `--data` để gỡ cả clip và cài đặt. Các chương trình bạn tự cài (Ollama, LM Studio) vẫn ở lại: hãy gỡ chúng như mọi
chương trình khác.
