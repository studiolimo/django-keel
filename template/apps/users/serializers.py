import hashlib

from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.account.models import SocialAccount, SocialProvider
from apps.users.models import User


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ("id", "provider", "created_date")
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    has_password = serializers.SerializerMethodField()
    social_accounts = serializers.SerializerMethodField()
    cache_key = serializers.SerializerMethodField()
    terms_up_to_date = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "cache_key",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "has_password",
            "social_accounts",
            "email_verified",
            "profile_complete",
            "avatar_preset",
            "terms_up_to_date",
        )
        read_only_fields = (
            "id",
            "cache_key",
            "username",
            "email",
            "has_password",
            "social_accounts",
            "email_verified",
            "profile_complete",
            "terms_up_to_date",
        )

    def get_cache_key(self, obj) -> str:
        return hashlib.sha256(str(obj.id).encode()).hexdigest()[:16]

    def get_has_password(self, obj):
        return obj.has_usable_password()

    def get_social_accounts(self, obj):
        accounts = obj.social_accounts.all()
        return SocialAccountSerializer(accounts, many=True).data

    def get_terms_up_to_date(self, obj) -> bool:
        return obj.terms_up_to_date

    def validate(self, attrs):
        if "first_name" in attrs and not attrs["first_name"].strip():
            raise serializers.ValidationError({"first_name": _("Il nome è obbligatorio.")})
        if "last_name" in attrs and not attrs["last_name"].strip():
            raise serializers.ValidationError({"last_name": _("Il cognome è obbligatorio.")})
        if "avatar" in attrs and not attrs["avatar"]:
            raise serializers.ValidationError({"avatar": _("L'avatar è obbligatorio.")})
        return attrs


class DisconnectSocialSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SocialProvider.choices)

    def validate(self, attrs):
        user = self.context["request"].user
        provider = attrs["provider"]

        # Verifica che l'account social esista
        if not user.social_accounts.filter(provider=provider).exists():
            raise serializers.ValidationError(f"No {provider} account linked.")

        # Impedisci lo scollegamento se e' l'unico metodo di login
        has_password = user.has_usable_password()
        social_count = user.social_accounts.count()

        if not has_password and social_count <= 1:
            raise serializers.ValidationError(
                "Cannot disconnect the only login method. Set a password first."
            )

        return attrs


class UpdateEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Check if email is already taken by another user."""
        user = self.context["request"].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class UpdateUsernameSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=150)

    def validate_username(self, value):
        """Check if username is already taken by another user."""
        user = self.context["request"].user
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        """Verify that the current password is correct."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Validate the new password strength."""
        validate_password(value)
        return value


class SetPasswordSerializer(serializers.Serializer):
    """For social-only users who don't have a password yet."""

    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if user.has_usable_password():
            raise serializers.ValidationError(
                "You already have a password. Use change-password instead."
            )
        return attrs

    def validate_new_password(self, value):
        validate_password(value)
        return value


class CompleteProfileSerializer(serializers.ModelSerializer):
    avatar_preset = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "avatar",
            "avatar_preset",
            "marketing_consent",
        ]

    def validate(self, attrs):
        # Require first_name and last_name
        if not attrs.get("first_name", "").strip():
            raise serializers.ValidationError({"first_name": _("First name is required.")})
        if not attrs.get("last_name", "").strip():
            raise serializers.ValidationError({"last_name": _("Last name is required.")})

        # Require photo or preset
        has_avatar = bool(attrs.get("avatar") or self.instance and self.instance.avatar)
        has_preset = bool(attrs.get("avatar_preset", "").strip())
        if not has_avatar and not has_preset:
            raise serializers.ValidationError(
                {"avatar_preset": _("Select an avatar preset or upload a photo.")}
            )
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.profile_complete = True
        instance.full_clean()
        instance.save()
        return instance
