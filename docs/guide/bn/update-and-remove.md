<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · **বাংলা** · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 এই পাতাটি স্বয়ংক্রিয়ভাবে অনুবাদ করা হয়েছে। এটিকে আরও ভালো করতে সাহায্য করুন: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# আপডেট আর মুছে ফেলা

## আপডেট

SMTV দিনে একবার নতুন ভার্সন খোঁজে (এটা বন্ধ করা যায়)। নতুন ভার্সন থাকলে সে দেখায় **Version … is available** (ভার্সন
… পাওয়া যাচ্ছে): **Update** (আপডেট) চাপুন।

- SMTV বন্ধ হয়, আপডেট হয় আর নিজেই আবার খুলে যায়, সাধারণত এক মিনিটের মধ্যে।
- কোনো রিকোয়েস্ট চললে আপডেট সেটা শেষ হওয়া পর্যন্ত অপেক্ষা করে — অথবা **Stop the jobs and update** (কাজ থামিয়ে আপডেট
  করুন) চাপুন; পরে **Continue** সেগুলো একই ধাপ থেকে চালিয়ে যায়।
- নতুন ভার্সন চালু না হলে আগেরটা নিজেই ফিরে আসে।
- নতুন ভার্সনগুলো SMTV-র নির্মাতারা সাইন করেন; ইনস্টলের আগে SMTV সাইন যাচাই করে।

আপডেটের সবকিছু আছে **Settings → Computer check → Updates** (সেটিংস → কম্পিউটার পরীক্ষা → আপডেট)-এ।

Windows বা Mac-এর জন্য SMTV ডাউনলোড করেছিলেন? **Update** (আপডেট) নতুন ইনস্টলার ডাউনলোড করে, যাচাই করে আর খোলে:
সেখানে ইনস্টল শেষ করুন (Mac-এ নতুন SMTV টেনে Applications-এ ছেড়ে দিন আর **Replace** চাপুন)। ZIP থেকে নেওয়া Windows
কপি নিজে আপডেট হয় না: [রিলিজ পেজ](https://github.com/streammomenttv/smtv/releases/latest) থেকে নতুন ZIP ডাউনলোড করুন।

SMTV অন্যভাবে ইনস্টল করেছিলেন? Docker-এ নতুন ভার্সন মানে নতুন ইমেজ; দেখুন [অভিজ্ঞ ব্যবহারকারীদের জন্য](../../advanced.md#docker)।

## মুছে ফেলা

**Settings → Computer check → Remove SMTV from this computer** (এই কম্পিউটার থেকে SMTV মুছুন; **Remove…** বোতাম)
প্রোগ্রাম আর SMTV আইকন মুছে দেয়। আপনার ক্লিপ থেকে যায় — সেগুলোও মুছতে **Also remove clips, jobs, settings and keys**
(ক্লিপ, কাজ, সেটিংস আর চাবিও মুছুন)-এ টিক দিন।

Windows বা Mac-এর জন্য SMTV ডাউনলোড করেছিলেন? প্রোগ্রামটা সিস্টেমের নিয়মে মুছুন (ওপরের বোতাম শুধু ক্লিপ আর
সেটিংস মোছে, যদি সেগুলোয় টিক দেন):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall**। ZIP থেকে নেওয়া কপি: তার ফোল্ডার মুছে দিন।
- **Mac:** **SMTV** টেনে **Applications** থেকে **Trash**-এ নিয়ে যান।

টার্মিনালে এক লাইনে ইনস্টল করেছিলেন? উইন্ডো ছাড়া, টার্মিনালে:

```bash
smtv uninstall
```

ক্লিপ আর সেটিংসও মুছতে `--data` যোগ করুন। যে প্রোগ্রামগুলো আপনি নিজে ইনস্টল করেছেন (Ollama, LM Studio) সেগুলো থেকে
যায়: অন্য যেকোনো প্রোগ্রামের মতো সেগুলো মুছুন।
