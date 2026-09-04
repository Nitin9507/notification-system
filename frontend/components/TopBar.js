"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export default function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <header className="topbar">
      <span className="brand">Notification System</span>
      <nav>
        {user ? (
          <>
            <Link href="/dashboard">
              <button className="subtle">Dashboard</button>
            </Link>
            {user.is_staff && (
              <Link href="/admin">
                <button className="subtle">Admin</button>
              </Link>
            )}
            <span className="muted mono">{user.username}</span>
            <button onClick={handleLogout}>Log out</button>
          </>
        ) : (
          <Link href="/login">
            <button className="subtle">Log in</button>
          </Link>
        )}
      </nav>
    </header>
  );
}
