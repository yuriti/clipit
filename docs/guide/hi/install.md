<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · **हिन्दी** · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 यह पेज अपने-आप अनुवाद किया गया है। इसे बेहतर बनाने में मदद करें: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [मूल पाठ: Русский](../install.md).

# SMTV इंस्टॉल करें

एक फ़ाइल डाउनलोड करें, उसे खोलें, और एक **SMTV** आइकन आ जाता है। SMTV को जो कुछ चाहिए, सब उसके अंदर है।
एडमिनिस्ट्रेटर पासवर्ड की ज़रूरत नहीं।

| आपका कंप्यूटर | डाउनलोड | साइज़ |
|---|---|---|
| **Windows 10 या 11** (64-बिट) | [Windows के लिए SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) | करीब 130 MB |
| **Mac** — Apple silicon (M1 और नए) या Intel, macOS 13+ | [Mac के लिए SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | करीब 270 MB |

सभी वर्ज़न और उनके चेकसम: [रिलीज़ पेज](https://github.com/yuriti/clipit/releases/latest)।

**पहली बार सिस्टम चेतावनी क्यों देता है।** SMTV के पास अभी डिजिटल साइन नहीं है। Windows का साइन थोड़ा बाद में आएगा,
macOS का जितनी जल्दी हो सके, और फिर यह चेतावनी चली जाएगी। SMTV का कोड खुला है: कोई भी पढ़ सकता है कि वह क्या करता है।

## Windows

1. **Windows के लिए SMTV** (फ़ाइल `SMTV-…-windows-x64-setup.exe`) डाउनलोड करें और उसे खोलें।
2. Windows एक नीली विंडो **«Windows protected your PC»** दिखाता है। **More info** दबाएँ, फिर **Run anyway**।
3. इंस्टॉलर दो-तीन सवाल पूछता है (भाषा, डेस्कटॉप पर आइकन) — **Next** और **Install** दबाएँ।
4. आख़िर में **Launch SMTV** पर टिक रहने दें और **Finish** दबाएँ। अगली बार SMTV को **Start** मेन्यू से (या डेस्कटॉप
   आइकन से) खोलें।

इंस्टॉलर SMTV को आपके अपने यूज़र फ़ोल्डर में रखता है; वह **Settings → Apps** में दिखता है, जहाँ से आप उसे हटा सकते हैं।

**बिना इंस्टॉल किए:** [ZIP फ़ाइल](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)
डाउनलोड करें, उसे कहीं भी अनज़िप करें (जैसे Documents में) और `SMTV` फ़ोल्डर में **SMTV.exe** खोलें। यह कॉपी खुद
अपडेट नहीं होती: नया वर्ज़न मतलब नई ZIP।

### Windows 11: Smart App Control

अगर **Smart App Control** चालू है (Windows Security → App & browser control), तो Windows बिना साइन वाले प्रोग्राम पूरी
तरह रोक देता है, और उन्हें चलने देने का कोई बटन नहीं है। SMTV के लिए Smart App Control बंद करने की ज़रूरत नहीं।
इसके बजाय SMTV को एक लाइन से इंस्टॉल करें — यह Smart App Control चालू होने पर भी काम करता है:
[टर्मिनल में एक लाइन](#अनुभवी-यूज़र्स-के-लिए-टर्मिनल-में-एक-लाइन)। जब SMTV साइन हो जाएगा, तो वहाँ डाउनलोड भी काम करेगा।

## Mac

1. **Mac के लिए SMTV** डाउनलोड करें। यह हर Mac के लिए एक ही फ़ाइल है, Apple silicon हो या Intel: SMTV आपके Mac के प्रोसेसर के लिए बना वर्ज़न खुद चलाता है।
2. डाउनलोड की हुई `.dmg` खोलें। एक विंडो खुलती है जिसमें SMTV और **Applications** फ़ोल्डर है: **SMTV** को खींचकर
   **Applications** पर छोड़ें।
3. **Applications** खोलें और **SMTV** पर डबल-क्लिक करें। macOS कहता है कि वह SMTV की जाँच नहीं कर सकता और उसे नहीं
   खोलता। **Done** दबाएँ।
4. **System Settings → Privacy & Security** खोलें और नीचे स्क्रॉल करें। «SMTV was blocked…» के पास **Open Anyway** दबाएँ,
   अपने Mac का पासवर्ड डालें और **Open** दबाएँ।
   macOS 14 पर एक छोटा रास्ता है: Applications में **SMTV** पर राइट-क्लिक → **Open** → **Open**।

सिर्फ़ पहली बार: उसके बाद SMTV आम क्लिक से खुलता है, Applications या Launchpad से। यही कदम `.dmg` के अंदर «How to
open» फ़ाइल में भी हैं।

## पहली शुरुआत

SMTV आपका कंप्यूटर जाँचता है और पहली क्लिप तक के तीन कदम दिखाता है। उनके नीचे वह **आपकी भाषा के लिए बोली पहचानने वाला
हिस्सा** देता है — वह हिस्सा जो स्ट्रीम की बोली को टेक्स्ट में बदलता है। यह डाउनलोड के अंदर नहीं है, क्योंकि हर भाषा को
अपना चाहिए (0.9–2.5 GB)। **Fix** (ठीक करें) दबाएँ और प्रगति देखें, या इसे छोड़ दें: पहली रिक्वेस्ट इसे खुद डाउनलोड कर
लेगी।

**आपको क्या चाहिए:** कम से कम 5 GB खाली जगह, 6 घंटे की स्ट्रीम के लिए 20 GB; इंटरनेट। ग्राफ़िक्स कार्ड की ज़रूरत नहीं।

## अनुभवी यूज़र्स के लिए: टर्मिनल में एक लाइन

वही SMTV, [uv](https://astral.sh/uv) से — Python प्रोग्राम के लिए एक छोटा आधिकारिक टूल — आपके यूज़र फ़ोल्डर में इंस्टॉल।
इसे **Linux** पर, **Smart App Control** के साथ, या अगर आपको टर्मिनल पसंद है तो इस्तेमाल करें। यह डाउनलोड किए गए ऐप की
तरह विंडो से अपडेट होता है।

**Windows:** **Start** दबाएँ, `PowerShell` टाइप करें, **Windows PowerShell** (नीली विंडो) खोलें, यह लाइन पेस्ट करें
(राइट क्लिक या Ctrl+V) और **Enter** दबाएँ:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

Smart App Control चालू होने पर इंस्टॉलर SMTV को python.org के साइन किए हुए Python पर इंस्टॉल करता है (वह इसे इंस्टॉल
करने को कह सकता है — मान जाएँ) और SMTV को उसी के ज़रिए चलाता है। अगर टर्मिनल कहे कि वह `smtv` नहीं चला सकता, तो
**SMTV** आइकन इस्तेमाल करें।

**Mac या Linux:** **Terminal** खोलें (Mac पर: Cmd+Space, `Terminal` टाइप करें, Enter), यह लाइन पेस्ट करें और **Enter**
दबाएँ:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

तब तक इंतज़ार करें जब तक वह न कहे कि काम हो गया (2–10 मिनट)। SMTV अपने-आप खुल जाता है; **SMTV** आइकन Windows पर Start
मेन्यू में, Mac पर Applications में, Linux पर ऐप्लिकेशन मेन्यू में है। इस रास्ते में SMTV पहली बार **ffmpeg** (वीडियो
टूल) को **Fix** से इंस्टॉल करने का सुझाव देता है; ऊपर वाले डाउनलोड में यह पहले से अंदर है।

दोनों इंस्टॉलर छोटे और खुले हैं: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh)।

## अगर सिस्टम चेतावनी दे

- **Windows: «Windows protected your PC»** (SmartScreen)। **More info** दबाएँ, फिर **Run anyway**।
- **Windows 11: Smart App Control SMTV को रोकता है।** जब तक SMTV साइन नहीं हो जाता,
  [टर्मिनल में एक लाइन](#अनुभवी-यूज़र्स-के-लिए-टर्मिनल-में-एक-लाइन) इस्तेमाल करें।
- **Windows: फ़ायरवॉल पूछता है** कि क्या SMTV नेटवर्क इस्तेमाल कर सकता है। **प्राइवेट** नेटवर्क के लिए इजाज़त दें: फ़ोन
  पर खोलने के लिए SMTV को इसकी ज़रूरत है। अगर फ़ोन की ज़रूरत नहीं, तो मना करना भी ठीक है।
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» या «developer cannot be verified»। **System Settings →
  Privacy & Security** खोलें, नीचे स्क्रॉल करें और SMTV के पास **Open Anyway** दबाएँ।
- **Mac: «SMTV would like to accept incoming connections»** — अगर आप फ़ोन पर SMTV इस्तेमाल करना चाहते हैं, तो इजाज़त दें।
- **एंटीवायरस** शिकायत करता है? SMTV नया है और अभी साइन नहीं हुआ, इसलिए कुछ एंटीवायरस उससे सावधान रहते हैं। उसका कोड
  खुला है, और हर फ़ाइल के चेकसम [रिलीज़ पेज](https://github.com/yuriti/clipit/releases/latest) पर हैं
  (`SHA256SUMS.txt`)।

आगे: [आपकी पहली क्लिप](first-clip.md)।
