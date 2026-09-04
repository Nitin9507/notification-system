"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import TopBar from "@/components/TopBar";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    email: "",
    first_name: "",
    phone_e164: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (field) => (event) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.register(form);
      await login(form.username, form.password);
      router.push("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <TopBar />
      <div className="shell narrow">
        <div className="card">
          <h2>Create an account</h2>
          <p className="hint">
            Your email and phone number are the delivery addresses for the email and
            WhatsApp channels.
          </p>
          <form onSubmit={handleSubmit} className="stack">
            <div>
              <label htmlFor="username">Username</label>
              <input id="username" value={form.username} onChange={update("username")} required />
            </div>
            <div>
              <label htmlFor="first_name">First name</label>
              <input id="first_name" value={form.first_name} onChange={update("first_name")} />
            </div>
            <div>
              <label htmlFor="email">Email</label>
              <input id="email" type="email" value={form.email} onChange={update("email")} required />
            </div>
            <div>
              <label htmlFor="phone">WhatsApp number</label>
              <input
                id="phone"
                value={form.phone_e164}
                onChange={update("phone_e164")}
                placeholder="918559050811"
              />
              <p className="muted mono" style={{ marginTop: 4 }}>
                Country code first, no “+”. Must be whitelisted in the Meta sandbox.
              </p>
            </div>
            <div>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={form.password}
                onChange={update("password")}
                autoComplete="new-password"
                required
              />
            </div>
            {error && <p className="error">{error}</p>}
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create account"}
            </button>
          </form>
          <p className="muted" style={{ marginTop: 16 }}>
            Already registered? <Link href="/login">Log in</Link>
          </p>
        </div>
      </div>
    </>
  );
}
