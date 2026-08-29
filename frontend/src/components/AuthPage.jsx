import React, { useState } from "react";

const AUTH_BASE = "http://localhost:8000/auth";
import { Sprout, User, Shield, Mail, Lock, KeyRound, UserPlus, LogIn, Globe } from "lucide-react";
import "./auth.css";

// 1. MULTILINGUAL DICTIONARY
const AUTH_TEXT = {
  en: { 
    title: "Krushi Mitra", subLogin: "Welcome back! Log in to your account.", subSignup: "Create a new account to get started.", 
    farmer: "Farmer", admin: "Admin", name: "Full Name", email: "Email Address", pass: "Password", key: "Admin Access Key", 
    btnLogin: "Login to Dashboard", btnSignup: "Create Account", askSignup: "Don't have an account?", askLogin: "Already have an account?", 
    linkSignup: "Sign up", linkLogin: "Log in" 
  },
  hi: { 
    title: "कृषी मित्र", subLogin: "वापसी पर स्वागत है! अपने खाते में लॉग इन करें।", subSignup: "शुरू करने के लिए एक नया खाता बनाएं।", 
    farmer: "किसान", admin: "व्यवस्थापक", name: "पूरा नाम", email: "ईमेल पता", pass: "पासवर्ड", key: "व्यवस्थापक कुंजी (Admin Key)", 
    btnLogin: "डैशबोर्ड में लॉग इन करें", btnSignup: "खाता बनाएं", askSignup: "क्या आपके पास खाता नहीं है?", askLogin: "क्या आपके पास पहले से खाता है?", 
    linkSignup: "साइन अप करें", linkLogin: "लॉग इन करें" 
  },
  mr: { 
    title: "कृषी मित्र", subLogin: "परत आल्याबद्दल स्वागत आहे! तुमच्या खात्यात लॉग इन करा.", subSignup: "सुरू करण्यासाठी नवीन खाते तयार करा.", 
    farmer: "शेतकरी", admin: "अॅडमिन", name: "पूर्ण नाव", email: "ईमेल पत्ता", pass: "पासवर्ड", key: "अॅडमिन की (Admin Key)", 
    btnLogin: "डॅशबोर्डवर लॉग इन करा", btnSignup: "खाते तयार करा", askSignup: "तुमचे खाते नाहीये का?", askLogin: "तुमचे आधीच खाते आहे का?", 
    linkSignup: "साइन अप करा", linkLogin: "लॉग इन करा" 
  }
};

export default function AuthPage({ onLoginSuccess, lang, setLang }) {
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState("user"); 
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authError, setAuthError] = useState("");
  
  // Load the current translations based on the selected language
  const t = AUTH_TEXT[lang] || AUTH_TEXT.en; 
  
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    adminKey: "",
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setIsSubmitting(true);

    const endpoint = isLogin ? `${AUTH_BASE}/login` : `${AUTH_BASE}/register`;
    const payload = isLogin
      ? {
          email: formData.email,
          password: formData.password,
          role: role === "admin" ? "admin" : "farmer",
          adminKey: role === "admin" ? formData.adminKey : undefined,
        }
      : {
          name: formData.name,
          email: formData.email,
          password: formData.password,
          role: role === "admin" ? "admin" : "farmer",
          adminKey: role === "admin" ? formData.adminKey : undefined,
        };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setAuthError(data.detail || "Authentication failed. Please check your details.");
        return;
      }

      if (data.token) {
        localStorage.setItem("krushi_token", data.token);
      }

      onLoginSuccess({
        role: data.user.role,
        user: data.user,
        profile: data.profile,
      });
    } catch {
      setAuthError("Cannot reach the server. Make sure the backend is running on port 8000.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper" style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
      
      {/* STRUCTURED LANGUAGE SELECTOR */}
      <div className="auth-lang-pill animate-in slide-in-from-top-4 duration-500">
        <Globe size={18} className="auth-lang-icon" />
        <button 
          onClick={() => setLang("en")} 
          className={`auth-lang-btn ${lang === "en" ? "active" : ""}`}
        >
          English
        </button>
        <button 
          onClick={() => setLang("mr")} 
          className={`auth-lang-btn ${lang === "mr" ? "active" : ""}`}
        >
          मराठी
        </button>
        <button 
          onClick={() => setLang("hi")} 
          className={`auth-lang-btn ${lang === "hi" ? "active" : ""}`}
        >
          हिंदी
        </button>
      </div>

      {/* MAIN AUTH CARD */}
      <div className="auth-card animate-in zoom-in-95 duration-500">
        
        <div className="auth-header">
          <div className="auth-logo-box">
            <Sprout size={36} color="#97BC62" />
          </div>
          <h1 className="auth-title">{t.title}</h1>
          <p className="auth-subtitle">{isLogin ? t.subLogin : t.subSignup}</p>
        </div>

        <div className="auth-toggle-track">
          <button
            type="button"
            onClick={() => setRole("user")}
            className={`auth-toggle-btn ${role === "user" ? "active" : ""}`}
          >
            <User size={18} /> {t.farmer}
          </button>
          <button
            type="button"
            onClick={() => setRole("admin")}
            className={`auth-toggle-btn ${role === "admin" ? "active" : ""}`}
          >
            <Shield size={18} /> {t.admin}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          
          {!isLogin && (
            <div className="input-group">
              <label className="input-label">{t.name}</label>
              <div className="input-wrapper">
                <User size={18} className="input-icon" />
                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleChange}
                  className="auth-input"
                  placeholder="Enter your full name"
                />
              </div>
            </div>
          )}

          <div className="input-group">
            <label className="input-label">{t.email}</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="auth-input"
                placeholder="name@example.com"
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">{t.pass}</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="auth-input"
                placeholder="••••••••"
              />
            </div>
          </div>

          {role === "admin" && (
            <div className="input-group" style={{ marginTop: '0.5rem' }}>
              <label className="input-label" style={{ color: '#EF4444' }}>{t.key}</label>
              <div className="input-wrapper">
                <KeyRound size={18} className="input-icon" style={{ color: '#EF4444' }} />
                <input
                  type="password"
                  name="adminKey"
                  required
                  value={formData.adminKey}
                  onChange={handleChange}
                  className="auth-input admin-key-input"
                  placeholder="Enter secret admin key"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={isSubmitting}
            style={isSubmitting ? { opacity: 0.7, cursor: "not-allowed" } : {}}
          >
            {isSubmitting ? "Verifying…" : (isLogin ? t.btnLogin : t.btnSignup)}
            {!isSubmitting && (isLogin ? <LogIn size={20} /> : <UserPlus size={20} />)}
          </button>

          {authError && (
            <div
              role="alert"
              style={{
                color: "#EF4444",
                fontSize: "0.825rem",
                textAlign: "center",
                marginTop: "0.25rem",
                padding: "0.5rem",
                background: "#FEF2F2",
                borderRadius: "0.5rem",
                border: "1px solid #FECACA",
              }}
            >
              {authError}
            </div>
          )}

          <div className="auth-footer">
            <span style={{ marginRight: '0.25rem' }}>{isLogin ? t.askSignup : t.askLogin}</span>
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setFormData({ name: "", email: "", password: "", adminKey: "" });
                setAuthError("");
              }}
              className="auth-link"
            >
              {isLogin ? t.linkSignup : t.linkLogin}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}