<!-- languages -->
[English](../troubleshooting.md) · [Русский](../ru/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · **हिन्दी** · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 यह पेज अपने-आप अनुवाद किया गया है। इसे बेहतर बनाने में मदद करें: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# कुछ गड़बड़ हो गई

## 1. Computer check → Fix

**Settings → Computer check** (सेटिंग्स → कंप्यूटर जाँच) वह सब देखता है जिसकी SMTV को ज़रूरत है और लाइन-दर-लाइन बताता
है कि क्या ठीक है और क्या नहीं। किसी समस्या के पास **Fix** (ठीक करें) बटन होता है: SMTV जो कर सकता है उसे खुद इंस्टॉल
या ठीक करता है और दिखाता है कि वह क्या कर रहा है।

<img src="../../images/check.png" alt="Settings → Computer check: हर लाइन अपनी स्थिति और Fix बटन के साथ" width="820">

| लाइन कहती है | क्या करें |
|---|---|
| **Video (ffmpeg)** नहीं है | **Fix** दबाएँ: SMTV ffmpeg इंस्टॉल करता है, वह वीडियो टूल जो वह इस्तेमाल करता है। |
| **Captions** (सबटाइटल) काम नहीं करते | **Fix** दबाएँ: SMTV ऐसा ffmpeg इंस्टॉल करता है जो सबटाइटल बना सके। |
| **AI**: कुछ भी जुड़ा नहीं | **Settings → AI** में एक चुनें — [कौन-सा](connect-ai.md)। |
| **Connection to StreamMoment** (StreamMoment से कनेक्शन) फ़ेल | इंटरनेट जाँचें; VPN या फ़ायरवॉल इसे रोक सकता है। फ़ाइलें इसके बिना भी काम करती हैं। |
| **Free space** (खाली जगह) कम है | डिस्क पर कुछ जगह खाली करें: 6 घंटे की स्ट्रीम को प्रोसेस होते समय करीब 20 GB चाहिए। |
| **Speech to text**: कोई मॉडल डाउनलोड नहीं हुआ | वह पहली रिक्वेस्ट पर अपने-आप डाउनलोड होता है; या **Settings → Speech to text** में **Download** दबाएँ। |

जिस सुधार के लिए एडमिनिस्ट्रेटर पासवर्ड चाहिए, वह कभी चुपचाप नहीं चलता: SMTV कमांड के साथ एक टर्मिनल खोलता है, ताकि
आप देख सकें कि वह क्या करता है।

## 2. आम समस्याएँ

- **लिंक काम नहीं करता।** लिंक के लिए [StreamMoment अकाउंट](account.md) चाहिए। अकाउंट नहीं है? रिकॉर्डिंग खुद डाउनलोड
  करें और SMTV को फ़ाइल दें।
- **कोई क्लिप नहीं, या बहुत कम।** SMTV सिर्फ़ वही पल रखता है जिन्हें AI ने अच्छा माना। छोटी या शांत स्ट्रीम से कम क्लिप
  मिल सकती हैं। आपके कंप्यूटर पर मुफ़्त AI क्लाउड वाले से कम अच्छे पल ढूँढता है।
- **«Too many requests».** आपकी AI सर्विस का फ़्री प्लान अपनी सीमा तक पहुँच गया: इंतज़ार करें, या पेड प्लान या अकाउंट
  इस्तेमाल करें।
- **फ़ोन पर SMTV नहीं खुलता।** वही Wi-Fi, कोई VPN नहीं, फ़ायरवॉल में SMTV को इजाज़त दें — देखें [फ़ोन](phone.md)।
- **Windows: टर्मिनल `smtv` चलाने से मना करता है।** यह Smart App Control है; SMTV को उसके आइकन से खोलें।
- **विंडो का SMTV से कनेक्शन टूट गया।** विंडो बंद करें और SMTV फिर से खोलें।

रुकी हुई रिक्वेस्ट आगे बढ़ सकती है: **Continue** दबाएँ — SMTV उसी चरण से शुरू करता है और जो हो चुका है उसे दोबारा नहीं
करता।

## 3. समस्या की रिपोर्ट करें

फिर भी अटके हैं? हमें बताएँ — इससे सबको मदद मिलती है।

1. **Settings → Computer check → Report a problem** (समस्या की रिपोर्ट करें; **Report…** बटन, यह **Settings → About** में
   भी है), या फ़ेल हुई रिक्वेस्ट के नीचे वाला बटन।
2. SMTV दिखाता है कि रिपोर्ट में क्या जाता है: वर्ज़न, कंप्यूटर जाँच, सेटिंग्स और लॉग। **कुंजियाँ और टोकन हटा दिए जाते
   हैं**, आपका होम फ़ोल्डर `~` के रूप में दिखता है। लिंक और फ़ाइलों के नाम तब तक शामिल नहीं होते जब तक आप बॉक्स पर टिक न
   करें।
3. **Save and open GitHub** (सेव करें और GitHub खोलें) दबाएँ। SMTV आर्काइव सेव करता है, और ब्राउज़र में सारांश भरा हुआ एक
   नया issue खुलता है। आर्काइव उसमें खींचकर डालें और **Submit** दबाएँ।

SMTV अपने-आप कुछ नहीं भेजता। विंडो के बिना: टर्मिनल में `smtv report` चलाएँ। आप सीधे
[issue भी खोल सकते हैं](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml)।
