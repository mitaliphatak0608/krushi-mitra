import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Sprout, Home, User as UserIcon, FileText,
  MessageCircle, CloudSun, CheckCircle2,
  AlertCircle, UploadCloud, Leaf, LogOut, Check,
  Wheat, Loader2
} from "lucide-react";
import "./dashboard.css";
import NotificationBell from "./NotificationBell";


// Eligibility is now evaluated server-side — one source of truth.
const ELIGIBILITY_ENDPOINT = "http://localhost:8000/eligibility";

// --- 2. EXPANDED MULTILINGUAL DICTIONARY ---
const DASH_TEXT = {
  en: { 
    // Sidebar & Home
    dash: "Farmer Dashboard", home: "Home Overview", profile: "Personalization", docs: "Info & Documents", 
    talk: "Talk to Krushi Mitra", out: "Sign Out", welcome: "Welcome back", weather: "Region & Weather", 
    elig: "Scheme Eligibility", active: "Active Crop Status", rec: "Recommended Schemes for Your Farm", ask: "Ask Krushi Mitra",
    
    // Personalization Tab
    persTitle: "Farm & Profile Personalization", persSub: "Keep your crop, land, and income data updated for real-time recommendations.",
    sec1: "1. Basic & Land Information", nameLabel: "Full Name", langLabel: "Preferred Language", landLabel: "Landholding (Hectares)", regLabel: "Farming Region", catLabel: "Social Category",
    sec2: "2. Crop & Agricultural Details", cropLabel: "Current Crop Season", primCropLabel: "Primary Crop Category", orgLabel: "Organic Farming Practice?",
    sec3: "3. Income & Financial Details", incLabel: "Estimated Annual Farm Income (₹)", taxLabel: "Do you pay Income Tax?", loanLabel: "Active Outstanding Crop Loan?",
    saveBtn: "Save Profile & Update Schemes",
    saveSuccess: "Profile saved! Recommended schemes in Home tab have been updated for your farm.",
    
    // Documents Tab
    docTitle: "Stored Documents & Records", docSub: "Verified documents required across central and state welfare portals.",
    doc1Name: "7/12 & 8A Extract (Land Record)", doc1Desc: "Verified against MahaDBT portal.", viewRec: "View Record",
    doc2Name: "Identity Proof", doc2Desc: "Verified and linked to DBT account.", viewDet: "View Details",
    doc3Name: "Bank Passbook / Sowing Certificate", doc3Desc: "Required for crop insurance claims and loan interest subvention.", uploadBtn: "Upload"
  },
  hi: { 
    dash: "किसान डैशबोर्ड", home: "होम अवलोकन", profile: "प्रोफ़ाइल", docs: "दस्तावेज़", 
    talk: "कृषी मित्र से बात करें", out: "लॉग आउट", welcome: "वापसी पर स्वागत है", weather: "क्षेत्र और मौसम", 
    elig: "योजना पात्रता", active: "वर्तमान फसल स्थिति", rec: "आपके खेत के लिए अनुशंसित योजनाएं", ask: "कृषी मित्र से पूछें",
    
    persTitle: "खेत और प्रोफ़ाइल वैयक्तिकरण", persSub: "वास्तविक समय की सिफारिशों के लिए अपनी फसल, भूमि और आय डेटा को अद्यतित रखें।",
    sec1: "1. बुनियादी और भूमि जानकारी", nameLabel: "पूरा नाम", langLabel: "पसंदीदा भाषा", landLabel: "भूमि (हेक्टेयर)", regLabel: "कृषि क्षेत्र", catLabel: "सामाजिक श्रेणी",
    sec2: "2. फसल और कृषि विवरण", cropLabel: "वर्तमान फसल का मौसम", primCropLabel: "प्राथमिक फसल श्रेणी", orgLabel: "जैविक खेती का अभ्यास?",
    sec3: "3. आय और वित्तीय विवरण", incLabel: "अनुमानित वार्षिक कृषि आय (₹)", taxLabel: "क्या आप आयकर देते हैं?", loanLabel: "सक्रिय बकाया फसल ऋण?",
    saveBtn: "प्रोफ़ाइल सहेजें और योजनाएं अपडेट करें",
    saveSuccess: "प्रोफ़ाइल सहेज ली गई! होम टैब पर अनुशंसित योजनाएं अपडेट हो गई हैं।",
    
    docTitle: "संग्रहीत दस्तावेज़ और रिकॉर्ड", docSub: "केंद्रीय और राज्य कल्याण पोर्टल पर आवश्यक सत्यापित दस्तावेज़।",
    doc1Name: "7/12 और 8A (भूमि रिकॉर्ड)", doc1Desc: "महाडीबीटी पोर्टल से सत्यापित।", viewRec: "रिकॉर्ड देखें",
    doc2Name: "पहचान प्रमाण", doc2Desc: "सत्यापित और डीबीटी खाते से जुड़ा हुआ।", viewDet: "विवरण देखें",
    doc3Name: "बैंक पासबुक / बुवाई प्रमाण पत्र", doc3Desc: "फसल बीमा दावों और ऋण ब्याज छूट के लिए आवश्यक।", uploadBtn: "अपलोड करें"
  },
  mr: { 
    dash: "शेतकरी डॅशबोर्ड", home: "होम विहंगावलोकन", profile: "प्रोफाइल", docs: "कागदपत्रे", 
    talk: "कृषी मित्रशी बोला", out: "लॉग आउट", welcome: "परत आल्याबद्दल स्वागत आहे", weather: "प्रदेश आणि हवामान", 
    elig: "योजना पात्रता", active: "सध्याची पीक स्थिती", rec: "तुमच्या शेतासाठी शिफारस केलेल्या योजना", ask: "कृषी मित्रला विचारा",
    
    persTitle: "शेत आणि प्रोफाइल वैयक्तिकीकरण", persSub: "रिअल-टाइम शिफारसींसाठी तुमचा पीक, जमीन आणि उत्पन्नाचा डेटा अपडेट ठेवा.",
    sec1: "1. मूलभूत आणि जमिनीची माहिती", nameLabel: "पूर्ण नाव", langLabel: "पसंतीची भाषा", landLabel: "जमीन (हेक्टर)", regLabel: "शेतीचा प्रदेश", catLabel: "सामाजिक प्रवर्ग",
    sec2: "2. पीक आणि कृषी तपशील", cropLabel: "सध्याचा पीक हंगाम", primCropLabel: "प्राथमिक पीक श्रेणी", orgLabel: "सेंद्रिय शेतीचा सराव?",
    sec3: "3. उत्पन्न आणि आर्थिक तपशील", incLabel: "अंदाजित वार्षिक कृषी उत्पन्न (₹)", taxLabel: "तुम्ही आयकर भरता का?", loanLabel: "सक्रिय थकीत पीक कर्ज?",
    saveBtn: "प्रोफाइल सेव्ह करा आणि योजना अपडेट करा",
    saveSuccess: "प्रोफाइल सेव्ह झाली! होम टॅबवरील शिफारस केलेल्या योजना अपडेट झाल्या आहेत.",
    
    docTitle: "संचित कागदपत्रे आणि रेकॉर्ड", docSub: "केंद्र आणि राज्य कल्याण पोर्टलवर आवश्यक सत्यापित कागदपत्रे.",
    doc1Name: "7/12 आणि 8A उतारा (जमिनीचा रेकॉर्ड)", doc1Desc: "महाडीबीटी पोर्टलवरून सत्यापित.", viewRec: "रेकॉर्ड पहा",
    doc2Name: "ओळख पुरावा", doc2Desc: "सत्यापित आणि डीबीटी खात्याशी जोडलेले.", viewDet: "तपशील पहा",
    doc3Name: "बँक पासबुक / पेरणी प्रमाणपत्र", doc3Desc: "पीक विमा दावे आणि कर्ज व्याज सवलतीसाठी आवश्यक.", uploadBtn: "अपलोड करा"
  }
};

// --- 3. SIDEBAR COMPONENT ---
function Sidebar({ activeTab, setActiveTab, onLogout, t }) {
  const navItems = [
    { id: "home", label: t.home, icon: Home },
    { id: "profile", label: t.profile, icon: UserIcon },
    { id: "docs", label: t.docs, icon: FileText },
  ];

  return (
    <div className="dash-sidebar">
      <div className="dash-sidebar-header">
        <div className="dash-logo-icon">
          <Sprout size={20} color="var(--dash-accent)" />
        </div>
        <div>
          <p className="text-white font-bold text-sm">Krushi Mitra</p>
          <p className="text-xs" style={{ color: 'var(--dash-accent)' }}>{t.dash}</p>
        </div>
      </div>

      <nav className="dash-sidebar-nav">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`dash-nav-btn ${activeTab === id ? "active" : ""}`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <div style={{ padding: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <Link to="/chat" className="dash-btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', textDecoration: 'none', backgroundColor: 'var(--dash-accent)', color: 'var(--dash-primary-dark)' }}>
          <MessageCircle size={18} />
          {t.talk}
        </Link>
        
        <button onClick={onLogout} className="dash-nav-btn" style={{ color: '#E8B4A0', justifyContent: 'center' }}>
          <LogOut size={18} />
          {t.out}
        </button>
      </div>
    </div>
  );
}

// --- 4. MAIN DASHBOARD COMPONENT ---
export default function FarmerDashboard({ onLogout, lang, setLang, userData, setUserData }) {
  const [activeTab, setActiveTab] = useState("home");
  const t = DASH_TEXT[lang] || DASH_TEXT.en;

  // Eligibility comes from the backend — one source of truth for all screens
  const [eligibilityResults, setEligibilityResults] = useState([]);
  const [eligLoading, setEligLoading]               = useState(false);
  const [eligError, setEligError]                   = useState(false);
  const [saveStatus, setSaveStatus]                 = useState("idle"); // "idle" | "saving" | "saved"

  const fetchEligibility = useCallback((profileToUse = userData, langToUse = lang) => {
    setEligLoading(true);
    setEligError(false);
    fetch(ELIGIBILITY_ENDPOINT, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ profile: profileToUse, lang: langToUse }),
    })
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((data) => setEligibilityResults(data))
      .catch(() => { setEligError(true); setEligibilityResults([]); })
      .finally(() => setEligLoading(false));
  }, [userData, lang]);

  const handleSaveProfile = async () => {
    setSaveStatus("saving");
    const token = localStorage.getItem("krushi_token");
    if (token) {
      try {
        await fetch("http://localhost:8000/profile", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ profile: userData }),
        });
      } catch (err) {
        console.error("Failed to persist profile to database:", err);
      }
    }
    // Update backend eligibility immediately with current profile without navigating away
    fetchEligibility(userData, lang);
    setSaveStatus("saved");
    setTimeout(() => {
      setSaveStatus("idle");
    }, 4000);
  };

  // Automatically keep eligibility schemes synchronized whenever profile or language changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchEligibility(userData, lang);
    }, 300);
    return () => clearTimeout(timer);
  }, [userData, lang]);

  // Convenience: eligible subset for the count badge
  const eligibleSchemes = eligibilityResults.filter((s) => s.eligible);

  return (
    <div className="dashboard-wrapper animate-in fade-in duration-300 relative">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onLogout={onLogout} t={t} />
      
      <div className="dash-main relative">
        {/* GLOBAL LANGUAGE TOGGLE + NOTIFICATION BELL */}
        <div className="absolute top-6 right-8 flex items-center gap-2 z-10">
          <NotificationBell lang={lang} profile={userData} />
          <div className="flex items-center bg-white rounded-full shadow-sm border border-gray-200 p-1">
            {["en", "hi", "mr"].map((code) => (
              <button 
                key={code} 
                onClick={() => setLang(code)} 
                className={`px-3 py-1 text-xs font-bold rounded-full transition-colors ${lang === code ? "bg-[#2C5F2D] text-white" : "text-gray-500 hover:bg-gray-100"}`}
              >
                {code === "en" ? "EN" : code === "hi" ? "हिं" : "मर"}
              </button>
            ))}
          </div>
        </div>

        {/* --- HOME TAB --- */}
        {activeTab === "home" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="dash-header">
              <h1 className="dash-title">{t.welcome}, {userData.name}!</h1>
              <p className="dash-subtitle">
                Profile match: {userData.landholding} ha • {userData.cropSeason} Season • {userData.primaryCrop}
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
              <div className="dash-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--dash-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>{t.weather}</p>
                  <p style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--dash-text)' }}>{userData.location}</p>
                  <p style={{ color: 'var(--dash-primary)', fontWeight: 600, fontSize: '0.9rem' }}>{userData.region} • 32°C</p>
                </div>
                <CloudSun size={42} color="#E8A33D" />
              </div>

              <div className="dash-card primary-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.25rem', opacity: 0.85 }}>{t.elig}</p>
                  <p style={{ fontSize: '1.5rem', fontWeight: 800 }}>{eligibleSchemes.length} Schemes</p>
                  <p style={{ fontSize: '0.85rem', opacity: 0.9 }}>Matched to your crops & income</p>
                </div>
                <Leaf size={42} color="var(--dash-accent)" />
              </div>

              <div className="dash-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--dash-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>{t.active}</p>
                  <p style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--dash-text)' }}>{userData.cropSeason} Cycle</p>
                  <p style={{ color: 'var(--dash-muted)', fontSize: '0.85rem' }}>{userData.primaryCrop}</p>
                </div>
                <Wheat size={40} color="var(--dash-primary)" />
              </div>
            </div>


            <h2 className="dash-title" style={{ fontSize: '1.3rem', marginBottom: '1rem' }}>
              {t.rec}
            </h2>

            {/* Backend unavailable banner */}
            {eligError && (
              <div className="dash-card" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem 1.25rem', borderColor: '#E8B4A0', backgroundColor: '#FDF3F0' }}>
                <AlertCircle size={20} color="#8B4A3D" />
                <div>
                  <p style={{ fontWeight: 700, color: '#8B4A3D', fontSize: '0.9rem' }}>Backend server unavailable</p>
                  <p style={{ fontSize: '0.8rem', color: '#8B4A3D', opacity: 0.8 }}>Start the API server: <code>uvicorn backend.main:app --port 8000</code></p>
                </div>
              </div>
            )}

            {/* Loading spinner */}
            {eligLoading && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
                <Loader2 size={28} className="animate-spin" color="var(--dash-primary)" />
              </div>
            )}

            {/* Eligible scheme cards */}
            {!eligLoading && !eligError && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {eligibleSchemes.map((scheme) => (
                  <div key={scheme.scheme_id} className="dash-card" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                      <div style={{ padding: '0.5rem', backgroundColor: '#EAF3E4', borderRadius: '10px', marginTop: '0.1rem' }}>
                        <Check size={20} color="var(--dash-primary)" />
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <p style={{ fontWeight: 800, color: 'var(--dash-text)', fontSize: '1.05rem' }}>{scheme.name}</p>
                          <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.2rem 0.5rem', borderRadius: '6px', backgroundColor: '#EAF3E4', color: 'var(--dash-primary)' }}>
                            {scheme.category}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--dash-primary)', marginTop: '0.2rem' }}>
                          {scheme.benefit}
                        </p>
                        <p style={{ fontSize: '0.8rem', color: 'var(--dash-muted)', marginTop: '0.15rem' }}>
                          ✓ {scheme.note}
                        </p>
                      </div>
                    </div>

                    <Link to="/chat" style={{ textDecoration: 'none' }}>
                      <button className="dash-btn-primary" style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}>
                        {t.ask}
                      </button>
                    </Link>
                  </div>
                ))}

                {eligibleSchemes.length === 0 && eligibilityResults.length > 0 && (
                  <div className="dash-card" style={{ textAlign: 'center', padding: '2rem' }}>
                    <p style={{ color: 'var(--dash-muted)' }}>No schemes match your current profile. Update your profile or consult the chatbot.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}


        {/* --- PERSONALIZATION TAB --- */}
        {activeTab === "profile" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ maxWidth: '860px' }}>
            <div className="dash-header">
              <h2 className="dash-title">{t.persTitle}</h2>
              <p className="dash-subtitle">{t.persSub}</p>
            </div>

            <div className="dash-card" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              
              {/* SECTION 1 */}
              <div>
                <p style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--dash-primary-dark)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', borderBottom: '1px solid var(--dash-border)', paddingBottom: '0.5rem' }}>
                  {t.sec1}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                  <div className="dash-input-group">
                    <label>{t.nameLabel}</label>
                    <input type="text" value={userData.name} onChange={(e) => setUserData({ ...userData, name: e.target.value })} className="dash-input" />
                  </div>
                  <div className="dash-input-group">
                    <label>{t.langLabel}</label>
                    <select value={userData.language} onChange={(e) => setUserData({ ...userData, language: e.target.value })} className="dash-input">
                      <option>English</option>
                      <option>Marathi</option>
                      <option>Hindi</option>
                    </select>
                  </div>
                  <div className="dash-input-group">
                    <label>{t.landLabel}</label>
                    <input type="number" step="0.1" min="0" value={userData.landholding} onChange={(e) => setUserData({ ...userData, landholding: e.target.value })} className="dash-input" />
                  </div>
                  <div className="dash-input-group">
                    <label>{t.regLabel}</label>
                    <select value={userData.region} onChange={(e) => setUserData({ ...userData, region: e.target.value })} className="dash-input">
                      <option>Marathwada</option>
                      <option>Vidarbha</option>
                      <option>Western Maharashtra</option>
                      <option>North Maharashtra (Khandesh)</option>
                      <option>Konkan</option>
                    </select>
                  </div>
                  <div className="dash-input-group">
                    <label>{t.catLabel}</label>
                    <select value={userData.category} onChange={(e) => setUserData({ ...userData, category: e.target.value })} className="dash-input">
                      <option>General</option>
                      <option>OBC</option>
                      <option>SC</option>
                      <option>ST</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* SECTION 2 */}
              <div>
                <p style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--dash-primary-dark)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', borderBottom: '1px solid var(--dash-border)', paddingBottom: '0.5rem' }}>
                  {t.sec2}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                  <div className="dash-input-group">
                    <label>{t.cropLabel}</label>
                    <select value={userData.cropSeason} onChange={(e) => setUserData({ ...userData, cropSeason: e.target.value })} className="dash-input">
                      <option>Kharif</option>
                      <option>Rabi</option>
                      <option>Annual Commercial</option>
                      <option>Summer</option>
                    </select>
                  </div>
                  <div className="dash-input-group">
                    <label>{t.primCropLabel}</label>
                    <select value={userData.primaryCrop} onChange={(e) => setUserData({ ...userData, primaryCrop: e.target.value })} className="dash-input">
                      <option>Cotton & Soybean</option>
                      <option>Food Grains & Oilseeds</option>
                      <option>Horticulture & Fruits</option>
                      <option>Sugarcane (Commercial)</option>
                      <option>Vegetables & Pulses</option>
                    </select>
                  </div>
                  <div className="dash-input-group">
                    <label>{t.orgLabel}</label>
                    <select value={userData.isOrganic} onChange={(e) => setUserData({ ...userData, isOrganic: e.target.value })} className="dash-input">
                      <option value="No">No (Conventional)</option>
                      <option value="Yes">Yes (Organic)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* SECTION 3 */}
              <div>
                <p style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--dash-primary-dark)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem', borderBottom: '1px solid var(--dash-border)', paddingBottom: '0.5rem' }}>
                  {t.sec3}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                  <div className="dash-input-group">
                    <label>{t.incLabel}</label>
                    <input 
                      type="number" step="5000" 
                      value={userData.annualIncome} 
                      onChange={(e) => setUserData({ ...userData, annualIncome: e.target.value })} 
                      className="dash-input" 
                    />
                  </div>
                  <div className="dash-input-group">
                    <label>{t.taxLabel}</label>
                    <select value={userData.isTaxPayer} onChange={(e) => setUserData({ ...userData, isTaxPayer: e.target.value })} className="dash-input">
                      <option value="No">No</option>
                      <option value="Yes">Yes</option>
                    </select>
                  </div>
                  <div className="dash-input-group">
                    <label>{t.loanLabel}</label>
                    <select value={userData.hasOutstandingLoan} onChange={(e) => setUserData({ ...userData, hasOutstandingLoan: e.target.value })} className="dash-input">
                      <option value="Yes">Yes</option>
                      <option value="No">No</option>
                    </select>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <button
                  onClick={handleSaveProfile}
                  disabled={saveStatus === "saving"}
                  className="dash-btn-primary"
                  style={{
                    width: '100%',
                    padding: '0.85rem',
                    fontSize: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    opacity: saveStatus === "saving" ? 0.75 : 1,
                    cursor: saveStatus === "saving" ? "not-allowed" : "pointer"
                  }}
                >
                  {saveStatus === "saving" ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      <span>Updating schemes...</span>
                    </>
                  ) : (
                    <>
                      <Check size={18} />
                      <span>{t.saveBtn}</span>
                    </>
                  )}
                </button>

                {saveStatus === "saved" && (
                  <div
                    role="status"
                    className="animate-in fade-in slide-in-from-top-2 duration-300"
                    style={{
                      padding: '0.75rem 1rem',
                      background: '#EAF3E4',
                      border: '1px solid #C2E0B2',
                      borderRadius: '8px',
                      color: '#2C5F2D',
                      fontSize: '0.9rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      fontWeight: 600
                    }}
                  >
                    <CheckCircle2 size={18} color="#2C5F2D" />
                    <span>{t.saveSuccess || "Profile saved! Recommended schemes on Home tab have been updated."}</span>
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

        {/* --- DOCUMENTS TAB --- */}
        {activeTab === "docs" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ maxWidth: '860px' }}>
            <div className="dash-header">
              <h2 className="dash-title">{t.docTitle}</h2>
              <p className="dash-subtitle">{t.docSub}</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="dash-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ padding: '0.5rem', backgroundColor: '#EAF3E4', borderRadius: '10px' }}>
                    <CheckCircle2 size={24} color="var(--dash-primary)" />
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: 'var(--dash-text)' }}>{t.doc1Name}</p>
                    <p style={{ fontSize: '0.85rem', color: 'var(--dash-muted)' }}>{t.doc1Desc}</p>
                  </div>
                </div>
                <button style={{ background: 'none', border: 'none', color: 'var(--dash-primary)', fontWeight: 700, cursor: 'pointer' }}>{t.viewRec}</button>
              </div>

              <div className="dash-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ padding: '0.5rem', backgroundColor: '#EAF3E4', borderRadius: '10px' }}>
                    <CheckCircle2 size={24} color="var(--dash-primary)" />
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: 'var(--dash-text)' }}>{t.doc2Name}</p>
                    <p style={{ fontSize: '0.85rem', color: 'var(--dash-muted)' }}>{t.doc2Desc}</p>
                  </div>
                </div>
                <button style={{ background: 'none', border: 'none', color: 'var(--dash-primary)', fontWeight: 700, cursor: 'pointer' }}>{t.viewDet}</button>
              </div>

              <div className="dash-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem', borderColor: 'var(--dash-danger)', backgroundColor: 'var(--dash-danger-bg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ padding: '0.5rem', backgroundColor: '#fff', borderRadius: '10px' }}>
                    <AlertCircle size={24} color="var(--dash-danger)" />
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: 'var(--dash-danger)' }}>{t.doc3Name}</p>
                    <p style={{ fontSize: '0.85rem', color: 'var(--dash-danger)', opacity: 0.8 }}>{t.doc3Desc}</p>
                  </div>
                </div>
                <button style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--dash-danger)', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}>
                  <UploadCloud size={16} /> {t.uploadBtn}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}