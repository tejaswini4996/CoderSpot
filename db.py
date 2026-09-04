# db.py
#
# A tiny wrapper around Python's built-in `sqlite3` module — this is what
# stores every application someone submits through the site. SQLite stores
# everything in a single file (coderspot.db) that's created automatically
# the first time the app runs. No separate database server needed.
#
# IMPORTANT — if you're deploying to Vercel (or any serverless host):
# Vercel's filesystem is read-only everywhere except /tmp, and /tmp is
# wiped every time your app "cold starts" (which happens often — after
# periods of no traffic, on every deploy, sometimes between requests).
# That means SQLite will work well enough to stop the 500 error below,
# but your data (events, users, applications, blog posts) will
# periodically vanish without warning. SQLite on Vercel is fine for a
# quick demo, but NOT safe for a real launch.
#
# For anything real, do one of these instead:
#   1. Deploy to a host with a persistent disk — Render, Railway, or
#      PythonAnywhere all work great for a small Flask app like this and
#      SQLite will behave normally (no code changes needed).
#   2. Keep deploying to Vercel, but switch to a real hosted database
#      (Vercel Postgres, Supabase, Neon, etc. all have free tiers) instead
#      of SQLite. That's a bigger change than this file — ask if you want
#      help with that migration.

import os
import sqlite3
import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from data.events import EVENTS as SEED_EVENTS

# On Vercel, only /tmp is writable. DB_PATH can also be overridden
# directly via an environment variable if you need a custom location.
if os.environ.get("DB_PATH"):
    DB_PATH = os.environ["DB_PATH"]
elif os.environ.get("VERCEL"):
    DB_PATH = "/tmp/coderspot.db"
else:
    DB_PATH = "coderspot.db"

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_TO_NUM = {name: i + 1 for i, name in enumerate(MONTH_ORDER)}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Creates the applications and testimonials tables if they don't
    already exist. Safe to call every time the app starts."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT NOT NULL,
            applicant_email TEXT NOT NULL,
            event_id INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            note TEXT,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            program_name TEXT,
            message TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'program',
            month TEXT NOT NULL,
            month_num INTEGER NOT NULL,
            window TEXT,
            category TEXT NOT NULL DEFAULT 'all',
            format TEXT NOT NULL DEFAULT 'Remote',
            summary TEXT,
            link TEXT,
            added_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            subscribed INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            recipient_count INTEGER NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,
            author_id INTEGER,
            author_name TEXT NOT NULL DEFAULT 'CoderSpot Team',
            published_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, event_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blog_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_id INTEGER,
            author_name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migrations for columns added after initial release
    existing_user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "email_verified" not in existing_user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")

    existing_event_cols = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
    if "views" not in existing_event_cols:
        conn.execute("ALTER TABLE events ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
    conn.commit()

    # Lightweight migration: if blog_posts already existed from an older
    # version of this app (before authorship was added), add the new
    # columns instead of silently failing later.
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(blog_posts)")}
    if "author_id" not in existing_columns:
        conn.execute("ALTER TABLE blog_posts ADD COLUMN author_id INTEGER")
    if "author_name" not in existing_columns:
        conn.execute("ALTER TABLE blog_posts ADD COLUMN author_name TEXT NOT NULL DEFAULT 'CoderSpot Team'")
    conn.commit()

    # Same idea for users — add Google/GitHub OAuth columns if this
    # database was created before OAuth login existed.
    existing_user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "oauth_provider" not in existing_user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN oauth_provider TEXT")
    if "oauth_id" not in existing_user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN oauth_id TEXT")
    conn.commit()

    # Seed the events table from data/events.py the very first time the app
    # runs, so the calendar isn't empty. After this, new events are added
    # through the admin panel (or by editing rows in the database) — the
    # Python file is only used for this initial seed.
    existing_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if existing_events == 0:
        conn.executemany(
            """
            INSERT INTO events
                (name, kind, month, month_num, window, category, format, summary, link, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e["name"], e.get("kind", "program"), e["month"], e["month_num"], e["window"],
                    e["category"], e["format"], e["summary"], e["link"],
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                )
                for e in SEED_EVENTS
            ],
        )
        conn.commit()

    # NOTE: testimonials are never pre-seeded — the section starts empty
    # and only shows real stories submitted by visitors and approved by
    # an admin at /admin/testimonials.

    conn.close()


def save_application(applicant_name, applicant_email, event_id, event_name, note):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO applications
            (applicant_name, applicant_email, event_id, event_name, note, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            applicant_name,
            applicant_email.lower().strip(),
            event_id,
            event_name,
            note,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    conn.close()


def get_all_applications():
    """Returns every submitted application, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def get_applied_event_ids(email):
    """Returns the set of event ids a given email has already applied to
    — used to show 'Applied ✓' instead of 'Apply' and to block duplicate
    one-click applications."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT event_id FROM applications WHERE applicant_email = ?",
        (email.lower().strip(),),
    ).fetchall()
    conn.close()
    return {row["event_id"] for row in rows}


def save_testimonial(name, program_name, message):
    """Saves a new testimonial as UNAPPROVED (approved=0) — it won't show
    on the public site until you approve it from /admin/testimonials."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO testimonials (name, program_name, message, approved, submitted_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (name, program_name, message, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def get_approved_testimonials(limit=None):
    """Returns approved testimonials, most recent first. Pass a `limit`
    to get just the first few (handy for a home page preview)."""
    conn = get_connection()
    query = "SELECT * FROM testimonials WHERE approved = 1 ORDER BY id DESC"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def get_all_testimonials():
    """Returns every testimonial (approved or not), most recent first —
    used on the admin review page."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM testimonials ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def approve_testimonial(testimonial_id):
    conn = get_connection()
    conn.execute(
        "UPDATE testimonials SET approved = 1 WHERE id = ?", (testimonial_id,)
    )
    conn.commit()
    conn.close()


def delete_testimonial(testimonial_id):
    conn = get_connection()
    conn.execute("DELETE FROM testimonials WHERE id = ?", (testimonial_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Events — programs, open source pushes, and coding contests all live in
# the same table, distinguished by the "kind" column.
# ---------------------------------------------------------------------

def add_event(name, kind, month, window, category, event_format, summary, link):
    """Adds a new event. `kind` is one of 'program', 'open_source', 'contest'."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO events (name, kind, month, month_num, window, category, format, summary, link, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name, kind, month, MONTH_TO_NUM[month], window, category,
            event_format, summary, link, datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    conn.close()


def get_all_events():
    """Returns every event, ordered by month then insertion order."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY month_num ASC, id ASC"
    ).fetchall()
    conn.close()
    return rows


def get_event_by_id(event_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    conn.close()
    return row


def get_events_by_month():
    """Returns a dict of {month_name: [events...]} in calendar order."""
    events = get_all_events()
    grouped = {month: [] for month in MONTH_ORDER}
    for event in events:
        grouped[event["month"]].append(event)
    return grouped


def delete_event(event_id):
    conn = get_connection()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Client accounts — people who sign up to receive the monthly email.
# ---------------------------------------------------------------------

def create_user(name, email, password):
    """Creates a new client account. Returns the new user's id, or None
    if that email is already registered."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, subscribed, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                name, email.lower().strip(), generate_password_hash(password),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def create_oauth_user(name, email, provider, provider_id):
    """
    Creates a new client account for someone who signed in with Google or
    GitHub — no password was ever typed, so we store an unusable random
    placeholder hash just to satisfy the password_hash column. They can
    only ever log back in via that same OAuth provider (or reset a
    password later, if that feature gets added).
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, subscribed, created_at, oauth_provider, oauth_id)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                name, email.lower().strip(),
                generate_password_hash(secrets.token_hex(32)),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                provider, provider_id,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def link_oauth_to_user(user_id, provider, provider_id):
    """Attaches a Google/GitHub identity to an existing account — used
    when someone who already signed up with a password later uses
    'Continue with Google/GitHub' with the same email."""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET oauth_provider = ?, oauth_id = ? WHERE id = ?",
        (provider, provider_id, user_id),
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def verify_user_password(email, password):
    """Returns the user row if the email/password combo is correct, else None."""
    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_subscribed_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM users WHERE subscribed = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def set_user_subscribed(user_id, subscribed):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET subscribed = ? WHERE id = ?", (1 if subscribed else 0, user_id)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Admin accounts — the site owner (and anyone they add) who can manage
# events, testimonials, applications, and send the newsletter.
# ---------------------------------------------------------------------

def create_admin(email, password):
    """Creates a new admin account. Returns the new admin's id, or None
    if that email is already registered as an admin."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO admins (email, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (
                email.lower().strip(), generate_password_hash(password),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_admin_by_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM admins WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return row


def get_admin_by_id(admin_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM admins WHERE id = ?", (admin_id,)).fetchone()
    conn.close()
    return row


def verify_admin_password(email, password):
    admin = get_admin_by_email(email)
    if admin and check_password_hash(admin["password_hash"], password):
        return admin
    return None


def any_admin_exists():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    conn.close()
    return count > 0


# ---------------------------------------------------------------------
# Newsletter send log — just a record of when a monthly email went out
# and to how many people, shown on the admin newsletter page.
# ---------------------------------------------------------------------

def log_newsletter_send(subject, recipient_count):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO newsletter_sends (subject, recipient_count, sent_at)
        VALUES (?, ?, ?)
        """,
        (subject, recipient_count, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def get_newsletter_sends():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM newsletter_sends ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------
# Blog posts — any signed-in user can write one from their account.
# author_id references users.id (NULL for posts written by an admin,
# which are attributed to "CoderSpot Team" instead).
# ---------------------------------------------------------------------

def slugify(title):
    slug = "".join(c.lower() if c.isalnum() else "-" for c in title)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "post"


def create_blog_post(title, body, author_id=None, author_name="CoderSpot Team"):
    conn = get_connection()
    base_slug = slugify(title)
    slug = base_slug
    suffix = 2
    # Make sure the slug is unique by appending -2, -3, etc. if needed.
    while conn.execute("SELECT 1 FROM blog_posts WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    conn.execute(
        """
        INSERT INTO blog_posts (title, slug, body, author_id, author_name, published_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, slug, body, author_id, author_name, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()
    return slug


def get_all_blog_posts():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM blog_posts ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def get_blog_posts_by_author(user_id):
    """Returns every post written by a specific user, most recent first —
    used on their account page."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM blog_posts WHERE author_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_blog_post_by_slug(slug):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM blog_posts WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    return row


def get_blog_post_by_id(post_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM blog_posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()
    return row


def delete_blog_post(post_id):
    conn = get_connection()
    conn.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Settings — small key/value store, currently used for the automatic
# newsletter schedule (which day of the month, and when it last sent).
# ---------------------------------------------------------------------

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Feedback — an open "suggest anything" box for visitors. Not moderated
# or shown publicly (unlike testimonials) — just a private inbox for you
# to read at /admin/feedback.
# ---------------------------------------------------------------------

def save_feedback(name, email, message):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO feedback (name, email, message, submitted_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            name.strip() if name else None,
            email.strip() if email else None,
            message.strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    conn.commit()
    conn.close()


def get_all_feedback():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM feedback ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def delete_feedback(feedback_id):
    conn = get_connection()
    conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Bookmarks — logged-in users saving programs to a personal shortlist.
# ---------------------------------------------------------------------

def add_bookmark(user_id, event_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO bookmarks (user_id, event_id, created_at) VALUES (?, ?, ?)",
            (user_id, event_id, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already bookmarked, nothing to do
    finally:
        conn.close()


def remove_bookmark(user_id, event_id):
    conn = get_connection()
    conn.execute("DELETE FROM bookmarks WHERE user_id = ? AND event_id = ?", (user_id, event_id))
    conn.commit()
    conn.close()


def is_bookmarked(user_id, event_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM bookmarks WHERE user_id = ? AND event_id = ?", (user_id, event_id)
    ).fetchone()
    conn.close()
    return row is not None


def get_user_bookmarks(user_id):
    """Returns the full event rows a user has bookmarked, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT events.* FROM events
        JOIN bookmarks ON bookmarks.event_id = events.id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.id DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------
# Event view counts — simple analytics for "most viewed programs".
# ---------------------------------------------------------------------

def increment_event_views(event_id):
    conn = get_connection()
    conn.execute("UPDATE events SET views = views + 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


def get_most_viewed_events(limit=5):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY views DESC, id ASC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_related_events(event, limit=3):
    """Other events with the same kind, excluding the event itself."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE kind = ? AND id != ? ORDER BY RANDOM() LIMIT ?",
        (event["kind"], event["id"], limit),
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------
# Blog comments
# ---------------------------------------------------------------------

def add_comment(post_id, author_id, author_name, message):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO blog_comments (post_id, author_id, author_name, message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_id, author_id, author_name, message, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()


def get_comments_for_post(post_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM blog_comments WHERE post_id = ? ORDER BY id ASC", (post_id,)
    ).fetchall()
    conn.close()
    return rows


def get_comment_by_id(comment_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM blog_comments WHERE id = ?", (comment_id,)).fetchone()
    conn.close()
    return row


def delete_comment(comment_id):
    conn = get_connection()
    conn.execute("DELETE FROM blog_comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------

def mark_email_verified(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
