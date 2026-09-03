import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Sprout, LayoutGrid, ListChecks, BarChart3, Settings, Search,
  AlertTriangle, CheckCircle2, Pencil, ChevronDown, ChevronUp, Globe, 
  ExternalLink, LogOut, Users, RefreshCw, UserCheck, Bell, Plus, Trash2, Clock,
  Shield, Sliders, Database, Phone, Check, RotateCcw, Save, Zap, AlertCircle
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import "./admin-dashboard.css"; // Import the new CSS!

// Keep Hex constants ONLY for the Recharts library (which requires raw hex codes)
const FOREST = "#2C5F2D";
const MOSS = "#97BC62";
const GOLD = "#E8A33D";
const DANGER = "#B45B4A";

const INITIAL_SCHEMES = [
  { id: "PMKISAN", name: "PM-KISAN", category: "Income Support", type: "Central", status: "Open", lastVerified: "2026-08-22", verifyNeeded: [], benefit: "₹6,000/year in 3 installments." },
  { id: "PMFBY", name: "PM Fasal Bima Yojana", category: "Insurance", type: "Central", status: "Open", lastVerified: "2026-08-22", verifyNeeded: [], benefit: "Premium capped 2% Kharif / 1.5% Rabi / 5% commercial." },
  { id: "KCC", name: "Kisan Credit Card", category: "Credit", type: "Central", status: "Open", lastVerified: "2026-08-22", verifyNeeded: [], benefit: "Subsidized short-term crop loans." },
  { id: "NAMO_SHETKARI", name: "Namo Shetkari Maha Sanman Nidhi", category: "Income Support", type: "State", status: "Open", lastVerified: "2026-08-22", verifyNeeded: [], benefit: "₹6,000/year state top-up." },
  { id: "MICRO_IRRIGATION", name: "Micro-Irrigation Subsidy", category: "Irrigation", type: "State", status: "Open", lastVerified: "2026-08-22", verifyNeeded: ["Medium band % unconfirmed"], benefit: "80%/70% subsidy + region top-up." },
  { id: "SMAM", name: "Farm Mechanization (SMAM)", category: "Mechanization", type: "State", status: "Closed", lastVerified: "2026-08-15", verifyNeeded: ["Category % unconfirmed"], benefit: "Tractor/equipment subsidy." },
  { id: "SOLAR_PUMP", name: "Solar Pump Yojana", category: "Energy", type: "State", status: "Open", lastVerified: "2026-08-22", verifyNeeded: [], benefit: "Farmer pays 10% (5% SC/ST)." },
  { id: "FARM_POND", name: "Farm Pond Scheme", category: "Irrigation", type: "State", status: "Open", lastVerified: "2026-08-20", verifyNeeded: ["Exact amount unconfirmed"], benefit: "Subsidy for pond construction." },
  { id: "WELL_SUBSIDY", name: "Well Subsidy", category: "Irrigation", type: "State", status: "Open", lastVerified: "2026-08-22", verifyNeeded: ["Category % unconfirmed"], benefit: "Up to ₹4L new / ₹1L repair." },
  { id: "KARJMAFI", name: "Karjmafi Yojana", category: "Debt Relief", type: "State", status: "Closed", lastVerified: "2026-08-10", verifyNeeded: ["Waiver amount changes per cycle"], benefit: "Crop loan waiver." },
  { id: "PKVY", name: "PKVY Organic Farming Grant", category: "Sustainability", type: "Central/State", status: "Open", lastVerified: "2026-08-18", verifyNeeded: [], benefit: "Vermicompost + certification support." },
];

const QUERY_VOLUME = [
  { category: "Income Support", queries: 142 },
  { category: "Irrigation", queries: 118 },
  { category: "Insurance", queries: 96 },
  { category: "Energy", queries: 74 },
  { category: "Mechanization", queries: 51 },
  { category: "Credit", queries: 43 },
  { category: "Debt Relief", queries: 38 },
  { category: "Sustainability", queries: 22 },
];

const LANGUAGE_SPLIT = [
  { name: "Marathi", value: 48 },
  { name: "Hindi", value: 33 },
  { name: "English", value: 19 },
];
const LANG_COLORS = [FOREST, MOSS, GOLD];

// --- SUB-COMPONENTS ---
function StatCard({ label, value, icon: Icon, tone }) {
  return (
    <div className="admin-card stat-card">
      <div className="stat-icon-wrapper" style={{ backgroundColor: tone }}>
        <Icon size={22} color="#fff" />
      </div>
      <div>
        <p className="stat-value">{value}</p>
        <p className="stat-label">{label}</p>
      </div>
    </div>
  );
}

function StatusPill({ status, onClick }) {
  const open = status === "Open";
  return (
    <button onClick={onClick} className={`status-pill ${open ? "status-open" : "status-closed"}`}>
      <span className="relative flex h-2 w-2">
        {open && <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 bg-green-500" />}
        <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: open ? FOREST : "#9CA3A3" }} />
      </span>
      {status}
    </button>
  );
}

function Sidebar({ view, setView, onLogout }) {
  const items = [
    { key: "overview", label: "Overview", icon: LayoutGrid },
    { key: "schemes", label: "Schemes", icon: ListChecks },
    { key: "users", label: "Registered Farmers", icon: Users },
    { key: "notifications", label: "Notifications", icon: Bell },
    { key: "analytics", label: "Usage Analytics", icon: BarChart3 },
    { key: "settings", label: "Settings", icon: Settings },
  ];
  
  return (
    <div className="admin-sidebar">
      <div className="admin-sidebar-header">
        <div className="admin-logo-icon">
          <Sprout size={20} color="var(--admin-accent)" />
        </div>
        <div>
          <p className="text-white font-bold text-sm">Krushi Mitra</p>
          <p className="text-xs" style={{ color: "var(--admin-accent)" }}>Admin Console</p>
        </div>
      </div>
      
      <nav className="admin-sidebar-nav">
        {items.map(({ key, label, icon: Icon }) => (
          <button 
            key={key} 
            onClick={() => setView(key)}
            className={`admin-nav-btn ${view === key ? "active" : ""}`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <div style={{ padding: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <Link 
          to="/chat" 
          target="_blank" 
          className="admin-nav-btn" 
          style={{ justifyContent: 'center', backgroundColor: 'var(--admin-accent)', color: 'var(--admin-primary-dark)', textDecoration: 'none' }}
        >
          <ExternalLink size={16} /> Preview Public Site
        </Link>
        
        <button 
          onClick={onLogout}
          className="admin-nav-btn"
          style={{ color: '#E8B4A0', justifyContent: 'center', border: '1px solid #8B4A3D' }}
        >
          <LogOut size={16} /> Sign Out
        </button>
      </div>
    </div>
  );
}

function OverviewView({ schemes }) {
  const openCount = schemes.filter((s) => s.status === "Open").length;
  const flagged = schemes.filter((s) => s.verifyNeeded.length > 0).length;
  
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
      
      {/* Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <StatCard label="Total Schemes" value={schemes.length} icon={ListChecks} tone={FOREST} />
        <StatCard label="Open Now" value={openCount} icon={CheckCircle2} tone={MOSS} />
        <StatCard label="Languages" value="3" icon={Globe} tone={GOLD} />
        <StatCard label="Flagged for Verification" value={flagged} icon={AlertTriangle} tone={DANGER} />
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        
        <div className="admin-card">
          <p className="admin-title" style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Queries by Scheme Category</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={QUERY_VOLUME} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DCE3D9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#5C6F5E" }} />
              <YAxis type="category" dataKey="category" tick={{ fontSize: 11, fill: "#1A2E1B" }} width={110} />
              <Tooltip cursor={{ fill: '#F4F7F2' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
              <Bar dataKey="queries" fill={FOREST} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="admin-card">
          <p className="admin-title" style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Query Language Split</p>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={LANGUAGE_SPLIT} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={50} label>
                {LANGUAGE_SPLIT.map((entry, i) => <Cell key={i} fill={LANG_COLORS[i % LANG_COLORS.length]} />)}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 12, fontWeight: 600 }} />
              <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

      </div>
    </div>
  );
}

function SchemesView({ schemes, toggleStatus }) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(null);
  
  const filtered = useMemo(
    () => schemes.filter((s) => s.name.toLowerCase().includes(query.toLowerCase()) || s.category.toLowerCase().includes(query.toLowerCase())),
    [schemes, query]
  );

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
      
      {/* Search Bar */}
      <div className="admin-search-wrapper">
        <Search size={18} color="var(--admin-muted)" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search schemes or categories..."
          className="admin-search-input"
        />
      </div>

      {/* Table */}
      <div className="admin-table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Scheme Name</th>
              <th>Category</th>
              <th>Type</th>
              <th>Status</th>
              <th>Last Verified</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <React.Fragment key={s.id}>
                <tr>
                  <td className="td-bold">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {s.name}
                      {s.verifyNeeded.length > 0 && (
                        <span title={s.verifyNeeded.join("; ")}>
                          <AlertTriangle size={14} color="var(--admin-warning)" />
                        </span>
                      )}
                    </div>
                  </td>
                  <td>{s.category}</td>
                  <td>{s.type}</td>
                  <td>
                    <StatusPill status={s.status} onClick={() => toggleStatus(s.id)} />
                  </td>
                  <td>{s.lastVerified}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button 
                      onClick={() => setExpanded(expanded === s.id ? null : s.id)} 
                      style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--admin-primary)', fontWeight: 700 }}
                    >
                      <Pencil size={14} />
                      {expanded === s.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </td>
                </tr>
                
                {/* Expanded Details Row */}
                {expanded === s.id && (
                  <tr className="admin-expanded-row">
                    <td colSpan={6} style={{ padding: 0, border: 'none' }}>
                      <div className="admin-expanded-content">
                        <p style={{ color: 'var(--admin-text)', marginBottom: '0.5rem' }}>
                          <span style={{ fontWeight: 800 }}>Primary Benefit:</span> {s.benefit}
                        </p>
                        {s.verifyNeeded.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--admin-danger)', fontSize: '0.85rem', fontWeight: 600 }}>
                            <AlertTriangle size={14} /> 
                            Needs Verification: {s.verifyNeeded.join(" | ")}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: '0.8rem', color: 'var(--admin-muted)', paddingLeft: '0.5rem' }}>
        * Click a status pill to toggle it Open/Closed. Click the pencil icon to expand details.
      </p>
    </div>
  );
}

function UsersView() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const loadUsers = () => {
    setLoading(true);
    fetch("http://localhost:8000/admin/users")
      .then((res) => {
        if (!res.ok) throw new Error();
        return res.json();
      })
      .then((data) => setUsers(data))
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const filtered = useMemo(() => {
    return users.filter((u) => {
      const searchStr = `${u.name} ${u.email} ${u.role} ${u.profile?.region || ''} ${u.profile?.primaryCrop || ''}`.toLowerCase();
      return searchStr.includes(query.toLowerCase());
    });
  }, [users, query]);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
      {/* Search & Actions Bar */}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div className="admin-search-wrapper" style={{ flex: 1 }}>
          <Search size={18} color="var(--admin-muted)" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search registered farmers by name, email, region, or crop..."
            className="admin-search-input"
          />
        </div>
        <button
          onClick={loadUsers}
          className="admin-btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem' }}
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {/* Table */}
      <div className="admin-card table-card" style={{ overflowX: 'auto' }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Farmer / User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Region</th>
              <th>Land (ha)</th>
              <th>Primary Crop</th>
              <th>Registered On</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '3rem', color: 'var(--admin-muted)' }}>
                  Loading registered users from database...
                </td>
              </tr>
            )}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '3rem', color: 'var(--admin-muted)' }}>
                  No registered users found.
                </td>
              </tr>
            )}

            {!loading && filtered.map((u) => (
              <tr key={u.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <div style={{ padding: '0.4rem', backgroundColor: '#EAF3E4', borderRadius: '50%', color: 'var(--admin-primary)' }}>
                      <UserCheck size={16} />
                    </div>
                    <div>
                      <p style={{ fontWeight: 700, color: 'var(--admin-text)' }}>{u.name}</p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--admin-muted)' }}>ID #{u.id}</span>
                    </div>
                  </div>
                </td>
                <td style={{ color: 'var(--admin-muted)', fontSize: '0.9rem' }}>{u.email}</td>
                <td>
                  <span style={{
                    padding: '0.2rem 0.6rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    backgroundColor: u.role === 'admin' ? '#FEF2F2' : '#EAF3E4',
                    color: u.role === 'admin' ? '#B45B4A' : 'var(--admin-primary)'
                  }}>
                    {u.role}
                  </span>
                </td>
                <td style={{ fontWeight: 600 }}>{u.profile?.region || "—"}</td>
                <td>{u.profile?.landholding ? `${u.profile.landholding} ha` : "—"}</td>
                <td style={{ color: 'var(--admin-primary)', fontWeight: 600 }}>{u.profile?.primaryCrop || "—"}</td>
                <td style={{ fontSize: '0.85rem', color: 'var(--admin-muted)' }}>
                  {u.created_at ? new Date(u.created_at).toLocaleDateString() : "Recent"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: '0.8rem', color: 'var(--admin-muted)', paddingLeft: '0.5rem' }}>
        Total Registered: {users.length} accounts stored in SQLite database (`backend/users.db`).
      </p>
    </div>
  );
}

// --- NOTIFICATIONS VIEW ---
const SCHEME_OPTIONS = [
  { id: "PMFBY",           name: "PM Fasal Bima Yojana (१ रुपयात पीक विमा)" },
  { id: "SOLAR_PUMP",      name: "Magel Tyala Saur Krishi Pump (सौर कृषी पंप)" },
  { id: "SMAM",            name: "Farm Mechanization (कृषी यांत्रिकीकरण)" },
  { id: "MICRO_IRRIGATION",name: "Micro-Irrigation Subsidy (सूक्ष्म सिंचन)" },
  { id: "PMKISAN",         name: "PM-KISAN (पीएम-किसान सन्मान निधी)" },
  { id: "NAMO_SHETKARI",   name: "Namo Shetkari Maha Sanman Nidhi (नमो शेतकरी)" },
  { id: "FARM_POND",       name: "Farm Pond Scheme (मागेल त्याला शेततळे)" },
  { id: "WELL_SUBSIDY",    name: "Well Subsidy (नवीन विहीर / दुरुस्ती)" },
  { id: "KCC",             name: "Kisan Credit Card (केसीसी पीक कर्ज)" },
  { id: "PKVY",            name: "PKVY Organic Farming (सेंद्रिय शेती अनुदान)" },
  { id: "KARJMAFI",        name: "Karjmafi Yojana (पीक कर्ज माफी)" },
];

const AUTHENTIC_SCHEME_ALERTS = {
  PMFBY: {
    source: "Agriculture Dept., Govt. of Maharashtra (MahaAgri) & MoA&FW, GoI",
    link: "https://pmfby.gov.in",
    new_scheme: {
      days: 0,
      en: {
        title: "Official Announcement: Maharashtra ₹1 Crop Insurance Scheme (PMFBY) Active",
        body: "Govt of Maharashtra notification: Kharif/Rabi crop insurance enrollment is officially active under the landmark ₹1 farmer premium scheme. Farmers pay only ₹1 token amount; state and central governments pay the remaining premium. Coverage protects against post-harvest and localized calamities."
      },
      hi: {
        title: "आधिकारिक घोषणा: महाराष्ट्र ₹1 फसल बीमा योजना (PMFBY) आवेदन खुले",
        body: "महाराष्ट्र शासन अधिसूचना: ऐतिहासिक ₹1 किसान प्रीमियम योजना के तहत खरीफ/रबी फसल बीमा नामांकन सक्रिय है। किसान केवल ₹1 टोकन शुल्क देकर पूर्ण फसल नुकसान जोखिम सुरक्षा प्राप्त कर सकते हैं।"
      },
      mr: {
        title: "अधिकृत घोषणा: महाराष्ट्र १ रुपयात पीक विमा (PMFBY) अर्ज प्रक्रिया सुरू",
        body: "महाराष्ट्र शासन कृषी विभाग परिपत्रक: ऐतिहासिक '१ रुपयात पीक विमा' योजनेअंतर्गत खरीप/रब्बी पिकांसाठी विमा नोंदणी सुरू झाली आहे. शेतकऱ्यांनी फक्त ₹१ भरून गारपीट, अवकाळी पाऊस व दुष्काळापासून पिकांचे संपूर्ण विमा संरक्षण मिळवावे."
      }
    },
    closing_soon: {
      days: 10,
      en: {
        title: "Official Notice: PMFBY ₹1 Crop Insurance Enrollment Deadline Approaching",
        body: "Govt. of Maharashtra Agriculture Dept announcement: The application window for Maharashtra's landmark ₹1 Crop Insurance Scheme is closing soon. Farmers need to pay only ₹1 token fee with 7/12 extract and crop sowing certificate to receive comprehensive yield loss risk coverage. Enroll on pmfby.gov.in or your nearest Aaple Sarkar / CSC centre."
      },
      hi: {
        title: "आधिकारिक अधिसूचना: ₹1 फसल बीमा (PMFBY) खरीफ/रबी नामांकन की अंतिम तिथि निकट",
        body: "महाराष्ट्र शासन कृषि विभाग सूचना: महाराष्ट्र की ऐतिहासिक '₹1 फसल बीमा योजना' के तहत नामांकन की समयसीमा जल्द समाप्त हो रही है। व्यापक उत्पादन नुकसान कवरेज हेतु 7/12 और बुवाई प्रमाणपत्र के साथ केवल ₹1 का टोकन शुल्क देकर pmfby.gov.in या नजदीकी ग्राहक सेवा केंद्र (CSC) पर आवेदन करें।"
      },
      mr: {
        title: "अधिकृत शासन परिपत्रक: १ रुपयात पीक विमा (PMFBY) नोंदणीची मुदत संपत आहे",
        body: "महाराष्ट्र शासन कृषी विभाग परिपत्रक: महाराष्ट्रातील ऐतिहासिक '१ रुपयात पीक विमा' योजनेची नोंदणी मुदत लवकरच समाप्त होत आहे. दुष्काळ, अतिवृष्टी व अवकाळी नुकसानीपासून संरक्षणासाठी ७/१२ उतारा व पीक पेरणी दाखल्यासह केवळ ₹१ भरून pmfby.gov.in किंवा आपल्या जवळच्या आपले सरकार / सीएससी केंद्रावर तात्काळ नोंदणी करा."
      }
    }
  },
  SOLAR_PUMP: {
    source: "MSEDCL & Dept. of Energy, Govt. of Maharashtra",
    link: "https://mahadbt.maharashtra.gov.in",
    new_scheme: {
      days: 0,
      en: {
        title: "Official Announcement: Magel Tyala Saur Krishi Pump Quota Open (90-95% Subsidy)",
        body: "Government of Maharashtra (MSEDCL & MahaDBT) notice: Application window is active for 3 HP, 5 HP and 7.5 HP Solar Agricultural Pumps. General/OBC category farmers pay only 10% of the pump cost; SC/ST farmers pay only 5%. Apply with registered 7/12 extract and water source proof on MahaDBT / MSEDCL Solar Portal."
      },
      hi: {
        title: "आधिकारिक घोषणा: मागेल त्याला सौर कृषी पंप योजना नया कोटा खुला (90-95% सरकारी अनुदान)",
        body: "महाराष्ट्र शासन (महावितरण व महाडीबीटी) सूचना: 3 HP, 5 HP और 7.5 HP सौर कृषि पंपों के लिए नया कोटा उपलब्ध है। सामान्य/ओबीसी किसानों को मात्र 10% और SC/ST किसानों को केवल 5% अंशदान देना है। 7/12 उतारा और जल स्रोत प्रमाण के साथ महाडीबीटी पोर्टल पर ऑनलाइन आवेदन करें।"
      },
      mr: {
        title: "अधिकृत घोषणा: मागेल त्याला सौर कृषी पंप योजना नवीन कोटा खुला (९०% ते ९५% सरकारी अनुदान)",
        body: "महाराष्ट्र शासन (महावितरण व महाडीबीटी) अधिकृत सूचना: ३, ५ आणि ७.५ एचपी सौर कृषी पंपांसाठी नवीन कोटा अर्ज स्वीकारणे सुरू आहे. खुल्या व ओबीसी प्रवर्गातील शेतकऱ्यांना पंपाच्या किमतीच्या फक्त १०% आणि अनु. जाती/जमाती शेतकऱ्यांना फक्त ५% लाभार्थी हिस्सा भरावा लागेल. ७/१२ उतारा व जलस्रोत पुराव्यासह महाडीबीटी किंवा महावितरण सौर पोर्टलवर अर्ज करा."
      }
    },
    closing_soon: {
      days: 8,
      en: {
        title: "Quota Closing Alert: Magel Tyala Saur Krishi Pump District Allocation",
        body: "Govt of Maharashtra notice: Current district-wise solar pump beneficiary targets are reaching full allocation. Complete your MahaDBT application and demand note payment before target exhaustion."
      },
      hi: {
        title: "कोटा समाप्ति चेतावनी: मागेल त्याला सौर कृषी पंप जिला लक्ष्य आवंटन",
        body: "महाराष्ट्र शासन सूचना: जिलावार सौर कृषि पंप लक्ष्य पूरा होने वाला है। कोटा समाप्त होने से पहले अपना महाडीबीटी आवेदन और डिमांड नोट भुगतान पूरा करें।"
      },
      mr: {
        title: "कोटा मुदत सूचना: मागेल त्याला सौर कृषी पंप जिल्हा उद्दिष्ट पूर्ण होत आहे",
        body: "महाराष्ट्र शासन सूचना: जिल्ह्यातील सौर कृषी पंपांचे उद्दिष्ट पूर्ण होत आले आहे. लाभ घेण्यासाठी महाडीबीटीवर अर्ज व डिमांड नोट भरणे त्वरित पूर्ण करा."
      }
    }
  },
  SMAM: {
    source: "Commissioner of Agriculture, Govt. of Maharashtra (MahaDBT)",
    link: "https://mahadbt.maharashtra.gov.in",
    new_scheme: {
      days: 0,
      en: {
        title: "Official Notification: MahaDBT Agricultural Machinery & Tractor Subsidy Open",
        body: "Commissioner of Agriculture notice: Subsidies on tractors (<=35 HP, up to ₹1,25,000) and farm implements (rotavator, power tiller, thresher) are open for application on MahaDBT Shetkari portal."
      },
      hi: {
        title: "आधिकारिक अधिसूचना: महाडीबीटी कृषि यंत्रीकरण व ट्रैक्टर अनुदान आवेदन शुरू",
        body: "कृषि आयुक्त सूचना: 35 एचपी तक के ट्रैक्टरों (अधिकतम ₹1.25 लाख) तथा कृषि यंत्रों (रोटावेटर, पावर टिलर) पर अनुदान हेतु महाडीबीटी पोर्टल पर ऑनलाइन आवेदन आमंत्रित हैं।"
      },
      mr: {
        title: "अधिकृत परिपत्रक: महाडीबीटी कृषी यांत्रिकीकरण व ट्रॅक्टर अनुदान अर्ज सुरू",
        body: "कृषी आयुक्तालय सूचना: ३५ एचपी पर्यंतचे ट्रॅक्टर (जास्तीत जास्त ₹१,२५,००० पर्यंत) तसेच रोटाव्हेटर, पॉवर टिलर व थ्रेशर यांच्या अनुदानासाठी महाडीबीटी पोर्टलवर अर्ज सुरू झाले आहेत."
      }
    },
    closing_soon: {
      days: 6,
      en: {
        title: "Official Cutoff: MahaDBT Farm Mechanization & Tractor Subsidy Lottery Draw",
        body: "Commissioner of Agriculture, Maharashtra State advisory: Registration for the upcoming computerized lottery for tractor subsidy (up to ₹1,25,000 for <=35HP) and farm implements (rotavator, power tiller, seed drill) closes shortly. Ensure your MahaDBT application fee of ₹23.60 is paid to be included in the draw."
      },
      hi: {
        title: "आधिकारिक सूचना: महाडीबीटी कृषि यंत्रीकरण (ट्रैक्टर व कृषि यंत्र) लॉटरी आवेदन की अंतिम तिथि",
        body: "कृषि आयुक्त, महाराष्ट्र राज्य सूचना: 35 एचपी तक के ट्रैक्टर (अनुदान ₹1.25 लाख तक) तथा रोटावेटर, पावर टिलर व बीज ड्रिल की आगामी कंप्यूटरीकृत लॉटरी के लिए आवेदन प्रक्रिया जल्द समाप्त हो रही है। ड्रॉ में सम्मिलित होने हेतु महाडीबीटी पर ₹23.60 शुल्क का भुगतान सुनिश्चित करें।"
      },
      mr: {
        title: "अधिकृत अंतिम मुदत: महाडीबीटी कृषी यांत्रिकीकरण (ट्रॅक्टर व अवजारे सोडत) अर्ज नोंदणी",
        body: "कृषी आयुक्तालय, महाराष्ट्र राज्य सूचना: ३५ एचपी पर्यंतचे ट्रॅक्टर (अनुदान ₹१,२५,००० पर्यंत) आणि रोटाव्हेटर, पॉवर टिलर, पेरणीयंत्र यांच्या आगामी संगणकीय सोडतीसाठी अर्जाची अंतिम मुदत जवळ आली आहे. सोडतीत समावेश होण्यासाठी महाडीबीटीवर ₹२३.६० शुल्क भरून अर्ज पूर्ण करा."
      }
    }
  },
  MICRO_IRRIGATION: {
    source: "Dept. of Agriculture, Govt. of Maharashtra (MahaDBT)",
    link: "https://mahadbt.maharashtra.gov.in",
    new_scheme: {
      days: 0,
      en: {
        title: "Active Window: PMKSY Micro-Irrigation (80% Drip Subsidy + 10% Marathwada/Vidarbha Top-Up)",
        body: "MahaDBT Official Notice: Subsidies are being processed for Drip and Sprinkler systems under Per Drop More Crop. Marginal farmers (<1 ha) receive 80% subsidy, small farmers (1-2 ha) receive 70%, with an extra 10% state top-up for drought-prone districts of Marathwada and Vidarbha on first-come-first-served basis."
      },
      hi: {
        title: "सक्रिय योजना: पीएमकेएसवाई सूक्ष्म सिंचाई (80% ड्रिप अनुदान + मराठवाड़ा-विदर्भ 10% अतिरिक्त लाभ)",
        body: "महाडीबीटी आधिकारिक सूचना: 'प्रति बूंद अधिक फसल' के अंतर्गत ड्रिप व स्प्रिंकलर हेतु आवेदन खुले हैं। अल्प भूधारक (<1 हे.) को 80% व छोटे किसानों को 70% अनुदान तथा मराठवाड़ा व विदर्भ के सूखाग्रस्त जिलों के लिए 10% अतिरिक्त राज्य अनुदान उपलब्ध है।"
      },
      mr: {
        title: "सक्रिय योजना: सूक्ष्म सिंचन योजना (८०% ठिबक अनुदान + मराठवाडा-विदर्भासाठी अतिरिक्त १०% टॉप-अप)",
        body: "महाडीबीटी अधिकृत सूचना: 'प्रति थेंब अधिक पीक' अंतर्गत ठिबक व तुषार सिंचनासाठी अर्ज प्रक्रिया सुरू आहे. अल्पभूधारक शेतकऱ्यांना ८०% आणि लहान शेतकऱ्यांना ७०% अनुदान, तसेच मराठवाडा व विदर्भातील दुष्काळग्रस्त जिल्ह्यांसाठी अतिरिक्त १०% राज्य अनुदान 'प्रथम येणाऱ्यास प्रथम प्राधान्य' तत्त्वावर वाटप होत आहे."
      }
    },
    closing_soon: {
      days: 12,
      en: {
        title: "Budget Cutoff Notice: Micro-Irrigation Subsidy Target Allocation",
        body: "Govt of Maharashtra notice: District expenditure targets for micro-irrigation under PMKSY are concluding. Farmers with preliminary pre-sanctions must upload dealer bills to prevent lapses."
      },
      hi: {
        title: "बजट समाप्ति सूचना: सूक्ष्म सिंचाई अनुदान लक्ष्य आवंटन",
        body: "महाराष्ट्र शासन सूचना: पीएमकेएसवाई के तहत सूक्ष्म सिंचाई हेतु जिलावार बजट लक्ष्य पूरा हो रहा है। पूर्व-सहमति प्राप्त किसान देयक अपलोड करें।"
      },
      mr: {
        title: "बजेट मुदत सूचना: सूक्ष्म सिंचन योजना पूर्वसंमती व देयक अपलोड मुदत",
        body: "महाराष्ट्र शासन सूचना: ठिबक व तुषार सिंचन योजनेचे जिल्हा उद्दिष्ट संपत आले आहे. पूर्वसंमती मिळालेल्या शेतकऱ्यांनी अनुदान व्यपगत होऊ नये म्हणून अधिकृत विक्रेत्याचे बिल त्वरित अपलोड करावे."
      }
    }
  },
  PMKISAN: {
    source: "Ministry of Agriculture & Farmers Welfare, GoI & MahaAgri",
    link: "https://pmkisan.gov.in",
    new_scheme: {
      days: 0,
      en: {
        title: "Official Release: PM-KISAN & Namo Shetkari Joint Installment Disbursed",
        body: "Ministry of Agriculture & Maharashtra Govt advisory: The joint ₹4,000 DBT installment (₹2,000 Central PM-KISAN + ₹2,000 Maharashtra Namo Shetkari) has been authorized for direct transfer to Aadhaar-linked bank accounts."
      },
      hi: {
        title: "आधिकारिक घोषणा: पीएम-किसान व नमो शेतकरी संयुक्त ₹4,000 किस्त जारी",
        body: "कृषि मंत्रालय व महाराष्ट्र शासन सूचना: संयुक्त ₹4,000 की डीबीटी किस्त (₹2,000 केंद्र + ₹2,000 राज्य) आधार से जुड़े बैंक खातों में अंतरित की जा रही है।"
      },
      mr: {
        title: "अधिकृत घोषणा: पीएम-किसान व नमो शेतकरी संयुक्त ₹४,००० चा हप्ता वितरित",
        body: "कृषी मंत्रालय व महाराष्ट्र शासन सूचना: संयुक्त ₹४,००० चा हप्ता (₹२,००० केंद्र + ₹२,००० राज्य नमो शेतकरी) आधार संलग्न बँक खात्यात थेट जमा केला जात आहे."
      }
    },
    closing_soon: {
      days: 15,
      en: {
        title: "Urgent Compliance Notice: PM-KISAN & Namo Shetkari Maha Sanman Nidhi e-KYC Cutoff",
        body: "Ministry of Agriculture & Govt of Maharashtra directive: To receive the forthcoming ₹4,000 installment (₹2,000 Central PM-KISAN + ₹2,000 Maharashtra Namo Shetkari), all beneficiaries must complete biometric or OTP e-KYC on pmkisan.gov.in and ensure NPCI bank account seeding by the notified cutoff."
      },
      hi: {
        title: "अनिवार्य सूचना: पीएम-किसान व नमो शेतकरी योजना e-KYC व आधार-बैंक लिंकिंग की अंतिम तिथि",
        body: "कृषि मंत्रालय व महाराष्ट्र शासन निर्देश: आगामी ₹4,000 की किस्त (₹2,000 पीएम-किसान + ₹2,000 नमो शेतकरी) प्राप्त करने हेतु सभी लाभार्थी pmkisan.gov.in पर तत्काल बायोमेट्रिक या ओटीपी e-KYC तथा बैंक खाते में NPCI आधार सीडिंग अनिवार्य रूप से पूर्ण करें।"
      },
      mr: {
        title: "अत्यंत तातडीची सूचना: पीएम-किसान व नमो शेतकरी महासन्मान निधी e-KYC व आधार जोडणी मुदत",
        body: "कृषी मंत्रालय व महाराष्ट्र शासन परिपत्रक: आगामी ₹४,००० चा संयुक्त हप्ता (₹२,००० पीएम-किसान + ₹२,००० नमो शेतकरी) थेट खात्यात मिळवण्यासाठी pmkisan.gov.in वर बायोमेट्रिक/OTP e-KYC आणि बँक खात्याशी NPCI आधार संलग्नता अंतिम मुदतीपूर्वी पूर्ण करणे बंधनकारक आहे."
      }
    }
  }
};

const TYPE_LABELS = {
  new_scheme:   { label: "New Scheme",    color: "#2C5F2D", bg: "#EAF3E4" },
  closing_soon: { label: "Closing Soon",  color: "#D4870A", bg: "#FEF4E6" },
};

function NotificationsView() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  // Form state
  const [form, setForm] = useState({
    scheme_id: "PMFBY",
    type: "closing_soon",
    deadline: "",
    titleEn: "", titleHi: "", titleMr: "",
    bodyEn: "", bodyHi: "", bodyMr: "",
    official_source: "Agriculture Dept., Govt. of Maharashtra (MahaAgri) & MoA&FW, GoI",
    official_link: "https://pmfby.gov.in",
  });

  const loadNotifications = () => {
    setLoading(true);
    fetch("http://localhost:8000/admin/notifications")
      .then((r) => r.json())
      .then(setNotifications)
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadNotifications(); }, []);

  const handleDeactivate = (id) => {
    fetch(`http://localhost:8000/admin/notifications/${id}/deactivate`, { method: "PATCH" })
      .then(() => loadNotifications());
  };

  const handleAutoFill = () => {
    const alertData = AUTHENTIC_SCHEME_ALERTS[form.scheme_id];
    const typeData = alertData ? alertData[form.type] : null;

    if (alertData && typeData) {
      let deadlineDate = "";
      if (typeData.days > 0) {
        const d = new Date();
        d.setDate(d.getDate() + typeData.days);
        deadlineDate = d.toISOString().split("T")[0];
      }

      setForm((f) => ({
        ...f,
        deadline: deadlineDate,
        titleEn: typeData.en.title,
        titleHi: typeData.hi.title,
        titleMr: typeData.mr.title,
        bodyEn: typeData.en.body,
        bodyHi: typeData.hi.body,
        bodyMr: typeData.mr.body,
        official_source: alertData.source,
        official_link: alertData.link,
      }));
    } else {
      const scheme = SCHEME_OPTIONS.find((s) => s.id === form.scheme_id) || { name: form.scheme_id };
      const isNew = form.type === "new_scheme";
      setForm((f) => ({
        ...f,
        titleEn: isNew ? `Official Notice: ${scheme.name} Application Open` : `Official Notice: ${scheme.name} Deadline Approaching`,
        titleHi: isNew ? `आधिकारिक सूचना: ${scheme.name} आवेदन प्रारंभ` : `आधिकारिक सूचना: ${scheme.name} अंतिम तिथि निकट`,
        titleMr: isNew ? `अधिकृत शासन सूचना: ${scheme.name} अर्ज प्रक्रिया सुरू` : `अधिकृत शासन सूचना: ${scheme.name} अंतिम मुदत संपत आहे`,
        bodyEn: isNew
          ? `Government notification: The application window for ${scheme.name} is officially open on MahaDBT portal for eligible Maharashtra farmers.`
          : `Government notification: Applications for ${scheme.name} are closing soon. Complete your registration on the official portal before cutoff.`,
        bodyHi: isNew
          ? `सरकारी अधिसूचना: पात्र महाराष्ट्र किसानों के लिए महाडीबीटी पोर्टल पर ${scheme.name} हेतु आवेदन प्रक्रिया आधिकारिक रूप से चालू है।`
          : `सरकारी अधिसूचना: ${scheme.name} हेतु आवेदन जल्द समाप्त हो रहे हैं। अंतिम तिथि से पूर्व आधिकारिक पोर्टल पर आवेदन पूर्ण करें।`,
        bodyMr: isNew
          ? `शासन परिपत्रक: पात्र शेतकर्‍यांसाठी महाडीबीटी पोर्टलवर ${scheme.name} योजनेचे अर्ज अधिकृतपणे सुरू आहेत.`
          : `शासन परिपत्रक: ${scheme.name} योजनेचे अर्ज करण्याची अंतिम मुदत जवळ आली आहे. शेवटच्या तारखेपूर्वी अधिकृत पोर्टलवर अर्ज सादर करा.`,
        official_source: "Dept. of Agriculture, Govt. of Maharashtra (MahaDBT)",
        official_link: "https://mahadbt.maharashtra.gov.in",
      }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.titleEn || !form.bodyEn) return;
    setSubmitting(true);
    const payload = {
      scheme_id: form.scheme_id,
      type: form.type,
      title: { en: form.titleEn, hi: form.titleHi, mr: form.titleMr },
      body:  { en: form.bodyEn,  hi: form.bodyHi,  mr: form.bodyMr  },
      deadline: form.deadline || null,
      eligible_categories: [],
      official_source: form.official_source || "Dept. of Agriculture, Govt. of Maharashtra",
      official_link: form.official_link || "https://mahadbt.maharashtra.gov.in",
    };
    fetch("http://localhost:8000/admin/notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => {
        setSuccessMsg("Verified government alert published to all eligible farmers!");
        setTimeout(() => setSuccessMsg(""), 4000);
        setForm({
          scheme_id: "PMFBY",
          type: "closing_soon",
          deadline: "",
          titleEn: "", titleHi: "", titleMr: "",
          bodyEn: "", bodyHi: "", bodyMr: "",
          official_source: "Agriculture Dept., Govt. of Maharashtra (MahaAgri) & MoA&FW, GoI",
          official_link: "https://pmfby.gov.in",
        });
        loadNotifications();
      })
      .catch(() => setSuccessMsg("Error publishing notification."))
      .finally(() => setSubmitting(false));
  };

  const inputStyle = {
    width: "100%", padding: "0.6rem 0.8rem", borderRadius: "8px",
    border: "1.5px solid var(--admin-border)", fontSize: "0.85rem",
    color: "var(--admin-text)", outline: "none", boxSizing: "border-box",
    background: "#FAFCF9",
  };
  const labelStyle = { fontSize: "0.78rem", fontWeight: 700, color: "var(--admin-primary-dark)", display: "block", marginBottom: "0.35rem" };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">

      {/* CREATE ALERT FORM */}
      <div className="admin-card">
        <p className="admin-title" style={{ fontSize: "1.15rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Bell size={20} /> Publish Official Scheme Alert (Verified Notice)
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Row 1: Scheme + Type + Deadline */}
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={labelStyle}>Government Scheme</label>
              <select value={form.scheme_id} onChange={(e) => setForm({ ...form, scheme_id: e.target.value })} style={inputStyle}>
                {SCHEME_OPTIONS.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Announcement Type</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} style={inputStyle}>
                <option value="closing_soon">⏰ Closing Soon (Deadline Approaching)</option>
                <option value="new_scheme">🌱 New Scheme / Quota Open</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>Official Deadline (optional)</label>
              <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} style={inputStyle} />
            </div>
          </div>

          {/* Row 2: Official Source & Portal Link */}
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "1rem" }}>
            <div>
              <label style={labelStyle}>🏛️ Official Government Source / Resolution</label>
              <input
                value={form.official_source}
                onChange={(e) => setForm({ ...form, official_source: e.target.value })}
                placeholder="e.g. Dept. of Agriculture, Govt. of Maharashtra (MahaDBT)"
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>🌐 Official Portal Application Link</label>
              <input
                value={form.official_link}
                onChange={(e) => setForm({ ...form, official_link: e.target.value })}
                placeholder="e.g. https://mahadbt.maharashtra.gov.in"
                style={inputStyle}
                required
              />
            </div>
          </div>

          {/* Auto-fill button */}
          <div>
            <button type="button" onClick={handleAutoFill}
              style={{ padding: "0.55rem 1.1rem", borderRadius: "8px", border: "1.5px dashed var(--admin-primary)", background: "#F4F7F2", color: "var(--admin-primary-dark)", fontWeight: 700, fontSize: "0.82rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
            >
              ✨ Auto-fill verified government notice & official links
            </button>
          </div>

          {/* English */}
          <div style={{ background: "#F4F7F2", borderRadius: "10px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <p style={{ ...labelStyle, color: "#2C5F2D", marginBottom: 0 }}>🇬🇧 English Notice</p>
            <div>
              <label style={labelStyle}>Official Title</label>
              <input value={form.titleEn} onChange={(e) => setForm({ ...form, titleEn: e.target.value })} placeholder="e.g. Official Notice: PMFBY ₹1 Crop Insurance Enrollment Deadline" style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Notice Body</label>
              <textarea value={form.bodyEn} onChange={(e) => setForm({ ...form, bodyEn: e.target.value })} rows={2} placeholder="Official government notice text in English..." style={{ ...inputStyle, resize: "vertical" }} required />
            </div>
          </div>

          {/* Hindi */}
          <div style={{ background: "#FEF9F0", borderRadius: "10px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <p style={{ ...labelStyle, color: "#D4870A", marginBottom: 0 }}>🇮🇳 हिंदी सूचना</p>
            <div>
              <label style={labelStyle}>आधिकारिक शीर्षक (Title)</label>
              <input value={form.titleHi} onChange={(e) => setForm({ ...form, titleHi: e.target.value })} placeholder="जैसे: आधिकारिक अधिसूचना: ₹1 फसल बीमा योजना..." style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>आधिकारिक संदेश (Body)</label>
              <textarea value={form.bodyHi} onChange={(e) => setForm({ ...form, bodyHi: e.target.value })} rows={2} placeholder="हिंदी में आधिकारिक सरकारी संदेश..." style={{ ...inputStyle, resize: "vertical" }} />
            </div>
          </div>

          {/* Marathi */}
          <div style={{ background: "#F0F8FD", borderRadius: "10px", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <p style={{ ...labelStyle, color: "#1A6B8A", marginBottom: 0 }}>🇮🇳 मराठी परिपत्रक</p>
            <div>
              <label style={labelStyle}>अधिकृत शीर्षक (Title)</label>
              <input value={form.titleMr} onChange={(e) => setForm({ ...form, titleMr: e.target.value })} placeholder="उदा: अधिकृत शासन परिपत्रक: १ रुपयात पीक विमा नोंदणी मुदत..." style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>अधिकृत संदेश (Body)</label>
              <textarea value={form.bodyMr} onChange={(e) => setForm({ ...form, bodyMr: e.target.value })} rows={2} placeholder="मराठीत अधिकृत शासन संदेश..." style={{ ...inputStyle, resize: "vertical" }} />
            </div>
          </div>

          {successMsg && (
            <div style={{ padding: "0.75rem 1rem", borderRadius: "8px", background: "#EAF3E4", color: "#2C5F2D", fontWeight: 700, fontSize: "0.9rem" }}>
              ✓ {successMsg}
            </div>
          )}

          <div>
            <button type="submit" disabled={submitting} className="admin-btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.75rem" }}>
              <Bell size={16} />
              {submitting ? "Publishing..." : "Publish Official Verified Alert to Eligible Farmers"}
            </button>
          </div>
        </form>
      </div>

      {/* EXISTING NOTIFICATIONS TABLE */}
      <div className="admin-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <p className="admin-title" style={{ fontSize: "1.1rem", margin: 0 }}>Active & Published Verified Alerts</p>
          <button onClick={loadNotifications} className="admin-btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.5rem 1rem", fontSize: "0.8rem" }}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>

        <div className="admin-table-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Scheme</th>
                <th>Type</th>
                <th>Verified Government Notice</th>
                <th>Official Source & Portal</th>
                <th>Deadline</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8} style={{ textAlign: "center", padding: "2rem", color: "var(--admin-muted)" }}>Loading official alerts...</td></tr>
              )}
              {!loading && notifications.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: "center", padding: "2rem", color: "var(--admin-muted)" }}>No notifications published yet.</td></tr>
              )}
              {!loading && notifications.map((n) => {
                const typeInfo = TYPE_LABELS[n.type] || TYPE_LABELS.new_scheme;
                return (
                  <tr key={n.id}>
                    <td style={{ color: "var(--admin-muted)", fontSize: "0.8rem" }}>#{n.id}</td>
                    <td className="td-bold">{n.scheme_id}</td>
                    <td>
                      <span style={{ padding: "0.2rem 0.6rem", borderRadius: "6px", fontSize: "0.75rem", fontWeight: 700, background: typeInfo.bg, color: typeInfo.color }}>
                        {typeInfo.label}
                      </span>
                    </td>
                    <td style={{ maxWidth: "230px" }}>
                      <div style={{ fontWeight: 700, color: "var(--admin-text)", fontSize: "0.85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {n.title?.en || "—"}
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--admin-muted)", marginTop: "0.15rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {n.title?.mr || n.title?.hi || ""}
                      </div>
                    </td>
                    <td style={{ maxWidth: "180px", fontSize: "0.78rem" }}>
                      <div style={{ fontWeight: 600, color: "#2C5F2D", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {n.official_source || "Dept. of Agriculture"}
                      </div>
                      {n.official_link && (
                        <a
                          href={n.official_link.startsWith("http") ? n.official_link : `https://${n.official_link}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "var(--admin-primary)", fontSize: "0.72rem", display: "inline-flex", alignItems: "center", gap: "0.25rem", textDecoration: "underline", marginTop: "0.15rem" }}
                        >
                          <span>Official Portal</span>
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </td>
                    <td style={{ fontSize: "0.82rem", color: n.deadline ? "#D4870A" : "var(--admin-muted)", whiteSpace: "nowrap" }}>
                      {n.deadline ? (
                        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                          <Clock size={12} />{n.deadline}
                        </span>
                      ) : "Active Window"}
                    </td>
                    <td>
                      <span style={{ padding: "0.2rem 0.6rem", borderRadius: "6px", fontSize: "0.75rem", fontWeight: 700, background: n.is_active ? "#EAF3E4" : "#F3F4F6", color: n.is_active ? "#2C5F2D" : "#9CA3A3" }}>
                        {n.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      {n.is_active === 1 && (
                        <button
                          onClick={() => handleDeactivate(n.id)}
                          title="Deactivate this alert"
                          style={{ background: "none", border: "1px solid #E8B4A0", borderRadius: "6px", padding: "0.25rem 0.5rem", cursor: "pointer", color: "#B45B4A", display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.78rem", fontWeight: 700 }}
                        >
                          <Trash2 size={12} /> Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// --- SETTINGS VIEW ---
function SettingsView() {
  const [activeTab, setActiveTab] = useState("agriculture");
  const [settings, setSettings] = useState({
    active_season: "Kharif 2026-27",
    marginal_land_cap: 1.0,
    small_land_cap: 2.0,
    enable_drought_topup: true,
    search_threshold: 0.20,
    ai_response_mode: "detailed",
    default_language: "mr",
    enable_cross_lingual: true,
    alert_window_days: 14,
    auto_broadcast_status_change: true,
    sms_gateway_simulation: false,
    kisan_call_center: "1800-120-8040",
    pmkisan_helpline: "155261",
    mahadbt_portal_url: "https://mahadbt.maharashtra.gov.in",
    pmfby_portal_url: "https://pmfby.gov.in",
    pmkisan_portal_url: "https://pmkisan.gov.in",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [farmersCount, setFarmersCount] = useState(0);

  // Fetch settings from API on mount
  useEffect(() => {
    fetch("http://localhost:8000/settings")
      .then((r) => r.json())
      .then((data) => setSettings((prev) => ({ ...prev, ...data })))
      .catch(() => {})
      .finally(() => setLoading(false));

    // Also fetch farmers count for diagnostics
    fetch("http://localhost:8000/admin/users")
      .then((r) => r.json())
      .then((users) => setFarmersCount(Array.isArray(users) ? users.length : 0))
      .catch(() => {});
  }, []);

  const handleSave = () => {
    setSaving(true);
    fetch("http://localhost:8000/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    })
      .then((r) => r.json())
      .then((updated) => {
        setSettings((prev) => ({ ...prev, ...updated }));
        setSuccessMsg("Configuration saved to database successfully!");
        setTimeout(() => setSuccessMsg(""), 4000);
      })
      .catch(() => setSuccessMsg("Error saving settings."))
      .finally(() => setSaving(false));
  };

  const handleReset = () => {
    if (!window.confirm("Are you sure you want to reset all platform settings back to system defaults?")) return;
    setSaving(true);
    fetch("http://localhost:8000/settings/reset", { method: "POST" })
      .then((r) => r.json())
      .then((defaults) => {
        setSettings(defaults);
        setSuccessMsg("All settings have been reset to default values.");
        setTimeout(() => setSuccessMsg(""), 4000);
      })
      .catch(() => setSuccessMsg("Error resetting settings."))
      .finally(() => setSaving(false));
  };

  const inputStyle = {
    width: "100%", padding: "0.65rem 0.85rem", borderRadius: "8px",
    border: "1.5px solid var(--admin-border)", fontSize: "0.85rem",
    color: "var(--admin-text)", outline: "none", boxSizing: "border-box",
    background: "#FAFCF9",
  };
  const labelStyle = { fontSize: "0.78rem", fontWeight: 700, color: "var(--admin-primary-dark)", display: "block", marginBottom: "0.35rem" };

  const tabs = [
    { key: "agriculture", label: "🌾 Agriculture & Season", icon: Sprout },
    { key: "ai_search", label: "🤖 AI & Semantic Search", icon: Sliders },
    { key: "alerts", label: "🔔 Alert Policies", icon: Bell },
    { key: "helplines", label: "📞 Helplines & Portals", icon: Phone },
    { key: "diagnostics", label: "🔐 System & Diagnostics", icon: Shield },
  ];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">

      {/* Top action header */}
      <div className="admin-card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--admin-primary-dark)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Settings size={22} /> Platform & System Configuration
          </h2>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.82rem", color: "var(--admin-muted)" }}>
            Tune scheme rules, AI matching parameters, automated alerts, and official government portal links.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            type="button"
            onClick={handleReset}
            disabled={saving || loading}
            style={{
              padding: "0.55rem 1rem", borderRadius: "8px", border: "1.5px solid #E5EADF",
              background: "#fff", color: "var(--admin-muted)", fontWeight: 700, fontSize: "0.82rem",
              cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.4rem"
            }}
          >
            <RotateCcw size={14} /> Reset Defaults
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            className="admin-btn-primary"
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", padding: "0.6rem 1.4rem" }}
          >
            <Save size={15} /> {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>

      {successMsg && (
        <div style={{ padding: "0.8rem 1.2rem", borderRadius: "10px", background: "#EAF3E4", border: "1px solid #CDE2C9", color: "#2C5F2D", fontWeight: 700, fontSize: "0.88rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <CheckCircle2 size={18} /> {successMsg}
        </div>
      )}

      {/* Sub-navigation tabs */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "2px solid #E5EADF", paddingBottom: "0.25rem", overflowX: "auto" }}>
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.45rem",
                padding: "0.65rem 1.1rem", borderRadius: "10px", border: "none",
                fontSize: "0.85rem", fontWeight: 700, cursor: "pointer",
                background: isActive ? "var(--admin-primary)" : "transparent",
                color: isActive ? "#fff" : "var(--admin-muted)",
                transition: "all 0.15s ease", whiteSpace: "nowrap"
              }}
            >
              <Icon size={16} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: 🌾 AGRICULTURE & SEASONS */}
      {activeTab === "agriculture" && (
        <div className="space-y-6">
          <div className="admin-card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--admin-primary-dark)", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Sprout size={18} /> Crop Season & Landholding Definitions
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div>
                <label style={labelStyle}>Active Agricultural Season (Maharashtra)</label>
                <select
                  value={settings.active_season}
                  onChange={(e) => setSettings({ ...settings, active_season: e.target.value })}
                  style={inputStyle}
                >
                  <option value="Kharif 2026-27">🌧️ Kharif Cycle (June – October 2026)</option>
                  <option value="Rabi 2026-27">❄️ Rabi Cycle (October – March 2026-27)</option>
                  <option value="Summer (Zaid) 2027">☀️ Summer / Zaid Cycle (March – May 2027)</option>
                </select>
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Sets the default seasonal recommendations and crop insurance timeline across all farmer dashboards.
                </p>
              </div>

              <div>
                <label style={labelStyle}>Marathwada & Vidarbha Drought Relief Top-Up</label>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem" }}>
                  <input
                    type="checkbox"
                    id="topup_toggle"
                    checked={settings.enable_drought_topup}
                    onChange={(e) => setSettings({ ...settings, enable_drought_topup: e.target.checked })}
                    style={{ width: "18px", height: "18px", accentColor: "var(--admin-primary)", cursor: "pointer" }}
                  />
                  <label htmlFor="topup_toggle" style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--admin-text)", cursor: "pointer" }}>
                    Enable 10% Extra Regional Top-Up Subsidy for Drought-Prone Districts
                  </label>
                </div>
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Applies to Chhatrapati Sambhajinagar, Jalna, Beed, Nanded, Yavatmal, and drought-notified talukas.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px dashed var(--admin-border)" }}>
              <div>
                <label style={labelStyle}>Marginal Farmer Ceiling (Hectares)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="5"
                  value={settings.marginal_land_cap}
                  onChange={(e) => setSettings({ ...settings, marginal_land_cap: parseFloat(e.target.value) || 1.0 })}
                  style={inputStyle}
                />
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Standard: 1.0 hectare (qualifies for 80% maximum micro-irrigation subsidy).
                </p>
              </div>

              <div>
                <label style={labelStyle}>Small Farmer Ceiling (Hectares)</label>
                <input
                  type="number"
                  step="0.1"
                  min="1.0"
                  max="10"
                  value={settings.small_land_cap}
                  onChange={(e) => setSettings({ ...settings, small_land_cap: parseFloat(e.target.value) || 2.0 })}
                  style={inputStyle}
                />
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Standard: 2.0 hectares (qualifies for 70% micro-irrigation and preferential mechanization quota).
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: 🤖 AI & SEMANTIC SEARCH */}
      {activeTab === "ai_search" && (
        <div className="space-y-6">
          <div className="admin-card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--admin-primary-dark)", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Sliders size={18} /> Semantic Search & Natural Language Parameters
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "1.5rem" }}>
              <div>
                <label style={labelStyle}>
                  FAISS Match Confidence Threshold: <span style={{ color: "var(--admin-primary)", fontWeight: 800 }}>{settings.search_threshold}</span>
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.5rem" }}>
                  <input
                    type="range"
                    min="0.10"
                    max="0.50"
                    step="0.01"
                    value={settings.search_threshold}
                    onChange={(e) => setSettings({ ...settings, search_threshold: parseFloat(e.target.value) })}
                    style={{ flex: 1, accentColor: "var(--admin-primary)", cursor: "pointer" }}
                  />
                  <span style={{ fontSize: "0.9rem", fontWeight: 800, minWidth: "40px", color: "var(--admin-text)" }}>
                    {settings.search_threshold}
                  </span>
                </div>
                <p style={{ margin: "0.4rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Lower value (0.15–0.20) gives strict relevant matches. Higher value (0.35+) allows broader query matches.
                </p>
              </div>

              <div>
                <label style={labelStyle}>AI Response Guidance Style</label>
                <select
                  value={settings.ai_response_mode}
                  onChange={(e) => setSettings({ ...settings, ai_response_mode: e.target.value })}
                  style={inputStyle}
                >
                  <option value="detailed">📋 Comprehensive Step-by-Step with Document Checklist</option>
                  <option value="concise">⚡ Quick Factual Answers (Status & Eligibility Only)</option>
                </select>
                <p style={{ margin: "0.4rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Controls the length and document guidance included in Gemini/LLM interactions.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px dashed var(--admin-border)" }}>
              <div>
                <label style={labelStyle}>System-Wide Fallback Language</label>
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem" }}>
                  {[
                    { code: "mr", label: "मराठी (Marathi)" },
                    { code: "hi", label: "हिंदी (Hindi)" },
                    { code: "en", label: "English" },
                  ].map((l) => (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => setSettings({ ...settings, default_language: l.code })}
                      style={{
                        padding: "0.5rem 0.9rem", borderRadius: "8px",
                        border: settings.default_language === l.code ? "2px solid var(--admin-primary)" : "1.5px solid var(--admin-border)",
                        background: settings.default_language === l.code ? "#EAF3E4" : "#fff",
                        color: settings.default_language === l.code ? "var(--admin-primary-dark)" : "var(--admin-text)",
                        fontWeight: 700, fontSize: "0.82rem", cursor: "pointer"
                      }}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={labelStyle}>Cross-Lingual Semantic Matching</label>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.6rem" }}>
                  <input
                    type="checkbox"
                    id="crosslingual_toggle"
                    checked={settings.enable_cross_lingual}
                    onChange={(e) => setSettings({ ...settings, enable_cross_lingual: e.target.checked })}
                    style={{ width: "18px", height: "18px", accentColor: "var(--admin-primary)", cursor: "pointer" }}
                  />
                  <label htmlFor="crosslingual_toggle" style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--admin-text)", cursor: "pointer" }}>
                    Enable multilingual vector index search across Marathi, Hindi & English
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: 🔔 ALERT POLICIES */}
      {activeTab === "alerts" && (
        <div className="space-y-6">
          <div className="admin-card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--admin-primary-dark)", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Bell size={18} /> Automated Notification & Cutoff Broadcast Policies
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div>
                <label style={labelStyle}>"Closing Soon" Trigger Threshold (Days Before Deadline)</label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={settings.alert_window_days}
                  onChange={(e) => setSettings({ ...settings, alert_window_days: parseInt(e.target.value, 10) || 14 })}
                  style={inputStyle}
                />
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.74rem", color: "var(--admin-muted)" }}>
                  Schemes with deadlines inside this window automatically appear with amber warning badges in farmer alerts.
                </p>
              </div>

              <div>
                <label style={labelStyle}>Auto-Publish Alert on Scheme Opening</label>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.6rem" }}>
                  <input
                    type="checkbox"
                    id="auto_broadcast_toggle"
                    checked={settings.auto_broadcast_status_change}
                    onChange={(e) => setSettings({ ...settings, auto_broadcast_status_change: e.target.checked })}
                    style={{ width: "18px", height: "18px", accentColor: "var(--admin-primary)", cursor: "pointer" }}
                  />
                  <label htmlFor="auto_broadcast_toggle" style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--admin-text)", cursor: "pointer" }}>
                    Broadcast verified alert when a scheme status changes from "Closed" to "Open"
                  </label>
                </div>
              </div>
            </div>

            <div style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px dashed var(--admin-border)" }}>
              <label style={labelStyle}>Rural SMS / Kisan Call Center SMS Broadcast (Simulation Mode)</label>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.4rem" }}>
                <input
                  type="checkbox"
                  id="sms_toggle"
                  checked={settings.sms_gateway_simulation}
                  onChange={(e) => setSettings({ ...settings, sms_gateway_simulation: e.target.checked })}
                  style={{ width: "18px", height: "18px", accentColor: "var(--admin-primary)", cursor: "pointer" }}
                />
                <label htmlFor="sms_toggle" style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--admin-text)", cursor: "pointer" }}>
                  Simulate automated SMS dispatch for non-smartphone farmers on scheme cutoffs
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: 📞 HELPLINES & PORTALS */}
      {activeTab === "helplines" && (
        <div className="space-y-6">
          <div className="admin-card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--admin-primary-dark)", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Phone size={18} /> Official Government Helplines & Application Domains
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div>
                <label style={labelStyle}>Maharashtra Kisan Call Centre (Toll-Free)</label>
                <input
                  value={settings.kisan_call_center}
                  onChange={(e) => setSettings({ ...settings, kisan_call_center: e.target.value })}
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={labelStyle}>PM-KISAN National Helpline Number</label>
                <input
                  value={settings.pmkisan_helpline}
                  onChange={(e) => setSettings({ ...settings, pmkisan_helpline: e.target.value })}
                  style={inputStyle}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px dashed var(--admin-border)" }}>
              <div>
                <label style={labelStyle}>MahaDBT Portal URL</label>
                <input
                  value={settings.mahadbt_portal_url}
                  onChange={(e) => setSettings({ ...settings, mahadbt_portal_url: e.target.value })}
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={labelStyle}>PMFBY Crop Insurance URL</label>
                <input
                  value={settings.pmfby_portal_url}
                  onChange={(e) => setSettings({ ...settings, pmfby_portal_url: e.target.value })}
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={labelStyle}>PM-KISAN Portal URL</label>
                <input
                  value={settings.pmkisan_portal_url}
                  onChange={(e) => setSettings({ ...settings, pmkisan_portal_url: e.target.value })}
                  style={inputStyle}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: 🔐 SYSTEM DIAGNOSTICS */}
      {activeTab === "diagnostics" && (
        <div className="space-y-6">
          <div className="admin-card">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--admin-primary-dark)", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Shield size={18} /> System Diagnostics & Health Status
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
              {/* SQLite DB Card */}
              <div style={{ background: "#FAFCF9", border: "1px solid var(--admin-border)", borderRadius: "12px", padding: "1.1rem" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--admin-muted)" }}>DATABASE</span>
                  <Database size={16} color="var(--admin-primary)" />
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--admin-primary-dark)" }}>SQLite 3</div>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "#2C5F2D", fontWeight: 700 }}>
                  ● Active (`backend/users.db`)
                </p>
              </div>

              {/* Registered Farmers */}
              <div style={{ background: "#FAFCF9", border: "1px solid var(--admin-border)", borderRadius: "12px", padding: "1.1rem" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--admin-muted)" }}>REGISTERED FARMERS</span>
                  <Users size={16} color="var(--admin-primary)" />
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--admin-primary-dark)" }}>{farmersCount} Farmers</div>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--admin-muted)" }}>
                  Active beneficiary profiles
                </p>
              </div>

              {/* Verified Schemes */}
              <div style={{ background: "#FAFCF9", border: "1px solid var(--admin-border)", borderRadius: "12px", padding: "1.1rem" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--admin-muted)" }}>VERIFIED SCHEMES</span>
                  <ListChecks size={16} color="var(--admin-primary)" />
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--admin-primary-dark)" }}>11 Schemes</div>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "#2C5F2D", fontWeight: 700 }}>
                  ● Maharashtra & Central Active
                </p>
              </div>

              {/* Vector Store */}
              <div style={{ background: "#FAFCF9", border: "1px solid var(--admin-border)", borderRadius: "12px", padding: "1.1rem" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--admin-muted)" }}>VECTOR STORE</span>
                  <Zap size={16} color="var(--admin-primary)" />
                </div>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--admin-primary-dark)" }}>FAISS Index</div>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "#2C5F2D", fontWeight: 700 }}>
                  ● Multilingual Embeddings Ready
                </p>
              </div>
            </div>

            <div style={{ marginTop: "1.25rem", padding: "1rem", borderRadius: "10px", background: "#F4F7F2", border: "1px solid #DCE3D9", fontSize: "0.8rem", color: "var(--admin-text)" }}>
              <strong>Admin Access & Role:</strong> Super Administrator (<span style={{ color: "var(--admin-primary)", fontWeight: 700 }}>admin@krushimitra.gov.in</span>) with full authorization to publish verified GR alerts and update platform rules.
            </div>
          </div>
        </div>
      )}

    </div>
  );
}


// --- MAIN COMPONENT ---
export default function KrushiMitraAdminDashboard({ onLogout }) {
  const [view, setView] = useState("overview");
  const [schemes, setSchemes] = useState(INITIAL_SCHEMES);

  function toggleStatus(id) {
    setSchemes((prev) => prev.map((s) => (s.id === id ? { ...s, status: s.status === "Open" ? "Closed" : "Open" } : s)));
  }

  return (
    <div className="admin-wrapper">
      <Sidebar view={view} setView={setView} onLogout={onLogout} />
      
      <div className="admin-main">
        <div className="admin-header">
          <h1 className="admin-title">
            {view === "overview" && "Dashboard Overview"}
            {view === "schemes" && "Manage Govt. Schemes"}
            {view === "users" && "Registered Farmers & Accounts"}
            {view === "notifications" && "Scheme Alerts & Notifications"}
            {view === "analytics" && "Detailed Analytics"}
            {view === "settings" && "Console & System Settings"}
          </h1>
          <p className="admin-subtitle">Maharashtra Farmer Scheme Database · Krushi Mitra Admin</p>
        </div>

        {view === "overview" && <OverviewView schemes={schemes} />}
        {view === "schemes" && <SchemesView schemes={schemes} toggleStatus={toggleStatus} />}
        {view === "users" && <UsersView />}
        {view === "notifications" && <NotificationsView />}
        {view === "analytics" && <OverviewView schemes={schemes} />}
        {view === "settings" && <SettingsView />}
      </div>
    </div>
  );
}