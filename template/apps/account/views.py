from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.account.serializers import (
    AcceptTermsSerializer,
    EmailTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    SocialLoginSerializer,
    VerifyEmailSerializer,
)
from apps.account.social_auth import social_login
from apps.users.models import User


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class EmailLoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]  # type: ignore[assignment]


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]  # type: ignore[assignment]


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_205_RESET_CONTENT)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        result = social_login(
            provider=vd["provider"],
            token=vd["token"],
            terms_accepted=vd["terms_accepted"],
            marketing_consent=vd.get("marketing_consent", False),
            first_name=vd.get("first_name", ""),
            last_name=vd.get("last_name", ""),
        )
        return Response(result)


class AcceptTermsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone

        serializer = AcceptTermsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.terms_accepted_at = timezone.now()

        if "marketing_consent" in serializer.validated_data:
            user.marketing_consent = serializer.validated_data["marketing_consent"]
            if user.marketing_consent:
                user.marketing_consent_at = timezone.now()
            # marketing_consent_at is preserved on withdrawal (audit trail)

        user.full_clean()
        user.save()
        return Response({"terms_up_to_date": user.terms_up_to_date})


class PasswordResetRequestView(APIView):
    """
    API endpoint per richiedere reset password.

    POST /api/account/password-reset/request/
    Body: {"email": "user@example.com"}

    Risponde sempre con 200 per non rivelare quali email esistono.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": _(
                        "If an account exists with this email, "
                        "you will receive password reset instructions."
                    )
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    API endpoint per confermare reset password.

    POST /api/account/password-reset/confirm/
    Body: {
        "uid": "MQ",
        "token": "abcdef-123456",
        "new_password": "NewPass123!",
        "new_password2": "NewPass123!"
    }
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": _("Password has been reset successfully.")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": _("Email verified successfully.")})


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Risposta generica per non rivelare se l'email esiste
            return Response({"detail": _("Verification email sent.")})

        if user.email_verified:
            return Response({"detail": _("Email already verified.")})

        from apps.account.tasks import send_email_verification_task

        send_email_verification_task.delay(user.pk)
        return Response({"detail": _("Verification email sent.")})
