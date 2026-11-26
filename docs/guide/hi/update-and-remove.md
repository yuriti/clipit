<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · **हिन्दी** · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 यह पेज अपने-आप अनुवाद किया गया है। इसे बेहतर बनाने में मदद करें: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [मूल पाठ: Русский](../update-and-remove.md).

# अपडेट करना और हटाना

## अपडेट

SMTV दिन में एक बार नया वर्ज़न देखता है (आप इसे बंद कर सकते हैं)। जब नया वर्ज़न हो, तो वह **Version … is available**
(वर्ज़न … उपलब्ध है) दिखाता है: **Update** (अपडेट) दबाएँ।

- SMTV बंद होता है, अपडेट होता है और अपने-आप फिर खुल जाता है, आमतौर पर एक मिनट के अंदर।
- अगर कोई रिक्वेस्ट चल रही है, तो अपडेट उसके खत्म होने तक इंतज़ार करता है — या **Stop the jobs and update** (काम रोकें
  और अपडेट करें) दबाएँ; बाद में **Continue** उन्हें उसी चरण से आगे बढ़ाता है।
- अगर नया वर्ज़न शुरू नहीं होता, तो पिछला अपने-आप वापस आ जाता है।
- नए वर्ज़न SMTV के लेखकों द्वारा साइन किए जाते हैं; इंस्टॉल करने से पहले SMTV साइन की जाँच करता है।

अपडेट से जुड़ी हर चीज़ **Settings → Computer check → Updates** (सेटिंग्स → कंप्यूटर जाँच → अपडेट) में है।

Windows या Mac के लिए SMTV डाउनलोड किया था? **Update** (अपडेट) नया इंस्टॉलर डाउनलोड करता है, उसे जाँचता है और खोलता
है: इंस्टॉल वहीं पूरा करें (Mac पर नए SMTV को खींचकर Applications पर छोड़ें और **Replace** दबाएँ)। ZIP वाली Windows
कॉपी खुद अपडेट नहीं होती: [रिलीज़ पेज](https://github.com/streammomenttv/smtv/releases/latest) से नई ZIP डाउनलोड करें।

SMTV किसी और तरीके से इंस्टॉल किया था? Docker में नया वर्ज़न एक नई इमेज है; देखें [एडवांस्ड यूज़र्स के लिए](../../advanced.md#docker)।

## हटाना

**Settings → Computer check → Remove SMTV from this computer** (इस कंप्यूटर से SMTV हटाएँ; **Remove…** बटन) प्रोग्राम और
SMTV आइकन हटा देता है। आपकी क्लिप बनी रहती हैं — उन्हें भी हटाने के लिए **Also remove clips, jobs, settings and keys**
(क्लिप, काम, सेटिंग्स और कुंजियाँ भी हटाएँ) पर टिक करें।

Windows या Mac के लिए SMTV डाउनलोड किया था? प्रोग्राम को सिस्टम के तरीके से हटाएँ (ऊपर वाला बटन सिर्फ़ क्लिप और
सेटिंग्स हटाता है, अगर आप उन पर टिक करें):

- **Windows:** **Settings → Apps → Installed apps → SMTV → Uninstall**। ZIP वाली कॉपी: उसका फ़ोल्डर डिलीट कर दें।
- **Mac:** **SMTV** को **Applications** से खींचकर **Trash** में डालें।

टर्मिनल में एक लाइन से इंस्टॉल किया था? विंडो के बिना, टर्मिनल में:

```bash
smtv uninstall
```

क्लिप और सेटिंग्स भी हटाने के लिए `--data` जोड़ें। जो प्रोग्राम आपने खुद इंस्टॉल किए (Ollama, LM Studio) वे बने रहते हैं:
उन्हें किसी भी दूसरे प्रोग्राम की तरह हटाएँ।
