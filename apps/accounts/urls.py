from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("me/", views.MeView.as_view(), name="me"),
    path("recipients/", views.SavedRecipientListCreateView.as_view(), name="saved-recipients"),
]
