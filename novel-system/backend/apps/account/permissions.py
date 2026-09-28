"""DRF permission classes for RBAC."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasPermission(BasePermission):
    """Check a single permission code.

    Usage:
        class MyView(...):
            permission_classes = [HasPermission]
            required_permission = "novel.view"
    """

    required_permission: str | None = None

    def has_permission(self, request, view):
        # The view must declare `required_permission`
        perm = getattr(view, "required_permission", self.required_permission)
        if not perm:
            # No requirement declared — fall back to authenticated-only
            return bool(request.user and request.user.is_authenticated)
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.has_perm_code(perm)


class HasAnyPermission(BasePermission):
    """User has any one of a list of permission codes.

    Usage:
        class MyView(...):
            permission_classes = [HasAnyPermission]
            required_permissions = ["novel.view", "novel.edit"]
    """

    required_permissions: list[str] | None = None

    def has_permission(self, request, view):
        perms = getattr(view, "required_permissions", self.required_permissions) or []
        if not perms:
            return bool(request.user and request.user.is_authenticated)
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.has_any_perm_code(perms)


# ------------------------------------------------------------------
# Read vs Write split (common pattern)
# ------------------------------------------------------------------
class ReadOnlyOr(BasePermission):
    """Allow safe methods (GET/HEAD/OPTIONS) for any authenticated user,
    and require `required_permission` for write methods.
    """

    required_permission: str | None = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        perm = getattr(view, "required_permission", self.required_permission)
        if not perm:
            return user.is_staff
        return user.has_perm_code(perm)


# ------------------------------------------------------------------
# Pre-built permission classes for common cases
# ------------------------------------------------------------------
class CanViewNovel(HasPermission): required_permission = "novel.view"
class CanEditNovel(HasPermission): required_permission = "novel.edit"
class CanDeleteNovel(HasPermission): required_permission = "novel.delete"
class CanViewRule(HasPermission): required_permission = "rule.view"
class CanEditRule(HasPermission): required_permission = "rule.edit"
class CanDeleteRule(HasPermission): required_permission = "rule.delete"
class CanViewTask(HasPermission): required_permission = "task.view"
class CanEditTask(HasPermission): required_permission = "task.edit"
class CanRunTask(HasPermission): required_permission = "task.run"
class CanDeleteTask(HasPermission): required_permission = "task.delete"
class CanEditCleaner(HasPermission): required_permission = "cleaner.edit"
class CanEditClassifier(HasPermission): required_permission = "classifier.edit"
class CanManageSite(HasPermission): required_permission = "site.manage"
class CanManageDownload(HasPermission): required_permission = "download.manage"
class CanViewSEO(HasPermission): required_permission = "seo.view"
class CanManageUser(HasPermission): required_permission = "user.manage"
class CanViewSystem(HasPermission): required_permission = "system.view"
class CanEditSystem(HasPermission): required_permission = "system.edit"
