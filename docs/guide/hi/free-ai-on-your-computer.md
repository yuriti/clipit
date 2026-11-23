<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · **हिन्दी** · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 यह पेज अपने-आप अनुवाद किया गया है। इसे बेहतर बनाने में मदद करें: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# आपके कंप्यूटर पर मुफ़्त AI

AI सीधे आपके कंप्यूटर पर, मुफ़्त में चल सकता है: कुछ भी बाहर नहीं जाता, और कोई भुगतान नहीं। आपको AI मॉडल चलाने वाला
एक प्रोग्राम — **Ollama** या **LM Studio** — और एक मॉडल चाहिए, जैसे **Qwen**। SMTV प्रोग्राम को खुद ढूँढ लेता है।

**सच कहें तो:** घरेलू कंप्यूटर पर चलने वाले मॉडल क्लाउड वालों से कमज़ोर होते हैं, इसलिए क्लिप खराब बनती हैं, और सुझाए
गए मॉडलों में से कोई भी अभी SMTV के साथ टेस्ट नहीं हुआ है। अगर नतीजा निराश करे, तो [अकाउंट](account.md) या
[एक कुंजी](get-a-key.md) आज़माएँ।

## 1. कौन-सा मॉडल आपके कंप्यूटर पर चलेगा

मायने रखती है आपके ग्राफ़िक्स कार्ड की **वीडियो मेमोरी** (Apple silicon वाले Mac पर: पूरी मेमोरी)।

| वीडियो मेमोरी | मॉडल | डाउनलोड | नोट |
|---|---|---|---|
| 8 GB से कम | — | — | बहुत कम: अकाउंट या कुंजी इस्तेमाल करें |
| 8 GB | `qwen3:8b` | 5.2 GB | सबसे हल्का जो ठीक-ठाक काम करता है |
| 10–12 GB | `qwen3-vl:8b` या `gemma3:12b` | 6.1 / 8.1 GB | ये वीडियो के फ़्रेम भी देखते हैं |
| 16 GB और ज़्यादा | `qwen3:14b` | 9.3 GB | चारों में सबसे अच्छा |

7B («7 बिलियन») से छोटे मॉडल की सलाह नहीं दी जाती: वे ऐसे जवाब बिगाड़ देते हैं जिनकी SMTV को ज़रूरत है।

**अपनी वीडियो मेमोरी कैसे पता करें:**
- **Windows:** Ctrl+Shift+Esc दबाएँ → **Performance** → **GPU** → **Dedicated GPU memory**।
- **Mac:** Apple मेन्यू → **About This Mac** → **Memory**। Mac अपनी मेमोरी AI के साथ बाँटता है: 16 GB हो तो
  `qwen3:8b` लें, 32 GB या ज़्यादा हो तो `qwen3:14b`।

## 2a. Ollama (सबसे आसान)

1. [ollama.com/download](https://ollama.com/download) से Ollama डाउनलोड करें और किसी भी प्रोग्राम की तरह इंस्टॉल करें।
   यह अपने-आप शुरू होता है और घड़ी के पास रहता है।
2. SMTV में: **Settings → AI → Free, on this computer → Find on this computer** (सेटिंग्स → AI → मुफ़्त, इस कंप्यूटर
   पर → इस कंप्यूटर पर ढूँढें)। SMTV Ollama को ढूँढ लेता है।
3. सूची में **Ollama** खोलें: SMTV सुझाए गए मॉडल उनके साइज़ के साथ दिखाता है। ऊपर की टेबल वाले मॉडल के पास **Download**
   (डाउनलोड) दबाएँ और इंतज़ार करें (5–10 GB)।
4. हो गया। SMTV अपने चरणों के लिए वह मॉडल खुद चुन लेता है।

SMTV हर रिक्वेस्ट के लिए Ollama की मेमोरी ऐसे सेट करता है कि स्ट्रीम का पूरा टेक्स्ट उसमें आ जाए; आपको Ollama की
सेटिंग्स बदलने की ज़रूरत नहीं।

## 2b. LM Studio

1. [lmstudio.ai/download](https://lmstudio.ai/download) से LM Studio डाउनलोड करें और इंस्टॉल करें।
2. LM Studio में **Discover** खोलें, **Qwen3 8B** (या टेबल के हिसाब से 14B) खोजें और **Download** दबाएँ।
3. **Developer** टैब खोलें और **Start server** चालू करें (यह पोर्ट 1234 पर सुनता है)। मॉडल वहीं लोड करें।
4. SMTV में: **Settings → AI → Free, on this computer → Find on this computer**। SMTV LM Studio को ढूँढ लेता है।

## 3. क्लिप बनाएँ

SMTV को एक [वीडियो फ़ाइल](first-clip.md) दें। Twitch या YouTube के लिंक के लिए मुफ़्त AI के साथ भी [अकाउंट](account.md)
चाहिए: रिकॉर्डिंग अकाउंट ही लाता है।

मुफ़्त AI क्लाउड वाले से धीमा काम करता है; लंबी स्ट्रीम में कुछ घंटे लग सकते हैं। कंप्यूटर चालू रहने दें।
