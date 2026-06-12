from django.views.generic import TemplateView
from django_select2.views import AutoResponseView

from apps.dashboard.mixins import SuperuserPermissionMixin


class SuperuserSelect2View(SuperuserPermissionMixin, AutoResponseView):
    pass


class DashboardIndexView(SuperuserPermissionMixin, TemplateView):
    template_name = 'dashboard/index/index.html'
