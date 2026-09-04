"use client";

const PATHS = {
  whatsapp:
    "M12 2a10 10 0 0 0-8.6 15.1L2 22l5.1-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.5.1-.6.8-.8.9-.3.2-.5 0a6.7 6.7 0 0 1-2-1.2 7.4 7.4 0 0 1-1.4-1.7c-.1-.2 0-.4.1-.5l.4-.4.2-.4v-.4c0-.1-.5-1.4-.7-1.9s-.4-.4-.5-.4h-.5a1 1 0 0 0-.7.3 2.9 2.9 0 0 0-.9 2.2 5 5 0 0 0 1.1 2.7 11.5 11.5 0 0 0 4.4 3.9c1.6.6 2.2.7 3 .6a2.6 2.6 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .1-1.2c0-.1-.2-.2-.4-.3Z",
  email: "M3 5h18v14H3V5Zm2 2v.4l7 4.4 7-4.4V7H5Zm14 10V9.7l-7 4.4-7-4.4V17h14Z",
  web_push:
    "M12 2a6 6 0 0 0-6 6v3.6l-1.7 3A1 1 0 0 0 5.2 16h13.6a1 1 0 0 0 .9-1.5l-1.7-3V8a6 6 0 0 0-6-6Zm0 2a4 4 0 0 1 4 4v4.1l1 1.9H7l1-1.9V8a4 4 0 0 1 4-4Zm-2 14h4a2 2 0 0 1-4 0Z",
};

export default function ChannelIcon({ channel, size = 16 }) {
  const path = PATHS[channel];
  if (!path) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      style={{ flex: "none" }}
    >
      <path d={path} />
    </svg>
  );
}
