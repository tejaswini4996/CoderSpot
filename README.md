# CoderSpot

A calendar of coding programs, fellowships, bootcamps, open source pushes,
and coding contests — with client accounts, an admin panel, a blog, and a
monthly email newsletter.

## First-time setup

1. **Install Python** if you don't have it: https://www.python.org/downloads/
   (On Windows, check "Add Python to PATH" during install.)

2. **Open a terminal** in this project folder.

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Set up your environment file**:
   ```
   cp .env.example .env
   ```
   Then open `.env` and set `SECRET_KEY` to a real random value:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Paste the output in as `SECRET_KEY=...`. (Leave the Gmail fields for
   step 6, once you're ready to send email.)

5. **Create your admin account** (one time):
   ```
   python create_admin.py
   ```
   Follow the prompts for your admin email and password. This is separate
   from client accounts — it's what lets you log into `/admin`.

6. **Run the site**:
   ```
   python app.py
   ```
   Open http://127.0.0.1:5000 — you should see the homepage.

## How the site is organized

- **Public pages**: Home, Calendar, Testimonials, Blog, About
- **Client accounts**: anyone can sign up at `/signup` to get the monthly
  email. They can log in, view their account, and subscribe/unsubscribe
  at `/account`.
- **Admin panel**: log in at `/admin/login` (link in the footer) with the
  account you made in step 5. From `/admin` you can:
  - Manage events (add/delete programs, open source pushes, contests)
  - Write and publish blog posts
  - Review and approve testimonials
  - View applications submitted through the site
  - See all subscribers
  - Send the monthly newsletter (or check/change the automatic send day)

Client accounts and admin accounts are completely separate logins — an
admin does not automatically have a client account, and vice versa.

## Who can do what

- **Visitors**: browse everything public — Home, Calendar, Testimonials, Blog, About
- **Client accounts** (`/signup`): get the monthly email, manage their own subscription at `/account`, and can write and publish their own blog posts
- **Admin**: full access to everything at `/admin` — events, all blog posts (any author), testimonials, applications, subscribers, and the newsletter

There are only two roles — Admin and User. Any signed-up user can write
a blog post from their own account; there's no separate "blogger" login
or upgrade path. A regular user account can never gain admin access —
every admin page and admin action checks for a real admin session, with
no exceptions.

Admin login is **not** advertised anywhere on the public site — no nav
link, no footer link. It's a private URL only you should know:
`/admin/login`. Bookmark it. Once logged in, a link back to your
dashboard appears in the nav and footer for convenience — it only
disappears again after you log out.

### Creating your admin account

**Running locally?** Use the CLI script, same as before:
```
python create_admin.py
```

**Deployed somewhere without shell access (e.g. Vercel)?** Use the
built-in setup page instead:
1. Visit `https://your-site.com/admin/setup`
2. Since no admin account exists yet, this page is open — fill in an
   email and password and submit.
3. From then on, `/admin/setup` automatically returns a plain 404 to
   everyone (indistinguishable from a page that doesn't exist), **unless**
   you set an `ADMIN_SETUP_KEY` environment variable and visit
   `/admin/setup?key=that-value` — useful if you ever need to add a
   second admin account later without shell access.

## Adding events, open source programs & contests

Go to `/admin/events` → **+ Add a new event**. Fill in the name, type
(Program/Bootcamp, Open Source, or Coding Contest), month, timing note,
audience, format, summary, and official link. It appears on the site
immediately — no code editing needed.

`data/events.py` is only used to seed the calendar the very first time
the app runs (so it isn't empty on day one). After that, everything lives
in the database and is managed from `/admin/events`.

### Browsing by focus

The home page has three shortcut cards — **Open Source**, **Hackathons &
Contests**, and **Women in Tech** — that link straight to the calendar
pre-filtered to that focus (e.g. `/calendar?focus=open_source`). The
calendar's own filter bar has matching buttons so visitors can switch
between them without leaving the page.

## Writing blog posts

Any signed-up user can write one:
1. Log in (or sign up) as a regular user
2. Click **"Write a post"** in the nav, or go to `/write`
3. Fill in a title and body (plain paragraphs — a blank line starts a
   new paragraph) and publish

It's live immediately at `/blog/your-post-title`, attributed to your
account name. Manage your own posts (view or delete) from `/account`.

As admin, you can also write posts yourself from `/admin/blogs` (shown
as authored by "CoderSpot Team"), and you can delete **any** post
site-wide from there — not just your own.

## Testimonials

The site launches with **zero** testimonials — no placeholders. Real
visitors submit their story at `/testimonials`, and it stays hidden until
you approve it at `/admin/testimonials`. Approved ones show on the
Testimonials page and a preview appears on the home page.

## The monthly email newsletter

### Setting up Gmail sending

1. Turn on 2-Step Verification on the Gmail account you'll send from:
   https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords
   (a 16-character code — your regular Gmail password will NOT work here)
3. In your `.env` file, set:
   ```
   GMAIL_ADDRESS=youraddress@gmail.com
   GMAIL_APP_PASSWORD=the16charactercode
   ```
4. Restart the app.

### Automatic sending — how it really works

A background scheduler checks once a day, and sends the newsletter
automatically on a configurable day of the month (default: the 1st) to
everyone subscribed. Change the day at `/admin/newsletter`.

**Important:** this only works while `app.py` is actually running. On
your own laptop, that means it won't fire while the app is stopped or
your computer is off or asleep. For true "set and forget" automation,
deploy the app to a host that stays on 24/7 — e.g. Render, Railway, or
PythonAnywhere all have straightforward free/cheap tiers for a small
Flask app like this.

You can also click **Send now** on `/admin/newsletter` at any time,
independent of the schedule — useful for testing or sending something
out-of-cycle.

Every email includes a one-click unsubscribe link in the footer.

## Design

Professional/corporate light theme — navy (`#14213D`) and blue
(`#2F6FED`) accents on white, Inter typeface throughout. Categories are
"Women-focused" and "Open to all" (no other gender-based category).

## Deploying (recommended: Render)

This app is now confirmed working under gunicorn (a real production
server, tested locally) — the code is solid. If Vercel keeps giving you
a generic crash with no visible cause, switch to **Render** instead:
it's built for exactly this kind of app (Flask + SQLite + Jinja
templates), needs zero code changes, and comes with a Procfile and
`render.yaml` already included in this project.

### Deploy to Render

1. Push this project to a GitHub repo
2. Go to https://render.com → **New** → **Web Service** → connect your repo
3. Render will detect `render.yaml` automatically and fill in the build/start commands. If not, set them manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Add environment variables in the Render dashboard: `SECRET_KEY` (required — generate one with `python -c "import secrets; print(secrets.token_hex(32))"`), and optionally `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `ADMIN_SETUP_KEY`
5. Deploy. Visit `https://your-app.onrender.com/admin/setup` to create your admin account.

**Note on the free tier:** Render's free web services spin down after
15 minutes of inactivity and lose local files (including the SQLite
database) on restart, similar to Vercel. For a real launch, either
upgrade to a paid Render plan with a persistent disk, or move to a
hosted database (Postgres, etc.) — same caveat as Vercel below, just a
less aggressive version of it (Render only wipes on spin-down/redeploy,
not on every cold start).

If Render gives you an error, its logs are much easier to read than
Vercel's: dashboard → your service → **Logs** tab shows the real
traceback immediately, no separate command needed.

## Deploying to Vercel (if you want to keep trying)

This project includes `vercel.json` so it can deploy on Vercel's Python
runtime — the entry point is `app.py` directly (no wrapper file needed).

### If you see "This Serverless Function has crashed"

Vercel's public error page never shows the real Python error — you have
to go looking for it. Before changing anything, check the actual cause:
```
vercel logs <your-deployment-url>
```
or in the dashboard: your project → **Deployments** → click the deployment
→ **Functions** tab → click the function → **Logs**. The real traceback
(a `ModuleNotFoundError`, missing environment variable, etc.) will be
there. Fix based on what it actually says rather than guessing.

### Setup steps

- **Set environment variables** in your Vercel project settings:
  `SECRET_KEY` (required), and optionally `GMAIL_ADDRESS` /
  `GMAIL_APP_PASSWORD`, `ADMIN_SETUP_KEY`, and `CRON_SECRET`.
- **Create your admin account** via `/admin/setup` (see above) — you
  can't run `create_admin.py` on Vercel since there's no shell access.
- **Automatic newsletter sending** doesn't work the normal way here — a
  background scheduler thread doesn't survive between requests on
  serverless. Instead, `vercel.json` includes a daily Cron Job that hits
  `/cron/newsletter-check?key=...`. Update that URL in `vercel.json` with
  your real `CRON_SECRET` value before deploying.
- **⚠️ Data persistence**: Vercel's filesystem is read-only except `/tmp`,
  and `/tmp` gets wiped on cold starts (which happen often — after idle
  periods, on every redeploy, sometimes between requests). This means
  events, user accounts, applications, and blog posts stored in SQLite
  **can disappear without warning** on Vercel. This is fine for a demo,
  but not safe for a real launch. For a real launch, either:
  - Deploy instead to a host with a persistent disk — Render, Railway,
    or PythonAnywhere all work with zero code changes and SQLite behaves
    normally, or
  - Keep Vercel, but swap SQLite for a real hosted database (Vercel
    Postgres, Supabase, Neon, etc.) — a bigger change than this project
    currently supports out of the box.

## Security notes before deploying for real

- `create_admin.py` is the only way to create admin accounts — there's no
  public admin signup page, by design.
- Passwords are hashed with Werkzeug's `generate_password_hash` (never
  stored in plain text).
- Unsubscribe links use signed tokens (`itsdangerous`) so they can't be
  guessed or edited to unsubscribe someone else.
- `.env` and `coderspot.db` are both git-ignored — never commit them.
- Set a real `SECRET_KEY` in `.env` before deploying anywhere public (see
  step 4 above). The fallback dev key in `app.py` is NOT safe to use in
  production.
- The built-in Flask dev server (`python app.py`) is fine for local use,
  but for a real deployment use a production server (e.g. gunicorn)
  behind a host like Render or Railway.

## How the site is put together

```
coderspot/
├── app.py                 <- Flask routes, auth, scheduler
├── db.py                  <- Database (events, users, admins, blog, etc.)
├── email_utils.py         <- Gmail sending + unsubscribe tokens
├── create_admin.py        <- Run once (locally) to create your admin login
├── add_new_events.py      <- One-off script to backfill new seed events
├── vercel.json             <- Vercel build/routing/cron config (entry: app.py)
├── .env.example           <- Copy to .env and fill in real values
├── data/
│   └── events.py          <- One-time seed data for the calendar
├── templates/             <- All pages (see file names — fairly self-explanatory)
├── static/
│   ├── css/style.css      <- All visual styling
│   └── js/filter.js       <- Calendar filter buttons
├── coderspot.db             <- SQLite database (created automatically, git-ignored)
└── requirements.txt
```

## Ideas for what to build next

- Deploy to Render/Railway/PythonAnywhere so automatic sending actually
  runs 24/7
- Add password-reset ("forgot password") flows for both client and admin
  accounts
- Let users edit their own testimonial/application via an emailed link
- Add pagination once the blog or applications list gets long
