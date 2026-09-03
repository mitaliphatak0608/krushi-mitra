import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Leaf, Send, Mic, CheckCircle2, XCircle, AlertCircle, MapPin,
  Sprout, ExternalLink, ChevronDown, User, ArrowLeft, Loader2
} from "lucide-react";

const CHAT_ENDPOINT    = "http://localhost:8000/chat";
const SCHEMES_ENDPOINT = "http://localhost:8000/schemes";

const FOREST      = "#2C5F2D";
const FOREST_DARK = "#1F4620";
const MOSS        = "#97BC62";
const GOLD        = "#E8A33D";
const CREAM       = "#F7F8F5";
const CARD        = "#FFFFFF";
const INK         = "#1A2E1B";
const MUTED       = "#5C6F5E";

const REGIONS    = ["Marathwada", "Vidarbha", "Western Maharashtra"];
const CATEGORIES = ["General", "SC", "ST", "OBC"];

const UI_TEXT = {
  en: {
    title: "Krushi Mitra", tagline: "Ask about any farmer scheme, in your own language",
    profileLabel: "Your profile (for personalized answers)", landholding: "Landholding (ha)",
    region: "Region", category: "Category",
    placeholder: "Type your question… e.g. Am I eligible for solar pump?",
    send: "Send", eligible: "Eligible", notEligible: "Not eligible",
    verify: "Verify at CSC / official portal",
    docs: "Documents needed", officialLink: "Official portal",
    greeting: "Namaste! Ask me about the schemes— in English, Hindi, or Marathi.",
    notFound: "I couldn't find a matching scheme for that query. Try: crop insurance, drip irrigation, solar pump, kisan credit card, or loan waiver.",
    noServer: "Cannot reach the server. Please make sure the backend is running on port 8000.",
    typing: "Thinking…",
  },
  hi: {
    title: "कृषी मित्र", tagline: "किसी भी किसान योजना के बारे में अपनी भाषा में पूछें",
    profileLabel: "आपकी प्रोफ़ाइल (व्यक्तिगत उत्तरों के लिए)", landholding: "भूमि (हेक्टेयर)",
    region: "क्षेत्र", category: "श्रेणी",
    placeholder: "अपना प्रश्न लिखें… जैसे सौर पंप के लिए मैं पात्र हूं?",
    send: "भेजें", eligible: "पात्र", notEligible: "अपात्र",
    verify: "सीएससी / आधिकारिक पोर्टल पर सत्यापित करें",
    docs: "आवश्यक दस्तावेज़", officialLink: "आधिकारिक पोर्टल",
    greeting: "नमस्ते! पीएम-किसान, सूक्ष्म सिंचाई, सौर पंप, कुआं अनुदान, फसल बीमा और अधिक के बारे में पूछें।",
    notFound: "इस प्रश्न के लिए कोई योजना नहीं मिली। कोशिश करें: फसल बीमा, ड्रिप सिंचाई, सौर पंप, किसान क्रेडिट कार्ड।",
    noServer: "सर्वर से कनेक्ट नहीं हो सका। कृपया बैकएंड चालू करें।",
    typing: "सोच रहा हूं…",
  },
  mr: {
    title: "कृषी मित्र", tagline: "कोणत्याही शेतकरी योजनेबद्दल तुमच्या भाषेत विचारा",
    profileLabel: "तुमची प्रोफाइल (वैयक्तिक उत्तरांसाठी)", landholding: "जमीन (हेक्टर)",
    region: "प्रदेश", category: "प्रवर्ग",
    placeholder: "तुमचा प्रश्न लिहा… उदा. सौर पंपसाठी मी पात्र आहे का?",
    send: "पाठवा", eligible: "पात्र", notEligible: "अपात्र",
    verify: "सीएससी / अधिकृत पोर्टलवर पडताळणी करा",
    docs: "आवश्यक कागदपत्रे", officialLink: "अधिकृत पोर्टल",
    greeting: "नमस्कार! पीएम-किसान, सूक्ष्म सिंचन, सौर पंप, विहीर अनुदान, पीक विमा याबद्दल विचारा.",
    notFound: "या प्रश्नासाठी योजना सापडली नाही. वापरून पाहा: पीक विमा, ठिबक सिंचन, सौर पंप, किसान क्रेडिट कार्ड.",
    noServer: "सर्व्हरशी कनेक्ट होता आले नाही. कृपया बॅकएंड सुरू करा.",
    typing: "विचार करतो आहे…",
  },
};

// ---------------------------------------------------------------------------
// VerdictCard — renders a ChatResponse from the /chat endpoint
// ---------------------------------------------------------------------------
function VerdictCard({ response, lang }) {
  const ok = response.eligible;
  const t  = UI_TEXT[lang] || UI_TEXT.en;
  const schemeName  = response.scheme_name?.[lang] || response.scheme_id || "";
  const benefitText = response.benefit?.[lang] || "";
  const documents   = response.documents?.[lang] || [];

  return (
    <div className="mt-2 rounded-xl overflow-hidden border" style={{ borderColor: ok ? MOSS : "#E8B4A0", backgroundColor: CARD }}>
      {/* Header band */}
      <div className="flex items-center gap-2 px-3 py-2" style={{ backgroundColor: ok ? FOREST : "#8B4A3D" }}>
        {ok ? <CheckCircle2 size={18} color="#fff" /> : <XCircle size={18} color="#fff" />}
        <span className="text-sm font-bold text-white">{ok ? t.eligible : t.notEligible}</span>
        <span className="text-sm text-white opacity-90 ml-1">— {schemeName}</span>
      </div>

      <div className="p-3 space-y-2">
        {/* Benefit */}
        {benefitText && <p className="text-sm" style={{ color: INK }}>{benefitText}</p>}

        {/* Personalised eligibility note */}
        {response.note && (
          <p className="text-sm font-semibold" style={{ color: ok ? FOREST : "#8B4A3D" }}>
            {response.note}
          </p>
        )}

        {/* Documents */}
        {documents.length > 0 && (
          <div>
            <p className="text-xs font-semibold mb-1" style={{ color: MUTED }}>{t.docs}</p>
            <div className="flex flex-wrap gap-1">
              {documents.map((d, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-1 rounded-full"
                  style={{ backgroundColor: CREAM, color: INK, border: `1px solid ${MOSS}` }}
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Official link */}
        {response.link && (
          <div className="flex items-center gap-1 pt-1 text-xs font-semibold" style={{ color: FOREST }}>
            <ExternalLink size={13} />
            <span>{t.officialLink}: {response.link}</span>
          </div>
        )}

        {/* Disclaimer */}
        <div className="flex items-center gap-1 text-xs" style={{ color: GOLD }}>
          <AlertCircle size={13} />
          <span>{t.verify}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AllSchemesCard — renders a full list of all 11 schemes with eligibility tags
// ---------------------------------------------------------------------------
function AllSchemesCard({ response, lang, onSelectScheme }) {
  const t = UI_TEXT[lang] || UI_TEXT.en;
  const schemes = response.schemes || [];

  return (
    <div className="mt-2 rounded-xl overflow-hidden border space-y-2.5 p-3.5" style={{ borderColor: MOSS, backgroundColor: CARD }}>
      <div className="flex items-center gap-2 pb-2 border-b" style={{ borderColor: CREAM }}>
        <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: FOREST }}>
          <Sprout size={14} color="#fff" />
        </div>
        <p className="text-xs font-bold leading-relaxed" style={{ color: FOREST_DARK }}>
          {response.message}
        </p>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {schemes.map((s) => (
          <div
            key={s.scheme_id}
            onClick={() => onSelectScheme && onSelectScheme(s.name)}
            className="p-2.5 rounded-lg border transition-all cursor-pointer hover:shadow-sm"
            style={{
              borderColor: s.eligible ? MOSS : "#E8B4A0",
              backgroundColor: s.eligible ? "#F9FBF8" : "#FFFBFB"
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold" style={{ color: INK }}>{s.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white border text-gray-600 font-medium">
                  {s.category}
                </span>
              </div>
              <span
                className="text-[10px] px-2 py-0.5 rounded font-bold"
                style={{
                  backgroundColor: s.eligible ? '#EAF3E4' : '#FEF2F2',
                  color: s.eligible ? FOREST : '#8B4A3D'
                }}
              >
                {s.eligible ? (t.eligible || "Eligible") : (t.notEligible || "Not eligible")}
              </span>
            </div>
            <p className="text-xs mt-1" style={{ color: MUTED }}>{s.benefit}</p>
            {s.note && (
              <p className="text-[11px] font-semibold mt-0.5" style={{ color: s.eligible ? FOREST : '#8B4A3D' }}>
                ✓ {s.note}
              </p>
            )}
          </div>
        ))}
      </div>
      <p className="text-[11px] text-center pt-1" style={{ color: MUTED }}>
        💡 Click on any scheme card above to ask specific questions about it.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// IneligibleReasonsCard — shows ONLY the ineligible schemes with per-scheme reasons
// ---------------------------------------------------------------------------
function IneligibleReasonsCard({ response, lang, onSelectScheme }) {
  const schemes = response.schemes || [];

  if (schemes.length === 0) {
    // All schemes are eligible — show a congratulations message
    return (
      <div className="mt-2 rounded-xl overflow-hidden border p-3.5" style={{ borderColor: MOSS, backgroundColor: "#F0FBF0" }}>
        <div className="flex items-center gap-2">
          <CheckCircle2 size={20} color={FOREST} />
          <p className="text-sm font-bold" style={{ color: FOREST_DARK }}>{response.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-xl overflow-hidden border space-y-2.5 p-3.5" style={{ borderColor: "#E8B4A0", backgroundColor: CARD }}>
      {/* Header */}
      <div className="flex items-center gap-2 pb-2 border-b" style={{ borderColor: "#FDE8E0" }}>
        <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: "#8B4A3D" }}>
          <XCircle size={14} color="#fff" />
        </div>
        <p className="text-xs font-bold leading-relaxed" style={{ color: "#8B4A3D" }}>
          {response.message}
        </p>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {schemes.map((s) => (
          <div
            key={s.scheme_id}
            onClick={() => onSelectScheme && onSelectScheme(s.name)}
            className="p-2.5 rounded-lg border transition-all cursor-pointer hover:shadow-sm"
            style={{ borderColor: "#E8B4A0", backgroundColor: "#FFFBFB" }}
          >
            {/* Scheme name + category */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold" style={{ color: INK }}>{s.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white border text-gray-600 font-medium">
                  {s.category}
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold"
                style={{ backgroundColor: "#FEF2F2", color: "#8B4A3D" }}>
                Not eligible
              </span>
            </div>

            {/* Reason — highlighted prominently */}
            {s.note && (
              <div className="flex items-start gap-1.5 mt-1.5 p-1.5 rounded-md" style={{ backgroundColor: "#FEF2F2" }}>
                <AlertCircle size={12} color="#C0392B" className="mt-0.5 flex-shrink-0" />
                <p className="text-[11px] font-semibold" style={{ color: "#8B4A3D" }}>
                  {s.note}
                </p>
              </div>
            )}

            {/* Benefit text (lighter, for context) */}
            <p className="text-xs mt-1" style={{ color: MUTED }}>{s.benefit}</p>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-center pt-1" style={{ color: MUTED }}>
        💡 Click on any scheme to ask how you can become eligible.
      </p>
    </div>
  );
}


function TypingBubble({ lang }) {
  const t = UI_TEXT[lang] || UI_TEXT.en;
  return (
    <div className="flex justify-start">
      <div className="flex gap-2 max-w-xs sm:max-w-sm items-center">
        <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: FOREST }}>
          <Leaf size={13} color="#fff" />
        </div>
        <div
          className="px-3 py-2 rounded-2xl rounded-tl-sm text-sm flex items-center gap-2"
          style={{ backgroundColor: CARD, color: MUTED, border: `1px solid ${MOSS}` }}
        >
          <Loader2 size={14} className="animate-spin" style={{ color: FOREST }} />
          {t.typing}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main chat component
// ---------------------------------------------------------------------------
export default function KrushiMitraChatUI({ lang, setLang, profile = {} }) {
  const navigate = useNavigate();
  const t = UI_TEXT[lang] || UI_TEXT.en;

  // Local profile overrides (mini profile bar in the chat header)
  // Starts from the shared App-level profile, user can tweak without leaving chat
  const [localProfile, setLocalProfile] = useState({
    landholding: profile.landholding ?? 1.5,
    region:      profile.region      ?? "Marathwada",
    category:    profile.category    ?? "General",
  });

  // Keep localProfile in sync if the parent profile changes (e.g. after dashboard save)
  useEffect(() => {
    setLocalProfile({
      landholding: profile.landholding ?? 1.5,
      region:      profile.region      ?? "Marathwada",
      category:    profile.category    ?? "General",
    });
  }, [profile.landholding, profile.region, profile.category]);

  const [showProfile, setShowProfile] = useState(true);
  const [input, setInput]             = useState("");
  const [isLoading, setIsLoading]     = useState(false);
  const [quickChips, setQuickChips]   = useState([]);
  const [messages, setMessages]       = useState([
    { id: 1, from: "bot", text: t.greeting },
  ]);

  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Load scheme names from /schemes for quick-reply chips
  useEffect(() => {
    fetch(SCHEMES_ENDPOINT)
      .then((r) => r.ok ? r.json() : [])
      .then((data) => {
        const chips = data
          .map((s) => s.scheme_name?.[lang] || s.scheme_name?.en || s.scheme_id)
          .filter(Boolean)
          .slice(0, 6); // show max 6 chips
        setQuickChips(chips);
      })
      .catch(() => {
        // Fallback chips if server unreachable
        setQuickChips(["PM-KISAN", "Solar pump", "Crop insurance", "Drip irrigation"]);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  // Merge local profile bar values over the full parent profile for the API call
  const effectiveProfile = { ...profile, ...localProfile };

  async function handleSend(rawText) {
    const text = (rawText ?? input).trim();
    if (!text || isLoading) return;

    const userMsg = { id: Date.now(), from: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(CHAT_ENDPOINT, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          query:   text,
          lang:    lang,
          profile: effectiveProfile,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server error ${res.status}`);
      }

      const data = await res.json();

      let botMsg;
      if (data.found) {
        botMsg = { id: Date.now() + 1, from: "bot", response: data };
      } else {
        botMsg = { id: Date.now() + 1, from: "bot", text: t.notFound };
      }
      setMessages((m) => [...m, botMsg]);

    } catch {
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, from: "bot", text: t.noServer },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="w-full h-full min-h-screen flex flex-col" style={{ backgroundColor: CREAM, fontFamily: "Georgia, 'Noto Serif Devanagari', serif" }}>

      {/* ---- Header ---- */}
      <div className="px-4 py-3 flex items-center justify-between" style={{ backgroundColor: FOREST }}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="text-white hover:opacity-80 transition-opacity p-1">
            <ArrowLeft size={22} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ backgroundColor: FOREST_DARK }}>
              <Sprout size={18} color={MOSS} />
            </div>
            <div>
              <p className="text-white font-bold leading-tight" style={{ fontSize: 17 }}>{t.title}</p>
              <p className="leading-tight" style={{ color: MOSS, fontSize: 11 }}>{t.tagline}</p>
            </div>
          </div>
        </div>

        {/* Language toggle */}
        <div className="flex rounded-full overflow-hidden border" style={{ borderColor: MOSS }}>
          {["en", "hi", "mr"].map((code) => (
            <button
              key={code}
              onClick={() => setLang(code)}
              className="px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: lang === code ? GOLD : "transparent", color: lang === code ? FOREST_DARK : "#fff" }}
            >
              {code === "en" ? "EN" : code === "hi" ? "हिं" : "मर"}
            </button>
          ))}
        </div>
      </div>

      {/* ---- Mini profile bar ---- */}
      <div style={{ backgroundColor: "#EDF1E8", borderBottom: `1px solid ${MOSS}` }}>
        <button
          onClick={() => setShowProfile((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold"
          style={{ color: FOREST }}
        >
          <span className="flex items-center gap-1"><User size={13} /> {t.profileLabel}</span>
          <ChevronDown size={14} style={{ transform: showProfile ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
        </button>

        {showProfile && (
          <div className="px-4 pb-3 flex flex-wrap gap-3 text-xs">
            <label className="flex items-center gap-1" style={{ color: INK }}>
              {t.landholding}:
              <input
                type="number" step="0.1"
                value={localProfile.landholding}
                onChange={(e) => setLocalProfile((p) => ({ ...p, landholding: parseFloat(e.target.value) || 0 }))}
                className="w-16 px-1 py-0.5 rounded border"
                style={{ borderColor: MOSS }}
              />
            </label>
            <label className="flex items-center gap-1" style={{ color: INK }}>
              <MapPin size={12} /> {t.region}:
              <select
                value={localProfile.region}
                onChange={(e) => setLocalProfile((p) => ({ ...p, region: e.target.value }))}
                className="px-1 py-0.5 rounded border"
                style={{ borderColor: MOSS }}
              >
                {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1" style={{ color: INK }}>
              {t.category}:
              <select
                value={localProfile.category}
                onChange={(e) => setLocalProfile((p) => ({ ...p, category: e.target.value }))}
                className="px-1 py-0.5 rounded border"
                style={{ borderColor: MOSS }}
              >
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
        )}
      </div>

      {/* ---- Messages ---- */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((m) =>
          m.from === "user" ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-xs sm:max-w-sm px-3 py-2 rounded-2xl rounded-tr-sm text-sm text-white" style={{ backgroundColor: MOSS }}>
                {m.text}
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start">
              <div className="flex gap-2 max-w-xs sm:max-w-sm">
                <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: FOREST }}>
                  <Leaf size={13} color="#fff" />
                </div>
                <div className="w-full">
                  {m.text && (
                    <div className="px-3 py-2 rounded-2xl rounded-tl-sm text-sm" style={{ backgroundColor: CARD, color: INK, border: `1px solid ${MOSS}` }}>
                      {m.text}
                    </div>
                  )}
                  {m.response?.type === "all_schemes" && (
                    <AllSchemesCard
                      response={m.response}
                      lang={lang}
                      onSelectScheme={(schemeName) => handleSend(`Tell me details about ${schemeName}`)}
                    />
                  )}
                  {m.response?.type === "ineligible_reasons" && (
                    <IneligibleReasonsCard
                      response={m.response}
                      lang={lang}
                      onSelectScheme={(schemeName) => handleSend(`Why am I not eligible for ${schemeName}?`)}
                    />
                  )}
                  {m.response?.type === "greeting" && (
                    <div className="px-3.5 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed" style={{ backgroundColor: CARD, color: INK, border: `1px solid ${MOSS}` }}>
                      {m.response.message}
                    </div>
                  )}
                  {(!m.response?.type || m.response?.type === "scheme") && m.response?.found && (
                    <div>
                      {m.response.message && (
                        <div
                          className="px-3.5 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed mb-2 shadow-xs"
                          style={{ backgroundColor: CARD, color: INK, border: `1px solid ${MOSS}`, whiteSpace: "pre-line" }}
                        >
                          {m.response.message}
                        </div>
                      )}
                      <VerdictCard response={m.response} lang={lang} />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        )}

        {/* Typing indicator while API is in flight */}
        {isLoading && <TypingBubble lang={lang} />}

        <div ref={bottomRef} />
      </div>

      {/* ---- Quick-reply chips ---- */}
      <div className="px-4 flex flex-wrap gap-2 pb-2">
        {quickChips.map((q) => (
          <button
            key={q}
            onClick={() => handleSend(q)}
            disabled={isLoading}
            className="text-xs px-3 py-1 rounded-full font-semibold"
            style={{
              backgroundColor: "#fff",
              color: isLoading ? MUTED : FOREST,
              border: `1px solid ${isLoading ? MUTED : FOREST}`,
              cursor: isLoading ? "not-allowed" : "pointer",
            }}
          >
            {q}
          </button>
        ))}
      </div>

      {/* ---- Input bar ---- */}
      <div className="px-4 pb-4 pt-1 flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-full" style={{ backgroundColor: "#fff", border: `1px solid ${MOSS}` }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isLoading && handleSend()}
            placeholder={t.placeholder}
            disabled={isLoading}
            className="flex-1 text-sm outline-none bg-transparent"
            style={{ color: INK }}
          />
          <Mic size={16} color={MUTED} />
        </div>
        <button
          onClick={() => handleSend()}
          disabled={isLoading}
          className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: isLoading ? MUTED : FOREST, cursor: isLoading ? "not-allowed" : "pointer" }}
        >
          {isLoading
            ? <Loader2 size={16} color="#fff" className="animate-spin" />
            : <Send size={16} color="#fff" />
          }
        </button>
      </div>
    </div>
  );
}