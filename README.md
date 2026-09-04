# Notification System

One admin screen that controls WhatsApp, email and web push notifications for
the whole site. Templates are written and toggled here — nobody logs into Meta,
Brevo or OneSignal to change a message.

```
Trigger (row)  ×  Channel (column)  =  Template (cell)  →  Adapter  →  Provider
```

| | Tech | Deployed on | Details |
|---|---|---|---|
| Backend | Python · Django · DRF · PostgreSQL | Render | [backend/README.md](backend/README.md) |
| Frontend | Next.js (App Router) | Vercel | [frontend/README.md](frontend/README.md) |

**Repository:** https://github.com/Nitin9507/notification-system
**Live frontend:** https://notification-system-khaki.vercel.app
**Live backend:** https://notification-system-api-lt95.onrender.com
**Walkthrough video:** _paste your unlisted link_

## Triggers built

| Code | Name | How it fires |
|---|---|---|
| `user.login` | Login | Django `user_logged_in` signal |
| `user.logout` | Logout | Django `user_logged_out` signal |
| `user.inactive_1d` | Not logged in 1 day | Hourly scan of `last_login` |
| `user.inactive_1w` | Not logged in 1 week | Hourly scan of `last_login` |

All four are seeded with templates on all three channels. New rows can be added
from the admin panel without touching code.

## Logging in as admin

Open https://notification-system-khaki.vercel.app/login and sign in:

| Username | Password |
|---|---|
| `admin` | `REPLACE_WITH_ADMIN_PASSWORD` |

Staff users land on **/admin**, the notification matrix. Anyone else lands on the
ordinary site at **/dashboard**, where triggers actually fire. Django's own admin
is at https://notification-system-api-lt95.onrender.com/django-admin/.

The account is created during the Render build from the `DJANGO_SUPERUSER_*`
environment variables, because the free plan has no shell to run
`createsuperuser` by hand.

> The backend sleeps after 15 minutes idle on Render's free tier, so the first
> request may take up to a minute.

## Run both locally

```bash
# backend  → http://localhost:8000
# PostgreSQL is required; create the database once:
sudo -u postgres psql -c "CREATE USER notif_user WITH PASSWORD 'notif_pass';"
sudo -u postgres psql -c "CREATE DATABASE notification_system OWNER notif_user;"
sudo -u postgres psql -c "ALTER USER notif_user CREATEDB;"

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate && python manage.py seed_notifications
python manage.py createsuperuser
python manage.py runserver

# frontend → http://localhost:3000
cd ../frontend
npm install
cp .env.example .env.local     # point NEXT_PUBLIC_API_URL at the backend
npm run dev
```

With no provider keys in `.env` the system runs in **dry-run**: messages are
rendered and logged but not transmitted. Add keys to send for real.

## Environment variables

Backend — see [`backend/.env.example`](backend/.env.example) for the annotated list:

| Variable | Purpose |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django basics |
| `DATABASE_URL` | PostgreSQL connection URL — required, no SQLite fallback |
| `CORS_ALLOWED_ORIGINS` | Your Vercel URL |
| `INTERNAL_CRON_SECRET` | Guards the scheduled-trigger endpoint |
| `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` | Meta Cloud API sandbox |
| `EMAIL_PROVIDER`, `BREVO_API_KEY` (or `POSTMARK_TOKEN`), `DEFAULT_FROM_EMAIL` | Transactional email |
| `ONESIGNAL_APP_ID`, `ONESIGNAL_REST_API_KEY`, `ONESIGNAL_TARGET_FIELD` | Web push |

Frontend: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ONESIGNAL_APP_ID`.

**Email provider:** this project uses **Brevo**, not Postmark. The brief permits
either; Brevo's free tier is 300 emails/day against Postmark's ~100/month, which
matters when re-testing templates. `EMAIL_PROVIDER=postmark` switches back.

## How it works

1. Something happens — a user logs in.
2. Django's auth signal calls `notify("user.login", user)`.
3. The dispatcher loads that trigger's templates, drops any whose row switch or
   cell toggle is off, and resolves each channel's recipient.
4. Each surviving template is rendered against the trigger context and handed to
   its `ChannelAdapter`.
5. Every attempt — sent, failed, skipped, or dry-run — is written to
   `NotificationLog` and shown in the admin panel.

The dispatcher never imports a provider. A fourth channel is one new adapter
class and one new enum value.

Condition triggers ("not logged in for a week") have no event to hook, so they
are a periodic scan driven by a GitHub Actions cron calling
`/api/internal/run-scheduled-triggers/` — Render's own cron jobs are paid. The
scan dedupes against the log, so a user away three days is messaged once, not
three times.

## Task D — the four questions

**What is a trigger? Give 3 examples.**
A trigger is anything on the website that should cause a notification to go out
— an event or a condition. Three examples that are not login: *order placed*
(the user completes a purchase), *password reset* (the user asks to reset it),
and *not logged in for 7 days* (a condition found by a periodic scan, not an
event). One trigger is one row in the admin table.

**What are the three channels?**
WhatsApp (a message on the user's phone, via the WhatsApp Cloud API), Email (an
email in their inbox, via Brevo), and Web Push (a pop-up in their browser, via
OneSignal). Each channel is a column, and a trigger can use one, two, or all
three — each with its own template.

**Why create templates in the admin panel instead of on Postmark / WhatsApp?**
Because otherwise the message text lives in three different vendor dashboards
with three different logins, and nobody can see what a trigger actually sends
without visiting all of them. Keeping templates here means one screen shows every
message, non-technical staff can edit text without vendor accounts, changing
email providers doesn't touch the copy, and every send is logged in one audit
trail. The vendors become interchangeable delivery pipes.

**What is Web Push?**
A notification the browser shows even when the site isn't open, delivered by a
service worker the user opted into. It works on desktop and Android browsers,
needs HTTPS, and requires explicit permission. It is browser-only here — no
mobile app push, per the brief.

## Production notes

- **Sending is synchronous.** `notify()` calls the providers inside the request that
  triggered it, so a login waits on up to three HTTP calls (15s timeout each). That
  keeps the system dependency-free and easy to demo, but a real deployment should hand
  dispatch to a queue (Celery or RQ) so provider latency never touches user-facing
  requests. The adapter boundary means only `dispatcher.notify()` would change.
- **JWTs live in `localStorage`** so any XSS could read them; production would use
  httpOnly cookies. The client refreshes an expired access token transparently.
- **Webhook signatures** are verified against `WHATSAPP_APP_SECRET` when it is set. It
  must be set in production — without it, anyone could forge an inbound message and
  open a user's 24-hour WhatsApp window.
- **Rate limits** default to 30 requests/min anonymous and 240/min authenticated,
  tunable with `THROTTLE_ANON` / `THROTTLE_USER`.
- With `DEBUG=False` the app enables HSTS, HTTPS redirect (behind Render's proxy),
  secure cookies, `nosniff` and `X-Frame-Options: DENY`, and refuses to start without
  a `SECRET_KEY`.

## Known constraints

- **WhatsApp 24-hour rule.** Meta only accepts free-form text within 24h of the
  user messaging your number; outside that, an approved template is required. A
  WhatsApp cell stores both. The adapter sends your own wording first and retries
  with the approved template only if Meta rejects it, so the window never has to
  be tracked locally.
- **Sandbox recipients.** The Meta test number only delivers to whitelisted
  numbers, and its access token expires roughly daily.
- **Render free tier.** The service sleeps after 15 minutes idle; the first
  request takes ~50s. Hit `/healthz/` to warm it before recording.
