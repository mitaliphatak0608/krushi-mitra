import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Leaf, Send, Mic, CheckCircle2, XCircle, AlertCircle, MapPin,
  Sprout, ExternalLink, ChevronDown, User, ArrowLeft, Loader2,
  Sparkles, Globe, ChevronUp, AlertTriangle,
} from "lucide-react";
import VoiceAssistant from "./VoiceAssistant";

// ---------------------------------------------------------------------------
// API endpoints (unchanged)
// ---------------------------------------------------------------------------
const CHAT_ENDPOINT    = "http://localhost:8000/chat";
const AI_CHAT_ENDPOINT = "http://localhost:8000/ai/chat";
const SCHEMES_ENDPOINT = "http://localhost:8000/schemes";

// ---------------------------------------------------------------------------
// Design tokens — single source of truth
// ---------------------------------------------------------------------------
const C = {
  forest:      "#2C5F2D",
  forestDark:  "#1F4620",
  forestLight: "#3A7A3C",
  moss:        "#97BC62",
  mossLight:   "#B8D48C",
  gold:        "#E8A33D",
  goldLight:   "#F5C87A",
  cream:       "#F4F7F1",
  white:       "#FFFFFF",
  ink:         "#1A2E1B",
  inkMid:      "#2D4A2F",
  muted:       "#5C6F5E",
  mutedLight:  "#8FA08F",
  border:      "#D8E5D0",
  borderLight: "#EBF3E6",
  redDark:     "#7F2B24",
  redBg:       "#FEF2F1",
  redBorder:   "#F9C5BF",
};

const REGIONS    = ["Marathwada", "Vidarbha", "Western Maharashtra"];
const CATEGORIES = ["General", "SC", "ST", "OBC"];

// ---------------------------------------------------------------------------
// Application status badge config
// ---------------------------------------------------------------------------
function getStatusConfig(status) {
  const cfg = {
    open:          { emoji: "🟢", label: "Open",                color: "#166534", bg: "#dcfce7", border: "#86efac" },
    seasonal:      { emoji: "🟢", label: "Open / Seasonal",     color: "#0369a1", bg: "#e0f2fe", border: "#7dd3fc" },
    active_auto:   { emoji: "🟢", label: "Active — Auto",       color: "#166534", bg: "#dcfce7", border: "#86efac" },
    portal_closed: { emoji: "🟠", label: "Portal Closed",       color: "#92400e", bg: "#fef3c7", border: "#fcd34d" },
    closed:        { emoji: "🔴", label: "Closed",              color: "#991b1b", bg: "#fee2e2", border: "#fca5a5" },
    cycle_based:   { emoji: "🟡", label: "Cycle-Based",         color: "#92400e", bg: "#fef3c7", border: "#fcd34d" },
    unconfirmed:   { emoji: "🟡", label: "Not Confirmed",       color: "#92400e", bg: "#fef3c7", border: "#fcd34d" },
  };
  return cfg[status] || cfg.open;
}

function StatusPill({ status, small = false }) {
  const c = getStatusConfig(status);
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "3px",
      fontSize: small ? "0.6rem" : "0.65rem", fontWeight: 700,
      padding: small ? "0.1rem 0.45rem" : "0.2rem 0.6rem",
      borderRadius: "999px",
      backgroundColor: c.bg, color: c.color,
      border: `1px solid ${c.border}`,
      whiteSpace: "nowrap", letterSpacing: "0.01em",
    }}>
      {c.emoji} {c.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Multilingual UI strings
// ---------------------------------------------------------------------------
const UI_TEXT = {
  en: {
    title: "Krushi Mitra",
    subtitle: "AI Agricultural Assistant",
    profileLabel: "Your Profile",
    landholding: "Landholding (ha)",
    region: "Region", category: "Category",
    placeholder: "Ask about any scheme… e.g. Am I eligible for Solar Pump?",
    send: "Send", eligible: "Eligible", notEligible: "Not eligible",
    verify: "Verify at CSC / official portal before applying",
    docs: "Documents needed", officialLink: "Official portal",
    greeting: "Namaste! Ask me about the schemes— in English, Hindi, or Marathi.",
    notFound: "I couldn't find a matching scheme. Try: crop insurance, drip irrigation, solar pump, or kisan credit card.",
    noServer: "Cannot reach the server. Please make sure the backend is running on port 8000.",
    typing: "Thinking…",
    aiOn: "Smart AI", aiOff: "Smart AI",
    aiTitle: "Toggle Smart AI mode (uses Gemini AI + semantic search)",
    sourcesTitle: "Verified Sources",
    profileExpand: "Personalize for accurate eligibility",
    backToDashboard: "Dashboard",
  },
  hi: {
    title: "कृषी मित्र",
    subtitle: "एआई कृषि सहायक",
    profileLabel: "आपकी प्रोफ़ाइल",
    landholding: "भूमि (हेक्टेयर)",
    region: "क्षेत्र", category: "श्रेणी",
    placeholder: "अपना प्रश्न लिखें… जैसे सौर पंप के लिए मैं पात्र हूं?",
    send: "भेजें", eligible: "पात्र", notEligible: "अपात्र",
    verify: "आवेदन से पहले सीएससी / आधिकारिक पोर्टल पर सत्यापित करें",
    docs: "आवश्यक दस्तावेज़", officialLink: "आधिकारिक पोर्टल",
    greeting: "नमस्ते! पीएम-किसान, सूक्ष्म सिंचाई, सौर पंप, फसल बीमा के बारे में पूछें।",
    notFound: "इस प्रश्न के लिए योजना नहीं मिली। कोशिश करें: फसल बीमा, ड्रिप सिंचाई, सौर पंप।",
    noServer: "सर्वर से कनेक्ट नहीं हो सका। कृपया बैकएंड चालू करें।",
    typing: "सोच रहा हूं…",
    aiOn: "स्मार्ट AI", aiOff: "स्मार्ट AI",
    aiTitle: "स्मार्ट AI टॉगल करें",
    sourcesTitle: "सत्यापित स्रोत",
    profileExpand: "सटीक पात्रता के लिए व्यक्तिगत करें",
    backToDashboard: "डैशबोर्ड",
  },
  mr: {
    title: "कृषी मित्र",
    subtitle: "एआय कृषी सहाय्यक",
    profileLabel: "तुमची प्रोफाइल",
    landholding: "जमीन (हेक्टर)",
    region: "प्रदेश", category: "प्रवर्ग",
    placeholder: "तुमचा प्रश्न लिहा… उदा. सौर पंपसाठी मी पात्र आहे का?",
    send: "पाठवा", eligible: "पात्र", notEligible: "अपात्र",
    verify: "अर्ज करण्यापूर्वी सीएससी / अधिकृत पोर्टलवर पडताळणी करा",
    docs: "आवश्यक कागदपत्रे", officialLink: "अधिकृत पोर्टल",
    greeting: "नमस्कार! पीएम-किसान, सूक्ष्म सिंचन, सौर पंप, पीक विमा याबद्दल विचारा.",
    notFound: "या प्रश्नासाठी योजना सापडली नाही. वापरून पाहा: पीक विमा, ठिबक सिंचन, सौर पंप.",
    noServer: "सर्व्हरशी कनेक्ट होता आले नाही. कृपया बॅकएंड सुरू करा.",
    typing: "विचार करतो आहे…",
    aiOn: "स्मार्ट AI", aiOff: "स्मार्ट AI",
    aiTitle: "स्मार्ट AI टॉगल करा",
    sourcesTitle: "अधिकृत संदर्भ",
    profileExpand: "अचूक पात्रतेसाठी वैयक्तिक करा",
    backToDashboard: "डॅशबोर्ड",
  },
};

// ---------------------------------------------------------------------------
// VerdictCard — single-scheme eligibility result
// ---------------------------------------------------------------------------
function VerdictCard({ response, lang }) {
  const ok = response.eligible;
  const t  = UI_TEXT[lang] || UI_TEXT.en;
  const schemeName  = response.scheme_name?.[lang] || response.scheme_id || "";
  const benefitText = response.benefit?.[lang] || "";
  const documents   = response.documents?.[lang] || [];

  return (
    <div style={{
      marginTop: "0.75rem",
      borderRadius: "14px",
      overflow: "hidden",
      border: `1px solid ${ok ? C.border : C.redBorder}`,
      backgroundColor: C.white,
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    }}>
      {/* Header band */}
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        padding: "10px 14px",
        backgroundColor: ok ? C.forest : C.redDark,
      }}>
        {ok
          ? <CheckCircle2 size={16} color="#fff" aria-hidden="true" />
          : <XCircle size={16} color="#fff" aria-hidden="true" />
        }
        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "#fff" }}>
          {ok ? t.eligible : t.notEligible}
        </span>
        {schemeName && (
          <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.85)", marginLeft: "2px" }}>
            — {schemeName}
          </span>
        )}
      </div>

      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: "8px" }}>

        {/* Benefit */}
        {benefitText && (
          <p style={{ fontSize: "0.82rem", color: C.ink, lineHeight: 1.55, margin: 0 }}>
            {benefitText}
          </p>
        )}

        {/* Eligibility note */}
        {response.note && (
          <p style={{
            fontSize: "0.82rem", fontWeight: 600, margin: 0,
            color: ok ? C.forest : C.redDark,
            lineHeight: 1.5,
          }}>
            {response.note}
          </p>
        )}

        {/* Documents */}
        {documents.length > 0 && (
          <div>
            <p style={{ fontSize: "0.72rem", fontWeight: 700, color: C.muted, marginBottom: "5px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {t.docs}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {documents.map((d, i) => (
                <span key={i} style={{
                  fontSize: "0.72rem", padding: "3px 8px", borderRadius: "999px",
                  backgroundColor: C.cream, color: C.ink,
                  border: `1px solid ${C.border}`,
                }}>
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Official link */}
        {response.link && response.link.startsWith("https://") && (
          <div style={{ display: "flex", alignItems: "center", gap: "5px", paddingTop: "2px" }}>
            <ExternalLink size={12} color={C.forest} aria-hidden="true" />
            <a
              href={response.link}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open official website for ${schemeName}`}
              style={{ fontSize: "0.72rem", fontWeight: 600, color: C.forest, textDecoration: "none" }}
              onMouseEnter={e => e.currentTarget.style.textDecoration = "underline"}
              onMouseLeave={e => e.currentTarget.style.textDecoration = "none"}
            >
              {t.officialLink || "Official Website"} ↗
            </a>
          </div>
        )}

        {/* Disclaimer */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "5px", paddingTop: "2px" }}>
          <AlertCircle size={12} color={C.gold} style={{ flexShrink: 0, marginTop: "1px" }} aria-hidden="true" />
          <span style={{ fontSize: "0.7rem", color: C.muted, lineHeight: 1.4 }}>{t.verify}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AllSchemesCard — lists all 11 schemes with eligibility
// ---------------------------------------------------------------------------
function AllSchemesCard({ response, lang, onSelectScheme }) {
  const t = UI_TEXT[lang] || UI_TEXT.en;
  const schemes = response.schemes || [];

  return (
    <div style={{
      marginTop: "0.75rem",
      borderRadius: "14px",
      overflow: "hidden",
      border: `1px solid ${C.border}`,
      backgroundColor: C.white,
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        padding: "10px 14px",
        backgroundColor: C.cream,
        borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{
          width: 24, height: 24, borderRadius: "50%",
          backgroundColor: C.forest,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <Sprout size={13} color="#fff" aria-hidden="true" />
        </div>
        <p style={{ fontSize: "0.78rem", fontWeight: 700, color: C.inkMid, margin: 0, lineHeight: 1.4 }}>
          {response.message}
        </p>
      </div>

      <div style={{ maxHeight: "380px", overflowY: "auto", padding: "10px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {schemes.map((s) => (
            <div
              key={s.scheme_id}
              onClick={() => onSelectScheme && onSelectScheme(s.name)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelectScheme && onSelectScheme(s.name); } }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "10px 12px",
                borderRadius: "10px",
                border: `1px solid ${s.eligible ? C.border : C.redBorder}`,
                backgroundColor: s.eligible ? "#F8FBF5" : "#FFFAF9",
                cursor: "pointer",
                transition: "box-shadow 0.15s, transform 0.1s",
              }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.08)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 700, color: C.ink }}>{s.name}</span>
                  <span style={{
                    fontSize: "0.65rem", padding: "1px 7px", borderRadius: "999px",
                    backgroundColor: C.cream, color: C.muted,
                    border: `1px solid ${C.border}`, fontWeight: 600,
                  }}>
                    {s.category}
                  </span>
                </div>
                <span style={{
                  fontSize: "0.65rem", padding: "2px 8px", borderRadius: "999px", fontWeight: 700,
                  backgroundColor: s.eligible ? "#DCFCE7" : C.redBg,
                  color: s.eligible ? "#166534" : C.redDark,
                }}>
                  {s.eligible ? (t.eligible || "Eligible") : (t.notEligible || "Not eligible")}
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: C.muted, margin: "4px 0 0", lineHeight: 1.45 }}>
                {s.benefit}
              </p>
              {s.note && (
                <p style={{ fontSize: "0.72rem", fontWeight: 600, margin: "3px 0 0", color: s.eligible ? C.forest : C.redDark }}>
                  ✓ {s.note}
                </p>
              )}
              {s.link && s.link.startsWith("https://") && (
                <div style={{ marginTop: "6px" }}>
                  <a
                    href={s.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open official website for ${s.name}`}
                    style={{ fontSize: "0.72rem", fontWeight: 600, color: C.forest, textDecoration: "none" }}
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={e => e.currentTarget.style.textDecoration = "underline"}
                    onMouseLeave={e => e.currentTarget.style.textDecoration = "none"}
                  >
                    {t.officialLink || "Official Website"} ↗
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <p style={{ fontSize: "0.7rem", textAlign: "center", color: C.mutedLight, padding: "8px 0 10px", margin: 0 }}>
        💡 Tap any scheme to ask a specific question about it
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// IneligibleReasonsCard
// ---------------------------------------------------------------------------
function IneligibleReasonsCard({ response, lang, onSelectScheme }) {
  const schemes = response.schemes || [];

  if (schemes.length === 0) {
    return (
      <div style={{
        marginTop: "0.75rem", borderRadius: "14px", overflow: "hidden",
        border: `1px solid ${C.border}`, backgroundColor: "#F0FBF0", padding: "12px 14px",
        display: "flex", alignItems: "center", gap: "8px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      }}>
        <CheckCircle2 size={18} color={C.forest} aria-hidden="true" />
        <p style={{ fontSize: "0.82rem", fontWeight: 700, color: C.forest, margin: 0, lineHeight: 1.4 }}>
          {response.message}
        </p>
      </div>
    );
  }

  return (
    <div style={{
      marginTop: "0.75rem",
      borderRadius: "14px",
      overflow: "hidden",
      border: `1px solid ${C.redBorder}`,
      backgroundColor: C.white,
      boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        padding: "10px 14px",
        backgroundColor: C.redBg,
        borderBottom: `1px solid ${C.redBorder}`,
      }}>
        <div style={{
          width: 22, height: 22, borderRadius: "50%", backgroundColor: C.redDark,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <XCircle size={12} color="#fff" aria-hidden="true" />
        </div>
        <p style={{ fontSize: "0.78rem", fontWeight: 700, color: C.redDark, margin: 0, lineHeight: 1.4 }}>
          {response.message}
        </p>
      </div>

      <div style={{ maxHeight: "380px", overflowY: "auto", padding: "10px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {schemes.map((s) => (
            <div
              key={s.scheme_id}
              onClick={() => onSelectScheme && onSelectScheme(s.name)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelectScheme && onSelectScheme(s.name); } }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "10px 12px",
                borderRadius: "10px",
                border: `1px solid ${C.redBorder}`,
                backgroundColor: C.redBg,
                cursor: "pointer",
                transition: "box-shadow 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.08)"; }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px", flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 700, color: C.ink }}>{s.name}</span>
                  <span style={{
                    fontSize: "0.65rem", padding: "1px 7px", borderRadius: "999px",
                    backgroundColor: C.white, color: C.muted,
                    border: `1px solid ${C.redBorder}`, fontWeight: 600,
                  }}>
                    {s.category}
                  </span>
                </div>
                <span style={{
                  fontSize: "0.65rem", padding: "2px 8px", borderRadius: "999px", fontWeight: 700,
                  backgroundColor: C.redBg, color: C.redDark,
                  border: `1px solid ${C.redBorder}`,
                }}>
                  Not eligible
                </span>
              </div>

              {s.note && (
                <div style={{
                  display: "flex", alignItems: "flex-start", gap: "5px",
                  marginTop: "6px", padding: "6px 8px", borderRadius: "8px",
                  backgroundColor: "#FFEDE9",
                }}>
                  <AlertTriangle size={11} color="#B91C1C" style={{ flexShrink: 0, marginTop: "1px" }} aria-hidden="true" />
                  <p style={{ fontSize: "0.72rem", fontWeight: 600, color: C.redDark, margin: 0, lineHeight: 1.4 }}>
                    {s.note}
                  </p>
                </div>
              )}

              <p style={{ fontSize: "0.73rem", color: C.muted, margin: "4px 0 0", lineHeight: 1.4 }}>
                {s.benefit}
              </p>

              {s.link && s.link.startsWith("https://") && (
                <div style={{ marginTop: "6px" }}>
                  <a
                    href={s.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open official website for ${s.name}`}
                    style={{ fontSize: "0.72rem", fontWeight: 600, color: C.redDark, textDecoration: "none" }}
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={e => e.currentTarget.style.textDecoration = "underline"}
                    onMouseLeave={e => e.currentTarget.style.textDecoration = "none"}
                  >
                    {t.officialLink || "Official Website"} ↗
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <p style={{ fontSize: "0.7rem", textAlign: "center", color: C.mutedLight, padding: "8px 0 10px", margin: 0 }}>
        💡 Tap any scheme to ask how to become eligible
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TypingBubble — animated three-dot loader
// ---------------------------------------------------------------------------
function TypingBubble() {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start", padding: "0 12px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          backgroundColor: C.forest,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <Leaf size={12} color="#fff" aria-hidden="true" />
        </div>
        <div style={{
          padding: "10px 14px", borderRadius: "18px", borderTopLeftRadius: "4px",
          backgroundColor: C.white,
          border: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", gap: "5px",
        }}>
          {[0, 1, 2].map((i) => (
            <span key={i} style={{
              width: 7, height: 7, borderRadius: "50%",
              backgroundColor: C.moss,
              display: "inline-block",
              animation: `km-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SourcesChip — shows verified sources in AI mode
// ---------------------------------------------------------------------------
function SourcesChip({ sources, lang }) {
  const t = UI_TEXT[lang] || UI_TEXT.en;
  if (!sources || sources.length === 0) return null;
  return (
    <div style={{
      marginTop: "6px",
      padding: "8px 10px",
      borderRadius: "10px",
      backgroundColor: "#F0FBF0",
      border: `1px solid ${C.border}`,
    }}>
      <p style={{ fontSize: "0.7rem", fontWeight: 700, color: C.forest, margin: "0 0 4px", display: "flex", alignItems: "center", gap: "4px" }}>
        <span>📚</span> {t.sourcesTitle}
      </p>
      {sources.map((s, i) => (
        <p key={i} style={{ fontSize: "0.7rem", color: C.muted, margin: "1px 0 0", lineHeight: 1.4 }}>
          • {s.name}{s.authority ? ` (${s.authority})` : ""}
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ErrorBubble
// ---------------------------------------------------------------------------
function ErrorBubble({ text }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: "8px",
      padding: "10px 14px",
      borderRadius: "12px",
      backgroundColor: C.redBg,
      border: `1px solid ${C.redBorder}`,
      marginTop: "4px",
    }}>
      <AlertCircle size={14} color={C.redDark} style={{ flexShrink: 0, marginTop: "1px" }} aria-hidden="true" />
      <p style={{ fontSize: "0.82rem", color: C.redDark, margin: 0, lineHeight: 1.5 }}>{text}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main KrushiMitraChatUI component
// ---------------------------------------------------------------------------
export default function KrushiMitraChatUI({ lang, setLang, profile = {} }) {
  const navigate = useNavigate();
  const t = UI_TEXT[lang] || UI_TEXT.en;

  // Local profile overrides
  const [localProfile, setLocalProfile] = useState({
    landholding: profile.landholding ?? 1.5,
    region:      profile.region      ?? "Marathwada",
    category:    profile.category    ?? "General",
  });

  useEffect(() => {
    setLocalProfile({
      landholding: profile.landholding ?? 1.5,
      region:      profile.region      ?? "Marathwada",
      category:    profile.category    ?? "General",
    });
  }, [profile.landholding, profile.region, profile.category]);

  const [showProfile, setShowProfile] = useState(false);
  const [input, setInput]             = useState("");
  const [isLoading, setIsLoading]     = useState(false);
  const [showVoice, setShowVoice]     = useState(false);
  const [useAI, setUseAI]             = useState(true);
  const [quickChips, setQuickChips]   = useState([]);
  const [messages, setMessages]       = useState([
    { id: 1, from: "bot", text: t.greeting },
  ]);

  const bottomRef  = useRef(null);
  const inputRef   = useRef(null);

  // Auto-scroll
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Load quick-reply chips from /schemes
  useEffect(() => {
    fetch(SCHEMES_ENDPOINT)
      .then((r) => r.ok ? r.json() : [])
      .then((data) => {
        const chips = data
          .map((s) => s.scheme_name?.[lang] || s.scheme_name?.en || s.scheme_id)
          .filter(Boolean)
          .slice(0, 6);
        setQuickChips(chips);
      })
      .catch(() => {
        setQuickChips(["PM-KISAN", "Solar pump", "Crop insurance", "Drip irrigation"]);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  const effectiveProfile = { ...profile, ...localProfile };

  // ---- Core send logic (unchanged from original) ----
  async function handleSend(rawText) {
    const text = (rawText ?? input).trim();
    if (!text || isLoading) return;

    const userMsg = { id: Date.now(), from: "user", text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const endpoint = useAI ? AI_CHAT_ENDPOINT : CHAT_ENDPOINT;
      const payload  = useAI
        ? { message: text, language: lang, profile: effectiveProfile }
        : { query: text, lang: lang, profile: effectiveProfile };

      const res = await fetch(endpoint, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();

      let botMsg;
      if (useAI) {
        const found = data.found !== false;
        if (found) {
          botMsg = {
            id: Date.now() + 1, from: "bot",
            text: data.answer || data.message || "",
            response: data,
            sources: data.sources || [],
          };
        } else {
          botMsg = {
            id: Date.now() + 1, from: "bot",
            text: data.answer || t.notFound,
            isError: !data.answer,
          };
        }
      } else {
        if (data.found) {
          botMsg = { id: Date.now() + 1, from: "bot", response: data };
        } else {
          botMsg = { id: Date.now() + 1, from: "bot", text: t.notFound, isError: false };
        }
      }
      setMessages((m) => [...m, botMsg]);
    } catch {
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, from: "bot", text: t.noServer, isError: true },
      ]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  // ---- Key injection for bouncing dots animation ----
  useEffect(() => {
    const id = "km-bounce-style";
    if (document.getElementById(id)) return;
    const style = document.createElement("style");
    style.id = id;
    style.textContent = `
      @keyframes km-bounce {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
        40%            { transform: translateY(-5px); opacity: 1; }
      }
      @keyframes km-pulse-ring {
        0%   { transform: scale(1); opacity: 0.7; }
        100% { transform: scale(1.6); opacity: 0; }
      }
      .km-chat-input:focus { outline: none; }
      .km-chip:hover { background-color: #EBF3E5 !important; }
      .km-send-btn:hover:not(:disabled) { background-color: #3A7A3C !important; transform: scale(1.05); }
      .km-send-btn:active:not(:disabled) { transform: scale(0.97); }
      .km-mic-btn:hover { background-color: #E8F0E4 !important; }
      .km-lang-btn:hover { opacity: 0.85; }
      .km-ai-toggle:hover { filter: brightness(1.05); }
    `;
    document.head.appendChild(style);
  }, []);

  // =========================================================================
  // RENDER
  // =========================================================================
  return (
    <div style={{
      width: "100%",
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      backgroundColor: C.cream,
      fontFamily: "'Inter', 'Noto Serif Devanagari', system-ui, sans-serif",
      overflow: "hidden",
    }}>

      {/* ================================================================
          HEADER
      ================================================================ */}
      <header style={{
        backgroundColor: C.forest,
        padding: "0 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "60px",
        flexShrink: 0,
        boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
        zIndex: 10,
      }}>
        {/* Left: back + title */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => navigate("/dashboard")}
            title={t.backToDashboard}
            aria-label={t.backToDashboard}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: "#fff", display: "flex", alignItems: "center",
              padding: "6px", borderRadius: "8px",
              opacity: 0.85, transition: "opacity 0.15s",
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = "1"}
            onMouseLeave={e => e.currentTarget.style.opacity = "0.85"}
          >
            <ArrowLeft size={20} aria-hidden="true" />
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
            <div style={{
              width: 36, height: 36, borderRadius: "10px",
              backgroundColor: C.forestDark,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Sprout size={18} color={C.moss} aria-hidden="true" />
            </div>
            <div>
              <p style={{ margin: 0, fontWeight: 800, fontSize: "1rem", color: "#fff", letterSpacing: "-0.01em", lineHeight: 1.2 }}>
                {t.title}
              </p>
              <p style={{ margin: 0, fontSize: "0.68rem", color: C.mossLight, lineHeight: 1 }}>
                {t.subtitle}
              </p>
            </div>
          </div>
        </div>

        {/* Right: AI toggle + language selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Smart AI toggle */}
          <button
            onClick={() => setUseAI((v) => !v)}
            className="km-ai-toggle"
            title={t.aiTitle}
            aria-label={`${t.aiOn} is currently ${useAI ? "ON" : "OFF"}. Click to toggle.`}
            aria-pressed={useAI}
            style={{
              display: "flex", alignItems: "center", gap: "5px",
              padding: "5px 10px", borderRadius: "999px",
              fontSize: "0.7rem", fontWeight: 700,
              backgroundColor: useAI ? C.gold : "rgba(255,255,255,0.12)",
              color: useAI ? C.forestDark : "#fff",
              border: `1.5px solid ${useAI ? C.gold : "rgba(255,255,255,0.3)"}`,
              cursor: "pointer", transition: "all 0.2s",
              letterSpacing: "0.01em",
            }}
          >
            <Sparkles size={12} aria-hidden="true" />
            <span>{t.aiOn}</span>
            <span style={{
              padding: "1px 5px", borderRadius: "999px",
              backgroundColor: useAI ? C.forestDark : "rgba(255,255,255,0.2)",
              color: useAI ? C.gold : "#fff",
              fontSize: "0.6rem", fontWeight: 800,
            }}>
              {useAI ? "ON" : "OFF"}
            </span>
          </button>

          {/* Language selector */}
          <div style={{
            display: "flex", borderRadius: "999px", overflow: "hidden",
            border: `1.5px solid rgba(151,188,98,0.6)`,
          }}
            role="group" aria-label="Language selector"
          >
            {["en", "hi", "mr"].map((code) => (
              <button
                key={code}
                onClick={() => setLang(code)}
                className="km-lang-btn"
                aria-label={code === "en" ? "English" : code === "hi" ? "Hindi" : "Marathi"}
                aria-pressed={lang === code}
                style={{
                  padding: "4px 9px",
                  fontSize: "0.68rem", fontWeight: 700,
                  backgroundColor: lang === code ? C.gold : "transparent",
                  color: lang === code ? C.forestDark : "#fff",
                  border: "none", cursor: "pointer",
                  transition: "background-color 0.15s",
                }}
              >
                {code === "en" ? "EN" : code === "hi" ? "हिं" : "मर"}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ================================================================
          PROFILE BAR (collapsible)
      ================================================================ */}
      <div style={{
        backgroundColor: "#EEF4E8",
        borderBottom: `1px solid ${C.border}`,
        flexShrink: 0,
      }}>
        <button
          onClick={() => setShowProfile((v) => !v)}
          aria-expanded={showProfile}
          aria-label="Toggle profile panel"
          style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "8px 16px",
            fontSize: "0.72rem", fontWeight: 600, color: C.forest,
            background: "none", border: "none", cursor: "pointer",
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <User size={12} aria-hidden="true" />
            {t.profileLabel}
            <span style={{
              fontSize: "0.64rem", color: C.mutedLight, fontWeight: 400, marginLeft: "2px",
            }}>
              — {t.profileExpand}
            </span>
          </span>
          {showProfile
            ? <ChevronUp size={13} aria-hidden="true" />
            : <ChevronDown size={13} aria-hidden="true" />
          }
        </button>

        {showProfile && (
          <div style={{
            padding: "0 16px 12px",
            display: "flex", flexWrap: "wrap", gap: "12px",
          }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: C.ink }}>
              {t.landholding}:
              <input
                type="number" step="0.1" min="0"
                value={localProfile.landholding}
                onChange={(e) => setLocalProfile((p) => ({ ...p, landholding: parseFloat(e.target.value) || 0 }))}
                style={{
                  width: 64, padding: "3px 6px", borderRadius: "8px",
                  border: `1.5px solid ${C.border}`, fontSize: "0.75rem",
                  color: C.ink, backgroundColor: C.white,
                }}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: C.ink }}>
              <MapPin size={11} aria-hidden="true" /> {t.region}:
              <select
                value={localProfile.region}
                onChange={(e) => setLocalProfile((p) => ({ ...p, region: e.target.value }))}
                style={{
                  padding: "3px 6px", borderRadius: "8px",
                  border: `1.5px solid ${C.border}`, fontSize: "0.75rem",
                  color: C.ink, backgroundColor: C.white,
                }}
              >
                {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: C.ink }}>
              {t.category}:
              <select
                value={localProfile.category}
                onChange={(e) => setLocalProfile((p) => ({ ...p, category: e.target.value }))}
                style={{
                  padding: "3px 6px", borderRadius: "8px",
                  border: `1.5px solid ${C.border}`, fontSize: "0.75rem",
                  color: C.ink, backgroundColor: C.white,
                }}
              >
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
        )}
      </div>

      {/* ================================================================
          MESSAGE LIST
      ================================================================ */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "16px 12px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
        role="log" aria-label="Chat conversation" aria-live="polite"
      >
        {messages.map((m) =>
          m.from === "user" ? (
            // ---- USER BUBBLE ----
            <div key={m.id} style={{ display: "flex", justifyContent: "flex-end", paddingLeft: "16%" }}>
              <div style={{
                padding: "10px 14px",
                borderRadius: "18px", borderTopRightRadius: "4px",
                backgroundColor: C.forest,
                color: "#fff",
                fontSize: "0.88rem",
                lineHeight: 1.55,
                maxWidth: "100%",
                wordBreak: "break-word",
                boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
              }}>
                {m.text}
              </div>
            </div>
          ) : (
            // ---- ASSISTANT BUBBLE ----
            <div key={m.id} style={{ display: "flex", justifyContent: "flex-start", paddingRight: "8%" }}>
              <div style={{ display: "flex", gap: "8px", alignItems: "flex-start", maxWidth: "100%" }}>
                {/* Avatar */}
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  backgroundColor: C.forest,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0, marginTop: "2px",
                }}>
                  <Leaf size={12} color="#fff" aria-hidden="true" />
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Text bubble */}
                  {m.text && (
                    m.isError ? (
                      <ErrorBubble text={m.text} />
                    ) : (
                      <div style={{
                        padding: "10px 14px",
                        borderRadius: "18px", borderTopLeftRadius: "4px",
                        backgroundColor: C.white,
                        border: `1px solid ${C.border}`,
                        fontSize: "0.87rem",
                        lineHeight: 1.6,
                        color: C.ink,
                        whiteSpace: "pre-line",
                        wordBreak: "break-word",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                      }}>
                        {m.text}
                      </div>
                    )
                  )}

                  {/* Verified sources */}
                  {m.sources && m.sources.length > 0 && (
                    <SourcesChip sources={m.sources} lang={lang} />
                  )}

                  {/* Scheme-type response cards */}
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
                  {m.response?.type === "greeting" && !m.text && (
                    <div style={{
                      padding: "10px 14px",
                      borderRadius: "18px", borderTopLeftRadius: "4px",
                      backgroundColor: C.white,
                      border: `1px solid ${C.border}`,
                      fontSize: "0.87rem", lineHeight: 1.6, color: C.ink,
                      boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                    }}>
                      {m.response.message}
                    </div>
                  )}
                  {(!m.response?.type || m.response?.type === "scheme") && m.response?.found && (
                    <div>
                      {!m.text && m.response.message && (
                        <div style={{
                          padding: "10px 14px",
                          borderRadius: "18px", borderTopLeftRadius: "4px",
                          backgroundColor: C.white,
                          border: `1px solid ${C.border}`,
                          fontSize: "0.87rem", lineHeight: 1.6, color: C.ink,
                          whiteSpace: "pre-line", wordBreak: "break-word",
                          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                          marginBottom: "4px",
                        }}>
                          {m.response.message}
                        </div>
                      )}
                      {m.response?.scheme_name && (
                        <VerdictCard response={m.response} lang={lang} />
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        )}

        {/* Typing indicator */}
        {isLoading && <TypingBubble />}

        <div ref={bottomRef} />
      </div>

      {/* ================================================================
          QUICK-REPLY CHIPS
      ================================================================ */}
      {quickChips.length > 0 && (
        <div style={{
          padding: "6px 12px 4px",
          display: "flex", flexWrap: "wrap", gap: "6px",
          flexShrink: 0,
          borderTop: `1px solid ${C.borderLight}`,
          backgroundColor: C.cream,
        }}
          role="group" aria-label="Quick-reply suggestions"
        >
          {quickChips.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={isLoading}
              className="km-chip"
              style={{
                fontSize: "0.72rem", fontWeight: 600,
                padding: "5px 12px", borderRadius: "999px",
                backgroundColor: C.white,
                color: isLoading ? C.mutedLight : C.forest,
                border: `1.5px solid ${isLoading ? C.border : C.moss}`,
                cursor: isLoading ? "not-allowed" : "pointer",
                transition: "background-color 0.15s",
                whiteSpace: "nowrap",
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* ================================================================
          INPUT BAR
      ================================================================ */}
      <div style={{
        padding: "8px 12px 12px",
        flexShrink: 0,
        backgroundColor: C.cream,
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          backgroundColor: C.white,
          border: `1.5px solid ${C.border}`,
          borderRadius: "999px",
          padding: "6px 6px 6px 14px",
          boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}
          onFocusCapture={e => {
            e.currentTarget.style.borderColor = C.moss;
            e.currentTarget.style.boxShadow = `0 0 0 3px rgba(151,188,98,0.15)`;
          }}
          onBlurCapture={e => {
            e.currentTarget.style.borderColor = C.border;
            e.currentTarget.style.boxShadow = "0 1px 4px rgba(0,0,0,0.07)";
          }}
        >
          <input
            ref={inputRef}
            className="km-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isLoading && handleSend()}
            placeholder={t.placeholder}
            disabled={isLoading}
            aria-label="Type your message"
            style={{
              flex: 1,
              fontSize: "0.87rem",
              color: C.ink,
              backgroundColor: "transparent",
              border: "none",
              lineHeight: 1.5,
              minWidth: 0,
            }}
          />

          {/* Mic button */}
          <button
            onClick={() => setShowVoice(true)}
            className="km-mic-btn"
            disabled={isLoading}
            aria-label="Start voice input"
            title="Voice Assistant"
            style={{
              width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
              backgroundColor: C.cream,
              border: `1.5px solid ${C.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: isLoading ? "not-allowed" : "pointer",
              transition: "background-color 0.15s",
            }}
          >
            <Mic size={15} color={isLoading ? C.mutedLight : C.muted} aria-hidden="true" />
          </button>

          {/* Send button */}
          <button
            onClick={() => handleSend()}
            disabled={isLoading || !input.trim()}
            className="km-send-btn"
            aria-label="Send message"
            style={{
              width: 36, height: 36, borderRadius: "50%", flexShrink: 0,
              backgroundColor: (isLoading || !input.trim()) ? C.border : C.forest,
              border: "none",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: (isLoading || !input.trim()) ? "not-allowed" : "pointer",
              transition: "background-color 0.2s, transform 0.15s",
            }}
          >
            {isLoading
              ? <Loader2 size={15} color="#fff" className="animate-spin" aria-hidden="true" />
              : <Send size={15} color="#fff" aria-hidden="true" />
            }
          </button>
        </div>
      </div>

      {/* ================================================================
          VOICE ASSISTANT OVERLAY (functionality unchanged)
      ================================================================ */}
      {showVoice && (
        <VoiceAssistant
          lang={lang}
          setLang={setLang}
          profile={localProfile}
          useAI={useAI}
          onClose={() => setShowVoice(false)}
        />
      )}
    </div>
  );
}
