from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.account.models import SocialProvider

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    # terms_accepted removed as explicit required field — T&C acceptance is now implicit on register
    marketing_consent = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "marketing_consent",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        now = timezone.now()
        validated_data.pop("password2")
        marketing_consent = validated_data.pop("marketing_consent")
        password = validated_data.pop("password")

        # Normalise email (lowercase domain) the same way UserManager.create_user() does
        validated_data["email"] = User.objects.normalize_email(validated_data["email"])
        user = User(**validated_data)
        user.set_password(password)
        user.terms_accepted_at = now  # implicit acceptance on registration
        user.email_verified = False  # must verify email
        if marketing_consent:
            user.marketing_consent = True
            user.marketing_consent_at = now
        user.full_clean()
        user.save()

        from apps.account.tasks import send_email_verification_task

        send_email_verification_task.delay(user.pk)
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):  # type: ignore[override]  # return type widens to include bool values
        attrs[self.username_field] = attrs[self.username_field].lower()
        data: dict = super().validate(attrs)  # sets self.user after authentication
        # super().validate() always sets self.user or raises AuthenticationFailed — assert not needed
        data["terms_up_to_date"] = self.user.terms_up_to_date  # type: ignore[union-attr]  # super().validate() always sets self.user or raises
        data["email_verified"] = self.user.email_verified  # type: ignore[union-attr]
        data["profile_complete"] = self.user.profile_complete  # type: ignore[union-attr]
        return data


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SocialProvider.choices)
    token = serializers.CharField(required=True)
    terms_accepted = serializers.BooleanField(required=False, default=False)
    marketing_consent = serializers.BooleanField(required=False, default=False)
    first_name = serializers.CharField(required=False, default="", allow_blank=True)
    last_name = serializers.CharField(required=False, default="", allow_blank=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer per richiedere reset password."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Normalizza email (case-insensitive)."""
        return value.lower()

    def save(self, **_kwargs):
        """
        Cerca utente e triggera invio email.
        Non rivela se l'email esiste o no (security best practice).
        """
        email = self.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)
            # Importa qui per evitare circular import
            from apps.account.tasks import send_password_reset_email_task

            send_password_reset_email_task.delay(user.id)
        except User.DoesNotExist:
            # Silent fail per security (non rivelare quali email esistono)
            pass
        return True


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer per confermare reset password con nuova password."""

    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    new_password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        """Valida token, uid e password match."""
        # Valida password match
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": _("Passwords must match.")})

        # Valida password strength
        validate_password(attrs["new_password"])

        # Decodifica uid e trova utente
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError(
                {"uid": _("Invalid or expired reset link.")}
            ) from None

        # Valida token
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": _("Invalid or expired reset link.")})

        attrs["user"] = user
        return attrs

    def save(self, **_kwargs):
        """Salva nuova password."""
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class AcceptTermsSerializer(serializers.Serializer):
    marketing_consent = serializers.BooleanField(required=False)


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        from apps.account.tokens import email_verification_token

        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError(
                {"uid": _("Invalid or expired verification link.")}
            ) from None

        if not email_verification_token.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": _("Invalid or expired verification link.")})

        attrs["user"] = user
        return attrs

    def save(self, **_kwargs):
        user = self.validated_data["user"]
        if not user.email_verified:
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified", "email_verified_at"])
        return user


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
