from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    LoginView,
    MeView,
    PermissionViewSet,
    RoleViewSet,
    UserViewSet,
)

app_name = "account"

router = DefaultRouter()
router.register("permissions", PermissionViewSet)
router.register("roles", RoleViewSet)
router.register("users", UserViewSet)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("", include(router.urls)),
]
