"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import TopBar from "@/components/TopBar";
import { explain } from "@/lib/friendly";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login(username, password);
      router.push(user?.is_staff ? "/admin" : "/dashboard");
    } catch (err) {
      setError(
        err.status === 401
          ? "That username and password don’t match. Please try again."
          : explain(err.message)
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <TopBar />
      <div className="shell narrow">
        <div className="card">
          <h2>Welcome back</h2>
          <p className="hint">
            Sign in to your account. We’ll let you know by WhatsApp, email or a browser
            pop-up, depending on what’s switched on.
          </p>
          <form onSubmit={handleSubmit} className="stack">
            <div>
              <label htmlFor="username">Username</label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                required
              />
            </div>
            <div>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="error">{error}</p>}
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="muted" style={{ marginTop: 16 }}>
            New here? <Link href="/register">Create an account</Link>
          </p>
        </div>
        <p className="muted" style={{ textAlign: "center", marginTop: 16, fontSize: 12.5 }}>
          Administrators are taken straight to the notification settings after signing in.
        </p>
      </div>
    </>
  );
}
