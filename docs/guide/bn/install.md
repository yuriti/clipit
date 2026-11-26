<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · **বাংলা** · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 এই পাতাটি স্বয়ংক্রিয়ভাবে অনুবাদ করা হয়েছে। এটিকে আরও ভালো করতে সাহায্য করুন: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [মূল লেখা: Русский](../install.md).

# SMTV ইনস্টল করুন

একটা ফাইল ডাউনলোড করুন, খুলুন, আর একটা **SMTV** আইকন চলে আসে। SMTV-র যা যা লাগে সব তার ভেতরেই আছে।
অ্যাডমিনিস্ট্রেটর পাসওয়ার্ড লাগে না।

| আপনার কম্পিউটার | ডাউনলোড | সাইজ |
|---|---|---|
| **Windows 10 বা 11** (64-বিট) | [Windows-এর জন্য SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) | প্রায় 130 MB |
| **Mac** — Apple silicon (M1 আর নতুন) বা Intel, macOS 13+ | [Mac-এর জন্য SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | প্রায় 270 MB |

সব ভার্সন আর তাদের চেকসাম: [রিলিজ পেজ](https://github.com/yuriti/clipit/releases/latest)।

**প্রথমবার সিস্টেম কেন সতর্ক করে।** SMTV-র এখনো ডিজিটাল সাইন নেই। Windows-এর সাইন আসবে একটু পরে, macOS-এর যত
তাড়াতাড়ি সম্ভব, আর তারপর এই সতর্কবার্তা চলে যাবে। SMTV-র কোড খোলা: যে কেউ পড়ে দেখতে পারেন এটা কী করে।

## Windows

1. **Windows-এর জন্য SMTV** (ফাইল `SMTV-…-windows-x64-setup.exe`) ডাউনলোড করে খুলুন।
2. Windows একটা নীল উইন্ডো দেখায় **«Windows protected your PC»**। **More info** চাপুন, তারপর **Run anyway**।
3. ইনস্টলার দু-একটা প্রশ্ন করে (ভাষা, ডেস্কটপে আইকন) — **Next** আর **Install** চাপুন।
4. শেষে **Launch SMTV**-এ টিক রেখে দিন আর **Finish** চাপুন। পরের বার SMTV খুলুন **Start** মেনু থেকে (বা ডেস্কটপের
   আইকন থেকে)।

ইনস্টলার SMTV রাখে আপনার নিজের ইউজার ফোল্ডারে; এটা **Settings → Apps**-এ দেখা যায়, সেখান থেকে মুছেও ফেলা যায়।

**ইনস্টল না করে:** [ZIP ফাইল](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)
ডাউনলোড করুন, যেকোনো জায়গায় আনজিপ করুন (যেমন Documents-এ) আর `SMTV` ফোল্ডারে **Start SMTV** খুলুন। এই কপি নিজে
আপডেট হয় না: নতুন ভার্সন মানে নতুন ZIP।

### Windows 11: Smart App Control

**Smart App Control** চালু থাকলে (Windows Security → App & browser control) Windows সাইন ছাড়া প্রোগ্রাম পুরোপুরি
আটকে দেয়, আর ছাড়ার কোনো বোতাম নেই। SMTV-র জন্য Smart App Control বন্ধ করতে হবে না। তার বদলে এক লাইনে SMTV ইনস্টল
করুন — Smart App Control চালু থাকলেও এটা কাজ করে: [টার্মিনালে এক লাইন](#অভিজ্ঞ-ব্যবহারকারীদের-জন্য-টার্মিনালে-এক-লাইন)।
SMTV সাইন হয়ে গেলে সেখানে ডাউনলোডও কাজ করবে।

## Mac

1. **Mac-এর জন্য SMTV** ডাউনলোড করুন। এটা সব Mac-এর জন্য একটাই ফাইল, Apple silicon হোক বা Intel: SMTV আপনার Mac-এর প্রসেসরের জন্য বানানো ভার্সন নিজেই চালু করে।
2. ডাউনলোড করা `.dmg` খুলুন। একটা উইন্ডো খোলে, তাতে SMTV আর **Applications** ফোল্ডার: **SMTV** টেনে
   **Applications**-এর ওপর ছেড়ে দিন।
3. **Applications** খুলুন আর **SMTV**-তে ডাবল-ক্লিক করুন। macOS বলে সে SMTV যাচাই করতে পারছে না, আর এটা খোলে না।
   **Done** চাপুন।
4. **System Settings → Privacy & Security** খুলুন আর নিচে স্ক্রল করুন। «SMTV was blocked…»-এর পাশে **Open Anyway**
   চাপুন, আপনার Mac-এর পাসওয়ার্ড দিন আর **Open** চাপুন।
   macOS 14-এ একটা ছোট উপায় আছে: Applications-এ **SMTV**-তে রাইট-ক্লিক → **Open** → **Open**।

শুধু প্রথমবার: তারপর থেকে SMTV সাধারণ ক্লিকেই খোলে, Applications বা Launchpad থেকে। একই ধাপগুলো `.dmg`-এর ভেতরে
«How to open» ফাইলেও আছে।

## প্রথমবার চালু করা

SMTV আপনার কম্পিউটার পরীক্ষা করে আর প্রথম ক্লিপ পর্যন্ত তিনটে ধাপ দেখায়। তাদের নিচে সে দিতে চায় **আপনার ভাষার জন্য
কথা চেনার অংশ** — যে অংশটা স্ট্রিমের কথাকে লেখায় বদলায়। এটা ডাউনলোডের ভেতরে নেই, কারণ প্রতিটা ভাষার আলাদা লাগে
(0.9–2.5 GB)। **Fix** (ঠিক করুন) চাপুন আর অগ্রগতি দেখুন, অথবা বাদ দিন: প্রথম রিকোয়েস্ট নিজেই এটা ডাউনলোড করে নেবে।

**কী লাগবে:** অন্তত 5 GB খালি জায়গা, 6 ঘণ্টার স্ট্রিমের জন্য 20 GB; ইন্টারনেট। গ্রাফিক্স কার্ড লাগে না।

## অভিজ্ঞ ব্যবহারকারীদের জন্য: টার্মিনালে এক লাইন

একই SMTV, [uv](https://astral.sh/uv) দিয়ে — Python প্রোগ্রামের জন্য একটা ছোট অফিসিয়াল টুল — আপনার ইউজার ফোল্ডারে
ইনস্টল করা। এটা ব্যবহার করুন **Linux**-এ, **Smart App Control**-এর সঙ্গে, অথবা টার্মিনাল পছন্দ হলে। ডাউনলোড করা অ্যাপের
মতোই এটা উইন্ডো থেকে আপডেট হয়।

**Windows:** **Start** চাপুন, `PowerShell` টাইপ করুন, **Windows PowerShell** (নীল উইন্ডো) খুলুন, এই লাইনটা পেস্ট করুন
(রাইট ক্লিক বা Ctrl+V) আর **Enter** চাপুন:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

Smart App Control চালু থাকলে ইনস্টলার SMTV-কে python.org-এর সাইন করা Python-এর ওপর ইনস্টল করে (সেটা ইনস্টল করতে
চাইতে পারে — রাজি হন) আর তার মাধ্যমেই SMTV চালায়। যদি টার্মিনাল বলে সে `smtv` চালাতে পারছে না, তাহলে **SMTV** আইকন
ব্যবহার করুন।

**Mac বা Linux:** **Terminal** খুলুন (Mac-এ: Cmd+Space, `Terminal` টাইপ করুন, Enter), এই লাইনটা পেস্ট করুন আর
**Enter** চাপুন:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

কাজ শেষ বলা পর্যন্ত অপেক্ষা করুন (2–10 মিনিট)। SMTV নিজেই খুলে যায়; **SMTV** আইকন আছে Windows-এ Start মেনুতে, Mac-এ
Applications-এ, Linux-এ অ্যাপ্লিকেশন মেনুতে। এই পথে প্রথমবার SMTV **Fix** দিয়ে **ffmpeg** (ভিডিও টুল) ইনস্টল করে দিতে
চায়; ওপরের ডাউনলোডে এটা আগে থেকেই ভেতরে আছে।

দুটো ইনস্টলারই ছোট আর খোলা: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh)।

## সিস্টেম সতর্ক করলে

- **Windows: «Windows protected your PC»** (SmartScreen)। **More info** চাপুন, তারপর **Run anyway**।
- **Windows 11: Smart App Control SMTV আটকে দেয়।** SMTV সাইন না হওয়া পর্যন্ত
  [টার্মিনালে এক লাইন](#অভিজ্ঞ-ব্যবহারকারীদের-জন্য-টার্মিনালে-এক-লাইন) ব্যবহার করুন।
- **Windows: ফায়ারওয়াল জিজ্ঞেস করে** SMTV নেটওয়ার্ক ব্যবহার করতে পারবে কি না। **প্রাইভেট** নেটওয়ার্কের জন্য অনুমতি
  দিন: ফোনে খোলার জন্য SMTV-র এটা দরকার। ফোন না লাগলে না বললেও চলবে।
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» বা «developer cannot be verified»। **System Settings →
  Privacy & Security** খুলুন, নিচে স্ক্রল করুন আর SMTV-র পাশে **Open Anyway** চাপুন।
- **Mac: «SMTV would like to accept incoming connections»** — ফোনে SMTV ব্যবহার করতে চাইলে অনুমতি দিন।
- **অ্যান্টিভাইরাস** আপত্তি করছে? SMTV নতুন আর এখনো সাইন হয়নি, তাই কিছু অ্যান্টিভাইরাস এটা নিয়ে সাবধান থাকে। এর কোড
  খোলা, আর প্রতিটা ফাইলের চেকসাম আছে [রিলিজ পেজে](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`)।

এরপর: [আপনার প্রথম ক্লিপ](first-clip.md)।
