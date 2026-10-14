from django.urls import path
from .views import CreateUserView, LoginView, ModifyUserView, user_stats

urlpatterns = [
    path("/", CreateUserView.as_view(), name="create-user"),
    path("/login/", LoginView.as_view(), name="login"),
    path("/<str:user_id>/", ModifyUserView.as_view(), name="modify-user"),
    path('/<str:user_id>/stats/', user_stats, name='user-stats'),
]