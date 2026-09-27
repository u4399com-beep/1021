"""Account views — login, refresh, me, user/role/permission CRUD (RBAC)."""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Permission, Role
from .permissions import CanManageUser
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        u = request.user
        if not u.check_password(ser.validated_data["old_password"]):
            return Response({"error": "旧密码错误"}, status=400)
        u.set_password(ser.validated_data["new_password"])
        u.save()
        return Response({"status": "ok"})


# ------------------------------------------------------------------
# RBAC: Permissions / Roles / Users
# ------------------------------------------------------------------
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only — permissions are seeded by the `init_default_data` command."""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = (permissions.IsAuthenticated, CanManageUser)
    filterset_fields = ("code",)
    search_fields = ("code", "name", "description")


class RoleViewSet(viewsets.ModelViewSet):
    """Role CRUD + assign permissions."""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = (permissions.IsAuthenticated, CanManageUser)
    filterset_fields = ("is_system",)
    search_fields = ("name", "code", "description")

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """Return the static permission catalog defined in models.py."""
        from .models import PERMISSION_CATALOG
        return Response([
            {"code": c, "name": n, "description": d}
            for c, n, d in PERMISSION_CATALOG
        ])

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_system:
            return Response({"error": "系统内置角色不可删除"}, status=400)
        return super().destroy(request, *args, **kwargs)


class UserViewSet(viewsets.ModelViewSet):
    """User CRUD with role assignment."""

    queryset = User.objects.all()
    permission_classes = (permissions.IsAuthenticated, CanManageUser)
    filterset_fields = ("is_active", "is_staff")
    search_fields = ("username", "email", "nickname")
    ordering = ("-id",)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def assign_roles(self, request, pk=None):
        user = self.get_object()
        role_ids = request.data.get("role_ids", [])
        roles = Role.objects.filter(id__in=role_ids)
        user.roles.set(roles)
        return Response({"status": "ok", "roles": list(user.roles.values_list("id", flat=True))})

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user.is_superuser:
            return Response({"error": "不可禁用超级管理员"}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response({"status": "ok", "is_active": user.is_active})

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)
