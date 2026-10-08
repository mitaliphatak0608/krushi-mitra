import os
from backend import rules as eligibility
import json
import re
import string
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "schemes_content.json"
with DATA_FILE.open(encoding="utf-8") as _f:
    schemes = json.load(_f)
scheme_map = {s["scheme_id"]: s for s in schemes}

from backend.sms_state import get_session, update_session, reset_session, stop_session
from backend.scheme_search import search_schemes_semantic
from backend.qa_engine import synthesize_answer, DOC_KEYWORDS, MONEY_KEYWORDS, ELIGIBILITY_KEYWORDS, APPLY_KEYWORDS, WHY_KEYWORDS

VALID_AGRI_KEYWORDS = {
    # English
    "scheme", "schemes", "agriculture", "farming", "farmer", "crop", "crops", "land", 
    "landholding", "income", "tax", "loan", "kcc", "pm", "kisan", "pmkisan", "solar", 
    "pump", "tractor", "well", "irrigation", "namo", "shetkari", "yojana", "fund", 
    "rupees", "pond", "insurance", "mechanization", "karjmafi", "pkvy", "smam", "pmfby",
    "subsidy", "subsidies", "document", "documents", "apply", "eligibility", "eligible",
    "benefit", "benefits", "application", "register", "registration", "portal", "website",
    # Hindi
    "योजना", "योजनाएं", "दस्तावेज", "दस्तावेज़", "आवेदन", "पात्रता", "पात्र", "लाभ",
    "सब्सिडी", "कृषि", "खेती", "किसान", "फसल", "भूमि", "आय", "टैक्स", "ऋण", "कर्ज",
    "कर्जमाफी", "सोलर", "पंप", "ट्रैक्टर", "कुआं", "सिंचाई", "नमो", "शेतकरी", "पैसा",
    "रुपये", "जानकारी", "पीएम", "बीमा", "मशीन", "तालाब", "अनुदान",
    # Marathi
    "योजना", "कागदपत्रे", "अर्ज", "पात्रता", "पात्र", "फायदे", "सबसिडी", "अनुदान",
    "कृषी", "शेती", "शेतकरी", "पीक", "जमीन", "उत्पन्न", "कर", "कर्ज", "कर्जमाफी",
    "सौर", "पंप", "ट्रॅक्टर", "विहीर", "सिंचन", "नमो", "शेतकरी", "पैसे", "रुपये",
    "माहिती", "पीएम", "विमा", "तळे", "शेततळे", "मशीन", "मिळेल", "हवी"
}

def is_valid_agri_query(msg: str) -> bool:
    msg_clean = msg.lower()
    msg_no_punct = msg_clean.translate(str.maketrans('', '', string.punctuation))
    tokens = set(msg_no_punct.split())
    
    for kw in VALID_AGRI_KEYWORDS:
        if kw in tokens:
            return True
        # For non-ascii (Hindi/Marathi) words or longer English words, allow substring match
        if len(kw) >= 3 and kw in msg_clean:
            is_ascii = all(ord(c) < 128 for c in kw)
            if not is_ascii or len(kw) > 4:
                return True
    return False

LANG_TEXTS = {
    "welcome_lang": {
        "en": "🌾 Welcome to Krushi Mitra!\n\nPlease select your language:\n\n1. English\n2. हिंदी\n3. मराठी\n\nReply with 1, 2 or 3.",
        "hi": "🌾 कृषि मित्र में आपका स्वागत है!\n\nकृपया अपनी भाषा चुनें:\n\n1. English\n2. हिंदी\n3. मराठी\n\n1, 2 या 3 में से जवाब दें।",
        "mr": "🌾 कृषी मित्रमध्ये आपले स्वागत आहे!\n\nकृपया आपली भाषा निवडा:\n\n1. English\n2. हिंदी\n3. मराठी\n\n1, 2 किंवा 3 असे उत्तर द्या."
    },
    "stop": {
        "en": "SMS assistance stopped. Send START whenever you want to begin again.",
        "hi": "SMS सहायता बंद कर दी गई है। दोबारा शुरू करने के लिए START भेजें।",
        "mr": "SMS मदत थांबवली आहे. पुन्हा सुरू करण्यासाठी START पाठवा."
    },
    "reset": {
        "en": "Your SMS session has been reset. Send START to begin again.",
        "hi": "आपका SMS सत्र रीसेट कर दिया गया है। फिर से शुरू करने के लिए START भेजें।",
        "mr": "तुमचे SMS सत्र रीसेट केले safe. पुन्हा सुरू करण्यासाठी START पाठवा."
    },
    "back": {
        "en": "Going back to the previous menu.",
        "hi": "पिछले मेनू पर वापस जा रहे हैं।",
        "mr": "मागील मेनूवर परत जात आहोत."
    },
    "help": {
        "en": "👨‍🌾 Human Assistance\n\nYou can get help from a nearby Common Service Centre (CSC).\n\nA CSC operator can help you with:\n• Scheme application\n• Documents\n• Eligibility clarification\n• Online application support\n\nReply WEB to open the Krushi Mitra website.",
        "hi": "👨‍🌾 मानव सहायता\n\nआप नजदीकी कॉमन सर्विस सेंटर (CSC) से सहायता प्राप्त कर सकते हैं।\n\nCSC ऑपरेटर आपकी मदद कर सकता है:\n• योजना आवेदन\n• दस्तावेज़\n• पात्रता संबंधी जानकारी\n• ऑनलाइन आवेदन सहायता\n\nकृषि मित्र वेबसाइट खोलने के लिए WEB भेजें।",
        "mr": "👨‍🌾 मानवीय मदत\n\nतुम्ही जवळच्या कॉमन सर्विस सेंटर (CSC) कडून मदत घेऊ शकता.\n\nCSC ऑपरेटर तुम्हाला मदत करू शकतो:\n• योजना अर्ज\n• कागदपत्रे\n• पात्रतेबाबत माहिती\n• ऑनलाइन अर्जासाठी मदत\n\nकृषी मित्र वेबसाइट उघडण्यासाठी WEB पाठवा."
    },
    "web": {
        "en": "🌐 Krushi Mitra website:\n{url}",
        "hi": "🌐 कृषि मित्र वेबसाइट:\n{url}",
        "mr": "🌐 कृषी मित्र वेबसाइट:\n{url}"
    },
    "invalid_num": {
        "en": "Please enter a valid number.\n\nExample:\n2.5",
        "hi": "कृपया एक वैध संख्या दर्ज करें।\n\nउदाहरण:\n2.5",
        "mr": "कृपया योग्य संख्या प्रविष्ट करा.\n\nउदाहरण:\n2.5"
    },
    "invalid_bool": {
        "en": "Please reply Yes or No (or 1 / 2).",
        "hi": "कृपया हाँ या नहीं (या 1 / 2) में उत्तर दें।",
        "mr": "कृपया होय किंवा नाही (किंवा 1 / 2) असे उत्तर द्या."
    },
    "invalid_text": {
        "en": "Please provide a valid answer.",
        "hi": "कृपया एक वैध उत्तर प्रदान करें।",
        "mr": "कृपया एक वैध उत्तर द्या."
    },
    "invalid_scheme": {
        "en": "Invalid scheme number. Please reply with a valid number from the list.",
        "hi": "अमान्य योजना संख्या। कृपया सूची से एक वैध संख्या के साथ उत्तर दें।",
        "mr": "अवैध योजना क्रमांक. कृपया सूचीमधून योग्य क्रमांकासह उत्तर द्या."
    },
    "apply": {
        "en": "To apply, please visit your nearest CSC or reply WEB for the online portal.\nReply BACK to return to schemes.",
        "hi": "आवेदन करने के लिए, कृपया अपने निकटतम CSC पर जाएं या ऑनलाइन पोर्टल के लिए WEB का उत्तर दें।\nयोजनाओं पर लौटने के लिए BACK का उत्तर दें।",
        "mr": "अर्ज करण्यासाठी, कृपया तुमच्या जवळच्या CSC ला भेट द्या किंवा ऑनलाइन पोर्टलसाठी WEB असे उत्तर द्या.\nयोजनांवर परत येण्यासाठी BACK असे उत्तर द्या."
    },
    "unknown": {
        "en": "I didn't understand that.\nReply HELP for options or RESET to start over.",
        "hi": "मुझे वह समझ में नहीं आया।\nविकल्पों के लिए HELP या फिर से शुरू करने के लिए RESET का उत्तर दें।",
        "mr": "मला ते समजले नाही.\nपर्यायांसाठी HELP किंवा पुन्हा सुरू करण्यासाठी RESET असे उत्तर द्या."
    },
    "no_semantic_match": {
        "en": "I couldn't identify a specific scheme from your question. Please mention the scheme name or ask your question differently.",
        "hi": "मैं आपके प्रश्न से किसी विशेष योजना की पहचान नहीं कर पाया। कृपया योजना का नाम लिखें या प्रश्न अलग तरीके से पूछें।",
        "mr": "तुमच्या प्रश्नावरून मला विशिष्ट योजना ओळखता आली नाही. कृपया योजनेचे नाव लिहा किंवा प्रश्न वेगळ्या पद्धतीने विचारा."
    },
    "invalid_query": {
        "en": "❌ Invalid Query\n\nThis message is not related to Krushi Mitra's agricultural services.\n\nYou can ask about:\n• Farmer government schemes\n• Scheme eligibility\n• Scheme benefits\n• Required documents\n• How to apply\n• Your farmer profile\n\nReply START to create/update your farmer profile.\nReply HELP for human assistance.",
        "hi": "❌ अमान्य प्रश्न\n\nयह संदेश कृषि मित्र की कृषि सेवाओं से संबंधित नहीं है।\n\nआप निम्न के बारे में पूछ सकते हैं:\n• किसान सरकारी योजनाएं\n• योजना पात्रता\n• योजना लाभ\n• आवश्यक दस्तावेज\n• आवेदन कैसे करें\n• आपकी किसान प्रोफ़ाइल\n\nअपनी किसान प्रोफ़ाइल बनाने/अपडेट करने के लिए START भेजें।\nमानव सहायता के लिए HELP भेजें।",
        "mr": "❌ अवैध प्रश्न\n\nहा संदेश कृषी मित्रच्या कृषी सेवांशी संबंधित नाही.\n\nतुम्ही याबद्दल विचारू शकता:\n• शेतकरी सरकारी योजना\n• योजना पात्रता\n• योजनेचे फायदे\n• आवश्यक कागदपत्रे\n• अर्ज कसा करावा\n• तुमची शेतकरी प्रोफाइल\n\nतुमची शेतकरी प्रोफाइल तयार/अपडेट करण्यासाठी START पाठवा.\nमानवीय मदतीसाठी HELP पाठवा."
    }
}

QUESTIONS = [
    {
        "id": "landholding",
        "type": "float",
        "field_name": {"en": "landholding", "hi": "भूमि", "mr": "जमीन"},
        "text": {
            "en": "Q1/8\nWhat is your landholding?\nReply in hectares.",
            "hi": "प्रश्न 1/8\nआपके पास कितनी भूमि है?\nकृपया हेक्टेयर में बताएं।",
            "mr": "प्रश्न 1/8\nतुमच्याकडे किती जमीन आहे?\nकृपया हेक्टरमध्ये माहिती द्या."
        }
    },
    {
        "id": "region",
        "type": "str",
        "field_name": {"en": "region", "hi": "क्षेत्र", "mr": "प्रदेश"},
        "text": {
            "en": "Q2/8\nWhich region are you from?",
            "hi": "प्रश्न 2/8\nआप किस क्षेत्र से हैं?",
            "mr": "प्रश्न 2/8\nतुम्ही कोणत्या प्रदेशातील आहात?"
        }
    },
    {
        "id": "primaryCrop",
        "type": "str",
        "field_name": {"en": "primary crop", "hi": "मुख्य फसल", "mr": "प्रमुख पीक"},
        "text": {
            "en": "Q3/8\nWhat is your primary crop?",
            "hi": "प्रश्न 3/8\nआपकी मुख्य फसल कौन सी है?",
            "mr": "प्रश्न 3/8\nतुमचे प्रमुख पीक कोणते आहे?"
        }
    },
    {
        "id": "category",
        "type": "str",
        "field_name": {"en": "social category", "hi": "सामाजिक श्रेणी", "mr": "सामाजिक श्रेणी"},
        "text": {
            "en": "Q4/8\nWhat is your social category?",
            "hi": "प्रश्न 4/8\nआपकी सामाजिक श्रेणी क्या है?",
            "mr": "प्रश्न 4/8\nतुमची सामाजिक श्रेणी कोणती आहे?"
        }
    },
    {
        "id": "annualIncome",
        "type": "float",
        "field_name": {"en": "annual income", "hi": "वार्षिक आय", "mr": "वार्षिक उत्पन्न"},
        "text": {
            "en": "Q5/8\nWhat is your annual household income?\nPlease enter the amount in ₹.",
            "hi": "प्रश्न 5/8\nआपकी वार्षिक पारिवारिक आय कितनी है?\nकृपया राशि ₹ में दर्ज करें।",
            "mr": "प्रश्न 5/8\nतुमचे वार्षिक कौटुंबिक उत्पन्न किती आहे?\nकृपया रक्कम ₹ मध्ये नोंदवा."
        }
    },
    {
        "id": "cropSeason",
        "type": "str",
        "field_name": {"en": "crop season", "hi": "फसल का मौसम", "mr": "पीक हंगाम"},
        "text": {
            "en": "Q6/8\nWhat is your primary crop season? (e.g., Kharif, Rabi)",
            "hi": "प्रश्न 6/8\nआपकी मुख्य फसल का मौसम क्या है? (जैसे, खरीफ, रबी)",
            "mr": "प्रश्न 6/8\nतुमचा मुख्य पीक हंगाम कोणता आहे? (उदा., खरीप, रब्बी)"
        }
    },
    {
        "id": "hasOutstandingLoan",
        "type": "bool",
        "field_name": {"en": "outstanding loan", "hi": "बकाया ऋण", "mr": "थकीत कर्ज"},
        "text": {
            "en": "Q7/8\nDo you currently have an outstanding bank crop loan?\n\n1. Yes\n2. No",
            "hi": "प्रश्न 7/8\nक्या आपके पास वर्तमान में कोई बकाया बैंक फसल ऋण है?\n\n1. हाँ\n2. नहीं",
            "mr": "प्रश्न 7/8\nतुमच्याकडे सध्या कोणतेही थकीत बँक पीक कर्ज आहे का?\n\n1. होय\n2. नाही"
        }
    },
    {
        "id": "isTaxPayer",
        "type": "bool",
        "field_name": {"en": "income tax payer", "hi": "आयकर दाता", "mr": "आयकर भरणारे"},
        "text": {
            "en": "Q8/8\nDoes anyone in your household pay income tax?\n\n1. Yes\n2. No",
            "hi": "प्रश्न 8/8\nक्या आपके परिवार में कोई आयकर भरता है?\n\n1. हाँ\n2. नहीं",
            "mr": "प्रश्न 8/8\nतुमच्या कुटुंबातील कोणी आयकर भरतो का?\n\n1. होय\n2. नाही"
        }
    }
]

SCHEME_REQUIRED_FIELDS = {
    "PMKISAN": ["isTaxPayer"],
    "NAMO_SHETKARI": ["isTaxPayer"],
    "PMFBY": ["cropSeason"],
    "MICRO_IRRIGATION": ["landholding", "region"],
    "SOLAR_PUMP": ["category"],
    "WELL_SUBSIDY": ["landholding"],
    "KCC": ["primaryCrop"],
    "KARJMAFI": ["hasOutstandingLoan"],
    "PKVY": [],
    "SMAM": [],
    "FARM_POND": ["landholding"]
}

def format_scheme_list(profile, lang):
    eligible = []
    for s_id, rule_fn in eligibility.RULES.items():
        scheme = scheme_map.get(s_id)
        if not scheme: continue
        res = rule_fn(profile)
        if res["eligible"]:
            name = scheme.get("scheme_name", {}).get(lang, scheme.get("scheme_name", {}).get("en", s_id))
            eligible.append({"id": s_id, "name": name})

    if lang == "hi":
        text = "🎉 आपकी किसान प्रोफ़ाइल तैयार है!\n\n📍 कृषि प्रोफ़ाइल\n\n"
        text += f"भूमि: {profile.get('landholding')} हेक्टेयर\n"
        text += f"क्षेत्र: {profile.get('region')}\n"
        text += f"मुख्य फसल: {profile.get('primaryCrop')}\n"
        text += f"श्रेणी: {profile.get('category')}\n"
        text += f"वार्षिक आय: ₹{profile.get('annualIncome')}\n\n"
        text += "🌾 अनुशंसित योजनाएँ\n\n"
    elif lang == "mr":
        text = "🎉 तुमची शेतकरी प्रोफाइल तयार आहे!\n\n📍 शेतीचा सारांश\n\n"
        text += f"जमीन: {profile.get('landholding')} हेक्टर\n"
        text += f"प्रदेश: {profile.get('region')}\n"
        text += f"प्रमुख पीक: {profile.get('primaryCrop')}\n"
        text += f"श्रेणी: {profile.get('category')}\n"
        text += f"वार्षिक उत्पन्न: ₹{profile.get('annualIncome')}\n\n"
        text += "🌾 शिफारस केलेल्या योजना\n\n"
    else:
        text = "🎉 Your farmer profile is ready!\n\n📍 Farm Summary\n\n"
        text += f"Landholding: {profile.get('landholding')} ha\n"
        text += f"Region: {profile.get('region')}\n"
        text += f"Primary Crop: {profile.get('primaryCrop')}\n"
        text += f"Category: {profile.get('category')}\n"
        text += f"Annual Income: ₹{profile.get('annualIncome')}\n\n"
        text += "🌾 Recommended Schemes\n\n"
        
    for idx, s in enumerate(eligible, 1):
        text += f"{idx}. ✅ {s['name']}\n"
        
    if lang == "hi":
        text += "\nविवरण के लिए नंबर भेजें।\nसहायता के लिए HELP भेजें।"
    elif lang == "mr":
        text += "\nतपशीलासाठी क्रमांक पाठवा.\nमदतीसाठी HELP पाठवा."
    else:
        text += "\nReply with a number for details.\nReply HELP for assistance."

    return text, eligible

def validate_answer(q_type, answer, lang):
    if q_type == "float":
        try:
            val = float(answer)
            return True, val
        except ValueError:
            return False, LANG_TEXTS["invalid_num"][lang]
    elif q_type == "bool":
        ans = answer.strip().lower()
        if ans in ("yes", "y", "true", "1", "होय", "हाँ", "हो", "yes."):
            return True, True
        elif ans in ("no", "n", "false", "0", "2", "नाही", "नहीं", "no."):
            return True, False
        else:
            return False, LANG_TEXTS["invalid_bool"][lang]
    else:
        if not answer.strip():
            return False, LANG_TEXTS["invalid_text"][lang]
        return True, answer.strip()

def check_profile_update(msg, profile, lang):
    """Detect simple explicit profile updates."""
    # Landholding update
    land_match = re.search(r'(landholding|जमीन|भूमि).*(?:is|now|आता|है|आहे)?\s*([\d\.]+)', msg, re.IGNORECASE)
    if land_match:
        try:
            val = float(land_match.group(2))
            profile["landholding"] = val
            return True, "landholding", val
        except:
            pass
    # Income update
    inc_match = re.search(r'(income|उत्पन्न|आय).*(?:is|now|आता|है|आहे)?\s*([\d]+)', msg, re.IGNORECASE)
    if inc_match:
        try:
            val = float(inc_match.group(2))
            profile["annualIncome"] = val
            return True, "annual income", val
        except:
            pass
    return False, None, None

def get_missing_questions(profile, scheme_id):
    required = SCHEME_REQUIRED_FIELDS.get(scheme_id, [])
    missing = []
    for idx, q in enumerate(QUESTIONS):
        if q["id"] in required and q["id"] not in profile:
            missing.append(idx)
    return missing

def process_sms(phone: str, message: str) -> dict:
    import backend.database as db
    db.save_sms_message(phone, "incoming", message)
    
    result = _process_sms_inner(phone, message)
    
    if result.get("success") and result.get("message"):
        db.save_sms_message(phone, "outgoing", result["message"])
        
    return result

def _process_sms_inner(phone: str, message: str) -> dict:
    msg = message.strip()
    msg_upper = msg.upper()
    session = get_session(phone)
    state = session["state"]
    lang = session.get("language", "en")
    profile = session.get("profile", {})
    
    # Common Commands Handling
    is_stop = msg_upper in ("STOP", "रुकें", "थांबा")
    is_reset = msg_upper in ("RESET", "रीसेट")
    is_help = msg_upper in ("HELP", "मदद", "मदत")
    is_web = msg_upper in ("WEB", "WEBSITE", "LINK", "वेब", "वेबसाइट", "लिंक")
    is_back = msg_upper in ("BACK", "वापस", "मागे")

    if msg_upper == "START":
        reset_session(phone, language="en")
        update_session(phone, "SELECT_LANG")
        return {
            "success": True,
            "message": LANG_TEXTS["welcome_lang"]["en"],
            "state": "SELECT_LANG",
            "language": "en"
        }
    
    if is_stop:
        stop_session(phone)
        return {"success": True, "message": LANG_TEXTS["stop"][lang], "state": "STOPPED", "language": lang}
    
    if is_reset:
        reset_session(phone, lang)
        update_session(phone, "SELECT_LANG")
        return {"success": True, "message": LANG_TEXTS["welcome_lang"][lang], "state": "SELECT_LANG", "language": lang}
        
    if is_web:
        url = os.environ.get("KRUSHI_MITRA_WEB_URL", "http://localhost:5173")
        return {"success": True, "message": LANG_TEXTS["web"][lang].format(url=url), "state": state, "language": lang}
        
    if is_help:
        return {"success": True, "message": LANG_TEXTS["help"][lang], "state": state, "language": lang}
        
    if state == "STOPPED":
        return {"success": True, "message": LANG_TEXTS["stop"][lang], "state": "STOPPED", "language": lang}
        
    if state == "INIT":
        return {"success": True, "message": "Welcome to Krushi Mitra SMS Demo.\n\nReply START to begin.", "state": "INIT", "language": lang}
        
    if state == "SELECT_LANG":
        if msg in ("1", "english", "English", "en"):
            selected_lang = "en"
        elif msg in ("2", "hindi", "हिंदी", "hi"):
            selected_lang = "hi"
        elif msg in ("3", "marathi", "मराठी", "mr"):
            selected_lang = "mr"
        else:
            return {"success": True, "message": LANG_TEXTS["welcome_lang"]["en"], "state": "SELECT_LANG", "language": "en"}
        
        update_session(phone, "Q_0", language=selected_lang)
        return {"success": True, "message": QUESTIONS[0]["text"][selected_lang], "state": "Q_0", "language": selected_lang}

    # Profile Update Override
    updated, field_name, new_val = check_profile_update(msg, profile, lang)
    if updated and state not in ("SELECT_LANG", "INIT"):
        update_session(phone, state, language=lang, profile=profile)
        if lang == "hi":
            msg_reply = f"आपकी {field_name} {new_val} अपडेट कर दी गई है।\n\nआप क्या जानना चाहते हैं?"
        elif lang == "mr":
            msg_reply = f"तुमची {field_name} {new_val} अपडेट केली आहे.\n\nतुम्हाला काय जाणून घ्यायचे आहे?"
        else:
            msg_reply = f"Your {field_name} has been updated to {new_val}.\n\nWhat would you like to know?"
        return {"success": True, "message": msg_reply, "state": state, "language": lang}

    # --- SEMANTIC SEARCH INTERCEPT (For queries not strictly answering a question, or if already finished questions) ---
    is_answering = False
    if state.startswith("Q_"):
        q_idx_str = state.split("_")[-1]
        if q_idx_str.isdigit():
            q_idx = int(q_idx_str)
            valid, _ = validate_answer(QUESTIONS[q_idx]["type"], msg, lang)
            is_answering = valid

    if not is_answering and not msg.isdigit() and not is_back and state not in ("SELECT_LANG", "INIT"):
        # Explicit intent gate: reject unrelated queries before any semantic search or context matching
        if not is_valid_agri_query(msg) and msg_upper != "APPLY":
            return {"success": True, "message": LANG_TEXTS["invalid_query"][lang], "state": state, "language": lang}

    raw_lower = msg.lower()
    has_q_kws = any(k in raw_lower for k in set.union(DOC_KEYWORDS, MONEY_KEYWORDS, ELIGIBILITY_KEYWORDS, APPLY_KEYWORDS, WHY_KEYWORDS))
    
    # Context-aware follow up for focused scheme
    if state in ("SCHEME_FOCUS_MENU", "SCHEME_DETAILS") and (has_q_kws or msg_upper == "APPLY") and not msg.isdigit():
        f_id = session.get("selected_scheme_id") or session.get("focused_scheme_id")
        # If they just asked a question without a scheme name, assume they mean the focused scheme
        if f_id and f_id in scheme_map:
            # Check if any other scheme name is explicitly mentioned
            mentioned_other = False
            for sid, s in scheme_map.items():
                if sid != f_id:
                    for sname in s.get("scheme_name", {}).values():
                        if sname.lower() in raw_lower:
                            mentioned_other = True
                            break
                if mentioned_other: break
            
            if not mentioned_other:
                # Use focused scheme
                scheme = scheme_map[f_id]
                missing = get_missing_questions(profile, f_id)
                if missing and any(k in raw_lower for k in ELIGIBILITY_KEYWORDS):
                    # Ask the missing question
                    q_idx = missing[0]
                    q = QUESTIONS[q_idx]
                    update_session(phone, f"Q_MISSING_{q_idx}", language=lang, profile=profile, pending_scheme=f_id, pending_query=msg)
                    if lang == "hi":
                        prefix = f"पात्रता की जांच करने के लिए, मुझे आपके {q['field_name']['hi']} की आवश्यकता है।\n\n"
                    elif lang == "mr":
                        prefix = f"पात्रता तपासण्यासाठी, मला तुमची {q['field_name']['mr']} आवश्यक आहे.\n\n"
                    else:
                        prefix = f"To check your eligibility, I only need your {q['field_name']['en']}.\n\n"
                    return {"success": True, "message": prefix + q["text"][lang], "state": f"Q_MISSING_{q_idx}", "language": lang}
                
                
                eval_res = eligibility.evaluate(f_id, profile)
                # If they typed APPLY explicitly, treat it as a 'how to apply' question
                query_to_synth = "how to apply" if msg_upper == "APPLY" else msg
                ans = synthesize_answer(query_to_synth, scheme, profile, eval_res, lang)
                
                # Remain in current state, just answer the question
                return {"success": True, "message": ans, "state": state, "language": lang}

    if not is_answering and not msg.isdigit() and state not in ("SELECT_LANG", "INIT"):
        best_entry, best_score = search_schemes_semantic(msg, threshold=0.20)
        if best_entry:
            scheme_id = best_entry["scheme_id"]
            scheme = best_entry["original_scheme"]
            
            # If asking about eligibility, check if we need missing info
            if any(k in raw_lower for k in ELIGIBILITY_KEYWORDS):
                missing = get_missing_questions(profile, scheme_id)
                if missing:
                    q_idx = missing[0]
                    q = QUESTIONS[q_idx]
                    update_session(phone, f"Q_MISSING_{q_idx}", language=lang, profile=profile, pending_scheme=scheme_id, pending_query=msg)
                    if lang == "hi":
                        prefix = f"पात्रता की जांच करने के लिए, मुझे आपके {q['field_name']['hi']} की आवश्यकता है।\n\n"
                    elif lang == "mr":
                        prefix = f"पात्रता तपासण्यासाठी, मला तुमची {q['field_name']['mr']} आवश्यक आहे.\n\n"
                    else:
                        prefix = f"To check your eligibility, I only need your {q['field_name']['en']}.\n\n"
                    return {"success": True, "message": prefix + q["text"][lang], "state": f"Q_MISSING_{q_idx}", "language": lang}

            eval_result = eligibility.evaluate(scheme_id, profile)
            
            if not has_q_kws and len(msg.split()) <= 5:
                name = scheme.get("scheme_name", {}).get(lang, scheme.get("scheme_name", {}).get("en", scheme_id))
                desc = scheme.get("eligibility_summary", {}).get(lang, scheme.get("eligibility_summary", {}).get("en", ""))
                
                if lang == "hi":
                    out_msg = f"🌾 {name}\n\nयह योजना: {desc}\n\nआप क्या जानना चाहते हैं?\n1. पात्रता\n2. लाभ\n3. दस्तावेज़\n4. आवेदन प्रक्रिया\n\nया अपना प्रश्न सीधे टाइप करें।"
                elif lang == "mr":
                    out_msg = f"🌾 {name}\n\nही योजना: {desc}\n\nतुम्हाला काय जाणून घ्यायचे आहे?\n1. पात्रता\n2. फायदे\n3. कागदपत्रे\n4. अर्ज प्रक्रिया\n\nकिंवा तुमचा प्रश्न थेट टाइप करा."
                else:
                    out_msg = f"🌾 {name}\n\nAbout: {desc}\n\nWhat would you like to know?\n1. Eligibility\n2. Benefits\n3. Documents\n4. How to apply\n\nOr type your question directly."
                    
                update_session(phone, "SCHEME_FOCUS_MENU", language=lang, selected_scheme_id=scheme_id, profile=profile)
                return {"success": True, "message": out_msg, "state": "SCHEME_FOCUS_MENU", "language": lang}
                
            ans = synthesize_answer(msg, scheme, profile, eval_result, lang)
            update_session(phone, "SCHEME_FOCUS_MENU", language=lang, selected_scheme_id=scheme_id, profile=profile)
            return {"success": True, "message": ans, "state": "SCHEME_FOCUS_MENU", "language": lang}
        elif state not in ("RECOMMENDATIONS", "SCHEME_DETAILS", "SCHEME_FOCUS_MENU"):
            # If in a question state, just fall through to normal validation to show error
            pass
        else:
            return {"success": True, "message": LANG_TEXTS["no_semantic_match"][lang], "state": state, "language": lang}

    # --- NORMAL QUESTION FLOW ---
    if state.startswith("Q_"):
        parts = state.split("_")
        q_idx = int(parts[-1])
        is_missing = "MISSING" in state
        
        q = QUESTIONS[q_idx]
        valid, val = validate_answer(q["type"], msg, lang)
        
        if not valid:
            return {"success": True, "message": val, "state": state, "language": lang}
            
        profile[q["id"]] = val
        
        if is_missing:
            pending_scheme = session.get("pending_scheme")
            pending_query = session.get("pending_query", "am I eligible")
            
            missing = get_missing_questions(profile, pending_scheme)
            if missing:
                next_idx = missing[0]
                next_q = QUESTIONS[next_idx]
                update_session(phone, f"Q_MISSING_{next_idx}", language=lang, profile=profile, pending_scheme=pending_scheme, pending_query=pending_query)
                return {"success": True, "message": next_q["text"][lang], "state": f"Q_MISSING_{next_idx}", "language": lang}
            else:
                scheme = scheme_map[pending_scheme]
                eval_res = eligibility.evaluate(pending_scheme, profile)
                ans = synthesize_answer(pending_query, scheme, profile, eval_res, lang)
                update_session(phone, "SCHEME_FOCUS_MENU", language=lang, profile=profile, selected_scheme_id=pending_scheme)
                # clear pending logic by omission
                return {"success": True, "message": ans, "state": "SCHEME_FOCUS_MENU", "language": lang}
        else:
            if q_idx + 1 < len(QUESTIONS):
                next_state = f"Q_{q_idx + 1}"
                update_session(phone, next_state, language=lang, profile=profile)
                return {"success": True, "message": QUESTIONS[q_idx + 1]["text"][lang], "state": next_state, "language": lang}
            else:
                recommendation_msg, eligible_schemes = format_scheme_list(profile, lang)
                update_session(phone, "RECOMMENDATIONS", language=lang, profile=profile, recommended_schemes=eligible_schemes)
                return {"success": True, "message": recommendation_msg, "state": "RECOMMENDATIONS", "language": lang}

    # --- RECOMMENDATIONS / DETAILS / MENU ---
    if state in ("RECOMMENDATIONS", "SCHEME_DETAILS", "SCHEME_FOCUS_MENU"):
        if is_back:
            recommendation_msg, _ = format_scheme_list(profile, lang)
            # Clear selected scheme when going back to recommendations
            update_session(phone, "RECOMMENDATIONS", language=lang, selected_scheme_id=None)
            return {"success": True, "message": recommendation_msg, "state": "RECOMMENDATIONS", "language": lang}
            
        if msg_upper == "APPLY":
            return {"success": True, "message": LANG_TEXTS["apply"][lang], "state": state, "language": lang}

        if msg.isdigit():
            if state == "SCHEME_FOCUS_MENU" and msg in ("1", "2", "3", "4"):
                f_id = session.get("selected_scheme_id") or session.get("focused_scheme_id")
                if not f_id or f_id not in scheme_map:
                    return {"success": True, "message": LANG_TEXTS["invalid_scheme"][lang], "state": state, "language": lang}
                
                scheme = scheme_map[f_id]
                missing = get_missing_questions(profile, f_id)
                if missing and msg == "1":  # If they asked for eligibility via shortcut '1'
                    q_idx = missing[0]
                    q = QUESTIONS[q_idx]
                    update_session(phone, f"Q_MISSING_{q_idx}", language=lang, profile=profile, pending_scheme=f_id, pending_query="am I eligible")
                    if lang == "hi":
                        prefix = f"पात्रता की जांच करने के लिए, मुझे आपके {q['field_name']['hi']} की आवश्यकता है।\n\n"
                    elif lang == "mr":
                        prefix = f"पात्रता तपासण्यासाठी, मला तुमची {q['field_name']['mr']} आवश्यक आहे.\n\n"
                    else:
                        prefix = f"To check your eligibility, I only need your {q['field_name']['en']}.\n\n"
                    return {"success": True, "message": prefix + q["text"][lang], "state": f"Q_MISSING_{q_idx}", "language": lang}

                eval_res = eligibility.evaluate(f_id, profile)
                
                if msg == "1":
                    ans = synthesize_answer("am I eligible", scheme, profile, eval_res, lang)
                elif msg == "2":
                    ans = synthesize_answer("what are the benefits", scheme, profile, eval_res, lang)
                elif msg == "3":
                    ans = synthesize_answer("what documents are required", scheme, profile, eval_res, lang)
                elif msg == "4":
                    ans = synthesize_answer("how to apply", scheme, profile, eval_res, lang)
                
                ans += f"\n\nReply BACK to return to schemes."
                return {"success": True, "message": ans, "state": "SCHEME_FOCUS_MENU", "language": lang}
            
            idx = int(msg) - 1
            schemes_list = session.get("recommended_schemes", [])
            if 0 <= idx < len(schemes_list):
                s_id = schemes_list[idx]["id"]
                scheme = scheme_map.get(s_id)
                
                name = scheme.get("scheme_name", {}).get(lang, scheme.get("scheme_name", {}).get("en", s_id))
                ben = scheme.get("benefit_text", {}).get(lang, scheme.get("benefit_text", {}).get("en", ""))
                cat = scheme.get("category", "")
                docs = scheme.get("documents_required", {}).get(lang, scheme.get("documents_required", {}).get("en", []))
                
                if lang == "hi":
                    docs_text = "\n".join([f"• {d}" for d in docs]) if docs else "कोई नहीं"
                    msg_txt = f"🌾 {name}\n\nपात्रता श्रेणी:\n{cat}\n\nलाभ:\n{ben}\n\nदस्तावेज़:\n{docs_text}\n\nसहायता के लिए APPLY भेजें\nयोजनाओं पर लौटने के लिए BACK भेजें।"
                elif lang == "mr":
                    docs_text = "\n".join([f"• {d}" for d in docs]) if docs else "काहीही नाही"
                    msg_txt = f"🌾 {name}\n\nपात्रता श्रेणी:\n{cat}\n\nफायदे:\n{ben}\n\nकागदपत्रे:\n{docs_text}\n\nमदतीसाठी APPLY पाठवा\nयोजनांवर परत येण्यासाठी BACK पाठवा."
                else:
                    docs_text = "\n".join([f"• {d}" for d in docs]) if docs else "None listed"
                    msg_txt = f"🌾 {name}\n\nCategory:\n{cat}\n\nBenefits:\n{ben}\n\nDocuments:\n{docs_text}\n\nReply APPLY for assistance\nReply BACK to return to schemes."
                
                update_session(phone, "SCHEME_DETAILS", language=lang, selected_scheme_id=s_id)
                return {"success": True, "message": msg_txt, "state": "SCHEME_DETAILS", "language": lang}
            else:
                return {"success": True, "message": LANG_TEXTS["invalid_scheme"][lang], "state": state, "language": lang}

    return {"success": True, "message": LANG_TEXTS["unknown"][lang], "state": state, "language": lang}
