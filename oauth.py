# oauth.py
#
# "Continue with Google" / "Continue with GitHub" login for CLIENT
# accounts (the /signup, /login side of the site — not admin, which
# stays password-only on purpose for security).
#
# Signing in with Google/GitHub creates a normal CoderSpot user account
# automatically the first time, matched by email — same account you'd
# get from /signup, just without typing a password.
#
# ============================================================
# SETUP — Google
# ============================================================
#   1. Go to https://console.cloud.google.com/apis/credentials
#   2. Create Credentials -> OAuth client ID -> Application type: Web application
#   3. Under "Authorized redirect URIs" add:
#        http://127.0.0.1:5000/login/google/callback   (for local testing)
#        https://your-deployed-site.com/login/google/callback  (production)
#   4. Copy the generated Client ID and Client Secret into your .env file:
#        GOOGLE_CLIENT_ID=...
#        GOOGLE_CLIENT_SECRET=...
#
# ============================================================
# SETUP — GitHub
# ============================================================
#   1. Go to https://github.com/settings/developers -> OAuth Apps -> New OAuth App
#   2. Set "Authorization callback URL" to:
#        http://127.0.0.1:5000/login/github/callback   (for local testing)
#        https://your-deployed-site.com/login/github/callback  (production)
#   3. Copy the Client ID, generate a Client Secret, and add both to .env:
#        GITHUB_CLIENT_ID=...
#        GITHUB_CLIENT_SECRET=...
#
# Until these env vars are set, the "Continue with Google/GitHub" buttons
# simply don't appear on the login/signup pages — nothing breaks.

import os
from authlib.integrations.flask_client import OAuth

oauth = OAuth()


def is_google_configured():
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def is_github_configured():
    return bool(os.environ.get("GITHUB_CLIENT_ID") and os.environ.get("GITHUB_CLIENT_SECRET"))


def init_oauth(app):
    """Call once, right after creating the Flask app."""
    oauth.init_app(app)

    if is_google_configured():
        oauth.register(
            name="google",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if is_github_configured():
        oauth.register(
            name="github",
            client_id=os.environ.get("GITHUB_CLIENT_ID"),
            client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "read:user user:email"},
        )
