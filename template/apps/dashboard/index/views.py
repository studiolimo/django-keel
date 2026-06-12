from django.views.generic import TemplateView

from apps.dashboard.mixins import SuperuserPermissionMixin


class DashboardIndexView(SuperuserPermissionMixin, TemplateView):
    template_name = "dashboard/index/index.html"
