import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import User
from apps.users.serializers import (
    ChangePasswordSerializer,
    CompleteProfileSerializer,
    DisconnectSocialSerializer,
    SetPasswordSerializer,
    UpdateEmailSerializer,
    UpdateUsernameSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get", "patch"])
    def info(self, request):
        if request.method == "GET":
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        # PATCH — update first_name, last_name, phone, avatar
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], url_path="update-email")
    def update_email(self, request):
        """Update user's email address."""
        serializer = UpdateEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.email = serializer.validated_data["email"]
        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch"], url_path="update-username")
    def update_username(self, request):
        """Update user's username."""
        serializer = UpdateUsernameSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.username = serializer.validated_data["username"]
        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """Change user's password."""
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="set-password")
    def set_password(self, request):
        """Set password for social-only users who don't have one yet."""
        serializer = SetPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response({"message": "Password set successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="disconnect-social")
    def disconnect_social(self, request):
        """Disconnect a social account from the user's profile."""
        serializer = DisconnectSocialSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.social_accounts.filter(provider=serializer.validated_data["provider"]).delete()

        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="complete-profile")
    def complete_profile(self, request):
        """Complete user profile with name and avatar."""
        was_already_complete = request.user.profile_complete
        serializer = CompleteProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if not was_already_complete:
            from apps.account.tasks import send_user_welcome_email_task

            send_user_welcome_email_task.delay(user.pk)
        return Response(UserSerializer(user).data)

    @action(detail=False, methods=["delete"], url_path="delete-account")
    def delete_account(self, request):
        """Anonymize the authenticated user's account (GDPR-compliant deletion).

        PII fields are wiped and the account is deactivated, but historical records
        (bookings, payments) are preserved for accounting and legal compliance.
        Pending and confirmed bookings are cancelled before anonymization.
        """
        user = request.user

        # Revoke all outstanding JWT refresh tokens for this user
        try:
            import contextlib

            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            from rest_framework_simplejwt.tokens import RefreshToken

            for token in OutstandingToken.objects.filter(user=user):
                with contextlib.suppress(Exception):
                    RefreshToken(str(token.token)).blacklist()  # type: ignore[arg-type]
        except ImportError:
            pass

        # Delete social account links so the provider UID can be re-used
        from apps.account.models import SocialAccount

        SocialAccount.objects.filter(user=user).delete()

        # Anonymize all PII on the user record
        anon_email = f"deleted_{user.pk}@deleted.invalid"
        user.email = anon_email
        user.username = None
        user.first_name = ""
        user.last_name = ""
        user.avatar = None
        user.avatar_preset = ""
        user.marketing_consent = False
        user.marketing_consent_at = None
        user.terms_accepted_at = None
        user.email_verified = False
        user.email_verified_at = None
        user.profile_complete = False
        user.is_active = False
        user.set_unusable_password()
        user.save(
            update_fields=[
                "email",
                "username",
                "first_name",
                "last_name",
                "avatar",
                "avatar_preset",
                "marketing_consent",
                "marketing_consent_at",
                "terms_accepted_at",
                "email_verified",
                "email_verified_at",
                "profile_complete",
                "is_active",
                "password",
            ]
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
