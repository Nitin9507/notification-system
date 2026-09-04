import "./globals.css";

import { AuthProvider } from "@/lib/auth";

export const metadata = {
  title: "Notification System",
  description: "Admin-managed WhatsApp, email and web push notifications",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
