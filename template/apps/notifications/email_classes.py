"""
Email template classes for each NotificationEvent.

Each class maps to a branded HTML template in templates/notifications/.
New events: add a class here + register in EMAIL_CLASS_REGISTRY.
"""

from apps.core.email_templates import EmailTemplate
from apps.notifications.enums import NotificationEvent


class PasswordResetNotificationEmail(EmailTemplate):
    subject_template = "notifications/subjects/password_reset.txt"
    html_template = "notifications/password_reset.html"


class UserWelcomeEmail(EmailTemplate):
    subject_template = "notifications/subjects/user_welcome.txt"
    html_template = "notifications/user_welcome.html"


class EmailVerificationEmail(EmailTemplate):
    subject_template = "notifications/subjects/email_verification.txt"
    html_template = "notifications/email_verification.html"


# Registry: event value → EmailTemplate subclass
# Aggiungere qui ogni nuovo evento email.
EMAIL_CLASS_REGISTRY: dict[str, type[EmailTemplate]] = {
    NotificationEvent.PASSWORD_RESET: PasswordResetNotificationEmail,
    NotificationEvent.USER_WELCOME: UserWelcomeEmail,
    NotificationEvent.EMAIL_VERIFICATION: EmailVerificationEmail,
}
