<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · **Tiếng Việt** · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 Trang này được dịch tự động. Hãy giúp cải thiện bản dịch: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Bản gốc: Русский](../get-a-key.md).

# Lấy key ở đâu

**Key** (một «API key») là một mật khẩu dài cho phép SMTV dùng dịch vụ AI thay mặt bạn. Bạn lấy nó trên trang của dịch
vụ sau khi đăng ký. SMTV chỉ giữ nó trên máy tính của bạn và chỉ gửi nó tới đúng dịch vụ đó; nó không bao giờ xuất
hiện trong log hay báo cáo sự cố.

> Giá và gói miễn phí có thể thay đổi. Những gì viết ở đây đã được đối chiếu với trang của chính các dịch vụ vào ngày **23.11.2026** — hãy kiểm tra trang của dịch vụ trước khi bắt đầu.

## Chọn dịch vụ nào

| Dịch vụ | Gói miễn phí | Lấy key ở đâu | Nên biết |
|---|---|---|---|
| **Google Gemini** | Có, giới hạn theo phút và theo ngày; các model miễn phí được liệt kê trên trang giá của Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Cách bắt đầu miễn phí dễ nhất; chỉ gói trả phí mới cần thiết lập thanh toán. Với gói miễn phí, Google có thể dùng những gì bạn gửi để cải thiện sản phẩm của họ và người thật có thể đọc nó — trừ Khu vực Kinh tế châu Âu, Thụy Sĩ và Vương quốc Anh. Không có ở mọi quốc gia (ví dụ không có ở Nga): xem danh sách khu vực của Google. |
| **Groq** | Có, có giới hạn, hiển thị trong bảng điều khiển của nó | [console.groq.com/keys](https://console.groq.com/keys) | Rất nhanh. Cũng có thể chuyển lời nói thành văn bản trên đám mây, giá rẻ (khoảng $0.04 cho mỗi giờ âm thanh với Whisper large-v3 turbo). |
| **OpenRouter** | Các model có tên kết thúc bằng `:free`: 20 yêu cầu mỗi phút, 50 mỗi ngày (1.000 mỗi ngày khi bạn đã mua $10 tín dụng) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Một key cho hàng trăm model của nhiều công ty. 50 yêu cầu mỗi ngày là không đủ cho một buổi stream dài. |
| **Mistral** | Hãy kiểm tra trên trang của họ: các trang này không nêu điều kiện miễn phí cho API | [console.mistral.ai](https://console.mistral.ai) | Một công ty châu Âu. |
| **DeepSeek** | Không | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Trả tiền từ số dư mà bạn phải nạp trước. |
| **OpenAI** | Không hứa tặng tín dụng miễn phí: tài khoản mới phải trả trước, từ $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Các model đứng sau ChatGPT. Gói đăng ký ChatGPT không giống với key: key được trả tiền riêng. Chỉ ở các quốc gia được hỗ trợ (không có ở Nga). |
| **Claude (Anthropic)** | Không | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Gói đăng ký Claude không giống với key. Chỉ ở các khu vực được hỗ trợ (không có ở Nga). |

SMTV cũng biết xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras và mọi địa chỉ tương thích OpenAI — xem
[dành cho người dùng nâng cao](../../advanced.md#ai-services-and-keys).

**Gói miễn phí có giới hạn.** Một buổi stream dài gửi rất nhiều yêu cầu; khi chạm giới hạn, dịch vụ trả lời «too many
requests» (quá nhiều yêu cầu) và SMTV sẽ chờ hoặc dừng. Với buổi stream 6–12 tiếng, gói trả phí hoặc
[tài khoản](account.md) sẽ phù hợp hơn.

## Ví dụ: key Gemini miễn phí, từng bước một

1. Mở [aistudio.google.com/apikey](https://aistudio.google.com/apikey) và đăng nhập bằng tài khoản Google.
2. Chấp nhận điều khoản nếu được hỏi.
3. Bấm **Create API key**. Sao chép key (nó bắt đầu bằng `AIza…`). Giữ bí mật như một mật khẩu.
4. Trong SMTV: **Settings → AI → Your own key → Add a key** (Cài đặt → AI → Key của riêng bạn → Thêm key).
5. Chọn **Gemini**, dán key, bấm **Check** (Kiểm tra). SMTV sẽ cho biết key có hoạt động không.
6. Xong. Mọi bước AI giờ đây dùng Gemini với model phù hợp; **Settings → AI steps** (Cài đặt → Các bước AI) cho biết
   là model nào.

Các dịch vụ khác cũng làm tương tự: đăng ký, tìm mục **API keys**, tạo một key, dán vào SMTV, bấm **Check**. Các dịch vụ
trả phí sẽ yêu cầu bạn thêm thẻ hoặc nạp tiền vào số dư trước.

## Key của bạn an toàn

- Được lưu trên máy tính của bạn, có mã hóa.
- Chỉ được gửi tới dịch vụ mà nó thuộc về. StreamMoment không bao giờ thấy nó.
- Bị mất hoặc bị lộ? Xóa nó trên trang của dịch vụ và tạo key mới.
