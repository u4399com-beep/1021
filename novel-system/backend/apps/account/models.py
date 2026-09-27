"""Account models — custom User."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, username, email, password, **extra):
        if not username:
            raise ValueError("username required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email="", password="", **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(username, email, password, **extra)

    def create_superuser(self, username, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("superuser must have is_staff=True")
        if extra.get("is_superuser") is not True:
            raise ValueError("superuser must have is_superuser=True")
        return self._create(username, email, password, **extra)


class User(AbstractUser):
    """Custom user — username + JWT."""

    email = models.EmailField("邮箱", blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    avatar = models.URLField("头像URL", blank=True)
    is_active = models.BooleanField("启用", default=True)
    last_login_ip = models.GenericIPAddressField("最近登录IP", null=True, blank=True)
    date_joined = models.DateTimeField("加入时间", auto_now_add=True)

    objects = UserManager()

    class Meta:
        db_table = "account_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.username
