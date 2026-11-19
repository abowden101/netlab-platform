"""OAuth authorize/callback helpers (GitHub + Google).

These are real OAuth flows: authorize URLs are built from the configured
client id, and the callback exchanges the code for an access token and
fetches the provider profile. Until OAuth client credentials are configured
in `.env`, the routes return 503 "OAuth not configured" — the stub is the
configuration, not the flow.
"""

import secrets
from urllib.parse import urlencode

import httpx

from app.core.config import settings

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class OAuthNotConfiguredError(Exception):
    pass


def _github_configured() -> bool:
    return bool(settings.oauth_github_client_id and settings.oauth_github_client_secret)


def _google_configured() -> bool:
    return bool(settings.oauth_google_client_id and settings.oauth_google_client_secret)


def build_authorize_url(provider: str, state: str | None = None) -> str:
    """Return the provider authorize URL. Raises OAuthNotConfiguredError
    when the provider has no client credentials configured."""
    state = state or secrets.token_urlsafe(16)
    if provider == "github":
        if not _github_configured():
            raise OAuthNotConfiguredError("GitHub OAuth is not configured")
        query = urlencode(
            {
                "client_id": settings.oauth_github_client_id,
                "redirect_uri": settings.oauth_github_redirect_uri,
                "scope": "read:user user:email",
                "state": state,
            }
        )
        return f"{GITHUB_AUTHORIZE_URL}?{query}"
    if provider == "google":
        if not _google_configured():
            raise OAuthNotConfiguredError("Google OAuth is not configured")
        query = urlencode(
            {
                "client_id": settings.oauth_google_client_id,
                "redirect_uri": settings.oauth_google_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
            }
        )
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"
    raise ValueError(f"unknown OAuth provider {provider!r}")


async def exchange_code(provider: str, code: str) -> dict:
    """Exchange an authorization code for the provider profile. Returns a
    dict with at least ``email`` and ``name``."""
    if provider == "github":
        if not _github_configured():
            raise OAuthNotConfiguredError("GitHub OAuth is not configured")
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.oauth_github_client_id,
                    "client_secret": settings.oauth_github_client_secret,
                    "code": code,
                    "redirect_uri": settings.oauth_github_redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            user_resp = await client.get(GITHUB_USER_URL, headers=headers, timeout=15)
            user_resp.raise_for_status()
            profile = user_resp.json()
            email = profile.get("email")
            if not email:
                emails_resp = await client.get(
                    GITHUB_EMAILS_URL, headers=headers, timeout=15
                )
                emails_resp.raise_for_status()
                primary = next(
                    (e for e in emails_resp.json() if e.get("primary")), None
                )
                email = (primary or {}).get("email")
            return {
                "email": email,
                "name": profile.get("name") or profile.get("login", ""),
                "provider_id": str(profile.get("id", "")),
            }
    if provider == "google":
        if not _google_configured():
            raise OAuthNotConfiguredError("Google OAuth is not configured")
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.oauth_google_client_id,
                    "client_secret": settings.oauth_google_client_secret,
                    "code": code,
                    "redirect_uri": settings.oauth_google_redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            user_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            user_resp.raise_for_status()
            profile = user_resp.json()
            return {
                "email": profile.get("email"),
                "name": profile.get("name", ""),
                "provider_id": str(profile.get("sub", "")),
            }
    raise ValueError(f"unknown OAuth provider {provider!r}")
