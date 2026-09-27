"""Account serializers."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Permission, Role

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True, slug_field="code", queryset=Permission.objects.all(), required=False
    )
    permissions_count = serializers.IntegerField(source="permissions.count", read_only=True)
    users_count = serializers.IntegerField(source="users.count", read_only=True)

    class Meta:
        model = Role
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    role_codes = serializers.SlugRelatedField(
        many=True, slug_field="code", source="roles", read_only=True
    )
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), source="roles", required=False
    )
    permission_codes = serializers.SerializerMethodField()
    is_superuser_user = serializers.BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "nickname", "avatar",
            "is_active", "is_staff", "is_superuser_user",
            "roles", "role_codes", "role_ids", "permission_codes",
            "last_login_ip", "date_joined",
        )
        read_only_fields = ("last_login_ip", "date_joined")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), source="roles", required=False
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "nickname", "password", "is_active", "is_staff", "role_ids")

    def create(self, validated):
        password = validated.pop("password")
        roles = validated.pop("roles", [])
        user = User(**validated)
        user.set_password(password)
        user.save()
        if roles:
            user.roles.set(roles)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), source="roles", required=False
    )

    class Meta:
        model = User
        fields = ("id", "email", "nickname", "avatar", "is_active", "is_staff", "password", "role_ids")

    def update(self, instance, validated):
        password = validated.pop("password", None)
        roles = validated.pop("roles", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            instance.roles.set(roles)
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["nickname"] = user.nickname or user.username
        token["is_superuser"] = user.is_superuser
        token["permissions"] = list(user.all_permission_codes())
        return token


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
