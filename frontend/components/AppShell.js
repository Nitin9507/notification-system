"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

const ICONS = {
  triggers: "M13 2 4.5 13H11l-1 9 8.5-11H12l1-9Z",
  activity: "M3 12h3.5l2.5 6 4-14 2.5 8H21",
  channels: "M4 5h16v10H7l-3 3V5Zm2 2v6h13V7H6Z",
  account:
    "M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5Z",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0 2a2 2 0 1 1 0 4 2 2 0 0 1 0-4Zm7.4 2 1.5 1.2-1.4 2.4-1.8-.6a7.6 7.6 0 0 1-1.6.9l-.4 1.9h-2.8l-.4-1.9a7.6 7.6 0 0 1-1.6-.9l-1.8.6-1.4-2.4L7.2 12l-1.5-1.2 1.4-2.4 1.8.6c.5-.4 1-.7 1.6-.9l.4-1.9h2.8l.4 1.9c.6.2 1.1.5 1.6.9l1.8-.6 1.4 2.4L19.4 12Z",
  site: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 2c1.2 0 2.6 2.2 3.1 5H8.9C9.4 6.2 10.8 4 12 4ZM4.3 11h3.2c.1-2 .5-3.8 1.1-5.1A8 8 0 0 0 4.3 11Zm0 2a8 8 0 0 0 4.3 5.1c-.6-1.3-1-3.1-1.1-5.1H4.3Zm5.2 0h5c-.1 1.9-.5 3.5-1 4.6-.5 1-1 1.4-1.5 1.4s-1-.4-1.5-1.4c-.5-1.1-.9-2.7-1-4.6Zm6.9 0h3.3a8 8 0 0 1-4.3 5.1c.5-1.3.9-3.1 1-5.1Zm0-2c-.1-2-.5-3.8-1-5.1a8 8 0 0 1 4.3 5.1h-3.3Z",
};

function NavIcon({ name }) {
  const stroked = name === "activity";
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill={stroked ? "none" : "currentColor"}
      stroke={stroked ? "currentColor" : "none"}
      strokeWidth={stroked ? 2 : 0}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

export default function AppShell({
  nav = [],
  active,
  onNavigate,
  title,
  subtitle,
  actions,
  children,
}) {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">N</span>
          Notification System
        </div>

        <nav className="sidebar-nav">
          {nav.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${active === item.key ? "active" : ""}`}
              onClick={() => (item.href ? router.push(item.href) : onNavigate(item.key))}
            >
              <NavIcon name={item.icon} />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="sidebar-user">
            <span className="avatar">{(user?.username || "?")[0].toUpperCase()}</span>
            <div style={{ minWidth: 0 }}>
              <div className="sidebar-user-name">{user?.username}</div>
              <div className="sidebar-user-role">
                {user?.is_staff ? "Administrator" : "Member"}
              </div>
            </div>
          </div>
          <button className="nav-item subtle-item" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="page-head">
          <div>
            <h1 className="page-title">{title}</h1>
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
          <div className="row">{actions}</div>
        </header>
        <div className="page-body">{children}</div>
      </main>
    </div>
  );
}
