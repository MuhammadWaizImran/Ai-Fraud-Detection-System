 # 🏛️ FINRA AI Fraud Surveillance System — Complete Project Guide
### (Pure Functional Guide: What It Is, Why It Exists, and Exactly What It Does)

---

## 🎯 1. What is this Project? (Simple Overview)

Yeh project ek **AI-Powered Financial Security & Surveillance System** hai. 

Aasan lafzon mein: **Jaise kisi baray mall ya bank mein CCTV camera aur smart security guards hotay hain jo chori ya mashkook harkat ko foran pakad letay hain, yeh project bilkul usi tarah stock market aur crypto exchanges par hone wali chori, heera-pheri aur fraud ko live (real-time) pakadta hai.**

Financial markets mein har second hazaron-lakhon orders aate aur jaate hain. Kuch chalak traders aur automated computer bots market ko manipulate karke aam logon ke paise loot letay hain. Yeh platform un sab par 24/7 nazar rakhta hai aur jaise hi koi galat trade aati hai, usay foran pakad kar alarm baja deta hai.

---

## ⚠️ 2. Why Was This Project Built? (The Real-World Problem)

Pehle zamane mein (aur aaj bhi boht si purani exchanges mein) fraud pakadne ka tareeqa boht purana tha:
1. **Boht Ziyada Der Se Pata Chalna (T+1 Delay)**: 
   Purane systems din khatam hone ke baad ya agle din reports check karte thay. Lekin tab tak fraud karne wala market ko loot chuka hota tha aur apna paisa nikal kar bhaag chuka hota tha.
2. **Purane Rules Ko Dhoka Dena Aasan Tha**: 
   Purane system sirf itna dekhte thay ke *"agar order $100,000 se bara ho toh check karo"*. Fraud karne walay is rule ko samajh kar $10,000 ke 10 alag alag chhotay orders daal dete thay aur bach nikalte thay.
3. **Boht Ziyada Jhootay Alarms (False Positives)**: 
   Purane rules 100 mein se 90 baar bekaar alarms baja dete thay, jis se security team thak jaati thi aur asal chor bach nikalta tha.

### 💡 Is Project Ne Is Problem Ko Kaise Hal Kiya?
- **Real-Time Speed**: Yeh din khatam hone ka intezar nahi karta. Trade aane ke **ek second ke hazarwen hissay (sub-millisecond)** ke andar yeh bata deta hai ke trade theek hai ya fraud.
- **Smart AI Brain**: Yeh sirf order ka size nahi dekhta, balki trader ka purana rawaiya, order cancel karne ki speed, aur market ka behavior sab aik sath check karta hai.
- **Consensus System**: 3 alag-alag AI models mil kar faisla karte hain, taake koi jhoota alarm na bajay.

---

## 🕵️ 3. Kaunse 5 Tarah Ke Frauds Yeh System Pakadta Hai?

Market mein hone wali 5 sab se bari heera-pheriyan jinhein yeh system pehchanta hai:

### 1. 👻 Spoofing (Jhoota Dikhawa)
- **Harkat**: Trader boht bara khareedari (Buy) ka order book mein daalta hai taake doosray log samjhein ke is coin/share ki boht demand hai aur price ooper jaye gi. Lekin jaisay hi price ooper aati hai, woh apna order execute hone se pehle foran cancel kar deta hai aur doosri taraf se profit kama kar nikal jata hai.
- **System Kaise Pakadta Hai**: System dekhta hai ke is trader ne order daal kar foran cancel kyun kiya? Iska cancel-to-trade ratio kitna ajeeb hai?

### 2. 🌊 Wash Trading (Khud Ko Hi Bechna)
- **Harkat**: Ek hi shakhs ya affiliated accounts aapas mein hi bar bar wahi coin khareedtay aur bechtay hain. Asal mein koi maal doosray ke paas nahi jaata, sirf market mein yeh dikhana hota hai ke yahan boht trading ho rahi hai taake naye log phans saken.
- **System Kaise Pakadta Hai**: System check karta hai ke buyer aur seller aapas mein connected hain aur volume achanak bina kisi waja ke fake tor par barh raha hai.

### 3. 🥞 Layering (Fake Jaal Bichana)
- **Harkat**: Trader alag-alag price levels par aik ke baad aik kayi fake orders ki layers (tehein) laga deta hai taake market ka balance hil jaye aur market doosron ko gumrah karay.
- **System Kaise Pakadta Hai**: System 1 minute ke andar aane walay orders ki high speed aur cancellation pattern ko pakad leta hai.

### 4. 🚀 Volume Spike / Pump & Dump (Artificial Hawa Bharna)
- **Harkat**: Kuch log mil kar achanak aam routine se 20 guna ya 50 guna bara volume daltay hain taake price rocket ki tarah ooper jaye. Jab aam log dekh kar khareedne aate hain, toh yeh chalak log apna maal mehnge daam bech kar bhaag jatay hain aur market crash ho jati hai.
- **System Kaise Pakadta Hai**: System 10-minute ke normal average volume se compare karta hai. Agar achanak abnormal spike aaye toh foran warning generate kar deta hai.

### 5. 📈 Marking the Close (Price Manipulation)
- **Harkat**: Jab market band hone ka waqt kareeb aata hai, toh jan-bujh kar ghalat qeemat par trade execute ki jati hai taake closing price ghalat print ho, kyunke agle din ke boht se contracts closing price par depend karte hain.
- **System Kaise Pakadta Hai**: System fair market price aur order execution price ke farq ko monitor karke off-market trades ko pakad leta hai.

---

## ⚙️ 4. How the Whole System Works (Step-by-Step Flow)

Jab bhi market chal rahi hoti hai, system mein yeh chaar marhalay (stages) hotay hain:

```text
  [Market Se Trade Aayi]
            │
            ▼
  [Step 1: Safai Aur Check (Lakehouse)] ➔ Ghalat data bahar, saaf data andar
            │
            ▼
  [Step 2: 10 Nishaniyan Check Karna]   ➔ Cancel speed, volume, trader ka purana record
            │
            ▼
  [Step 3: 3 AI Models Ka Faisla]       ➔ Teenon models apna vote dete hain
            │
            ▼
  [Step 4: Result & Action]
       ├── 🟢 Score < 0.50   ➔ SAFE (Order paas ho gaya)
       ├── 🟡 Score 0.50-0.85 ➔ SUSPICIOUS (Nazar rakho)
       └── 🚨 Score >= 0.85  ➔ FRAUD (Alarm baje ga, webhook alert jayega, globe par light chamke gi)
```

---

## 🌐 5. Website / Dashboard Par Kya-Kya Cheezein Hain?

Jab aap website open karte hain (`http://localhost:3000/index.html`), aapko samnay yeh ahem cheezein milti hain:

### 1. Top KPI Cards (Main Statistics)
- **Total Gold Lakehouse Trades**: System mein store 150,000 historical records ka base data, jo har naye aane walay order ke sath live barhta rehta hai (e.g. `150,150+`).
- **Total Frauds Intercepted**: Ab tak system ne kitne real frauds pakday hain (e.g. `22,870+`).
- **Gold Anomaly Rate**: Market mein fraud ka overall percentage (e.g. `15.24%`).
- **AI Latency**: AI ko ek trade check karne mein kitna waqt laga (`0.42 ms` — yaani ek second ka chhota hissa).
- **Monitored Trader Entities**: Total 200 traders jin par system musalsal nazar rakh raha hai.

### 2. 3D Interactive World Globe (Three.js)
- Samnay ek khubsurat 3D Earth Globe ghoom raha hota hai jis par dunya ke ahem financial shehar (New York, London, Tokyo, Singapore, Frankfurt, Dubai) mark kiye gaye hain.
- **Asal Feature**: Jaisay hi kisi shehar se koi bara Fraud order aata hai, us shehar ke ooper se **laal rang ki 3D shockwave roshni** phoot-ti hai aur screen par alarm flashing shuru ho jati hai.

### 3. Dynamic Charts (Graph aur Analytics)
- **Live Risk Stream**: Ek live chalta hua line graph jo har aane wali trade ka risk score plot karta hai. Agar line red line (0.85) ko chhu lay toh iska matlab fraud hai.
- **TreeSHAP Polar Ring**: Ek gol doughnut chart jo batata hai ke is trade mein sab se bara shak kis cheez par hua (Volume zyada tha? Ya cancellation zyada thi?).
- **Attack Distribution Bars**: Right side par 5 colored bars hain jo batatay hain ke market mein kaunsa fraud kitni tadaad mein ho raha hai.

### 4. Live Order Ledger (Records Ka Table)
- Har aane wali trade live is table mein add hoti hai:
  - Trader ID kaunsi hai?
  - Symbol kaunsa hai (Bitcoin, Ethereum, Solana)?
  - Price aur Volume kya hai?
  - Verdict kya aaya: **SAFE (Green)**, **SUSPICIOUS (Yellow)**, ya **FRAUD (Red)**?
- Aap kisi bhi waqt search kar sakte hain ya buttons daba kar sirf "Fraud Only" trades dekh sakte hain.

### 5. 🤖 AI Compliance Copilot (In-Browser Smart Chatbot)
- Table mein kisi bhi trade row par click karein, side se **AI Copilot** khul jata hai.
- Yeh aam zaban mein investigator ko batata hai:
  - *"Is trade mein trader ne 12 seconds mein 15 orders dale aur 85% cancel kardiye. Is waja se yeh Spoofing hai."*
  - *"FINRA Rule 2010 aur 5210 ke tehat is trader ka account freeze karne ki recommendation hai."*

---

## 📊 6. Power BI aur Reporting Side Par Kya Hai?

Auditers aur high-level executives ke liye platform ke sath Power BI templates aur Web 3D Surveillance dashboards shamil hain:
- **Trader Risk Exposure**: Kaunse traders consistently mashkook hain aur watchlist par hone chahiyein.
- **Loss Prevention Calculator**: System ne market ka kitna lakh/crore rupay ka nuqsan hone se bachaya.
- **Regulatory Compliance Audit Trail**: Har pakray gaye fraud ka legal evidence record jo court ya regulator ko pesh kiya ja sakta hai.

---

## 🏆 7. Summary: Is Project Ka Asal Impact Kya Hai?

Yeh platform financial market aur crypto venues ko ek **khud-mukhtar (autonomous) digital police** faraham karta hai:
1. **Paisa Lootne Se Bachata Hai**: Retail investors ka paisa fake volume aur pump-and-dump se mehfooz rehta hai.
2. **Ghanton Ka Kaam Seconds Mein**: Jo audit pehle teams ko karne mein 24 ghantay lagte thay, yeh computer sub-millisecond mein complete karta hai.
3. **Transparent & Trustworthy**: Sirf yeh nahi kehta ke fraud hai, balki proof aur reason (explainability) ke sath dikhata hai.
4. **100% Connected & Real**: 150,000 real lakehouse records ke sath linked hai aur har aane wali live trade ko genuine tareeqay se process karta hai.
