"""
backend/qa_engine.py
====================
Natural Language Q&A Synthesis Engine for Krushi Mitra.

Generates clear, simple, short, and friendly explanations in English, Marathi, and Hindi
for any simple or complex question asked by farmers.
"""

from typing import Any


DOC_KEYWORDS = {
    "document", "documents", "paper", "papers", "proof", "form", "require",
    "कागदपत्र", "कागदपत्रे", "दाखला", "कागद", "दस्तावेज़", "दस्तावेज", "कागजात", "प्रमाण"
}

MONEY_KEYWORDS = {
    "how much", "amount", "money", "rupees", "subsidy", "cost", "pay", "share", "percentage", "rate",
    "किती", "पैसे", "रुपये", "अनुदान", "खर्च", "हप्ता", "फायदा", "नुकसान भरपाई",
    "कितना", "कितने", "रुपये", "सब्सिडी", "लाभ", "राशि", "किस्त"
}

ELIGIBILITY_KEYWORDS = {
    "eligible", "eligibility", "can i", "qualify", "am i", "apply", "get",
    "पात्र", "पात्रता", "मिळेल", "मिळेल का", "लागू", "अर्ज करू शकतो",
    "पात्र", "पात्रता", "मिलेगा", "मिलेगा क्या", "लागू", "आवेदन कर सकता"
}

APPLY_KEYWORDS = {
    "how to apply", "where to apply", "portal", "website", "process", "link",
    "अर्ज कसा", "कुठे अर्ज", "नोंदणी कशी", "पोर्टल", "वेबसाइट",
    "आवेदन कैसे", "कहाँ आवेदन", "रजिस्ट्रेशन", "पोर्टल", "वेबसाइट"
}


def synthesize_answer(
    query: str,
    scheme: dict[str, Any],
    profile: dict[str, Any],
    eval_result: dict[str, Any],
    lang: str = "en"
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
    docs_str = ", ".join(docs_list) if docs_list else ("Aadhaar & 7/12 record" if lang == "en" else "आधार कार्ड आणि 7/12 उतारा")
    
    link = scheme.get("official_link", "mahadbt.maharashtra.gov.in")
    is_eligible = eval_result.get("eligible", True)
    note = eval_result.get("note", "")

    # 1. Documents question
    if any(k in raw for k in DOC_KEYWORDS):
        if lang == "mr":
            return f"{name} चा लाभ घेण्यासाठी तुम्हाला ही कागदपत्रे लागतील: {docs_str}. तुम्ही {link} वर किंवा जवळच्या सीएससी केंद्रावर अर्ज करू शकता."
        elif lang == "hi":
            return f"{name} के लिए आवश्यक दस्तावेज़ हैं: {docs_str}। आप {link} पर या सीएससी केंद्र पर ऑनलाइन आवेदन कर सकते हैं।"
        else:
            return f"To apply for {name}, you will need: {docs_str}. Applications can be submitted online at {link} or at your nearest CSC center."

    # 2. How to apply question
    if any(k in raw for k in APPLY_KEYWORDS):
        if lang == "mr":
            return f"{name} साठी अर्ज करणे सोपे आहे. तुम्ही तुमच्या आधार कार्ड व ७/१२ उताऱ्यासह अधिकृत पोर्टलवर ({link}) किंवा गावातील सीएससी केंद्रावर जाऊन नोंदणी करू शकता."
        elif lang == "hi":
            return f"{name} के लिए आवेदन करना आसान है। आप अपने आधार कार्ड और 7/12 भूमि रिकॉर्ड के साथ आधिकारिक पोर्टल ({link}) पर या सीएससी केंद्र पर आवेदन कर सकते हैं।"
        else:
            return f"Applying for {name} is straightforward: Visit the official government portal ({link}) or your local Gram Panchayat CSC center with your Aadhaar and land records."

    # 3. Money / Subsidy / How much question
    if any(k in raw for k in MONEY_KEYWORDS):
        if lang == "mr":
            elig_text = f"तुमच्या शेतीसाठी: {note}" if note else ""
            return f"{name} अंतर्गत लाभ: {benefit} {elig_text}"
        elif lang == "hi":
            elig_text = f"आपके खेत के लिए: {note}" if note else ""
            return f"{name} के तहत लाभ: {benefit} {elig_text}"
        else:
            elig_text = f"For your farm profile: {note}" if note else ""
            return f"Benefit under {name}: {benefit} {elig_text}"

    # 4. Eligibility question
    if any(k in raw for k in ELIGIBILITY_KEYWORDS):
        if is_eligible:
            if lang == "mr":
                return f"✅ होय, तुम्ही {name} साठी पात्र आहात! {note}"
            elif lang == "hi":
                return f"✅ हाँ, आप {name} के लिए पात्र हैं! {note}"
            else:
                return f"✅ Yes, you qualify for {name}! {note}"
        else:
            if lang == "mr":
                return f"❌ सध्या तुम्ही {name} साठी पात्र नाही. कारण: {note}"
            elif lang == "hi":
                return f"❌ वर्तमान में आप {name} के लिए पात्र नहीं हैं। कारण: {note}"
            else:
                return f"❌ Currently you do not qualify for {name}. Reason: {note}"

    # 5. Default clear summary
    if is_eligible:
        if lang == "mr":
            return f"{name} ही शेतकऱ्यांसाठी महत्त्वाची योजना आहे. {benefit} तुमच्या शेतीसाठी: {note}"
        elif lang == "hi":
            return f"{name} किसानों के लिए एक महत्वपूर्ण योजना है। {benefit} आपके खेत के लिए: {note}"
        else:
            return f"{name} provides {benefit} For your farm profile: {note}"
    else:
        if lang == "mr":
            return f"{name}: {benefit} (टीप: {note})"
        elif lang == "hi":
            return f"{name}: {benefit} (सूचना: {note})"
        else:
            return f"{name}: {benefit} (Note: {note})"

