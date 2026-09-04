# Notification System — Backend (Django + DRF)

Admin-managed notifications across three channels. Every message lives in this
app's own admin panel; nobody logs into Meta, Brevo or OneSignal to change text.

```
Trigger (row)  ×  Channel (column)  =  Template (cell)  →  Adapter  →  Provider
```

## Architecture

```
notifications/
├── models.py                    Trigger, NotificationTemplate, NotificationLog
├── dispatcher.py                notify() — resolves templates, toggles, recipients
├── renderer.py                  variable mapping + {{ placeholder }} substitution
├── channels/
│   ├── base.py                  ChannelAdapter / Message / SendResult
│   ├── whatsapp.py              WhatsApp Cloud API
│   ├── email.py                 Brevo or Postmark
│   └── webpush.py               OneSignal (browser only)
├── triggers.py                  auth signal receivers → notify()
├── services/scheduled.py        "not logged in for N days" scans
└── views.py                     admin API, event firing, cron endpoint, webhook
```

The dispatcher never imports a provider. Adding SMS means one new
`ChannelAdapter` subclass plus one value in `Channel` — nothing else changes.

**Toggle precedence:** `Trigger.is_active` (whole row) → `Template.is_enabled`
(one cell) → recipient present. A blocked send is still written to
`NotificationLog` with `status=skipped` and a reason, so "why didn't I get it?"
is always answerable.

**Dry-run by default.** With no provider credentials the adapters render and log
the message but never call the vendor (`status=dry_run`). The whole system runs
on a laptop with an empty `.env`.

## Run locally

PostgreSQL is required — there is no SQLite fallback, so local dev and the test
suite run the same engine as Render. Create the database once:

```bash
sudo -u postgres psql -c "CREATE USER notif_user WITH PASSWORD 'notif_pass';"
sudo -u postgres psql -c "CREATE DATABASE notification_system OWNER notif_user;"
sudo -u postgres psql -c "ALTER USER notif_user CREATEDB;"   # for the test database
```

Then:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # DATABASE_URL is prefilled for the above
python manage.py migrate
python manage.py seed_notifications  # 4 triggers × 3 channels
python manage.py createsuperuser
python manage.py runserver
```

`python manage.py test` runs 29 tests (Django creates and drops a
`test_notification_system` database, which is why `notif_user` needs `CREATEDB`) — renderer, dispatcher toggles/dedupe,
scheduled scans, and the admin API — none of which touch the network.

## API

Admin routes require a staff JWT (`is_staff=True`).

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Sign up (optional `phone_e164`) |
| POST | `/api/auth/login/` | JWT pair — **fires `user.login`** |
| POST | `/api/auth/logout/` | **Fires `user.logout`** |
| POST | `/api/auth/refresh/` | Refresh the access token |
| GET·PATCH | `/api/auth/me/` | Profile, incl. phone number |
| POST | `/api/auth/push-subscription/` | Store the browser's OneSignal id |
| GET | `/api/admin/matrix/` | The whole admin table in one payload |
| GET·POST | `/api/admin/triggers/` | List / create rows |
| GET·PUT·PATCH·DELETE | `/api/admin/triggers/<id>/` | One row |
| PATCH | `/api/admin/triggers/<id>/toggle/` | Row master switch |
| GET·PUT·PATCH·DELETE | `/api/admin/triggers/<id>/templates/<channel>/` | One cell (PUT upserts) |
| PATCH | `/api/admin/triggers/<id>/templates/<channel>/toggle/` | Cell on/off |
| POST | `/api/admin/triggers/<id>/templates/<channel>/test-send/` | Test send, bypasses toggles |
| GET | `/api/admin/logs/` | Delivery audit trail |
| POST | `/api/events/<code>/fire/` | Fire any event trigger for the signed-in user |
| POST | `/api/internal/run-scheduled-triggers/` | Inactivity scan (header `X-Cron-Secret`) |
| GET·POST | `/api/webhooks/whatsapp/` | Meta verification + inbound messages |

`channel` is one of `whatsapp`, `email`, `web_push`.

## Templates and variables

A cell stores `body` (plus `subject` for email/web push) and a `variables` map
from placeholder to a dotted path in the trigger context:

```json
{
  "subject": "You logged in successfully",
  "body": "Hi {{ first_name|default:'there' }}, you signed in at {{ now }}.",
  "variables": { "first_name": "user.first_name" }
}
```

Rendering uses Django's template engine, so filters work. An unknown
placeholder renders empty rather than raising — admins are not developers.

## The WhatsApp 24-hour rule

Meta only accepts free-form text within 24 hours of the user's last inbound
message. Outside that window a pre-approved template is required. So a WhatsApp
cell stores **both**: `body`, and `wa_template_name` + `wa_body_params`.

The adapter **sends the free-form text first and lets Meta decide**. If Meta
replies with a re-engagement error (131047 / 131051 / 470) it retries once with
the approved template. The window is never tracked locally.

That is deliberate. Meta delivers real inbound webhooks only to a *published*
app, so a sandbox app can never learn when a user's window opened — and guessing
was wrong in both directions: sending a template when free text would have
worked, or free text when the window had quietly closed. Letting the provider be
the authority removes the guess.

The inbound webhook is still implemented and verified (`/api/webhooks/whatsapp/`,
signature-checked against `WHATSAPP_APP_SECRET`); it simply is not load-bearing.

## Scheduled triggers

`user.inactive_1d` / `user.inactive_1w` have no event to hook, so they are a
periodic scan: `run_scheduled_triggers` finds users whose `last_login` is older
than the trigger's `inactivity_days` and notifies each once per window
(deduped against `NotificationLog`, so a user away three days is not messaged
three times).

Render's cron jobs are a paid feature, so the schedule lives in
`.github/workflows/scheduled-triggers.yml`, which POSTs to
`/api/internal/run-scheduled-triggers/` hourly and can be fired by hand from the
Actions tab. Locally: `python manage.py run_scheduled_triggers --dry-run`.

## Deploying to Render

`render.yaml` (at the repo root) provisions the web service and a free Postgres instance. Or by hand:

- **Root directory:** `backend`
- **Build:** `./build.sh` (installs, collectstatic, migrate, seed)
- **Start:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- **Env vars:** everything in `.env.example`, plus `DATABASE_URL`,
  `DEBUG=False`, `CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app`

Free instances sleep after 15 minutes; the first request takes ~50s. Hit
`/healthz/` to warm it before recording anything.

## Providers

| Channel | Service | Free tier | Notes |
|---|---|---|---|
| WhatsApp | Meta Cloud API sandbox | test number only | Token expires ~daily; recipients must be whitelisted |
| Email | Brevo (default) | 300/day | `EMAIL_PROVIDER=postmark` switches vendors |
| Web Push | OneSignal | free | Browser only; `ONESIGNAL_TARGET_FIELD` covers old and new app models |
