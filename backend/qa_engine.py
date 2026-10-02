"""
backend/qa_engine.py
====================
Natural Language Q&A Synthesis Engine for Krushi Mitra.

Generates clear, accurate, and distinct answers in English, Marathi, and Hindi
for any question asked by farmers about the 11 welfare schemes:
- Documents required
- Financial benefits & subsidies
- How to apply & portal links
- Eligibility criteria & personalized evaluation
- Reasons for ineligibility
- General scheme overview / about
"""

from typing import Any
import re

# 1. Documents required
DOC_KEYWORDS = {
    "document", "documents", "paper", "papers", "proof", "form", "paperwork",
    "certificate", "id proof", "record", "records", "7/12", "7 12",
    # Hindi
    "दस्तावेज", "दस्तावेज़", "कागजात", "कागज़ात", "डॉक्यूमेंट", "डॉक्यूमेंट्स",
    "प्रमाण पत्र", "प्रमाणपत्र", "कागद", "क्या कागद", "क्या दस्तावेज", "दस्तावेज क्या",
    "कौन से दस्तावेज", "कौन से कागजात", "कागजात क्या",
    # Marathi
    "कागदपत्र", "कागदपत्रे", "कागदपत्रांची", "दाखला", "डॉक्युमेंट", "डॉक्युमेंट्स",
    "कागदपत्रांची यादी", "काय काय लागेल", "काय कागदपत्रे", "कोणती कागदपत्रे",
    "कागदपत्रे काय", "कागदपत्र काय", "कागद काय",
}

# 2. Financial benefits, subsidy, payment, installment
MONEY_KEYWORDS = {
    "how much", "amount", "money", "rupees", "subsidy", "cost", "pay", "share",
    "percentage", "rate", "benefit", "benefits", "financial", "grant", "funds",
    "compensation", "installment",
    # Hindi
    "कितना", "कितने", "सब्सिडी", "लाभ", "फायदा", "फायदे", "राशि", "किस्त",
    "धनराशि", "अनुदान", "पैसा", "पैसे", "रुपये", "मुआवजा", "सहायता",
    "कितना पैसा", "कितनी सब्सिडी", "कितने रुपये", "क्या फायदा", "क्या लाभ",
    "लाभ क्या", "फायदा क्या", "कितनी राशि",
    # Marathi
    "किती", "पैसे", "रुपये", "अनुदान", "खर्च", "हप्ता", "फायदा", "फायदे",
    "लाभ", "नुकसान भरपाई", "सबसिडी", "मदत", "किती मिळतात", "किती मिळते",
    "किती रक्कम", "अनुदान किती", "काय फायदा", "काय फायदे", "काय लाभ",
    "लाभ काय", "फायदे काय",
}

# 3. How to apply, registration, portal, website
APPLY_KEYWORDS = {
    "how to apply", "where to apply", "how can i apply", "registration", "portal",
    "website", "process", "link", "online apply", "procedure", "steps", "submit",
    # Hindi
    "आवेदन कैसे", "कहाँ आवेदन", "आवेदन करना", "फॉर्म कैसे", "रजिस्ट्रेशन",
    "ऑनलाइन आवेदन", "अप्लाई कैसे", "पोर्टल", "वेबसाइट", "लिंक क्या है",
    "प्रक्रिया क्या", "आवेदन प्रक्रिया", "कहाँ जाना", "कहाँ संपर्क",
    # Marathi
    "अर्ज कसा", "कुठे अर्ज", "अर्ज करावा", "अर्ज करायचा", "फॉर्म कसा",
    "नोंदणी कशी", "पोर्टल", "वेबसाइट", "ऑनलाईन अर्ज", "अप्लाय कसा",
    "अप्लाय कसे", "अर्ज प्रक्रिया", "नोंदणी प्रक्रिया", "अर्ज कुठे",
    "अर्ज करण्यासाठी",
}

# 4. Eligibility & qualification (contains root and predicates in HI/MR)
ELIGIBILITY_KEYWORDS = {
    "eligible", "eligibility", "can i apply", "who can apply", "who is eligible",
    "criteria", "conditions", "qualify", "do i qualify", "can i get", "rules",
    "who qualifies", "am i",
    # Hindi
    "पात्र", "पात्रता", "पात्र हूँ", "पात्र है", "पात्र हैं", "क्या मैं पात्र",
    "किसे मिलेगा", "किसके लिए है", "कौन पात्र", "शर्तें क्या", "नियम क्या",
    "एलिजिबल हूँ", "एलिजिबल है", "मुझे मिलेगा क्या", "आवेदन कर सकता हूँ",
    "क्या मुझे मिलेगा", "पात्रता की शर्तें", "शर्तें", "नियम",
    # Marathi
    "पात्र", "पात्रता", "पात्र आहे", "पात्र आहेत", "मी पात्र", "कोण पात्र",
    "पात्र कोण", "कोणाला मिळते", "कोणासाठी आहे", "अटी काय", "शर्ती काय",
    "नियम काय", "एलिजिबल आहे", "मला मिळेल का", "मी अर्ज करू शकतो का",
    "पात्रतेच्या अटी", "अटी", "नियम",
}

# 5. Why ineligible / reasons
WHY_KEYWORDS = {
    "why not", "why am i not", "why ineligible", "reason for rejection", "why can't i",
    "why cannot", "what makes me ineligible", "why was i rejected",
    # Hindi — use multi-word phrases so single particles like 'का' or 'कैसे' don't match
    "क्यों नहीं", "पात्र क्यों नहीं", "कारण क्या है", "अपात्र क्यों", "क्यों नहीं मिला",
    "वजह क्या है", "कारण बताओ", "क्यों अपात्र",
    # Marathi — use multi-word phrases so 'का' doesn't falsely match on 'काय'
    "का नाही", "का अपात्र", "पात्र का नाही", "कारण काय आहे", "कारण काय",
    "कशामुळे नाही", "नाकारले का", "का मिळाले नाही", "अपात्र का",
}

# 6. General overview / what is the scheme
OVERVIEW_KEYWORDS = {
    "what is", "tell me about", "information about", "overview", "details of",
    "explain", "what does", "about scheme",
    # Hindi
    "क्या है", "के बारे में", "जानकारी दें", "जानकारी बताइए", "विवरण दें",
    "योजना क्या", "पूरी जानकारी", "विस्तार से बताएं",
    # Marathi
    "काय आहे", "बद्दल माहिती", "बद्दल सांगा", "माहिती द्या", "माहिती सांगा",
    "तपशील सांगा", "योजना काय", "माहिती काय", "सविस्तर सांगा",
}


def _has_any(text: str, kw_set: set) -> bool:
    """Check if any keyword phrase appears in lowercased text."""
    return any(k in text for k in kw_set)


def synthesize_answer(
    query: str,
    scheme: dict[str, Any],
    profile: dict[str, Any],
    eval_result: dict[str, Any],
    lang: str = "en",
    application_status: str = "open",
) -> str:
    """
    Synthesizes a short, precise, plain-language conversational answer
    tailored to the farmer's question and active farm profile.
    """
    raw = query.lower()
    scheme_id = scheme.get("scheme_id", "")

    name_dict = scheme.get("scheme_name", {})
    name = name_dict.get(lang) or name_dict.get("en", scheme_id)

    benefit_dict = scheme.get("benefit_text", {})
    benefit = benefit_dict.get(lang) or benefit_dict.get("en", "")

    docs_list = scheme.get("documents_required", {}).get(lang, [])
    if not docs_list:
        docs_list = scheme.get("documents_required", {}).get("en", [])
    
    docs_formatted = "\n".join(f"• {d}" for d in docs_list) if docs_list else (
        "• आधार कार्ड\n• ७/१२ उतारा\n• बँक पासबुक" if lang == "mr"
        else ("• आधार कार्ड\n• 7/12 भूमि रिकॉर्ड\n• बैंक पासबुक" if lang == "hi"
              else "• Aadhaar card\n• 7/12 land record\n• Bank passbook")
    )

    link = scheme.get("official_link", "mahadbt.maharashtra.gov.in")
    is_eligible = eval_result.get("eligible", True)
    note = eval_result.get("note", "")

    # Application status warning
    CLOSED_STATUSES = {"closed", "portal_closed", "cycle_based", "unconfirmed"}
    _status_warning = {
        "closed": {
            "en": "⚠️ Applications are currently CLOSED for this scheme. Check the official portal for reopening updates.",
            "hi": "⚠️ इस योजना के लिए आवेदन फिलहाल बंद हैं। पुनः खुलने के लिए आधिकारिक पोर्टल देखें।",
            "mr": "⚠️ या योजनेसाठी अर्ज सध्या बंद आहेत. पुन्हा सुरू होण्यासाठी अधिकृत पोर्टल तपासा.",
        },
        "portal_closed": {
            "en": "⚠️ MahaDBT portal is currently NOT accepting fresh applications for this scheme. It will reopen soon — check mahadbt.maharashtra.gov.in for updates.",
            "hi": "⚠️ महाडीबीटी पोर्टल अभी इस योजना के नए आवेदन स्वीकार नहीं कर रहा। जल्द खुलेगा — mahadbt.maharashtra.gov.in पर अपडेट देखें।",
            "mr": "⚠️ महाडीबीटी पोर्टल सध्या या योजनेसाठी नवीन अर्ज स्वीकारत नाही. लवकरच खुले होईल — mahadbt.maharashtra.gov.in तपासा.",
        },
        "cycle_based": {
            "en": "⚠️ This is a cycle-based scheme — applications are only accepted when a new government notification is issued. Check current Maharashtra notifications before applying.",
            "hi": "⚠️ यह चक्र-आधारित योजना है — आवेदन केवल तभी स्वीकार किए जाते हैं जब नई सरकारी अधिसूचना जारी हो। आवेदन से पहले वर्तमान महाराष्ट्र अधिसूचनाएं देखें।",
            "mr": "⚠️ ही चक्र-आधारित योजना आहे — नवीन शासन अधिसूचना जारी झाल्यावरच अर्ज स्वीकारले जातात. अर्ज करण्यापूर्वी सध्याच्या महाराष्ट्र अधिसूचना तपासा.",
        },
        "unconfirmed": {
            "en": "⚠️ The current application window for this scheme is not confirmed. Check mahadbt.maharashtra.gov.in or pgsindia-ncof.gov.in for the latest status before applying.",
            "hi": "⚠️ इस योजना की वर्तमान आवेदन विंडो की पुष्टि नहीं है। आवेदन से पहले mahadbt.maharashtra.gov.in पर नवीनतम स्थिति देखें।",
            "mr": "⚠️ या योजनेची सध्याची अर्ज विंडो निश्चित नाही. अर्ज करण्यापूर्वी mahadbt.maharashtra.gov.in वर नवीनतम स्थिती तपासा.",
        },
    }
    status_warn = ""
    if application_status in CLOSED_STATUSES:
        w = _status_warning.get(application_status, {})
        status_warn = w.get(lang) or w.get("en", "")

    # -----------------------------------------------------------------------
    # 1. WHY INELIGIBLE / REASON
    # -----------------------------------------------------------------------
    if _has_any(raw, WHY_KEYWORDS):
        if is_eligible:
            if lang == "mr":
                return (
                    f"✅ तुम्ही {name} साठी पात्र आहात!\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💰 योजनेचा लाभ: {benefit}"
                )
            elif lang == "hi":
                return (
                    f"✅ आप {name} के लिए पात्र हैं!\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💰 योजना का लाभ: {benefit}"
                )
            else:
                return (
                    f"✅ You qualify for {name}!\n\n"
                    f"📋 Reason: {note}\n\n"
                    f"💰 Benefit: {benefit}"
                )
        else:
            if lang == "mr":
                return (
                    f"❌ तुम्ही सध्या {name} साठी पात्र नाही.\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💡 टीप: तुमच्या प्रोफाइलमध्ये बदल केल्यास पात्रता बदलू शकते."
                )
            elif lang == "hi":
                return (
                    f"❌ आप वर्तमान में {name} के लिए पात्र नहीं हैं।\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💡 सुझाव: अपनी प्रोफ़ाइल अपडेट करने पर पात्रता बदल सकती है।"
                )
            else:
                return (
                    f"❌ You are currently NOT eligible for {name}.\n\n"
                    f"📋 Reason: {note}\n\n"
                    f"💡 Tip: Updating your farm profile may change your eligibility."
                )

    # -----------------------------------------------------------------------
    # 2. DOCUMENTS QUESTION
    # -----------------------------------------------------------------------
    if _has_any(raw, DOC_KEYWORDS):
        if lang == "mr":
            return (
                f"📄 **{name} साठी आवश्यक कागदपत्रे:**\n\n"
                f"{docs_formatted}\n\n"
                f"👉 अर्ज करण्यासाठी हे कागदपत्रे घेऊन {link} वर किंवा जवळच्या सीएससी केंद्रावर जा."
            )
        elif lang == "hi":
            return (
                f"📄 **{name} के लिए आवश्यक दस्तावेज़:**\n\n"
                f"{docs_formatted}\n\n"
                f"👉 आवेदन के लिए ये दस्तावेज़ लेकर {link} पर या नजदीकी सीएससी केंद्र पर जाएं।"
            )
        else:
            return (
                f"📄 **Documents required for {name}:**\n\n"
                f"{docs_formatted}\n\n"
                f"👉 Submit these documents at {link} or your nearest CSC center."
            )

    # -----------------------------------------------------------------------
    # 3. HOW TO APPLY QUESTION
    # -----------------------------------------------------------------------
    if _has_any(raw, APPLY_KEYWORDS):
        if lang == "mr":
            apply_text = (
                f"📝 **{name} साठी अर्ज कसा करावा:**\n\n"
                f"1️⃣ अधिकृत पोर्टल **{link}** वर जा किंवा जवळच्या सीएससी (CSC) केंद्रावर भेट द्या.\n"
                f"2️⃣ आधार कार्ड आणि ७/१२ उतारा सोबत ठेवा.\n"
                f"3️⃣ फॉर्म भरून आवश्यक कागदपत्रे अपलोड करा आणि पोचपावती घ्या."
            )
        elif lang == "hi":
            apply_text = (
                f"📝 **{name} के लिए आवेदन कैसे करें:**\n\n"
                f"1️⃣ आधिकारिक पोर्टल **{link}** पर जाएं या नजदीकी सीएससी केंद्र पर संपर्क करें।\n"
                f"2️⃣ आधार कार्ड और 7/12 भूमि रिकॉर्ड साथ रखें।\n"
                f"3️⃣ फॉर्म भरें, दस्तावेज़ अपलोड करें और पावती प्राप्त करें।"
            )
        else:
            apply_text = (
                f"📝 **How to apply for {name}:**\n\n"
                f"1️⃣ Visit the official portal: **{link}** or visit your nearest CSC center.\n"
                f"2️⃣ Keep your Aadhaar card and 7/12 land record ready.\n"
                f"3️⃣ Fill the application, upload documents, and save your receipt."
            )
        return f"{status_warn}\n\n{apply_text}".strip() if status_warn else apply_text

    # -----------------------------------------------------------------------
    # 4. MONEY / BENEFIT / SUBSIDY QUESTION
    # -----------------------------------------------------------------------
    if _has_any(raw, MONEY_KEYWORDS):
        elig_status = "✅" if is_eligible else "ℹ️"
        if lang == "mr":
            elig_text = f"तुमच्या शेतीसाठी पात्रता: {note}" if note else ""
            return (
                f"💰 **{name} अंतर्गत मिळणारा लाभ / अनुदान:**\n\n"
                f"{benefit}\n\n"
                f"{elig_status} {elig_text}".strip()
            )
        elif lang == "hi":
            elig_text = f"आपके खेत के लिए पात्रता: {note}" if note else ""
            return (
                f"💰 **{name} के तहत मिलने वाला लाभ / सब्सिडी:**\n\n"
                f"{benefit}\n\n"
                f"{elig_status} {elig_text}".strip()
            )
        else:
            elig_text = f"Eligibility for your farm: {note}" if note else ""
            return (
                f"💰 **Financial Benefit under {name}:**\n\n"
                f"{benefit}\n\n"
                f"{elig_status} {elig_text}".strip()
            )

    # -----------------------------------------------------------------------
    # 5. ELIGIBILITY / CRITERIA QUESTION
    # -----------------------------------------------------------------------
    if _has_any(raw, ELIGIBILITY_KEYWORDS):
        if is_eligible:
            if lang == "mr":
                return (
                    f"✅ **होय, तुम्ही {name} साठी पात्र आहात!**\n\n"
                    f"📋 **नियम व अट:** {note}\n\n"
                    f"💰 **मिळणारा लाभ:** {benefit}\n\n"
                    f"🌐 **अर्जाची लिंक:** {link}"
                )
            elif lang == "hi":
                return (
                    f"✅ **हाँ, आप {name} के लिए पात्र हैं!**\n\n"
                    f"📋 **नियम व शर्तें:** {note}\n\n"
                    f"💰 **मिलने वाला लाभ:** {benefit}\n\n"
                    f"🌐 **आवेदन लिंक:** {link}"
                )
            else:
                return (
                    f"✅ **Yes, you are eligible for {name}!**\n\n"
                    f"📋 **Criteria:** {note}\n\n"
                    f"💰 **Benefit:** {benefit}\n\n"
                    f"🌐 **Apply at:** {link}"
                )
        else:
            if lang == "mr":
                return (
                    f"❌ **सध्या तुम्ही {name} साठी पात्र नाही.**\n\n"
                    f"📋 **कारण:** {note}\n\n"
                    f"💡 **टीप:** प्रोफाइलमधील जमिनीचा तपशील अपडेट केल्यास पात्रता बदलू शकते."
                )
            elif lang == "hi":
                return (
                    f"❌ **वर्तमान में आप {name} के लिए पात्र नहीं हैं।**\n\n"
                    f"📋 **कारण:** {note}\n\n"
                    f"💡 **सुझाव:** अपनी प्रोफ़ाइल अपडेट करने पर पात्रता बदल सकती है।"
                )
            else:
                return (
                    f"❌ **You do not currently qualify for {name}.**\n\n"
                    f"📋 **Reason:** {note}\n\n"
                    f"💡 **Tip:** Updating your farm profile may change your eligibility."
                )

    # -----------------------------------------------------------------------
    # 6. OVERVIEW / ABOUT THE SCHEME (Default for general questions)
    # -----------------------------------------------------------------------
    status_emoji = "✅ पात्र" if is_eligible else "❌ सध्या अपात्र"
    status_emoji_hi = "✅ पात्र" if is_eligible else "❌ वर्तमान में अपात्र"
    status_emoji_en = "✅ Eligible" if is_eligible else "❌ Currently Not Eligible"

    if lang == "mr":
        return (
            f"🌾 **{name} — योजनेची माहिती:**\n\n"
            f"💰 **योजनेचा लाभ:** {benefit}\n\n"
            f"📋 **तुमची पात्रता स्थिती:** {status_emoji} ({note})\n\n"
            f"📄 **लागणारी कागदपत्रे:**\n{docs_formatted}\n\n"
            f"🌐 **अधिकृत पोर्टल:** {link}"
        )
    elif lang == "hi":
        return (
            f"🌾 **{name} — योजना का विवरण:**\n\n"
            f"💰 **योजना का लाभ:** {benefit}\n\n"
            f"📋 **आपकी पात्रता स्थिति:** {status_emoji_hi} ({note})\n\n"
            f"📄 **आवश्यक दस्तावेज़:**\n{docs_formatted}\n\n"
            f"🌐 **आधिकारिक पोर्टल:** {link}"
        )
    else:
        return (
            f"🌾 **{name} — Overview:**\n\n"
            f"💰 **Benefit:** {benefit}\n\n"
            f"📋 **Your Eligibility:** {status_emoji_en} ({note})\n\n"
            f"📄 **Required Documents:**\n{docs_formatted}\n\n"
            f"🌐 **Official Portal:** {link}"
        )
