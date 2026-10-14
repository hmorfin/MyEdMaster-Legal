from django.urls import path
from .views import DocumentView

urlpatterns = [
    path("/<str:user_id>/", DocumentView.as_view(), name="upload-document"),
]