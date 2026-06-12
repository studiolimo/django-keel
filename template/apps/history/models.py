from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from apps.users.models import User


class ObjectHistory(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(User, related_name='history', blank=True, null=True, on_delete=models.SET_NULL)
    system = models.BooleanField(default=False, help_text=u"Indicate a system message. For example, if a script change "
                                                          u"some data, we don't have a user to save, so it's a system "
                                                          u"message")
    creation_date = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True, null=True)

    @staticmethod
    def add_history(object, user, description, system_message=False):
        ObjectHistory.objects.create(
            content_object=object,
            user=user,
            system=system_message,
            description=description
        )
