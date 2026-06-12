from django.urls import include, path

app_name = "dashboard"

urlpatterns = [
    # Dashboard index
    path("", include("apps.dashboard.index.urls")),

    # user
    path("users/", include("apps.dashboard.user.urls")),
]
