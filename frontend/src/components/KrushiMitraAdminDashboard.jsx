import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Sprout, LayoutGrid, ListChecks, BarChart3, Settings, Search,
  AlertTriangle, CheckCircle2, Pencil, ChevronDown, ChevronUp, Globe, 
  ExternalLink, LogOut, Users, RefreshCw, UserCheck
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
            {view === "analytics" && "Detailed Analytics"}
            {view === "settings" && "Console Settings"}
          </h1>
          <p className="admin-subtitle">Maharashtra Farmer Scheme Database · Krushi Mitra Admin</p>
        </div>

        {view === "overview" && <OverviewView schemes={schemes} />}
        {view === "schemes" && <SchemesView schemes={schemes} toggleStatus={toggleStatus} />}
        {view === "users" && <UsersView />}
        {view === "analytics" && <OverviewView schemes={schemes} />}
        {view === "settings" && (
          <div className="admin-card" style={{ textAlign: 'center', padding: '4rem' }}>
            <Settings size={48} color="var(--admin-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <h3 style={{ color: 'var(--admin-text)', fontWeight: 800 }}>Settings Module</h3>
            <p style={{ color: 'var(--admin-muted)' }}>Role management and permissions coming in Phase 2.</p>
          </div>
        )}
      </div>
    </div>
  );
}