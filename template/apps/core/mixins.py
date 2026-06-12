from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedMixin(models.Model):
    """
    Abstract model mixin that adds timestamp fields.

    Provides:
        - created_date: automatically set on creation
        - modified_date: automatically updated on save
    """

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StatusQuerySet(models.QuerySet):
    """
    QuerySet with status-based filtering methods.

    Provides filtering methods for the three lifecycle states:
    active, inactive, and archived.

    Usage:
        class MyModelQuerySet(StatusQuerySet):
            def for_user(self, user):
                return self.filter(user=user)

        class MyModel(StatusMixin):
            objects = models.Manager.from_queryset(MyModelQuerySet)()
    """

    def active(self):
        """Return only active objects."""
        return self.filter(status=StatusChoice.ACTIVE)

    def inactive(self):
        """Return only inactive objects."""
        return self.filter(status=StatusChoice.INACTIVE)

    def archived(self):
        """Return only archived objects."""
        return self.filter(status=StatusChoice.ARCHIVED)

    def not_archived(self):
        """Return active or inactive objects (excludes archived)."""
        return self.exclude(status=StatusChoice.ARCHIVED)


class StatusChoice(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    ARCHIVED = "archived", _("Archived")


class StatusMixin(models.Model):
    """
    Abstract model mixin for entities with lifecycle state management.

    Provides:
        - status: CharField with three states (active, inactive, archived)
        - objects: default manager with StatusQuerySet (use .active(), .inactive(), etc.)

    States:
        - active: Object is active and usable normally (default)
        - inactive: Object is temporarily disabled, can be reactivated
        - archived: Object is logically deleted (soft delete), used when dependencies exist

    Usage:
        class MyModel(TimeStampedMixin, StatusMixin):
            pass

        # Query examples:
        MyModel.objects.all()           # All records
        MyModel.objects.active()        # Only active records
        MyModel.objects.not_archived()  # Active or inactive (excludes archived)
        MyModel.objects.archived()      # Only archived records
    """

    status = models.CharField(
        max_length=20,
        choices=StatusChoice.choices,
        default=StatusChoice.ACTIVE,
        verbose_name=_("Status"),
    )

    objects = models.Manager.from_queryset(StatusQuerySet)()

    class Meta:
        abstract = True

    @property
    def is_active(self):
        """Checks if the token is still active."""
        return self.status == StatusChoice.ACTIVE
