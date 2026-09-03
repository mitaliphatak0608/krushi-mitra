import React, { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { Bell, Sprout, Clock, CheckCheck, Loader2, ShieldCheck, ExternalLink, Building2 } from "lucide-react";
import "./NotificationBell.css";

const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "krushi_read_notifs";
const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

// ─── helpers ────────────────────────────────────────────────────────────────

function getReadSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveReadSet(set) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
}

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = new Date(dateStr) - new Date();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function localText(obj, lang) {
  if (!obj) return "";
  return obj[lang] || obj["en"] || "";
}

// ─── NotificationCard ────────────────────────────────────────────────────────

function NotificationCard({ notif, lang, isUnread, onRead }) {
  const isNew = notif.type === "new_scheme";
  const days = daysUntil(notif.deadline);

  const TYPE_TEXT = {
    new_scheme: {
      en: "New Scheme",
      hi: "नई योजना",
      mr: "नवीन योजना",
    },
    closing_soon: {
      en: "Closing Soon",
      hi: "जल्द बंद",
      mr: "मुदत संपत आहे",
    },
  };

  const VERIFIED_TEXT = {
    en: "Verified Govt Notice",
    hi: "सत्यापित सरकारी सूचना",
    mr: "अधिकृत शासन परिपत्रक",
  };

  const APPLY_TEXT = {
    en: "Official Portal",
    hi: "पोर्टल पर जाएं",
    mr: "अधिकृत पोर्टलवर जा",
  };

  return (
    <div
      className={`notif-card ${isUnread ? "unread" : ""}`}
      onClick={() => onRead(notif.id)}
    >
      {/* Top row: Badges & Unread indicator */}
      <div className="notif-top-row">
        <div className="notif-tag-group">
          <span className={`notif-type-pill ${isNew ? "new-scheme" : "closing-soon"}`}>
            {isNew ? <Sprout size={11} /> : <Clock size={11} />}
            {TYPE_TEXT[notif.type]?.[lang] || TYPE_TEXT[notif.type]?.en}
          </span>
          <span className="notif-official-badge" title="Verified against official Maharashtra Government & Central portals">
            <ShieldCheck size={11} />
            {VERIFIED_TEXT[lang] || VERIFIED_TEXT.en}
          </span>
        </div>
        {isUnread && <span className="notif-unread-dot" />}
      </div>

      {/* Main content */}
      <div className="notif-main-content">
        <div className={`notif-icon ${isNew ? "new-scheme" : "closing-soon"}`}>
          {isNew ? <Sprout size={18} /> : <Clock size={18} />}
        </div>

        <div className="notif-text-area">
          <p className="notif-title">{localText(notif.title, lang)}</p>
          <p className="notif-body">{localText(notif.body, lang)}</p>
          {notif.official_source && (
            <div className="notif-source-meta">
              <Building2 size={11} />
              <span>{notif.official_source}</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer: Deadline & Official Portal Action Link */}
      <div className="notif-card-footer">
        {days !== null ? (
          <span className="notif-deadline">
            <Clock size={11} />
            {days > 0
              ? (lang === "mr" ? `अंतिम मुदत: ${days} दिवस शिल्लक` : lang === "hi" ? `अंतिम तिथि: ${days} दिन शेष` : `Closes in ${days} day${days !== 1 ? "s" : ""}`)
              : days === 0
              ? (lang === "mr" ? "आज अंतिम दिवस!" : lang === "hi" ? "आज अंतिम दिन!" : "Closes today!")
              : (lang === "mr" ? "मुदत संपली" : lang === "hi" ? "समयसीमा समाप्त" : "Deadline passed")}
          </span>
        ) : <span />}

        {notif.official_link && (
          <a
            href={notif.official_link.startsWith("http") ? notif.official_link : `https://${notif.official_link}`}
            target="_blank"
            rel="noopener noreferrer"
            className="notif-portal-link"
            onClick={(e) => {
              e.stopPropagation();
              onRead(notif.id);
            }}
          >
            <span>{APPLY_TEXT[lang] || APPLY_TEXT.en}</span>
            <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function NotificationBell({ lang = "en", profile = {} }) {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [readSet, setReadSet] = useState(getReadSet);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, right: 0 });
  const bellRef = useRef(null);

  // ── Fetch notifications from backend ──
  const fetchNotifications = useCallback(() => {
    setLoading(true);
    fetch(`${API_BASE}/notifications`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, lang }),
    })
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((data) => setNotifications(data))
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  }, [profile, lang]);

  // Initial fetch + polling
  useEffect(() => {
    fetchNotifications();
    const timer = setInterval(fetchNotifications, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchNotifications]);

  // Refetch when window gets focus
  useEffect(() => {
    const onFocus = () => fetchNotifications();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Calculate position from bell button's bounding rect
  const updatePos = useCallback(() => {
    if (!bellRef.current) return;
    const rect = bellRef.current.getBoundingClientRect();
    setDropdownPos({
      top: rect.bottom + 8,          // 8px below the bell
      right: window.innerWidth - rect.right,  // align right edges
    });
  }, []);

  const handleToggle = () => {
    updatePos();
    setOpen((v) => !v);
  };

  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", updatePos);
    window.addEventListener("scroll", updatePos, true);
    return () => {
      window.removeEventListener("resize", updatePos);
      window.removeEventListener("scroll", updatePos, true);
    };
  }, [open, updatePos]);

  // ── Mark helpers ──
  const markRead = useCallback((id) => {
    setReadSet((prev) => {
      const next = new Set(prev);
      next.add(id);
      saveReadSet(next);
      return next;
    });
  }, []);

  const markAllRead = useCallback(() => {
    setReadSet((prev) => {
      const next = new Set(prev);
      notifications.forEach((n) => next.add(n.id));
      saveReadSet(next);
      return next;
    });
  }, [notifications]);

  // ── Derived state ──
  const unreadCount = notifications.filter((n) => !readSet.has(n.id)).length;

  const LABEL = { en: "Notifications", hi: "सूचनाएं", mr: "सूचना" };
  const MARK_ALL = { en: "Mark all read", hi: "सभी पढ़े हुए चिह्नित करें", mr: "सर्व वाचले म्हणून चिन्हांकित करा" };
  const EMPTY = { en: "You're all caught up! No new alerts.", hi: "कोई नई सूचना नहीं है।", mr: "कोणत्याही नवीन सूचना नाहीत." };

  // Dropdown is portaled to document.body to escape overflow:auto on dash-main
  const dropdown = open
    ? createPortal(
        <div
          className="notif-dropdown"
          style={{ position: "fixed", top: dropdownPos.top, right: dropdownPos.right }}
        >
          <div className="notif-dropdown-header">
            <h3>{LABEL[lang] || LABEL.en}</h3>
            {notifications.length > 0 && unreadCount > 0 && (
              <button className="notif-mark-all-btn" onClick={markAllRead}>
                <CheckCheck size={13} style={{ display: "inline", marginRight: 4 }} />
                {MARK_ALL[lang] || MARK_ALL.en}
              </button>
            )}
          </div>

          {loading ? (
            <div className="notif-loading">
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : notifications.length === 0 ? (
            <div className="notif-empty">
              <Bell size={32} strokeWidth={1.5} />
              <p>{EMPTY[lang] || EMPTY.en}</p>
            </div>
          ) : (
            <div className="notif-list">
              {notifications.map((n) => (
                <NotificationCard
                  key={n.id}
                  notif={n}
                  lang={lang}
                  isUnread={!readSet.has(n.id)}
                  onRead={markRead}
                />
              ))}
            </div>
          )}
        </div>,
        document.body
      )
    : null;

  return (
    <div className="notif-bell-wrapper" ref={bellRef}>
      <button
        className="notif-bell-btn"
        onClick={handleToggle}
        title={LABEL[lang] || LABEL.en}
        aria-label={`${LABEL[lang] || LABEL.en} — ${unreadCount} unread`}
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="notif-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>
        )}
      </button>

      {dropdown}
    </div>
  );
}
