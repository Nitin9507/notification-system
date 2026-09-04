"use client";

import { useEffect, useRef, useState } from "react";

import { CHANNEL_HELP, CHANNEL_LABELS, VARIABLES, preview } from "@/lib/friendly";

const EMPTY = {
  subject: "",
  body: "",
  wa_template_name: "",
  wa_language_code: "en_US",
  wa_body_params: [],
  variables: {},
  is_enabled: true,
};

export default function TemplateEditor({ trigger, channel, template, onClose, onSave }) {
  const dialogRef = useRef(null);
  const bodyRef = useRef(null);
  const [form, setForm] = useState(EMPTY);
  const [variablesText, setVariablesText] = useState("{}");
  const [paramsText, setParamsText] = useState("[]");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const values = { ...EMPTY, ...(template || {}) };
    setForm(values);
    setVariablesText(JSON.stringify(values.variables ?? {}, null, 2));
    setParamsText(JSON.stringify(values.wa_body_params ?? [], null, 2));
    setError("");
    dialogRef.current?.showModal();
  }, [template, trigger, channel]);

  const update = (field) => (event) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }));

  function insertVariable(token) {
    const field = bodyRef.current;
    if (!field) return;
    const start = field.selectionStart ?? form.body.length;
    const end = field.selectionEnd ?? form.body.length;
    const next = form.body.slice(0, start) + token + form.body.slice(end);
    setForm((prev) => ({ ...prev, body: next }));
    requestAnimationFrame(() => {
      field.focus();
      field.setSelectionRange(start + token.length, start + token.length);
    });
  }

  async function handleSave(event) {
    event.preventDefault();
    let variables;
    let waParams;
    try {
      variables = JSON.parse(variablesText || "{}");
    } catch {
      return setError("The advanced variable list isn’t valid JSON.");
    }
    try {
      waParams = JSON.parse(paramsText || "[]");
    } catch {
      return setError("The advanced WhatsApp values aren’t valid JSON.");
    }

    setBusy(true);
    setError("");
    try {
      await onSave({
        subject: form.subject,
        body: form.body,
        wa_template_name: form.wa_template_name,
        wa_language_code: form.wa_language_code || "en_US",
        wa_body_params: waParams,
        variables,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const isWhatsApp = channel === "whatsapp";
  const subjectLabel = channel === "email" ? "Subject line" : "Notification title";
  const channelName = CHANNEL_LABELS[channel] || channel;

  return (
    <dialog ref={dialogRef} onClose={onClose}>
      <form className="body stack" onSubmit={handleSave}>
        <div>
          <h3 style={{ marginBottom: 4 }}>
            {channelName} message for “{trigger.name}”
          </h3>
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            {CHANNEL_HELP[channel]}, sent whenever this happens.
          </p>
        </div>

        {!isWhatsApp && (
          <div>
            <label htmlFor="subject">{subjectLabel}</label>
            <input
              id="subject"
              value={form.subject}
              onChange={update("subject")}
              placeholder={
                channel === "email" ? "You logged in successfully" : "Welcome back!"
              }
            />
          </div>
        )}

        <div>
          <label htmlFor="body">Message</label>
          <textarea
            id="body"
            ref={bodyRef}
            value={form.body}
            onChange={update("body")}
            placeholder="Write what the person should read…"
          />
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 12.5 }}>
            Click to add personal details. They’re filled in for each person when the
            message is sent.
          </p>
          <div className="var-buttons">
            {VARIABLES.map((variable) => (
              <button
                type="button"
                key={variable.key}
                title={variable.hint}
                onClick={() => insertVariable(variable.token)}
              >
                + {variable.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label>Preview</label>
          <div className="preview-box">
            {form.body || form.subject ? (
              <>
                {!isWhatsApp && form.subject && (
                  <span className="msg-subject">{preview(form.subject)}</span>
                )}
                {preview(form.body)}
              </>
            ) : (
              <span className="preview-empty">Your message will appear here.</span>
            )}
          </div>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 12.5 }}>
            Shown with example details for a person called Nitin.
          </p>
        </div>

        <details className="advanced">
          <summary>Advanced settings</summary>
          <div className="stack">
            {isWhatsApp && (
              <>
                <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>
                  WhatsApp only allows your own wording within 24 hours of the person
                  messaging you. Outside that window it sends this pre-approved
                  template instead.
                </p>
                <div className="row">
                  <div style={{ flex: 2, minWidth: 200 }}>
                    <label htmlFor="wa_template_name">Approved template name</label>
                    <input
                      id="wa_template_name"
                      value={form.wa_template_name}
                      onChange={update("wa_template_name")}
                      placeholder="hello_world"
                      className="mono"
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 110 }}>
                    <label htmlFor="wa_language_code">Language</label>
                    <input
                      id="wa_language_code"
                      value={form.wa_language_code}
                      onChange={update("wa_language_code")}
                      className="mono"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="wa_body_params">Values for that template</label>
                  <textarea
                    id="wa_body_params"
                    value={paramsText}
                    onChange={(e) => setParamsText(e.target.value)}
                    style={{ minHeight: 56 }}
                  />
                </div>
              </>
            )}
            <div>
              <label htmlFor="variables">Extra details available in this message</label>
              <textarea
                id="variables"
                value={variablesText}
                onChange={(e) => setVariablesText(e.target.value)}
                style={{ minHeight: 64 }}
              />
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 12.5 }}>
                For developers. The buttons above cover everything most messages need.
              </p>
            </div>
          </div>
        </details>

        {error && <p className="error">{error}</p>}

        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button type="button" onClick={() => dialogRef.current?.close()}>
            Cancel
          </button>
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save message"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
