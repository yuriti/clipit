<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · **বাংলা** · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 এই পাতাটি স্বয়ংক্রিয়ভাবে অনুবাদ করা হয়েছে। এটিকে আরও ভালো করতে সাহায্য করুন: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [মূল লেখা: Русский](../speech-and-languages.md).

# কথা আর ভাষা

প্রথমে SMTV স্ট্রিমের কথাকে লেখায় বদলায়, প্রতিটা শব্দের সময় সহ — এভাবেই AI বোঝে কী ঘটেছিল। এটা চলে **আপনার কম্পিউটারে,
বিনামূল্যে**। SMTV স্ট্রিমের ভাষা নিজেই চিনে নেয়।

| ভাষা | মডেল | ডাউনলোড (একবার) | 12-কোর প্রসেসরে গতি |
|---|---|---|---|
| রুশ | GigaAM-v3, রুশের জন্য বানানো | 0.9 GB | রিয়েল টাইমের চেয়ে 54× দ্রুত |
| 25টা ইউরোপীয় ভাষা: ইংরেজি, স্প্যানিশ, জার্মান, ফরাসি, ইতালীয়, পর্তুগিজ, পোলিশ, ইউক্রেনীয় আর অন্যান্য | Parakeet-TDT v3 | 2.4 GB | রিয়েল টাইমের চেয়ে 33× দ্রুত |
| বাকি সব ভাষা: চীনা, জাপানি, কোরিয়ান, হিন্দি, বাংলা, কাজাখ, উজবেক, আজারবাইজানি, ভিয়েতনামি, ইন্দোনেশীয় আর আরও কয়েক ডজন | Whisper large-v3-turbo | 1.6 GB | এখনো মাপা হয়নি |

কোনো মডেল নিজে থেকেই ডাউনলোড হয়, প্রথমবার যখন তার ভাষার স্ট্রিম আসে। গ্রাফিক্স কার্ড লাগে না; NVIDIA কার্ড এটা দ্রুত
করে। Mac-এ Whisper প্রসেসরে চলে আর ধীর হয়।

**Settings → Speech to text** (সেটিংস → কথা থেকে লেখা) প্রতিটা মডেল দেখায়: কোথায় চলে, তার ভাষা, সাইজ আর গতি,
**Download** (ডাউনলোড) আর **Remove** (মুছুন) সহ। সেখানে প্রতিটা ভাষার জন্য অন্য মডেল বেছে নেওয়া যায়, আপনার নিজের চাবি
(Groq বা OpenAI) দিয়ে **Whisper in the cloud** (ক্লাউডে Whisper)-ও — দুর্বল কম্পিউটারে দ্রুত, তবে তখন অডিও আপনার
কম্পিউটার থেকে বাইরে যায়।

<img src="../../images/speech.png" alt="Settings → Speech to text: মডেলগুলো আর তারা কোন কোন ভাষা নেয়" width="820">

**উইন্ডোর ভাষা** আলাদা ব্যাপার: SMTV আপনার কম্পিউটারের ভাষায় কথা বলে; **Settings → Language and theme** (ভাষা আর থিম)
থেকে অন্য ভাষা বেছে নেওয়া যায়। আপনার ভাষা নেই বা অর্ধেক অনুবাদ হয়েছে? [অনুবাদে সাহায্য করুন](../../translations.md) —
প্রোগ্রামিং জানার দরকার নেই।
