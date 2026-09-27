"""Account models — custom User + RBAC role/permission."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# ------------------------------------------------------------------
# RBAC catalog
# ------------------------------------------------------------------
# Permissions are codified as `<resource>.<action>` strings:
#   novel.view      — view any book/chapter
#   novel.edit      — edit book/chapter
#   novel.delete    — soft/hard delete
#   rule.view       — view crawler rules
#   rule.edit       — create/edit/test rules
#   rule.delete     — delete rules
#   task.view       — view crawler tasks
#   task.run        — start/pause/stop tasks
#   task.edit       — create/edit tasks
#   task.delete     — delete tasks
#   cleaner.edit    — manage cleaning rules
#   classifier.edit— manage classification rules
#   site.manage     — manage sites / themes / nginx
#   download.manage — manage download templates + trigger downloads
#   seo.view        — view SEO panel
#   user.manage     — manage users & roles (admin only)
#   system.view     — view system settings
#   system.edit     — modify system settings (engine tier keys, etc.)

PERMISSION_CATALOG = [
    # Novel
    ("novel.view",       "查看小说",      "查看书籍/章节/分类/标签"),
    ("novel.edit",       "编辑小说",      "创建/编辑书籍、章节"),
    ("novel.delete",     "删除小说",      "软删除/硬删除书籍"),
    # Rules
    ("rule.view",        "查看采集规则",  "查看采集规则与采集源"),
    ("rule.edit",        "编辑采集规则",  "创建/编辑/测试采集规则"),
    ("rule.delete",      "删除采集规则",  "删除采集规则"),
    # Tasks
    ("task.view",        "查看采集任务",  "查看任务列表与详情"),
    ("task.run",         "执行采集任务",  "启动/暂停/停止任务"),
    ("task.edit",        "编辑采集任务",  "创建/编辑采集任务"),
    ("task.delete",      "删除采集任务",  "删除采集任务"),
    # Cleaner
    ("cleaner.edit",     "编辑清洗规则",  "管理内容清洗规则"),
    # Classifier
    ("classifier.edit",  "编辑分类规则",  "管理分类关键词与完结规则"),
    # Site
    ("site.manage",      "管理站点",      "管理站群、主题、nginx 配置"),
    # Downloads
    ("download.manage",  "管理下载",      "管理下载模板、触发文件生成"),
    # SEO
    ("seo.view",         "查看SEO面板",   "查看SEO检测面板"),
    # Users
    ("user.manage",      "管理用户",      "管理用户与角色权限"),
    # System
    ("system.view",      "查看系统设置",  "查看系统设置"),
    ("system.edit",      "编辑系统设置",  "修改系统设置（API Key等）"),
]


class Permission(models.Model):
    """Catalog of all known permission codes."""

    code = models.CharField("权限码", max_length=64, unique=True)
    name = models.CharField("名称", max_length=64)
    description = models.CharField("描述", max_length=255, blank=True)

    class Meta:
        db_table = "account_permission"
        verbose_name = "权限"
        verbose_name_plural = verbose_name
        ordering = ("code",)

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Role(models.Model):
    """Role aggregates a set of permissions and is assigned to users."""

    name = models.CharField("角色名", max_length=64, unique=True)
    code = models.CharField("角色代码", max_length=32, unique=True)
    description = models.CharField("描述", max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    is_system = models.BooleanField("系统内置", default=False, help_text="系统内置角色不可删除")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_role"
        verbose_name = "角色"
        verbose_name_plural = verbose_name
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# ------------------------------------------------------------------
# Custom user with roles
# ------------------------------------------------------------------
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
    """Custom user — username + JWT + roles (RBAC)."""

    email = models.EmailField("邮箱", blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    avatar = models.URLField("头像URL", blank=True)
    is_active = models.BooleanField("启用", default=True)
    last_login_ip = models.GenericIPAddressField("最近登录IP", null=True, blank=True)
    date_joined = models.DateTimeField("加入时间", auto_now_add=True)

    # RBAC — many-to-many to roles
    roles = models.ManyToManyField(Role, related_name="users", blank=True)

    objects = UserManager()

    class Meta:
        db_table = "account_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.username

    # --- permission helpers ---
    def has_perm_code(self, code: str) -> bool:
        """Check if the user has a specific permission code via any of their roles."""
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__code=code).exists()

    def has_any_perm_code(self, codes: list[str]) -> bool:
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__code__in=codes).exists()

    def all_permission_codes(self) -> set[str]:
        """Return all permission codes the user has (via roles)."""
        if self.is_superuser:
            return {code for code, _, _ in PERMISSION_CATALOG}
        return set(
            self.roles.values_list("permissions__code", flat=True)
        )
