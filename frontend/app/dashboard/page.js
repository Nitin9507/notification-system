"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import ChannelIcon from "@/components/ChannelIcon";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CHANNEL_HELP, CHANNEL_LABELS, explain } from "@/lib/friendly";
import { isConfigured, subscribeToPush } from "@/lib/onesignal";

const HEADINGS = {
  account: {
    title: "Your details",
    subtitle: "Where we send your notifications.",
  },
  try: {
    title: "Try it out",
    subtitle: "Make something happen and watch the notifications arrive.",
  },
};

export default function DashboardPage() {
  const { user, loading, refresh } = useAuth();
  const router = useRouter();
  const [toast, showToast] = useToast();
  const [section, setSection] = useState("account");
  const [phone, setPhone] = useState("");
  const [editingPhone, setEditingPhone] = useState(false);
  const [events, setEvents] = useState([]);
  const [busy, setBusy] = useState("");

  const loadEvents = useCallback(async () => {
    try {
      setEvents(await api.events());
    } catch {
      setEvents([]);
    }
  }, []);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (user) loadEvents();
  }, [user, loading, router, loadEvents]);

  useEffect(() => {
    if (user?.profile) setPhone(user.profile.phone_e164 || "");
  }, [user]);

  if (loading || !user) {
    return <p style={{ padding: 28, color: "#6b7280" }}>Loading…</p>;
  }

  const nav = [
    { key: "account", label: "Your details", icon: "account" },
    { key: "try", label: "Try it out", icon: "triggers" },
  ];
  if (user.is_staff) {
    nav.push({
      key: "admin",
      label: "Notification settings",
      icon: "settings",
      href: "/admin",
    });
  }

  const pushId = user.profile?.onesignal_player_id;
  const displayName = user.first_name || user.username;

  async function run(key, fn, message) {
    setBusy(key);
    try {
      const result = await fn();
      showToast(message(result), "ok");
      await refresh();
    } catch (err) {
      showToast(explain(err.message), "err");
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <AppShell
        nav={nav}
        active={section}
        onNavigate={setSection}
        title={
          section === "account" ? `Hi ${displayName}` : HEADINGS[section].title
        }
        subtitle={
          section === "account"
            ? user.last_login
              ? `Last signed in ${new Date(user.last_login).toLocaleString()}`
              : HEADINGS.account.subtitle
            : HEADINGS[section].subtitle
        }
      >
        {section === "account" && (
          <div className="card">
            <h2>How we reach you</h2>
            <p className="hint">
              Keep these up to date and you’ll get notified the way you prefer.
            </p>

            <div className="reach-grid">
              <div className="reach-card">
                <div className="reach-head">
                  <span className="channel-card-icon ready-icon">
                    <ChannelIcon channel="whatsapp" size={16} />
                  </span>
                  <div>
                    <div className="reach-name">{CHANNEL_LABELS.whatsapp}</div>
                    <div className="channel-card-note">{CHANNEL_HELP.whatsapp}</div>
                  </div>
                </div>

                {editingPhone ? (
                  <>
                    <input
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="918559050811"
                      aria-label="WhatsApp number"
                    />
                    <p className="muted" style={{ margin: 0, fontSize: 12 }}>
                      Country code first, no “+”.
                    </p>
                    <div className="row">
                      <button
                        className="primary small"
                        disabled={busy === "phone"}
                        onClick={() =>
                          run("phone", () => api.savePhone(phone), () => {
                            setEditingPhone(false);
                            return "WhatsApp number saved.";
                          })
                        }
                      >
                        Save
                      </button>
                      <button className="small" onClick={() => setEditingPhone(false)}>
                        Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="reach-value">{phone || "Not added yet"}</div>
                    <div className="spacer" />
                    <button className="small" onClick={() => setEditingPhone(true)}>
                      {phone ? "Change number" : "Add your number"}
                    </button>
                  </>
                )}
              </div>

              <div className="reach-card">
                <div className="reach-head">
                  <span className="channel-card-icon ready-icon">
                    <ChannelIcon channel="email" size={16} />
                  </span>
                  <div>
                    <div className="reach-name">{CHANNEL_LABELS.email}</div>
                    <div className="channel-card-note">{CHANNEL_HELP.email}</div>
                  </div>
                </div>
                <div className="reach-value">{user.email || "Not added yet"}</div>
                <div className="spacer" />
                <span className="muted" style={{ fontSize: 12 }}>
                  Taken from your account details.
                </span>
              </div>

              <div className="reach-card">
                <div className="reach-head">
                  <span className={`channel-card-icon ${pushId ? "ready-icon" : ""}`}>
                    <ChannelIcon channel="web_push" size={16} />
                  </span>
                  <div>
                    <div className="reach-name">{CHANNEL_LABELS.web_push}</div>
                    <div className="channel-card-note">{CHANNEL_HELP.web_push}</div>
                  </div>
                </div>

                {pushId ? (
                  <>
                    <span className="badge on" style={{ alignSelf: "flex-start" }}>
                      This browser is subscribed
                    </span>
                    <div className="spacer" />
                    <button
                      className="small"
                      disabled={busy === "push"}
                      onClick={() =>
                        run(
                          "push",
                          async () => api.savePushSubscription(await subscribeToPush()),
                          () => "Subscription refreshed."
                        )
                      }
                    >
                      Re-subscribe
                    </button>
                  </>
                ) : (
                  <>
                    <div className="reach-value">Not turned on in this browser</div>
                    <div className="spacer" />
                    <button
                      className="primary small"
                      disabled={busy === "push" || !isConfigured()}
                      onClick={() =>
                        run(
                          "push",
                          async () => api.savePushSubscription(await subscribeToPush()),
                          () => "Browser notifications turned on."
                        )
                      }
                    >
                      Turn on notifications
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {section === "try" && (
          <div className="card">
            <h2>Send yourself a notification</h2>
            <p className="hint">
              These are the things your website can notify about right now. Signing out
              from the sidebar fires the goodbye message.
            </p>
            {events.length === 0 ? (
              <p className="empty-state">Nothing is switched on at the moment.</p>
            ) : (
              <div className="pill-row">
                {events.map((event) => (
                  <button
                    key={event.code}
                    disabled={busy === event.code}
                    onClick={() =>
                      run(
                        event.code,
                        () => api.fireEvent(event.code),
                        (result) =>
                          `${event.name} — ` +
                          result.results
                            .map(
                              (r) =>
                                `${CHANNEL_LABELS[r.channel]}: ${
                                  r.status === "sent" ? "sent" : "not sent"
                                }`
                            )
                            .join(", ")
                      )
                    }
                  >
                    {busy === event.code ? "Sending…" : event.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </AppShell>
      {toast}
    </>
  );
}
