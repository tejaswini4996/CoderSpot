# app.py
#
# This is the entry point of the website. Flask reads this file, sets up
# routes (URLs), and for each one renders an HTML template.
#
# To run this site locally:
#   1. pip install -r requirements.txt
#   2. Copy .env.example to .env and fill in SECRET_KEY (and Gmail
#      credentials once you're ready to send the newsletter — see
#      email_utils.py for setup steps)
#   3. python create_admin.py   (creates your admin login, one time)
#   4. python app.py
#   5. Open http://127.0.0.1:5000 in your browser
#
# AUTOMATIC MONTHLY EMAIL — how it actually works:
#   A background scheduler checks once a day (see start_scheduler() below)
#   whether today is the configured "send day" and whether this month's
#   email has already gone out. If not, it sends automatically.
#   IMPORTANT: this only works while app.py is actually running. On your
#   own laptop, that means the automatic send won't fire while the app
#   is stopped or your computer is off. For true "set and forget"
#   automation, deploy this app to a host that stays on 24/7 (e.g.
#   Render, Railway, PythonAnywhere) — see README.md.

import os
import io
import csv
from datetime import date, timedelta, datetime
from urllib.parse import quote
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _SCHEDULER_AVAILABLE = True
except ImportError:
    # If APScheduler isn't installed for some reason (e.g. a host that
    # didn't pick up requirements.txt correctly), don't let that take
    # down the entire site — automatic sending just won't run, and
    # /cron/newsletter-check or the manual "Send now" button still work.
    BackgroundScheduler = None
    _SCHEDULER_AVAILABLE = False

import db
import email_utils
import oauth as oauth_module

load_dotenv()

app = Flask(__name__)

# Used to sign login sessions and unsubscribe links. Set a real value in
# .env before deploying anywhere other than your own machine.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")

# Sets up "Continue with Google/GitHub" — only actually registers a
# provider if its credentials are present in the environment (see
# oauth.py for setup steps). Nothing breaks if neither is configured.
oauth_module.init_oauth(app)

# Create the database tables (if they don't exist yet) and seed the
# calendar with starter events as soon as the app starts.
db.init_db()

# Human-readable labels for each event "kind" — this is now the site's
# ONLY category system (every event belongs to exactly one of these
# three), used in dropdowns, filters, and tags.
EVENT_KINDS = {
    "women_in_tech": "Women in Tech",
    "open_source": "Open Source",
    "contest": "Hackathon",
}


def _event_calendar_date(event):
    """
    Events only store a month, not an exact day (the real deadline is in
    the free-text 'window' field, e.g. 'Submissions close Sep 30, 2026').
    For a calendar reminder, we anchor to the 1st of that month, rolling
    over to next year if that month has already passed — so 'Add to
    Calendar' always points at an upcoming occurrence, not a stale one.
    """
    today = date.today()
    year = today.year if event["month_num"] >= today.month else today.year + 1
    return date(year, event["month_num"], 1)


def _ics_escape(text):
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def is_spam(request_form):
    """Honeypot check: a hidden field named 'website' that's invisible to
    real visitors (CSS-hidden) but that simple bots tend to fill in
    automatically. If it's non-empty, silently treat as spam."""
    return bool(request_form.get("website", "").strip())


def days_until_event(event):
    """Days from today until the event's anchor date (1st of its month,
    with the same year-rollover logic as the calendar links). Used for
    the 'X days left' countdown badge."""
    target = _event_calendar_date(event)
    return (target - date.today()).days


def build_calendar_links(event):
    """Returns Google Calendar + .ics download links for one event, for
    the 'Add to Calendar' button. Anchored to the 1st of the event's
    month as a reminder — see _event_calendar_date for why."""
    start = _event_calendar_date(event)
    end = start + timedelta(days=1)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    details = f"{event['window']} — {event['summary']} More info: {event['link']}"

    google_url = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(event['name'])}"
        f"&dates={start_str}/{end_str}"
        f"&details={quote(details)}"
        f"&location={quote(event['link'])}"
    )

    return {
        "google_url": google_url,
        "ics_url": url_for("event_ics", event_id=event["id"]),
    }


def get_current_month_name():
    """Returns the full name of the current month, e.g. 'August'."""
    return date.today().strftime("%B")


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------

def login_required(view):
    """Protects client-account pages like /account."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Protects every /admin/... page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_current_session():
    """Makes the logged-in client/admin available to every template, so
    the nav bar can show 'Log in' vs 'My account' etc. Also exposes which
    events the current user has already applied to, so event cards can
    show 'Applied ✓' instead of 'Apply' without every route needing to
    compute it separately."""
    current_user = db.get_user_by_id(session["user_id"]) if session.get("user_id") else None
    current_admin = db.get_admin_by_id(session["admin_id"]) if session.get("admin_id") else None
    applied_event_ids = db.get_applied_event_ids(current_user["email"]) if current_user else set()
    return dict(current_user=current_user, current_admin=current_admin, applied_event_ids=applied_event_ids)


# ---------------------------------------------------------------------
# Newsletter building — shared by both the manual "Send now" button and
# the automatic scheduled send, so they behave identically.
# ---------------------------------------------------------------------

def send_monthly_newsletter(intro=""):
    """
    Builds and sends this month's newsletter to every subscribed user.
    Returns (sent_count, failed_count, subject) or (0, 0, None) if there
    was nothing to send (no subscribers, or email not configured).
    """
    current_month = get_current_month_name()
    month_events = [e for e in db.get_all_events() if e["month"] == current_month]
    testimonial_picks = db.get_approved_testimonials(limit=2)
    subscribers = db.get_subscribed_users()
    subject = f"CoderSpot — {current_month} roundup"

    if not email_utils.is_email_configured() or not subscribers:
        return 0, 0, None

    def build_html(user):
        token = email_utils.make_unsubscribe_token(app.secret_key, user["id"])
        return render_template(
            "email_newsletter.html",
            user=user,
            intro=intro,
            month=current_month,
            events=month_events,
            testimonials=testimonial_picks,
            unsubscribe_url=url_for("unsubscribe", token=token, _external=True),
        )

    sent, failed = email_utils.send_newsletter(subscribers, subject, build_html)
    db.log_newsletter_send(subject, sent)
    return sent, failed, subject


def check_and_send_automatic_newsletter():
    """
    Called once a day by the scheduler. Sends the monthly newsletter
    automatically if today matches the configured send day AND this
    month's email hasn't already gone out.
    """
    with app.app_context():
        today = date.today()
        send_day = int(db.get_setting("newsletter_send_day", "1"))
        last_sent = db.get_setting("newsletter_last_sent_month")  # e.g. "2026-09"
        this_month_key = today.strftime("%Y-%m")

        if today.day == send_day and last_sent != this_month_key:
            sent, failed, subject = send_monthly_newsletter()
            if subject:
                db.set_setting("newsletter_last_sent_month", this_month_key)


def start_scheduler():
    if not _SCHEDULER_AVAILABLE:
        print("APScheduler not available — automatic sending disabled. "
              "Use /cron/newsletter-check with an external cron, or the "
              "manual 'Send now' button in /admin/newsletter instead.")
        return
    scheduler = BackgroundScheduler(daemon=True)
    # Checks once a day at 8:00am server time — cheap, and plenty
    # precise for a once-a-month email.
    scheduler.add_job(check_and_send_automatic_newsletter, "cron", hour=8, minute=0)
    scheduler.start()


# ---------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------

@app.route("/")
def home():
    """Home page: hero section + a short preview of this month's events."""
    current_month = get_current_month_name()
    all_events = db.get_all_events()
    featured = [e for e in all_events if e["month"] == current_month]

    if not featured:
        current_index = db.MONTH_ORDER.index(current_month)

        def months_away(event):
            return (event["month_num"] - 1 - current_index) % 12

        featured = sorted(all_events, key=months_away)[:3]

    testimonial_preview = db.get_approved_testimonials(limit=3)
    calendar_links = {e["id"]: build_calendar_links(e) for e in featured}

    return render_template(
        "index.html",
        current_month=current_month,
        featured=featured,
        total_programs=len(all_events),
        testimonials=testimonial_preview,
        calendar_links=calendar_links,
    )


@app.route("/calendar")
def calendar():
    """Full-year calendar page, events grouped by month. Accepts an
    optional ?focus= query param (all / women / open_source / contest)
    so links from the home page can land pre-filtered."""
    events_by_month = db.get_events_by_month()
    allowed_filters = {"all", "women_in_tech", "open_source", "contest"}
    initial_filter = request.args.get("focus", "all")
    if initial_filter not in allowed_filters:
        initial_filter = "all"

    all_events = db.get_all_events()
    calendar_links = {e["id"]: build_calendar_links(e) for e in all_events}

    return render_template(
        "calendar.html",
        events_by_month=events_by_month,
        month_order=db.MONTH_ORDER,
        current_month=get_current_month_name(),
        initial_filter=initial_filter,
        calendar_links=calendar_links,
    )


@app.route("/calendar/event/<int:event_id>.ics")
def event_ics(event_id):
    """Downloads a single .ics file for one event — works with Apple
    Calendar, Outlook, and any calendar app that isn't Google's (which
    uses the direct web link instead, built in build_calendar_links)."""
    event = db.get_event_by_id(event_id)
    if event is None:
        return "Event not found.", 404

    start = _event_calendar_date(event)
    end = start + timedelta(days=1)
    details = f"{event['window']} — {event['summary']} More info: {event['link']}"

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CoderSpot//Event Calendar//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:coderspot-event-{event['id']}@coderspot",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
        f"SUMMARY:{_ics_escape(event['name'])}",
        f"DESCRIPTION:{_ics_escape(details)}",
        f"URL:{event['link']}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    ics_content = "\r\n".join(ics_lines) + "\r\n"

    safe_name = "".join(c if c.isalnum() else "-" for c in event["name"]).strip("-").lower()
    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.ics"'},
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not message:
            flash("Please write your suggestion before submitting.", "error")
            return render_template("feedback.html", name=name, email=email, message=message)

        db.save_feedback(name, email, message)
        flash("Thanks for the suggestion! We read every one.", "success")
        return redirect(url_for("feedback"))

    current_user = db.get_user_by_id(session["user_id"]) if session.get("user_id") else None
    prefill_name = current_user["name"] if current_user else ""
    prefill_email = current_user["email"] if current_user else ""
    return render_template("feedback.html", name=prefill_name, email=prefill_email, message="")


@app.route("/admin/feedback")
@admin_required
def admin_feedback():
    all_feedback = db.get_all_feedback()
    return render_template("admin_feedback.html", feedback_list=all_feedback)


@app.route("/admin/feedback/delete/<int:feedback_id>", methods=["POST"])
@admin_required
def delete_feedback(feedback_id):
    db.delete_feedback(feedback_id)
    flash("Feedback deleted.", "success")
    return redirect(url_for("admin_feedback"))


@app.route("/program/<int:event_id>")
def program_detail(event_id):
    """A dedicated page for one program — what you land on when clicking
    its name from the home page or calendar, instead of just seeing it
    inline in a card."""
    event = db.get_event_by_id(event_id)
    if event is None:
        return "Program not found.", 404

    calendar_links = build_calendar_links(event)
    return render_template(
        "program_detail.html",
        event=event,
        calendar_links=calendar_links,
        kind_label=EVENT_KINDS.get(event["kind"], "Open Source"),
    )


@app.route("/apply/<int:event_id>", methods=["GET", "POST"])
def apply(event_id):
    """Application form for a single event. Pre-fills name/email if the
    visitor is logged in, but doesn't require an account."""
    event = db.get_event_by_id(event_id)
    if event is None:
        return "Program not found.", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        note = request.form.get("note", "").strip()

        if not name or not email:
            flash("Please fill in both your name and email.", "error")
            return render_template("apply.html", event=event, name=name, email=email, note=note)

        db.save_application(
            applicant_name=name,
            applicant_email=email,
            event_id=event["id"],
            event_name=event["name"],
            note=note,
        )
        flash(f"Application received for {event['name']}!", "success")
        return redirect(url_for("apply", event_id=event_id))

    current_user = db.get_user_by_id(session["user_id"]) if session.get("user_id") else None
    prefill_name = current_user["name"] if current_user else ""
    prefill_email = current_user["email"] if current_user else ""
    return render_template("apply.html", event=event, name=prefill_name, email=prefill_email, note="")


@app.route("/apply/<int:event_id>/quick", methods=["POST"])
@login_required
def quick_apply(event_id):
    """
    True one-click 'Easy Apply', like LinkedIn: for a logged-in user, this
    submits their saved name/email immediately with a single click — no
    form, no retyping, no extra page visit. Logged-out visitors still go
    through the regular /apply form since we don't have their info yet.
    """
    event = db.get_event_by_id(event_id)
    if event is None:
        return "Program not found.", 404

    user = db.get_user_by_id(session["user_id"])

    if event["id"] in db.get_applied_event_ids(user["email"]):
        flash(f"You've already applied to {event['name']}.", "error")
    else:
        db.save_application(
            applicant_name=user["name"],
            applicant_email=user["email"],
            event_id=event["id"],
            event_name=event["name"],
            note="",
        )
        flash(f"Applied to {event['name']} — done in one click!", "success")

    # Send them back wherever they clicked Apply from (calendar, home,
    # or the program's own page), instead of always redirecting to /.
    next_url = request.form.get("next") or url_for("home")
    return redirect(next_url)


@app.route("/testimonials", methods=["GET", "POST"])
def testimonials():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        program_name = request.form.get("program_name", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not message:
            flash("Please fill in your name and your story.", "error")
            return redirect(url_for("testimonials"))

        db.save_testimonial(name, program_name, message)
        flash("Thanks for sharing! Your testimonial will appear after a quick review.", "success")
        return redirect(url_for("testimonials"))

    approved = db.get_approved_testimonials()
    return render_template("testimonials.html", testimonials=approved)


@app.route("/blog")
def blog():
    posts = db.get_all_blog_posts()
    return render_template("blog.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = db.get_blog_post_by_slug(slug)
    if post is None:
        return "Post not found.", 404
    return render_template("blog_post.html", post=post)


# ---------------------------------------------------------------------
# Client accounts
# ---------------------------------------------------------------------

def _oauth_flags():
    """Passed to signup/login templates so the 'Continue with...' buttons
    only render when that provider is actually configured."""
    return {
        "google_configured": oauth_module.is_google_configured(),
        "github_configured": oauth_module.is_github_configured(),
    }


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("account"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not name or not email or not password:
            flash("Please fill in every field.", "error")
            return render_template("signup.html", name=name, email=email, **_oauth_flags())
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("signup.html", name=name, email=email, **_oauth_flags())
        if password != confirm:
            flash("Those passwords didn't match.", "error")
            return render_template("signup.html", name=name, email=email, **_oauth_flags())

        user_id = db.create_user(name, email, password)
        if user_id is None:
            flash("An account with that email already exists — try logging in.", "error")
            return render_template("signup.html", name=name, email=email, **_oauth_flags())

        session["user_id"] = user_id
        flash("Welcome! You're subscribed to the monthly roundup.", "success")
        return redirect(url_for("home"))

    return render_template("signup.html", name="", email="", **_oauth_flags())


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("account"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = db.verify_user_password(email, password)

        if not user:
            flash("Incorrect email or password.", "error")
            return render_template("login.html", email=email, **_oauth_flags())

        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(request.args.get("next") or url_for("home"))

    return render_template("login.html", email="", **_oauth_flags())


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You've been logged out.", "success")
    return redirect(url_for("home"))


def _find_or_create_oauth_user(email, name, provider, provider_id):
    """Shared by both Google and GitHub callbacks: link to an existing
    account with this email, or create a brand new one."""
    user = db.get_user_by_email(email)
    if user is None:
        user_id = db.create_oauth_user(name, email, provider, provider_id)
        user = db.get_user_by_id(user_id)
    else:
        db.link_oauth_to_user(user["id"], provider, provider_id)
    return user


@app.route("/login/google")
def login_google():
    if not oauth_module.is_google_configured():
        flash("Google login isn't set up on this site yet.", "error")
        return redirect(url_for("login"))
    redirect_uri = url_for("google_callback", _external=True)
    return oauth_module.oauth.google.authorize_redirect(redirect_uri)


@app.route("/login/google/callback")
def google_callback():
    if not oauth_module.is_google_configured():
        return redirect(url_for("login"))

    token = oauth_module.oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        flash("Google didn't return an email address — please try again.", "error")
        return redirect(url_for("login"))

    email = userinfo["email"]
    name = userinfo.get("name") or email.split("@")[0]
    user = _find_or_create_oauth_user(email, name, "google", userinfo.get("sub"))

    session["user_id"] = user["id"]
    flash(f"Welcome, {user['name']}!", "success")
    return redirect(url_for("home"))


@app.route("/login/github")
def login_github():
    if not oauth_module.is_github_configured():
        flash("GitHub login isn't set up on this site yet.", "error")
        return redirect(url_for("login"))
    redirect_uri = url_for("github_callback", _external=True)
    return oauth_module.oauth.github.authorize_redirect(redirect_uri)


@app.route("/login/github/callback")
def github_callback():
    if not oauth_module.is_github_configured():
        return redirect(url_for("login"))

    oauth_module.oauth.github.authorize_access_token()
    profile = oauth_module.oauth.github.get("user").json()

    email = profile.get("email")
    if not email:
        # GitHub only returns a public email if the user opted in — fall
        # back to their verified email list, which requires the
        # 'user:email' scope we already request.
        emails = oauth_module.oauth.github.get("user/emails").json()
        primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
        email = primary or next((e["email"] for e in emails if e.get("verified")), None)

    if not email:
        flash("We couldn't get a verified email from your GitHub account. Add one at github.com/settings/emails and try again.", "error")
        return redirect(url_for("login"))

    name = profile.get("name") or profile.get("login")
    user = _find_or_create_oauth_user(email, name, "github", str(profile.get("id")))

    session["user_id"] = user["id"]
    flash(f"Welcome, {user['name']}!", "success")
    return redirect(url_for("home"))


@app.route("/account")
@login_required
def account():
    user = db.get_user_by_id(session["user_id"])
    posts = db.get_blog_posts_by_author(user["id"])
    return render_template("account.html", user=user, posts=posts)


@app.route("/account/toggle-subscription", methods=["POST"])
@login_required
def toggle_subscription():
    user = db.get_user_by_id(session["user_id"])
    was_subscribed = bool(user["subscribed"])
    db.set_user_subscribed(user["id"], not was_subscribed)
    flash("Unsubscribed from the monthly email." if was_subscribed else "Subscribed to the monthly email.", "success")
    return redirect(url_for("account"))


@app.route("/unsubscribe/<token>")
def unsubscribe(token):
    """One-click unsubscribe link used in the footer of every newsletter
    email — works without needing to log in."""
    user_id = email_utils.read_unsubscribe_token(app.secret_key, token)
    if user_id is None:
        return "This unsubscribe link is invalid or has expired.", 400
    db.set_user_subscribed(user_id, False)
    return render_template("unsubscribed.html")


# ---------------------------------------------------------------------
# Admin login
# ---------------------------------------------------------------------

@app.route("/admin/setup", methods=["GET", "POST"])
def admin_setup():
    """
    Creates an admin account through the website itself — for hosts like
    Vercel where you can't run `python create_admin.py` from a shell.

    Access rules (this is what keeps it invisible/unusable to your
    regular users):
      - If NO admin account exists yet, this page is open — it's how you
        bootstrap your very first admin login on a fresh deploy.
      - Once at least one admin exists, this page requires a secret key
        (?key=... matching the ADMIN_SETUP_KEY environment variable) or
        it returns a plain 404, identical to a page that doesn't exist.
        Nobody without that secret can find or use it, and it's never
        linked from anywhere on the public site.

    Set ADMIN_SETUP_KEY in your environment to a long random value, then
    visit /admin/setup?key=that-value whenever you need to add another
    admin account later.
    """
    setup_key = os.environ.get("ADMIN_SETUP_KEY")
    provided_key = request.args.get("key") or request.form.get("key", "")
    admin_already_exists = db.any_admin_exists()

    if admin_already_exists and (not setup_key or provided_key != setup_key):
        return "Not found.", 404

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not email or not password:
            flash("Please fill in both fields.", "error")
            return render_template("admin_setup.html", key=provided_key)
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("admin_setup.html", key=provided_key)
        if password != confirm:
            flash("Those passwords didn't match.", "error")
            return render_template("admin_setup.html", key=provided_key)

        admin_id = db.create_admin(email, password)
        if admin_id is None:
            flash("An admin account with that email already exists.", "error")
            return render_template("admin_setup.html", key=provided_key)

        flash("Admin account created — you can log in now.", "success")
        return redirect(url_for("admin_login"))

    return render_template("admin_setup.html", key=provided_key)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        admin = db.verify_admin_password(email, password)

        if not admin:
            flash("Incorrect email or password.", "error")
            return render_template("admin_login.html", email=email)

        session["admin_id"] = admin["id"]
        flash("Welcome back.", "success")
        return redirect(request.args.get("next") or url_for("admin_dashboard"))

    return render_template("admin_login.html", email="")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    pending_testimonials = [t for t in db.get_all_testimonials() if not t["approved"]]
    stats = {
        "events": len(db.get_all_events()),
        "applications": len(db.get_all_applications()),
        "pending_testimonials": len(pending_testimonials),
        "subscribers": len(db.get_subscribed_users()),
        "blog_posts": len(db.get_all_blog_posts()),
        "feedback": len(db.get_all_feedback()),
    }
    return render_template("admin_dashboard.html", stats=stats)


# ---------------------------------------------------------------------
# Admin: events
# ---------------------------------------------------------------------

@app.route("/admin/events")
@admin_required
def admin_events():
    all_events = db.get_all_events()
    return render_template("admin_events.html", events=all_events, kinds=EVENT_KINDS)


@app.route("/admin/events/new", methods=["GET", "POST"])
@admin_required
def new_event():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        kind = request.form.get("kind", "open_source")
        month = request.form.get("month", "")
        window = request.form.get("window", "").strip()
        event_format = request.form.get("format", "Remote")
        summary = request.form.get("summary", "").strip()
        link = request.form.get("link", "").strip()

        if not name or not month or not summary or not link:
            flash("Please fill in the name, month, summary, and link.", "error")
            return render_template(
                "new_event.html", kinds=EVENT_KINDS, months=db.MONTH_ORDER, form=request.form,
            )

        # "category" no longer exists as a separate concept — every event
        # belongs to exactly one of the three kinds now — so we just pass
        # a fixed placeholder value to satisfy the database column.
        db.add_event(name, kind, month, window, "all", event_format, summary, link)
        flash(f'"{name}" was added to the calendar.', "success")
        return redirect(url_for("admin_events"))

    return render_template("new_event.html", kinds=EVENT_KINDS, months=db.MONTH_ORDER, form={})


@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    db.delete_event(event_id)
    flash("Event deleted.", "success")
    return redirect(url_for("admin_events"))


# ---------------------------------------------------------------------
# Admin: testimonials
# ---------------------------------------------------------------------

@app.route("/admin/testimonials")
@admin_required
def admin_testimonials():
    all_testimonials = db.get_all_testimonials()
    return render_template("admin_testimonials.html", testimonials=all_testimonials)


@app.route("/admin/testimonials/approve/<int:testimonial_id>", methods=["POST"])
@admin_required
def approve_testimonial(testimonial_id):
    db.approve_testimonial(testimonial_id)
    flash("Testimonial approved — it's now live on the site.", "success")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/delete/<int:testimonial_id>", methods=["POST"])
@admin_required
def delete_testimonial(testimonial_id):
    db.delete_testimonial(testimonial_id)
    flash("Testimonial deleted.", "success")
    return redirect(url_for("admin_testimonials"))


# ---------------------------------------------------------------------
# Admin: applications
# ---------------------------------------------------------------------

@app.route("/admin/applications")
@admin_required
def admin_applications():
    all_applications = db.get_all_applications()
    return render_template("applications.html", applications=all_applications)


# ---------------------------------------------------------------------
# Admin: blog (sees every post; can delete any post)
# ---------------------------------------------------------------------

@app.route("/admin/blogs")
@admin_required
def admin_blogs():
    posts = db.get_all_blog_posts()
    return render_template("admin_blogs.html", posts=posts, is_admin_view=True)


@app.route("/admin/blogs/new", methods=["GET", "POST"])
@admin_required
def new_blog():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

        if not title or not body:
            flash("Please fill in both the title and the post content.", "error")
            return render_template(
                "new_blog.html", form=request.form,
                action_url=url_for("new_blog"), back_url=url_for("admin_blogs"),
            )

        db.create_blog_post(title, body, author_id=None, author_name="CoderSpot Team")
        flash(f'"{title}" was published.', "success")
        return redirect(url_for("admin_blogs"))

    return render_template(
        "new_blog.html", form={},
        action_url=url_for("new_blog"), back_url=url_for("admin_blogs"),
    )


@app.route("/admin/blogs/delete/<int:post_id>", methods=["POST"])
@admin_required
def delete_blog(post_id):
    db.delete_blog_post(post_id)
    flash("Post deleted.", "success")
    return redirect(url_for("admin_blogs"))


# ---------------------------------------------------------------------
# User blog posts — any signed-in user (client account) can write and
# manage their own posts from /write and /account. There is no separate
# "blogger" role: just Admin (full access) and User (their own posts).
# ---------------------------------------------------------------------

@app.route("/write", methods=["GET", "POST"])
@login_required
def write_post():
    user = db.get_user_by_id(session["user_id"])

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

        if not title or not body:
            flash("Please fill in both the title and the post content.", "error")
            return render_template(
                "new_blog.html", form=request.form,
                action_url=url_for("write_post"), back_url=url_for("account"),
            )

        db.create_blog_post(title, body, author_id=user["id"], author_name=user["name"])
        flash(f'"{title}" was published.', "success")
        return redirect(url_for("account"))

    return render_template(
        "new_blog.html", form={},
        action_url=url_for("write_post"), back_url=url_for("account"),
    )


@app.route("/posts/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_own_post(post_id):
    post = db.get_blog_post_by_id(post_id)
    if post is None:
        return "Post not found.", 404
    if post["author_id"] != session["user_id"]:
        return "You can only delete your own posts.", 403

    db.delete_blog_post(post_id)
    flash("Post deleted.", "success")
    return redirect(url_for("account"))


# ---------------------------------------------------------------------
# Admin: subscribers + newsletter
# ---------------------------------------------------------------------

@app.route("/admin/subscribers")
@admin_required
def admin_subscribers():
    users = db.get_all_users()
    return render_template("admin_subscribers.html", users=users)


@app.route("/admin/newsletter", methods=["GET", "POST"])
@admin_required
def admin_newsletter():
    current_month = get_current_month_name()
    month_events = [e for e in db.get_all_events() if e["month"] == current_month]
    testimonial_picks = db.get_approved_testimonials(limit=2)
    subscribers = db.get_subscribed_users()
    default_subject = f"CoderSpot — {current_month} roundup"
    send_day = int(db.get_setting("newsletter_send_day", "1"))
    last_sent_month = db.get_setting("newsletter_last_sent_month")

    if request.method == "POST":
        if request.form.get("form_name") == "update_send_day":
            new_day = request.form.get("send_day", "1")
            if new_day.isdigit() and 1 <= int(new_day) <= 28:
                db.set_setting("newsletter_send_day", new_day)
                flash(f"Automatic send day updated to day {new_day} of each month.", "success")
            else:
                flash("Send day must be a number between 1 and 28.", "error")
            return redirect(url_for("admin_newsletter"))

        intro = request.form.get("intro", "").strip()

        if not email_utils.is_email_configured():
            flash(
                "Email isn't set up yet — add GMAIL_ADDRESS and GMAIL_APP_PASSWORD "
                "to your .env file first (see .env.example).",
                "error",
            )
            return redirect(url_for("admin_newsletter"))

        if not subscribers:
            flash("There are no subscribers to send to yet.", "error")
            return redirect(url_for("admin_newsletter"))

        sent, failed, subject = send_monthly_newsletter(intro=intro)
        db.set_setting("newsletter_last_sent_month", date.today().strftime("%Y-%m"))

        if failed:
            flash(f"Sent to {sent} subscriber(s) — {failed} failed. Check your Gmail settings.", "error")
        else:
            flash(f"Newsletter sent to {sent} subscriber(s).", "success")
        return redirect(url_for("admin_newsletter"))

    return render_template(
        "admin_newsletter.html",
        current_month=current_month,
        month_events=month_events,
        testimonials=testimonial_picks,
        subscriber_count=len(subscribers),
        default_subject=default_subject,
        email_configured=email_utils.is_email_configured(),
        sends=db.get_newsletter_sends(),
        send_day=send_day,
        last_sent_month=last_sent_month,
    )


@app.route("/cron/newsletter-check")
def cron_newsletter_check():
    """
    For serverless hosts (Vercel, etc.) where a background scheduler
    thread can't run continuously: point an external cron service at this
    URL once a day instead. Vercel Cron Jobs (see vercel.json) call this
    automatically if you deploy there.

    Protected by a shared secret (CRON_SECRET env var) passed as
    ?key=... so random visitors can't trigger it or use it to probe
    whether email is configured.
    """
    expected = os.environ.get("CRON_SECRET")
    if not expected or request.args.get("key") != expected:
        return "Not found.", 404

    check_and_send_automatic_newsletter()
    return {"ok": True}


# Start the background scheduler so automatic monthly sends check in
# daily while the app process is running. Guarded so Flask's debug
# auto-reloader (which spawns a parent watcher process, then a child
# process that actually serves requests) doesn't start two schedulers.
#
# On serverless hosts (Vercel sets the VERCEL env var) a background
# thread doesn't reliably survive between requests, so skip it there —
# use the /cron/newsletter-check endpoint with an external cron instead
# (see vercel.json and the README).
if os.environ.get("VERCEL"):
    pass  # rely on Vercel Cron hitting /cron/newsletter-check instead
elif __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_scheduler()
else:
    # Being run under a real WSGI server (e.g. gunicorn) on a host with a
    # persistent process — no reloader involved, so just start it directly.
    start_scheduler()

if __name__ == "__main__":
    app.run(debug=True)
