from django.urls import path

from apps.account.views import (
    AcceptTermsView,
    EmailLoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshTokenView,
    RegisterView,
    ResendVerificationEmailView,
    SocialLoginView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("accept-terms/", AcceptTermsView.as_view(), name="accept_terms"),
    path("social-login/", SocialLoginView.as_view(), name="social_login"),
    path("login/", EmailLoginView.as_view(), name="auth_login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth_refresh"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationEmailView.as_view(), name="resend-verification"),
]
