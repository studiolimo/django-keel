from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.UserListView.as_view(), name="user_list"),
    path("<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
    path("<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
]
