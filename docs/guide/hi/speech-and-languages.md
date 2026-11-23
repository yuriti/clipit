<!-- languages -->
[English](../speech-and-languages.md) · [Русский](../ru/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · **हिन्दी** · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 यह पेज अपने-आप अनुवाद किया गया है। इसे बेहतर बनाने में मदद करें: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# बोली और भाषाएँ

सबसे पहले SMTV स्ट्रीम की बोली को टेक्स्ट में बदलता है, हर शब्द के समय के साथ — इसी से AI समझता है कि क्या हुआ। यह
**आपके कंप्यूटर पर, मुफ़्त** चलता है। SMTV स्ट्रीम की भाषा खुद पहचान लेता है।

| भाषा | मॉडल | डाउनलोड (एक बार) | 12-कोर प्रोसेसर पर स्पीड |
|---|---|---|---|
| रूसी | GigaAM-v3, रूसी के लिए बना | 0.9 GB | रियल टाइम से 54× तेज़ |
| 25 यूरोपीय भाषाएँ: अंग्रेज़ी, स्पेनिश, जर्मन, फ़्रेंच, इटैलियन, पुर्तगाली, पोलिश, यूक्रेनी और दूसरी | Parakeet-TDT v3 | 2.4 GB | रियल टाइम से 33× तेज़ |
| बाकी सभी भाषाएँ: चीनी, जापानी, कोरियाई, हिन्दी, बांग्ला, कज़ाख़, उज़्बेक, अज़रबैजानी, वियतनामी, इंडोनेशियाई और दर्जनों दूसरी | Whisper large-v3-turbo | 1.6 GB | अभी नापा नहीं गया |

कोई मॉडल अपने-आप डाउनलोड होता है, जब पहली बार उसकी भाषा की स्ट्रीम आती है। ग्राफ़िक्स कार्ड की ज़रूरत नहीं; NVIDIA कार्ड
इसे तेज़ बनाता है। Mac पर Whisper प्रोसेसर पर चलता है और धीमा होता है।

**Settings → Speech to text** (सेटिंग्स → बोली से टेक्स्ट) हर मॉडल दिखाता है: वह कहाँ चलता है, उसकी भाषाएँ, साइज़ और
स्पीड, **Download** (डाउनलोड) और **Remove** (हटाएँ) के साथ। वहाँ हर भाषा के लिए दूसरा मॉडल चुना जा सकता है, आपकी अपनी
कुंजी (Groq या OpenAI) से **Whisper in the cloud** (क्लाउड में Whisper) भी — कमज़ोर कंप्यूटर पर तेज़, लेकिन तब ऑडियो
आपके कंप्यूटर से बाहर जाता है।

<img src="../../images/speech.png" alt="Settings → Speech to text: मॉडल और वे कौन-सी भाषाएँ लेते हैं" width="820">

**विंडो की भाषा** अलग चीज़ है: SMTV आपके कंप्यूटर की भाषा बोलता है; **Settings → Language and theme** (भाषा और थीम)
में दूसरी चुनी जा सकती है। आपकी भाषा नहीं है या आधी अनुवादित है? [अनुवाद में मदद करें](../../translations.md) —
प्रोग्रामिंग की ज़रूरत नहीं।
