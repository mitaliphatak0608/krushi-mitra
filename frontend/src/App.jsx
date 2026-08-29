import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import KrushiMitraAdminDashboard from "./components/KrushiMitraAdminDashboard.jsx";
import KrushiMitraChatUI from "./components/KrushiMitraChatUI.jsx";
import AuthPage from "./components/AuthPage.jsx";
import FarmerDashboard from "./components/FarmerDashboard.jsx";
import { Loader2 } from "lucide-react";
import "./style.css";

// Default farmer profile — shared between the dashboard and the chat
const DEFAULT_USER_DATA = {
  name: "Farmer",
  location: "Chhatrapati Sambhajinagar",
  region: "Marathwada",
  category: "General",
  landholding: 1.5,
  language: "English",
  annualIncome: 120000,
  isTaxPayer: "No",
  hasOutstandingLoan: "Yes",
  cropSeason: "Kharif",
  primaryCrop: "Cotton & Soybean",
  isOrganic: "No",
};

function RequireAdminAuth({ isAdmin, authLoading, children }) {
  if (authLoading) return null;
  if (!isAdmin) return <Navigate to="/auth" replace />;
  return children;
}

function RequireUserAuth({ isAuthenticated, isAdmin, authLoading, children }) {
  if (authLoading) return null;
  if (!isAuthenticated && !isAdmin) return <Navigate to="/auth" replace />;
  return children;
}

export default function App() {
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [lang, setLang] = useState("en");

  // Shared farmer profile — database persists it, dashboard edits it, chat reads it
  const [userData, setUserData] = useState(DEFAULT_USER_DATA);

  // Restore authenticated session and profile on page reload
  useEffect(() => {
    const token = localStorage.getItem("krushi_token");
    if (!token) {
      setAuthLoading(false);
      return;
    }

    fetch("http://localhost:8000/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Invalid token");
        return res.json();
      })
      .then((data) => {
        if (data.user?.role === "admin") {
          setIsAdminAuthenticated(true);
        } else {
          setIsUserAuthenticated(true);
          if (data.profile) {
            setUserData(data.profile);
          }
        }
      })
      .catch(() => {
        localStorage.removeItem("krushi_token");
        setIsUserAuthenticated(false);
        setIsAdminAuthenticated(false);
      })
      .finally(() => {
        setAuthLoading(false);
      });
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("krushi_token");
    setIsUserAuthenticated(false);
    setIsAdminAuthenticated(false);
    setUserData(DEFAULT_USER_DATA);
  };

  if (authLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#F7F9F6" }}>
        <Loader2 className="animate-spin" size={36} color="#2C5F2D" />
      </div>
    );
  }

  return (
    <div className="app-wrapper">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={
            isAdminAuthenticated ? <Navigate to="/admin" replace /> :
            isUserAuthenticated  ? <Navigate to="/dashboard" replace /> :
            <Navigate to="/auth" replace />
          } />

          <Route path="/auth" element={
            isAdminAuthenticated ? <Navigate to="/admin" replace /> :
            isUserAuthenticated  ? <Navigate to="/dashboard" replace /> :
            <AuthPage
              lang={lang}
              setLang={setLang}
              onLoginSuccess={(data) => {
                if (data.role === "admin") {
                  setIsAdminAuthenticated(true);
                } else {
                  setIsUserAuthenticated(true);
                  if (data.profile) {
                    setUserData(data.profile);
                  } else if (data.user?.name) {
                    setUserData((prev) => ({ ...prev, name: data.user.name }));
                  }
                }
              }}
            />
          } />

          <Route path="/dashboard" element={
            <RequireUserAuth
              isAuthenticated={isUserAuthenticated}
              isAdmin={isAdminAuthenticated}
              authLoading={authLoading}
            >
              <FarmerDashboard
                lang={lang}
                setLang={setLang}
                userData={userData}
                setUserData={setUserData}
                onLogout={handleLogout}
              />
            </RequireUserAuth>
          } />

          <Route path="/chat" element={
            <RequireUserAuth
              isAuthenticated={isUserAuthenticated}
              isAdmin={isAdminAuthenticated}
              authLoading={authLoading}
            >
              <KrushiMitraChatUI lang={lang} setLang={setLang} profile={userData} />
            </RequireUserAuth>
          } />

          <Route path="/admin" element={
            <RequireAdminAuth
              isAdmin={isAdminAuthenticated}
              authLoading={authLoading}
            >
              <KrushiMitraAdminDashboard onLogout={handleLogout} />
            </RequireAdminAuth>
          } />

          <Route path="*" element={<Navigate to="/auth" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}