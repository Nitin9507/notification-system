# Notification System — Frontend (Next.js)

Two surfaces against the Django API:

- **`/login`, `/register`, `/dashboard`** — the ordinary website, where triggers
  actually happen. Logging in and out fires `user.login` / `user.logout`; the
  dashboard is also where a user saves their WhatsApp number and subscribes this
  browser to web push.
- **`/admin`** — the matrix from the brief. Rows are triggers, columns are
  WhatsApp / Email / Web Push, each cell has a template with edit, on/off and
  test-send, plus the delivery log underneath.

```
app/
├── login | register | dashboard | admin   pages
components/
├── MatrixTable.js       the trigger × channel grid
├── TemplateEditor.js    one cell, in a modal
├── TopBar.js | Toast.js
lib/
├── api.js               fetch wrapper + JWT handling
├── auth.js              AuthProvider / useAuth
└── onesignal.js         web push subscribe flow
```

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev          # http://localhost:3000
```

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Django backend base URL, no trailing slash |
| `NEXT_PUBLIC_ONESIGNAL_APP_ID` | Web push app id; blank disables the subscribe button |

`public/OneSignalSDKWorker.js` must stay at the site root — the OneSignal SDK
looks for it there.

## Deploying to Vercel

- **Root directory:** `frontend`
- **Framework preset:** Next.js (build and output settings are detected)
- **Environment variables:** the two above, pointing at your Render URL

Then add the Vercel URL to the backend's `CORS_ALLOWED_ORIGINS` and
`FRONTEND_URL`.

## Notes

The JWT is kept in `localStorage`, which is fine for this assignment; a
production build would use an httpOnly cookie so XSS cannot read it. The admin
routes are guarded server-side by DRF's `IsAdminUser` — the frontend redirect
for non-staff users is convenience, not the security boundary.
