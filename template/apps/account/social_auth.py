"""Social authentication service layer.

Handles token verification for Google and Facebook,
user lookup/creation, and JWT generation.
"""

import logging

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from jwt import PyJWKClient
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.account.models import SocialAccount, SocialProvider

logger = logging.getLogger(__name__)
User = get_user_model()


def verify_google_token(token: str) -> dict:
    """Verify a Google OAuth2 access token via the userinfo endpoint.

    Returns:
        dict with keys: uid, email, first_name, last_name, extra_data
    """
    try:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as e:
        raise AuthenticationFailed(f"Failed to verify Google token: {e}") from e

    if resp.status_code != 200:
        raise AuthenticationFailed("Invalid Google access token.")

    userinfo = resp.json()
    email = userinfo.get("email", "").lower()
    if not email:
        raise AuthenticationFailed("Email not provided by Google.")

    return {
        "uid": userinfo["sub"],
        "email": email,
        "first_name": userinfo.get("given_name", ""),
        "last_name": userinfo.get("family_name", ""),
        "extra_data": {
            "picture": userinfo.get("picture", ""),
            "email_verified": userinfo.get("email_verified", False),
        },
    }


def verify_facebook_token(token: str) -> dict:
    """Verify a Facebook access token and return user info.

    Uses the Graph API debug_token endpoint + /me for user data.

    Returns:
        dict with keys: uid, email, first_name, last_name, extra_data
    """
    # Step 1: Debug token to verify it's valid and belongs to our app
    debug_url = "https://graph.facebook.com/debug_token"
    debug_params = {
        "input_token": token,
        "access_token": f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}",
    }
    try:
        debug_resp = requests.get(debug_url, params=debug_params, timeout=10)
        debug_data = debug_resp.json().get("data", {})
    except requests.RequestException as e:
        raise AuthenticationFailed(f"Failed to verify Facebook token: {e}") from e

    if not debug_data.get("is_valid"):
        raise AuthenticationFailed("Invalid Facebook token.")

    if str(debug_data.get("app_id")) != str(settings.FACEBOOK_APP_ID):
        raise AuthenticationFailed("Facebook token does not belong to this app.")

    # Step 2: Fetch user profile
    me_url = "https://graph.facebook.com/me"
    me_params = {
        "fields": "id,email,first_name,last_name,picture",
        "access_token": token,
    }
    try:
        me_resp = requests.get(me_url, params=me_params, timeout=10)
        me_data = me_resp.json()
    except requests.RequestException as e:
        raise AuthenticationFailed(f"Failed to fetch Facebook profile: {e}") from e

    email = me_data.get("email", "").lower()
    if not email:
        raise AuthenticationFailed("Email not provided by Facebook. Please grant email permission.")

    return {
        "uid": me_data["id"],
        "email": email,
        "first_name": me_data.get("first_name", ""),
        "last_name": me_data.get("last_name", ""),
        "extra_data": {
            "picture": me_data.get("picture", {}).get("data", {}).get("url", ""),
        },
    }


def verify_apple_token(token: str) -> dict:
    """Verify an Apple Sign In identity token (JWT signed by Apple).

    Uses Apple's public JWKS to verify the signature. No Apple secret needed.

    Returns:
        dict with keys: uid, email, first_name, last_name, extra_data
    """
    valid_audiences = [
        aud
        for aud in [
            getattr(settings, "APPLE_BUNDLE_ID", ""),
            getattr(settings, "APPLE_SERVICES_ID", ""),
        ]
        if aud
    ]

    try:
        jwks_client = PyJWKClient("https://appleid.apple.com/auth/keys")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer="https://appleid.apple.com",
        )
    except Exception as e:
        raise AuthenticationFailed(f"Invalid Apple identity token: {e}") from e

    email = payload.get("email", "").lower()
    if not email:
        raise AuthenticationFailed("Email not provided by Apple.")

    return {
        "uid": payload["sub"],
        "email": email,
        "first_name": "",
        "last_name": "",
        "extra_data": {
            "email_verified": payload.get("email_verified", True),
            "is_private_email": payload.get("is_private_email", False),
        },
    }


PROVIDER_VERIFIERS = {
    SocialProvider.GOOGLE: verify_google_token,
    SocialProvider.FACEBOOK: verify_facebook_token,
    SocialProvider.APPLE: verify_apple_token,
}


def social_login(
    provider: str,
    token: str,
    terms_accepted: bool = True,  # noqa: ARG001  # kept for backwards compat, now implicit
    marketing_consent: bool = False,
    first_name: str = "",
    last_name: str = "",
) -> dict:
    """Main social login flow.

    T&C acceptance is implicit for new users created via social login.
    For existing users (Cases 1 and 2), consent is handled via the accept-terms endpoint.

    Args:
        first_name/last_name: Provided by the frontend for Apple Sign In,
            since Apple only sends the name in the initial authorization response
            (not in the identity token).

    Returns:
        dict with keys: access, refresh, created, terms_up_to_date, email_verified, profile_complete
    """
    verifier = PROVIDER_VERIFIERS.get(SocialProvider(provider))
    if not verifier:
        raise AuthenticationFailed(f"Unsupported provider: {provider}")

    user_info = verifier(token)

    # Apple doesn't include name in the identity token — use frontend-provided values
    if not user_info["first_name"] and first_name:
        user_info["first_name"] = first_name
    if not user_info["last_name"] and last_name:
        user_info["last_name"] = last_name
    uid = user_info["uid"]
    email = user_info["email"]
    created = False
    # Determine if provider already verified the email
    provider_email_verified = user_info["extra_data"].get("email_verified", False)

    # Case 1: SocialAccount already exists
    try:
        social_account = SocialAccount.objects.select_related("user").get(
            provider=provider, provider_uid=uid
        )
        if not social_account.user.is_active:
            # Account was deleted (GDPR anonymized) — remove the stale link
            # and fall through to Case 2/3 so the user gets a fresh account.
            social_account.delete()
            raise SocialAccount.DoesNotExist
        user = social_account.user
        social_account.extra_data = user_info["extra_data"]
        social_account.save(update_fields=["extra_data", "modified_date"])
    except SocialAccount.DoesNotExist:
        # Case 2: User with same email exists → auto-link (treated as existing user login)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Case 3: Create new user — implicit T&C acceptance
            from django.utils import timezone

            now = timezone.now()
            user = User.objects.create_user(
                email=email,
                first_name=user_info["first_name"],
                last_name=user_info["last_name"],
                terms_accepted_at=now,
                email_verified=provider_email_verified,
                email_verified_at=now if provider_email_verified else None,
                marketing_consent=marketing_consent,
                marketing_consent_at=now if marketing_consent else None,
            )
            created = True

            from apps.account.tasks import (
                send_email_verification_task,
                send_user_welcome_email_task,
            )

            send_user_welcome_email_task.delay(user.pk)
            if not provider_email_verified:
                send_email_verification_task.delay(user.pk)

        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_uid=uid,
            extra_data=user_info["extra_data"],
        )

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "created": created,
        "terms_up_to_date": user.terms_up_to_date,
        "email_verified": user.email_verified,
        "profile_complete": user.profile_complete,
    }
