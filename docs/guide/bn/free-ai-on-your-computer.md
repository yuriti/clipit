<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · **বাংলা** · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 এই পাতাটি স্বয়ংক্রিয়ভাবে অনুবাদ করা হয়েছে। এটিকে আরও ভালো করতে সাহায্য করুন: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# আপনার কম্পিউটারে বিনামূল্যের AI

AI সরাসরি আপনার কম্পিউটারে, বিনামূল্যে চলতে পারে: কিছুই বাইরে যায় না, আর কোনো খরচ নেই। আপনার লাগবে AI মডেল চালানোর
একটা প্রোগ্রাম — **Ollama** বা **LM Studio** — আর একটা মডেল, যেমন **Qwen**। SMTV প্রোগ্রামটা নিজেই খুঁজে নেয়।

**সত্যি বলতে:** বাড়ির কম্পিউটারে চলে এমন মডেল ক্লাউডেরগুলোর চেয়ে দুর্বল, তাই ক্লিপ খারাপ হয়, আর সুপারিশ করা মডেলগুলোর
একটাও এখনো SMTV-র সাথে পরীক্ষা করা হয়নি। ফল হতাশ করলে [অ্যাকাউন্ট](account.md) বা [একটা চাবি](get-a-key.md) চেষ্টা
করুন।

## 1. কোন মডেল আপনার কম্পিউটারে চলবে

আসল ব্যাপার হলো আপনার গ্রাফিক্স কার্ডের **ভিডিও মেমোরি** (Apple silicon-এর Mac-এ: পুরো মেমোরি)।

| ভিডিও মেমোরি | মডেল | ডাউনলোড | মন্তব্য |
|---|---|---|---|
| 8 GB-র কম | — | — | খুবই কম: অ্যাকাউন্ট বা চাবি ব্যবহার করুন |
| 8 GB | `qwen3:8b` | 5.2 GB | সবচেয়ে হালকা যেটা মোটামুটি ভালো কাজ করে |
| 10–12 GB | `qwen3-vl:8b` বা `gemma3:12b` | 6.1 / 8.1 GB | এগুলো ভিডিওর ফ্রেমও দেখে |
| 16 GB বা বেশি | `qwen3:14b` | 9.3 GB | চারটের মধ্যে সেরা |

7B («7 বিলিয়ন»)-এর চেয়ে ছোট মডেল সুপারিশ করা হয় না: এগুলো SMTV-র দরকারি উত্তরগুলো ভেঙে ফেলে।

**আপনার ভিডিও মেমোরি কীভাবে জানবেন:**
- **Windows:** Ctrl+Shift+Esc চাপুন → **Performance** → **GPU** → **Dedicated GPU memory**।
- **Mac:** Apple মেনু → **About This Mac** → **Memory**। Mac তার মেমোরি AI-এর সাথে ভাগ করে: 16 GB থাকলে `qwen3:8b`
  নিন, 32 GB বা বেশি থাকলে `qwen3:14b`।

## 2a. Ollama (সবচেয়ে সহজ)

1. [ollama.com/download](https://ollama.com/download) থেকে Ollama ডাউনলোড করে অন্য যেকোনো প্রোগ্রামের মতো ইনস্টল করুন।
   এটা নিজেই চালু হয় আর ঘড়ির কাছে থাকে।
2. SMTV-তে: **Settings → AI → Free, on this computer → Find on this computer** (সেটিংস → AI → বিনামূল্যে, এই
   কম্পিউটারে → এই কম্পিউটারে খুঁজুন)। SMTV Ollama খুঁজে পায়।
3. তালিকায় **Ollama** খুলুন: SMTV সুপারিশ করা মডেলগুলো তাদের সাইজ সহ দেখায়। ওপরের টেবিলের মডেলটার পাশে **Download**
   (ডাউনলোড) চাপুন আর অপেক্ষা করুন (5–10 GB)।
4. হয়ে গেল। SMTV নিজের ধাপগুলোর জন্য সেই মডেল নিজেই বেছে নেয়।

SMTV প্রতিটা রিকোয়েস্টের জন্য Ollama-র মেমোরি এমনভাবে ঠিক করে যাতে পুরো স্ট্রিমের লেখা ধরে যায়; Ollama-র সেটিংস বদলানোর
দরকার নেই।

## 2b. LM Studio

1. [lmstudio.ai/download](https://lmstudio.ai/download) থেকে LM Studio ডাউনলোড করে ইনস্টল করুন।
2. LM Studio-তে **Discover** খুলুন, **Qwen3 8B** (বা টেবিল অনুযায়ী 14B) খুঁজুন আর **Download** চাপুন।
3. **Developer** ট্যাব খুলুন আর **Start server** চালু করুন (এটা পোর্ট 1234-এ শোনে)। মডেলটা সেখানেই লোড করুন।
4. SMTV-তে: **Settings → AI → Free, on this computer → Find on this computer**। SMTV LM Studio খুঁজে পায়।

## 3. ক্লিপ বানান

SMTV-কে একটা [ভিডিও ফাইল](first-clip.md) দিন। Twitch বা YouTube-এর লিংকের জন্য বিনামূল্যের AI থাকলেও
[অ্যাকাউন্ট](account.md) লাগে: রেকর্ডিং অ্যাকাউন্টই নিয়ে আসে।

বিনামূল্যের AI ক্লাউডেরটার চেয়ে ধীরে কাজ করে; লম্বা স্ট্রিমে কয়েক ঘণ্টা লাগতে পারে। কম্পিউটার চালু রাখুন।
