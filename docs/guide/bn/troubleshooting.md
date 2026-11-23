<!-- languages -->
[English](../troubleshooting.md) · [Русский](../ru/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · **বাংলা** · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 এই পাতাটি স্বয়ংক্রিয়ভাবে অনুবাদ করা হয়েছে। এটিকে আরও ভালো করতে সাহায্য করুন: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# কিছু একটা গোলমাল হয়েছে

## 1. Computer check → Fix

**Settings → Computer check** (সেটিংস → কম্পিউটার পরীক্ষা) SMTV-র যা যা দরকার সব দেখে আর লাইন ধরে ধরে জানায় কোনটা
ঠিক আছে আর কোনটা নেই। সমস্যার পাশে থাকে একটা **Fix** (ঠিক করুন) বোতাম: SMTV যা পারে নিজেই ইনস্টল বা মেরামত করে আর
দেখায় সে কী করছে।

<img src="../../images/check.png" alt="Settings → Computer check: প্রতিটা লাইন তার অবস্থা আর একটা Fix বোতাম সহ" width="820">

| লাইনে লেখা | কী করবেন |
|---|---|
| **Video (ffmpeg)** নেই | **Fix** চাপুন: SMTV ffmpeg ইনস্টল করে, যে ভিডিও টুল সে ব্যবহার করে। |
| **Captions** (সাবটাইটেল) কাজ করছে না | **Fix** চাপুন: SMTV এমন একটা ffmpeg ইনস্টল করে যা সাবটাইটেল আঁকতে পারে। |
| **AI**: কিছুই যুক্ত নেই | **Settings → AI**-তে একটা বেছে নিন — [কোনটা](connect-ai.md)। |
| **Connection to StreamMoment** (StreamMoment-এর সাথে সংযোগ) ব্যর্থ | ইন্টারনেট দেখুন; VPN বা ফায়ারওয়াল আটকাতে পারে। ফাইল এটা ছাড়াও কাজ করে। |
| **Free space** (খালি জায়গা) কম | ডিস্কে কিছু জায়গা খালি করুন: 6 ঘণ্টার স্ট্রিম প্রসেস হওয়ার সময় প্রায় 20 GB লাগে। |
| **Speech to text**: কোনো মডেল ডাউনলোড হয়নি | প্রথম রিকোয়েস্টে এটা নিজেই ডাউনলোড হয়; অথবা **Settings → Speech to text**-এ **Download** চাপুন। |

যে সমাধানে অ্যাডমিনিস্ট্রেটর পাসওয়ার্ড লাগে, তা কখনো চুপচাপ চলে না: SMTV কমান্ড সহ একটা টার্মিনাল খোলে, যাতে আপনি দেখতে
পান সে কী করছে।

## 2. সাধারণ সমস্যা

- **লিংক কাজ করছে না।** লিংকের জন্য [StreamMoment অ্যাকাউন্ট](account.md) লাগে। অ্যাকাউন্ট নেই? রেকর্ডিংটা নিজে ডাউনলোড
  করে SMTV-কে ফাইলটা দিন।
- **কোনো ক্লিপ নেই, বা খুব কম।** SMTV শুধু সেই মুহূর্তগুলো রাখে যেগুলোকে AI ভালো বলেছে। ছোট বা শান্ত স্ট্রিম থেকে কম
  ক্লিপ হতে পারে। আপনার কম্পিউটারে বিনামূল্যের AI ক্লাউডেরটার চেয়ে কম ভালো মুহূর্ত খুঁজে পায়।
- **«Too many requests»।** আপনার AI সার্ভিসের ফ্রি প্ল্যান সীমায় পৌঁছে গেছে: অপেক্ষা করুন, অথবা পেইড প্ল্যান বা
  অ্যাকাউন্ট ব্যবহার করুন।
- **ফোনে SMTV খুলছে না।** একই Wi-Fi, কোনো VPN নয়, ফায়ারওয়ালে SMTV-কে অনুমতি দিন — দেখুন [ফোন](phone.md)।
- **Windows: টার্মিনাল `smtv` চালাতে রাজি নয়।** এটা Smart App Control; SMTV তার আইকন থেকে খুলুন।
- **উইন্ডোর সাথে SMTV-র সংযোগ কেটে গেছে।** উইন্ডো বন্ধ করে SMTV আবার খুলুন।

থেমে যাওয়া রিকোয়েস্ট আবার চলতে পারে: **Continue** চাপুন — SMTV একই ধাপ থেকে শুরু করে আর যা হয়ে গেছে তা আবার করে না।

## 3. সমস্যার কথা জানান

তবুও আটকে আছেন? আমাদের জানান — এতে সবার উপকার হয়।

1. **Settings → Computer check → Report a problem** (সমস্যার কথা জানান; **Report…** বোতাম, এটা **Settings → About**-এও
   আছে), অথবা ব্যর্থ রিকোয়েস্টের নিচের বোতাম।
2. SMTV দেখায় রিপোর্টে কী কী যাবে: ভার্সন, কম্পিউটার পরীক্ষা, সেটিংস আর লগ। **চাবি আর টোকেন কেটে বাদ দেওয়া হয়**, আপনার
   হোম ফোল্ডার `~` হিসেবে দেখায়। আপনি বক্সে টিক না দিলে লিংক আর ফাইলের নাম বাদ থাকে।
3. **Save and open GitHub** (সেভ করে GitHub খুলুন) চাপুন। SMTV আর্কাইভ সেভ করে, আর ব্রাউজারে সারাংশ ভরা একটা নতুন issue
   খোলে। আর্কাইভটা টেনে এনে তাতে ছেড়ে দিন আর **Submit** চাপুন।

SMTV নিজে থেকে কিছুই পাঠায় না। উইন্ডো ছাড়া: টার্মিনালে `smtv report` চালান। আপনি সরাসরি
[issue খুলতেও পারেন](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml)।
