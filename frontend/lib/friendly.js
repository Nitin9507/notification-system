export const VARIABLES = [
  {
    key: "first_name",
    token: "{{ first_name|default:'there' }}",
    label: "First name",
    sample: "Nitin",
    hint: "Falls back to “there” if we don’t know their name",
  },
  {
    key: "username",
    token: "{{ username }}",
    label: "Username",
    sample: "nitin",
    hint: "The name they log in with",
  },
  {
    key: "email",
    token: "{{ email }}",
    label: "Email address",
    sample: "nitin@example.com",
    hint: "The address on their account",
  },
  {
    key: "site_name",
    token: "{{ site_name }}",
    label: "Site name",
    sample: "Notification System",
    hint: "The name of your website",
  },
];

function lookup(expression) {
  const key = String(expression).trim().split("|")[0].trim();
  return VARIABLES.find((variable) => variable.key === key);
}

/** Rewrite {{ template syntax }} as readable [Labels] for previews. */
export function humanize(text) {
  if (!text) return "";
  return text.replace(/\{\{([^}]+)\}\}/g, (match, expression) => {
    const variable = lookup(expression);
    return `[${variable ? variable.label : expression.trim().split("|")[0].trim()}]`;
  });
}

/** Fill placeholders with example values, so an admin sees a realistic message. */
export function preview(text) {
  if (!text) return "";
  return text.replace(/\{\{([^}]+)\}\}/g, (match, expression) => {
    const variable = lookup(expression);
    return variable ? variable.sample : "";
  });
}

export const CHANNEL_LABELS = {
  whatsapp: "WhatsApp",
  email: "Email",
  web_push: "Browser notification",
};

export const CHANNEL_HELP = {
  whatsapp: "A WhatsApp message on their phone",
  email: "An email in their inbox",
  web_push: "A pop-up in their web browser",
};

export const STATUS = {
  sent: { label: "Delivered", tone: "ok" },
  dry_run: { label: "Simulated", tone: "warn" },
  skipped: { label: "Not sent", tone: "muted" },
  failed: { label: "Failed", tone: "err" },
};

const FRIENDLY_ERRORS = [
  ["channel toggle is off", "This channel is switched off for this trigger"],
  ["trigger is switched off", "The whole trigger is switched off"],
  ["no recipient on file", "We don’t have their details for this channel"],
  ["credentials not configured", "No account connected for this channel yet"],
  ["not in allowed list", "This number isn’t on the WhatsApp test list"],
  ["session closed", "Outside WhatsApp’s 24-hour reply window"],
  ["token expired", "The WhatsApp access token has expired"],
];

/** Turn provider jargon into something an admin can act on. */
export function explain(error) {
  if (!error) return "";
  const match = FRIENDLY_ERRORS.find(([needle]) =>
    error.toLowerCase().includes(needle)
  );
  return match ? match[1] : error;
}

export function timeAgo(iso) {
  const then = new Date(iso);
  const seconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} hr ago`;
  return then.toLocaleDateString();
}
