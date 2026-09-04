"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import ChannelIcon from "@/components/ChannelIcon";
import MatrixTable from "@/components/MatrixTable";
import TemplateEditor from "@/components/TemplateEditor";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CHANNEL_HELP, CHANNEL_LABELS, STATUS, explain, timeAgo } from "@/lib/friendly";

const NEW_TRIGGER = { code: "", name: "", kind: "event", inactivity_days: "" };

const ADMIN_NAV = [
  { key: "triggers", label: "Triggers", icon: "triggers" },
  { key: "activity", label: "Activity", icon: "activity" },
  { key: "channels", label: "Channels", icon: "channels" },
  { key: "site", label: "View the website", icon: "site", href: "/dashboard" },
];

const MISSING_DETAILS = {
  whatsapp: "Add your WhatsApp number on the website, then try again.",
  email: "Your account has no email address yet.",
  web_push: "Turn on browser notifications on the website, then try again.",
};

const PROVIDERS = {
  whatsapp: "WhatsApp Cloud API (Meta sandbox)",
  email: "Brevo",
  web_push: "OneSignal",
};

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [toast, showToast] = useToast();

  const [section, setSection] = useState("triggers");
  const [matrix, setMatrix] = useState(null);
  const [logs, setLogs] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busyCell, setBusyCell] = useState("");
  const [newTrigger, setNewTrigger] = useState(NEW_TRIGGER);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [matrixData, logData] = await Promise.all([api.matrix(), api.logs(30)]);
      setMatrix(matrixData);
      setLogs(logData);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) return router.replace("/login");
    if (!user.is_staff) return router.replace("/dashboard");
    load();
  }, [user, loading, router, load]);

  if (loading || !user?.is_staff) {
    return <p style={{ padding: 28, color: "#6b7280" }}>Loading…</p>;
  }

  const activeTriggers = matrix?.triggers.filter((t) => t.is_active).length ?? 0;
  const liveMessages =
    matrix?.triggers.reduce(
      (total, t) =>
        total +
        Object.values(t.templates).filter((c) => c && c.is_enabled && t.is_active).length,
      0
    ) ?? 0;

  async function withCell(trigger, channel, fn) {
    setBusyCell(`${trigger.id}:${channel}`);
    try {
      return await fn();
    } catch (err) {
      showToast(explain(err.message), "err");
      return null;
    } finally {
      setBusyCell("");
    }
  }

  async function handleToggleCell(trigger, channel, isEnabled) {
    await withCell(trigger, channel, async () => {
      await api.toggleTemplate(trigger.id, channel, isEnabled);
      showToast(
        `${CHANNEL_LABELS[channel]} is now ${isEnabled ? "on" : "off"} for “${trigger.name}”.`
      );
      await load();
    });
  }

  async function handleTestSend(trigger, channel) {
    await withCell(trigger, channel, async () => {
      const log = await api.testSend(trigger.id, channel, "");
      const status = STATUS[log.status] || { label: log.status, tone: "muted" };

      if (log.status === "skipped" && !log.recipient) {
        showToast(
          `${CHANNEL_LABELS[channel]} test — nowhere to send it.\n` +
            `A test goes to you, and ${MISSING_DETAILS[channel]}`,
          "err"
        );
      } else {
        const where = log.recipient ? ` to ${log.recipient}` : "";
        const detail = log.error ? `\n${explain(log.error)}` : "";
        showToast(
          `${CHANNEL_LABELS[channel]} test — ${status.label}${where}.${detail}`,
          log.status === "failed" ? "err" : "ok"
        );
      }
      await load();
    });
  }

  async function handleToggleTrigger(trigger, isActive) {
    try {
      await api.toggleTrigger(trigger.id, isActive);
      showToast(`“${trigger.name}” is now ${isActive ? "sending" : "paused"}.`);
      await load();
    } catch (err) {
      showToast(explain(err.message), "err");
    }
  }

  async function handleCreateTrigger(event) {
    event.preventDefault();
    try {
      await api.createTrigger({
        code: newTrigger.code,
        name: newTrigger.name,
        kind: newTrigger.kind,
        inactivity_days:
          newTrigger.kind === "scheduled" && newTrigger.inactivity_days
            ? Number(newTrigger.inactivity_days)
            : null,
      });
      setNewTrigger(NEW_TRIGGER);
      setShowAddForm(false);
      showToast("New trigger added. Write a message for each channel next.");
      await load();
    } catch (err) {
      showToast(explain(err.message), "err");
    }
  }

  const HEADINGS = {
    triggers: {
      title: "Triggers",
      subtitle: matrix
        ? `${activeTriggers} of ${matrix.triggers.length} sending · ${liveMessages} messages switched on`
        : "Loading…",
    },
    activity: {
      title: "Activity",
      subtitle: "Every message we tried to send, newest first.",
    },
    channels: {
      title: "Channels",
      subtitle: "The services that deliver your messages.",
    },
  };

  const actions =
    section === "triggers" ? (
      <button className="primary" onClick={() => setShowAddForm((v) => !v)}>
        {showAddForm ? "Cancel" : "Add a trigger"}
      </button>
    ) : (
      <button onClick={load}>Refresh</button>
    );

  return (
    <>
      <AppShell
        nav={ADMIN_NAV}
        active={section}
        onNavigate={setSection}
        title={HEADINGS[section].title}
        subtitle={HEADINGS[section].subtitle}
        actions={actions}
      >
        {error && <p className="error">{error}</p>}

        {section === "triggers" && (
          <>
            {showAddForm && (
              <div className="card">
                <h2>Add something new to notify about</h2>
                <p className="hint">For example an order being placed.</p>
                <form className="row" onSubmit={handleCreateTrigger}>
                  <div style={{ flex: 1, minWidth: 170 }}>
                    <label htmlFor="name">What happens?</label>
                    <input
                      id="name"
                      value={newTrigger.name}
                      onChange={(e) =>
                        setNewTrigger({ ...newTrigger, name: e.target.value })
                      }
                      placeholder="Order placed"
                      required
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 170 }}>
                    <label htmlFor="code">Reference name</label>
                    <input
                      id="code"
                      className="mono"
                      value={newTrigger.code}
                      onChange={(e) =>
                        setNewTrigger({ ...newTrigger, code: e.target.value })
                      }
                      placeholder="order.placed"
                      required
                    />
                  </div>
                  <div style={{ width: 200 }}>
                    <label htmlFor="kind">When should it fire?</label>
                    <select
                      id="kind"
                      value={newTrigger.kind}
                      onChange={(e) =>
                        setNewTrigger({ ...newTrigger, kind: e.target.value })
                      }
                    >
                      <option value="event">As soon as it happens</option>
                      <option value="scheduled">After a period of inactivity</option>
                    </select>
                  </div>
                  {newTrigger.kind === "scheduled" && (
                    <div style={{ width: 120 }}>
                      <label htmlFor="days">Days away</label>
                      <input
                        id="days"
                        type="number"
                        min="1"
                        value={newTrigger.inactivity_days}
                        onChange={(e) =>
                          setNewTrigger({
                            ...newTrigger,
                            inactivity_days: e.target.value,
                          })
                        }
                        required
                      />
                    </div>
                  )}
                  <button
                    className="primary"
                    type="submit"
                    style={{ alignSelf: "flex-end" }}
                  >
                    Add
                  </button>
                </form>
              </div>
            )}

            <div className="card">
              <div className="help-note">
                Each row is something that happens on your website; each column is a way
                to reach the person. Flip a switch to turn a message on or off, or use
                <strong> Send me a test</strong> to see it yourself first.
              </div>
              {matrix ? (
                <MatrixTable
                  channels={matrix.channels}
                  triggers={matrix.triggers}
                  busyCell={busyCell}
                  onEdit={(trigger, channel, template) =>
                    setEditing({ trigger, channel, template })
                  }
                  onToggleCell={handleToggleCell}
                  onTestSend={handleTestSend}
                  onToggleTrigger={handleToggleTrigger}
                />
              ) : (
                <p className="muted">Loading your settings…</p>
              )}
            </div>
          </>
        )}

        {section === "activity" && (
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>What happened</th>
                    <th>Sent by</th>
                    <th>To</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 && (
                    <tr>
                      <td colSpan={5} className="empty-state">
                        Nothing sent yet. Try <strong>Send me a test</strong> on the
                        Triggers page.
                      </td>
                    </tr>
                  )}
                  {logs.map((log) => {
                    const status = STATUS[log.status] || {
                      label: log.status,
                      tone: "muted",
                    };
                    const trigger = matrix?.triggers.find(
                      (t) => t.code === log.trigger_code
                    );
                    return (
                      <tr key={log.id}>
                        <td className="muted">{timeAgo(log.created_at)}</td>
                        <td>
                          {trigger ? trigger.name : log.trigger_code}
                          {log.is_test && <span className="muted"> (test)</span>}
                        </td>
                        <td>{CHANNEL_LABELS[log.channel] || log.channel}</td>
                        <td className="mono">{log.recipient || "—"}</td>
                        <td>
                          <span className={`status-dot ${status.tone}`} />
                          {status.label}
                          {log.error && (
                            <div className="muted" style={{ fontSize: 12.5 }}>
                              {explain(log.error)}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {section === "channels" && (
          <div className="card">
            <p className="hint">
              Messages are written here and delivered by these services. Nobody needs to
              log in to them.
            </p>
            {(matrix?.channels || []).map((channel) => (
              <div
                key={channel.value}
                className={`channel-card ${channel.configured ? "ready" : "pending"}`}
                style={{ marginBottom: 10 }}
              >
                <span className="channel-card-icon">
                  <ChannelIcon channel={channel.value} size={18} />
                </span>
                <div>
                  <div className="channel-card-name">
                    {CHANNEL_LABELS[channel.value] || channel.label}
                  </div>
                  <div className="channel-card-note">
                    {channel.configured ? "Connected" : "Not connected yet"} ·{" "}
                    {PROVIDERS[channel.value]}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {CHANNEL_HELP[channel.value]}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </AppShell>

      {editing && (
        <TemplateEditor
          trigger={editing.trigger}
          channel={editing.channel}
          template={editing.template}
          onClose={() => setEditing(null)}
          onSave={async (payload) => {
            await api.saveTemplate(editing.trigger.id, editing.channel, payload);
            setEditing(null);
            showToast("Message saved.");
            await load();
          }}
        />
      )}
      {toast}
    </>
  );
}
