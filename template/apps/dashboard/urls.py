from django.urls import include, path

app_name = "dashboard"

urlpatterns = [
    # Dashboard index
    path("", include("apps.dashboard.index.urls")),

    # Select2
    # path("select2/", views.DashboardSelect2View.as_view(), name="select2"),

    # user
    path("users/", include("apps.dashboard.user.urls")),
]
