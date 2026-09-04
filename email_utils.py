# email_utils.py
#
# Handles sending the monthly newsletter email via a Gmail account, and
# generating/verifying the "one-click unsubscribe" links used in every
# email's footer.
#
# GMAIL SETUP (do this once):
#   1. Turn on 2-Step Verification on the Gmail account you'll send from:
#      https://myaccount.google.com/security
#   2. Create an "App Password" for this app:
#      https://myaccount.google.com/apppasswords
#      (Regular Gmail passwords do NOT work for this — it must be an App
#      Password, a 16-character code Google generates for you.)
#   3. Copy .env.example to .env and fill in:
#        GMAIL_ADDRESS=youraddress@gmail.com
#        GMAIL_APP_PASSWORD=the16charactercode
#   4. Never commit .env to version control — it's already in .gitignore.

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeSerializer, URLSafeTimedSerializer

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def is_email_configured():
    """True once GMAIL_ADDRESS and GMAIL_APP_PASSWORD are set in .env."""
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def get_serializer(secret_key):
    """Used to create/verify signed, tamper-proof unsubscribe links, so a
    link like /unsubscribe/<token> can't be guessed or edited by someone
    else to unsubscribe a different user."""
    return URLSafeSerializer(secret_key, salt="unsubscribe")


def make_unsubscribe_token(secret_key, user_id):
    return get_serializer(secret_key).dumps({"user_id": user_id})


def read_unsubscribe_token(secret_key, token):
    """Returns the user_id encoded in the token, or None if it's invalid."""
    try:
        data = get_serializer(secret_key).loads(token)
        return data.get("user_id")
    except Exception:
        return None


def get_timed_serializer(secret_key, salt):
    """Like get_serializer, but the resulting tokens expire — used for
    password resets and email verification, where a stale link should
    stop working."""
    return URLSafeTimedSerializer(secret_key, salt=salt)


def make_password_reset_token(secret_key, user_id):
    return get_timed_serializer(secret_key, "password-reset").dumps({"user_id": user_id})


def read_password_reset_token(secret_key, token, max_age=3600):
    """Valid for 1 hour by default. Returns the user_id, or None if the
    token is invalid or expired."""
    try:
        data = get_timed_serializer(secret_key, "password-reset").loads(token, max_age=max_age)
        return data.get("user_id")
    except Exception:
        return None


def make_email_verification_token(secret_key, user_id):
    return get_timed_serializer(secret_key, "verify-email").dumps({"user_id": user_id})


def read_email_verification_token(secret_key, token, max_age=604800):
    """Valid for 7 days by default."""
    try:
        data = get_timed_serializer(secret_key, "verify-email").loads(token, max_age=max_age)
        return data.get("user_id")
    except Exception:
        return None


def send_email(to_email, subject, html_body):
    """
    Sends a single HTML email via Gmail SMTP.
    Raises an exception on failure — the caller (the newsletter send loop)
    catches this per-recipient so one bad address doesn't stop the batch.
    """
    if not is_email_configured():
        raise RuntimeError(
            "Email isn't configured yet. Set GMAIL_ADDRESS and "
            "GMAIL_APP_PASSWORD in your .env file (see .env.example)."
        )

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, message.as_string())


def send_newsletter(recipients, subject, build_html_for_user, on_result=None):
    """
    Sends the same newsletter to a list of user rows, personalizing each
    copy's unsubscribe link.

    - recipients: list of user rows (each needs 'id' and 'email')
    - subject: email subject line
    - build_html_for_user: function(user) -> html string for that user
    - on_result: optional callback(user, success, error_message)

    Returns (sent_count, failed_count).
    """
    sent, failed = 0, 0
    for user in recipients:
        try:
            html = build_html_for_user(user)
            send_email(user["email"], subject, html)
            sent += 1
            if on_result:
                on_result(user, True, None)
        except Exception as exc:
            failed += 1
            if on_result:
                on_result(user, False, str(exc))
    return sent, failed
