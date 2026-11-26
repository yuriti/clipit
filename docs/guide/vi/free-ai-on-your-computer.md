<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · [English](../en/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · **Tiếng Việt** · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Trang này được dịch tự động. Hãy giúp cải thiện bản dịch: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Bản gốc: Русский](../free-ai-on-your-computer.md).

# AI miễn phí trên máy tính của bạn

AI có thể chạy ngay trên máy tính của bạn, miễn phí: không có gì rời khỏi máy, và không phải trả gì. Bạn cần một chương
trình chạy model AI — **Ollama** hoặc **LM Studio** — và một model, ví dụ **Qwen**. SMTV tự tìm thấy chương trình đó.

**Nói thật:** các model vừa với máy tính ở nhà yếu hơn các model đám mây, nên clip ra kém hơn, và chưa model nào trong số
được khuyến nghị đã được thử với SMTV. Nếu kết quả làm bạn thất vọng, hãy thử [tài khoản](account.md) hoặc
[một key](get-a-key.md).

## 1. Model nào hợp với máy tính của bạn

Điều quan trọng là **bộ nhớ video** của card đồ họa (trên máy Mac dùng chip Apple: toàn bộ bộ nhớ).

| Bộ nhớ video | Model | Dung lượng tải | Ghi chú |
|---|---|---|---|
| dưới 8 GB | — | — | Quá ít: hãy dùng tài khoản hoặc key |
| 8 GB | `qwen3:8b` | 5.2 GB | Nhẹ nhất mà vẫn chạy đủ tốt |
| 10–12 GB | `qwen3-vl:8b` hoặc `gemma3:12b` | 6.1 / 8.1 GB | Các model này còn xem được khung hình của video |
| 16 GB trở lên | `qwen3:14b` | 9.3 GB | Tốt nhất trong bốn model |

Không khuyến nghị các model nhỏ hơn 7B («7 tỷ»): chúng làm hỏng các câu trả lời mà SMTV cần.

**Cách xem bộ nhớ video:**
- **Windows:** bấm Ctrl+Shift+Esc → **Hiệu suất** (Performance) → **GPU** → **Bộ nhớ GPU chuyên dụng** (Dedicated GPU memory).
- **Mac:** menu Apple → **Giới thiệu về máy Mac này** (About This Mac) → **Bộ nhớ** (Memory). Mac dùng chung bộ nhớ
  với AI: có 16 GB thì chọn `qwen3:8b`, có 32 GB trở lên thì chọn `qwen3:14b`.

## 2a. Ollama (đơn giản nhất)

1. Tải Ollama từ [ollama.com/download](https://ollama.com/download) và cài như mọi chương trình khác. Nó tự khởi động
   và nằm gần đồng hồ.
2. Trong SMTV: **Settings → AI → Free, on this computer → Find on this computer** (Cài đặt → AI → Miễn phí, trên máy
   tính này → Tìm trên máy tính này). SMTV sẽ tìm thấy Ollama.
3. Mở **Ollama** trong danh sách: SMTV hiện các model được khuyến nghị cùng dung lượng. Bấm **Download** (Tải xuống) bên
   cạnh model trong bảng ở trên và chờ (5–10 GB).
4. Xong. SMTV tự chọn model đó cho các bước của nó.

SMTV tự đặt bộ nhớ cho Ollama ở mỗi yêu cầu sao cho vừa toàn bộ văn bản của buổi stream; bạn không cần đổi cài đặt của
Ollama.

## 2b. LM Studio

1. Tải LM Studio từ [lmstudio.ai/download](https://lmstudio.ai/download) và cài đặt.
2. Trong LM Studio mở **Discover**, tìm **Qwen3 8B** (hoặc 14B, theo bảng) và bấm **Download**.
3. Mở tab **Developer** và bật **Start server** (nó lắng nghe ở cổng 1234). Tải model lên ở đó.
4. Trong SMTV: **Settings → AI → Free, on this computer → Find on this computer**. SMTV sẽ tìm thấy LM Studio.

## 3. Làm một clip

Đưa cho SMTV một [file video](first-clip.md). Link tới Twitch hoặc YouTube vẫn cần [tài khoản](account.md) kể cả khi
dùng AI miễn phí: tài khoản là thứ tải bản ghi về.

AI miễn phí chạy chậm hơn AI đám mây; một buổi stream dài có thể mất vài tiếng. Hãy để máy tính bật.
