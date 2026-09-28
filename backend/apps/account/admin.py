from django.contrib import admin

from .models import Permission, Role, User


class RoleInline(admin.TabularInline):
    model = Role.users.through
    extra = 1


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "nickname", "email", "is_staff", "is_superuser",
                    "is_active", "last_login_ip", "date_joined", "get_roles")
    search_fields = ("username", "email", "nickname")
    list_filter = ("is_staff", "is_superuser", "is_active", "roles")
    filter_horizontal = ("roles",)
    readonly_fields = ("last_login_ip", "date_joined")

    def get_roles(self, obj):
        return ", ".join(r.name for r in obj.roles.all())


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system", "permissions_count", "users_count")
    list_filter = ("is_system",)
    search_fields = ("name", "code", "description")
    filter_horizontal = ("permissions",)
    readonly_fields = ("is_system",) if False else ()

    def permissions_count(self, obj):
        return obj.permissions.count()

    def users_count(self, obj):
        return obj.users.count()


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")
    search_fields = ("code", "name")
    ordering = ("code",)
