from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "nickname", "email", "is_staff", "is_superuser", "last_login_ip", "date_joined")
    search_fields = ("username", "email", "nickname")
    list_filter = ("is_staff", "is_superuser", "is_active")
