"""
backend/qa_engine.py
====================
Natural Language Q&A Synthesis Engine for Krushi Mitra.

Generates clear, simple, short, and friendly explanations in English, Marathi, and Hindi
for any simple or complex question asked by farmers.
"""

from typing import Any


DOC_KEYWORDS = {
    "document", "documents", "paper", "papers", "proof", "form", "require", "required",
    "needed", "need", "paperwork", "certificate", "id proof", "record", "records",
    "कागदपत्र", "कागदपत्रे", "दाखला", "कागद", "दस्तावेज़", "दस्तावेज", "कागजात", "प्रमाण",
    "कागद काय", "काय लागते", "काय लागेल", "प्रमाणपत्र",
    "दस्तावेज़ क्या", "क्या चाहिए", "कागज़ात",
}

MONEY_KEYWORDS = {
    "how much", "amount", "money", "rupees", "subsidy", "cost", "pay", "share",
    "percentage", "rate", "benefit", "financial", "grant", "funds", "compensation",
    "किती", "पैसे", "रुपये", "अनुदान", "खर्च", "हप्ता", "फायदा", "नुकसान भरपाई",
    "किती मिळते", "किती रक्कम", "अनुदान किती",
    "कितना", "कितने", "सब्सिडी", "लाभ", "राशि", "किस्त", "धनराशि", "अनुदान कितना",
}

ELIGIBILITY_KEYWORDS = {
    "eligible", "eligibility", "can i", "qualify", "am i", "apply", "get", "who can",
    "who is eligible", "criteria", "conditions", "requirement", "is i eligible",
    "पात्र", "पात्रता", "मिळेल", "मिळेल का", "लागू", "अर्ज करू शकतो",
    "मला मिळेल का", "मी घेऊ शकतो का", "अटी काय",
    "मिलेगा", "मिलेगा क्या", "आवेदन कर सकता", "मुझे मिलेगा", "पात्रता क्या है",
}

APPLY_KEYWORDS = {
    "how to apply", "where to apply", "portal", "website", "process", "link",
    "registration", "online", "offline", "submit", "procedure", "steps",
    "अर्ज कसा", "कुठे अर्ज", "नोंदणी कशी", "पोर्टल", "वेबसाइट", "अर्ज प्रक्रिया",
    "कुठे नोंदणी", "ऑनलाईन अर्ज",
    "आवेदन कैसे", "कहाँ आवेदन", "रजिस्ट्रेशन", "ऑनलाइन आवेदन",
}

WHY_KEYWORDS = {
    "why", "reason", "explain", "because", "cause", "what is the reason", "how come",
    "why not", "why am i not", "why can't", "why cannot", "what makes",
    "का", "कारण", "कशामुळे", "का नाही", "कसे",
    "क्यों", "कारण बताएं", "क्यों नहीं", "वजह", "कैसे",
}


def synthesize_answer(
    query: str,
    scheme: dict[str, Any],
    profile: dict[str, Any],
    eval_result: dict[str, Any],
    lang: str = "en",
    application_status: str = "open",
) -> str:
    """
    Synthesizes a short, simple, plain-language conversational answer
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
    docs_str = ", ".join(docs_list) if docs_list else (
        "Aadhaar Card, 7/12 land record, bank passbook" if lang == "en"
        else ("आधार कार्ड, ७/१२ उतारा, बँक पासबुक" if lang == "mr"
              else "आधार कार्ड, 7/12 भूमि रिकॉर्ड, बैंक पासबुक")
    )

    link = scheme.get("official_link", "mahadbt.maharashtra.gov.in")
    is_eligible = eval_result.get("eligible", True)
    note = eval_result.get("note", "")

    # --- Application status warning banner (shown for apply-intent answers) ---
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

    def _get_status_warning() -> str:
        if application_status in CLOSED_STATUSES:
            w = _status_warning.get(application_status, {})
            return w.get(lang) or w.get("en", "")
        return ""

    # Helper: check if ANY keyword from a set appears in the raw query
    def has_any(kw_set: set) -> bool:
        return any(k in raw for k in kw_set)

    # 1. Documents question
    if has_any(DOC_KEYWORDS):
        if lang == "mr":
            return (
                f"📄 {name} साठी आवश्यक कागदपत्रे:\n{docs_str}\n\n"
                f"तुम्ही {link} वर किंवा जवळच्या सीएससी केंद्रावर अर्ज करू शकता."
            )
        elif lang == "hi":
            return (
                f"📄 {name} के लिए आवश्यक दस्तावेज़:\n{docs_str}\n\n"
                f"आप {link} पर या नजदीकी सीएससी केंद्र पर आवेदन कर सकते हैं।"
            )
        else:
            return (
                f"📄 Documents required for {name}:\n{docs_str}\n\n"
                f"Applications can be submitted at {link} or your nearest CSC center."
            )

    # 2. How to apply question
    if has_any(APPLY_KEYWORDS):
        status_warn = _get_status_warning()
        if lang == "mr":
            apply_text = (
                f"📝 {name} साठी अर्ज करणे सोपे आहे:\n"
                f"1️⃣ {link} या अधिकृत पोर्टलवर जा.\n"
                f"2️⃣ आधार कार्ड व ७/१२ उतारा तयार ठेवा.\n"
                f"3️⃣ किंवा जवळच्या सीएससी केंद्रावर भेट द्या."
            )
        elif lang == "hi":
            apply_text = (
                f"📝 {name} के लिए आवेदन कैसे करें:\n"
                f"1️⃣ आधिकारिक पोर्टल {link} पर जाएं।\n"
                f"2️⃣ आधार कार्ड और 7/12 भूमि रिकॉर्ड तैयार रखें।\n"
                f"3️⃣ या नजदीकी सीएससी केंद्र पर जाएं।"
            )
        else:
            apply_text = (
                f"📝 How to apply for {name}:\n"
                f"1️⃣ Visit the official portal: {link}\n"
                f"2️⃣ Keep your Aadhaar Card and 7/12 land record ready.\n"
                f"3️⃣ Or visit your nearest Gram Panchayat / CSC center."
            )
        return f"{status_warn}\n\n{apply_text}".strip() if status_warn else apply_text

    # 3. Money / Subsidy / How much question
    if has_any(MONEY_KEYWORDS):
        elig_status = "✅" if is_eligible else "❌"
        if lang == "mr":
            elig_text = f"तुमच्या शेतीसाठी: {note}" if note else ""
            return f"{elig_status} {name} अंतर्गत लाभ:\n{benefit}\n\n{elig_text}".strip()
        elif lang == "hi":
            elig_text = f"आपके खेत के लिए: {note}" if note else ""
            return f"{elig_status} {name} के तहत लाभ:\n{benefit}\n\n{elig_text}".strip()
        else:
            elig_text = f"For your farm profile: {note}" if note else ""
            return f"{elig_status} Benefit under {name}:\n{benefit}\n\n{elig_text}".strip()

    # 4. Why / Reason question (why am I eligible / not eligible)
    if has_any(WHY_KEYWORDS):
        if is_eligible:
            if lang == "mr":
                return (
                    f"✅ तुम्ही {name} साठी पात्र आहात!\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💰 लाभ: {benefit}"
                )
            elif lang == "hi":
                return (
                    f"✅ आप {name} के लिए पात्र हैं!\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💰 लाभ: {benefit}"
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

    # 5. Eligibility question (am I eligible, can I apply, do I qualify)
    if has_any(ELIGIBILITY_KEYWORDS):
        if is_eligible:
            if lang == "mr":
                return (
                    f"✅ होय, तुम्ही {name} साठी पात्र आहात!\n\n"
                    f"📋 {note}\n\n"
                    f"💰 लाभ: {benefit}"
                )
            elif lang == "hi":
                return (
                    f"✅ हाँ, आप {name} के लिए पात्र हैं!\n\n"
                    f"📋 {note}\n\n"
                    f"💰 लाभ: {benefit}"
                )
            else:
                return (
                    f"✅ Yes, you qualify for {name}!\n\n"
                    f"📋 {note}\n\n"
                    f"💰 Benefit: {benefit}"
                )
        else:
            if lang == "mr":
                return (
                    f"❌ सध्या तुम्ही {name} साठी पात्र नाही.\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💡 प्रोफाइल अपडेट केल्यास पात्रता बदलू शकते."
                )
            elif lang == "hi":
                return (
                    f"❌ वर्तमान में आप {name} के लिए पात्र नहीं हैं।\n\n"
                    f"📋 कारण: {note}\n\n"
                    f"💡 प्रोफ़ाइल अपडेट करने पर पात्रता बदल सकती है।"
                )
            else:
                return (
                    f"❌ You do not currently qualify for {name}.\n\n"
                    f"📋 Reason: {note}\n\n"
                    f"💡 Updating your profile may change your eligibility."
                )

    # 6. Default structured summary — always gives useful info regardless of query
    if is_eligible:
        if lang == "mr":
            return (
                f"✅ {name}\n\n"
                f"💰 लाभ: {benefit}\n\n"
                f"📋 तुमच्यासाठी: {note}\n\n"
                f"🌐 अर्जासाठी: {link}"
            )
        elif lang == "hi":
            return (
                f"✅ {name}\n\n"
                f"💰 लाभ: {benefit}\n\n"
                f"📋 आपके लिए: {note}\n\n"
                f"🌐 आवेदन करें: {link}"
            )
        else:
            return (
                f"✅ {name}\n\n"
                f"💰 Benefit: {benefit}\n\n"
                f"📋 For your profile: {note}\n\n"
                f"🌐 Apply at: {link}"
            )
    else:
        if lang == "mr":
            return (
                f"❌ {name} — सध्या पात्र नाही\n\n"
                f"📋 कारण: {note}\n\n"
                f"💰 योजनेचा लाभ: {benefit}\n\n"
                f"💡 प्रोफाइल अपडेट केल्यास पात्रता बदलू शकते."
            )
        elif lang == "hi":
            return (
                f"❌ {name} — वर्तमान में अपात्र\n\n"
                f"📋 कारण: {note}\n\n"
                f"💰 योजना का लाभ: {benefit}\n\n"
                f"💡 प्रोफ़ाइल अपडेट करने पर पात्रता बदल सकती है।"
            )
        else:
            return (
                f"❌ {name} — Currently not eligible\n\n"
                f"📋 Reason: {note}\n\n"
                f"💰 Scheme benefit: {benefit}\n\n"
                f"💡 Tip: Updating your profile may change your eligibility."
            )
