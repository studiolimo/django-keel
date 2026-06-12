from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token generator for email verification.

    Uses the same mechanism as PasswordResetTokenGenerator but hashes
    email_verified state so the token is invalidated once the email is verified.
    """

    def _make_hash_value(self, user, timestamp):  # type: ignore[override]
        return f"{user.pk}{timestamp}{user.email_verified}"


email_verification_token = EmailVerificationTokenGenerator()
