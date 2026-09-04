"use client";

import ChannelIcon from "@/components/ChannelIcon";
import Switch from "@/components/Switch";
import { CHANNEL_HELP, CHANNEL_LABELS, humanize } from "@/lib/friendly";

function MessagePreview({ template }) {
  const body = humanize(template.body);
  const subject = humanize(template.subject);
  const parts = body.split(/(\[[^\]]+\])/g);

  return (
    <p className="msg-preview">
      {subject && <span className="msg-subject">{subject}</span>}
      {parts.map((part, index) =>
        part.startsWith("[") && part.endsWith("]") ? (
          <span className="chip" key={index}>
            {part.slice(1, -1)}
          </span>
        ) : (
          part
        )
      )}
    </p>
  );
}

export default function MatrixTable({
  channels,
  triggers,
  busyCell,
  onEdit,
  onToggleCell,
  onTestSend,
  onToggleTrigger,
}) {
  return (
    <div className="table-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th style={{ minWidth: 230 }}>When this happens</th>
            {channels.map((channel) => (
              <th key={channel.value}>
                <span className="col-head">
                  <ChannelIcon channel={channel.value} />
                  {CHANNEL_LABELS[channel.value] || channel.label}
                </span>
                <div className="col-head-note">{CHANNEL_HELP[channel.value]}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {triggers.map((trigger) => (
            <tr key={trigger.id}>
              <td>
                <div className="trigger-name">{trigger.name}</div>
                <p className="trigger-desc">
                  {trigger.description ||
                    (trigger.kind === "scheduled"
                      ? `Checked automatically every ${trigger.inactivity_days} day(s).`
                      : "Happens on the website.")}
                </p>
                <div className="toggle-row">
                  <Switch
                    checked={trigger.is_active}
                    onChange={(next) => onToggleTrigger(trigger, next)}
                    label={`Turn ${trigger.name} on or off`}
                  />
                  <span className={`toggle-label ${trigger.is_active ? "on" : "off"}`}>
                    {trigger.is_active ? "Sending" : "Paused"}
                  </span>
                </div>
              </td>

              {channels.map((channel) => {
                const template = trigger.templates[channel.value];
                const busy = busyCell === `${trigger.id}:${channel.value}`;

                return (
                  <td
                    key={channel.value}
                    className={`cell ${template && !template.is_enabled ? "off" : ""}`}
                  >
                    {template ? (
                      <div className="cell-inner">
                        <div className="toggle-row" style={{ marginBottom: 10 }}>
                          <Switch
                            checked={template.is_enabled}
                            disabled={busy}
                            onChange={(next) => onToggleCell(trigger, channel.value, next)}
                            label={`Turn ${channel.value} on or off for ${trigger.name}`}
                          />
                          <span
                            className={`toggle-label ${template.is_enabled ? "on" : "off"}`}
                          >
                            {template.is_enabled ? "On" : "Off"}
                          </span>
                          {template.is_enabled && !trigger.is_active && (
                            <span className="muted" style={{ fontSize: 11.5 }}>
                              paused above
                            </span>
                          )}
                        </div>

                        <MessagePreview template={template} />

                        <div>
                          <button
                            className="link-btn"
                            onClick={() => onEdit(trigger, channel.value, template)}
                          >
                            Edit
                          </button>
                          <button
                            className="link-btn"
                            disabled={busy}
                            onClick={() => onTestSend(trigger, channel.value)}
                          >
                            {busy ? "Sending…" : "Send me a test"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="cell-inner">
                        <p className="cell-empty">Nothing is sent here yet.</p>
                        <button
                          className="small primary"
                          onClick={() => onEdit(trigger, channel.value, null)}
                        >
                          Write a message
                        </button>
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
