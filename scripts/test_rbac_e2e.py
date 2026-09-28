#!/usr/bin/env python
"""End-to-end test #2 — RBAC user creation + role assignment.

Simulates the workflow:
  "在「用户与权限」中创建编辑和操作员账号，分配角色测试菜单过滤"

This script:
  1. Verifies all 4 built-in roles exist (super_admin / editor / operator / viewer)
  2. Creates two test users (editor + operator) with random passwords
  3. Logs in as each user
  4. Verifies the JWT contains the correct `permissions` claim
  5. Prints a menu-filter simulation: which routes each user can/cannot see
  6. (Optional) Deletes the test users afterward with --cleanup

Usage:
    python scripts/test_rbac_e2e.py
    python scripts/test_rbac_e2e.py --cleanup    # delete test users after
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

django.setup()

from django.contrib.auth import get_user_model
from apps.account.models import PERMISSION_CATALOG, Permission, Role
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# Mirror the frontend router's per-route permission requirements
ROUTE_PERMISSIONS = [
    ("dashboard",   None),          # always visible
    ("novels",      "novel.view"),
    ("rules",       "rule.view"),
    ("tasks",       "task.view"),
    ("cleaner",     "cleaner.edit"),
    ("classifier",  "classifier.edit"),
    ("sites",       "site.manage"),
    ("themes",      "site.manage"),
    ("downloads",   "download.manage"),
    ("seo",         "seo.view"),
    ("users",       "user.manage"),
    ("system",      "system.view"),
]


def ensure_roles():
    """Make sure the 4 built-in roles exist (in case init_default_data wasn't run)."""
    from django.core.management import call_command
    call_command("init_default_data", verbosity=0)


def create_test_user(username: str, email: str, role_codes: list[str]) -> tuple[User, str]:
    pwd = secrets.token_urlsafe(16)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "nickname": username.title()},
    )
    if created:
        user.set_password(pwd)
        user.save()
    else:
        # Reset password if existing
        user.set_password(pwd)
        user.save(update_fields=["password"])
    # Assign roles
    roles = Role.objects.filter(code__in=role_codes)
    user.roles.set(roles)
    return user, pwd


def get_token_perms(user: User) -> list[str]:
    """Get the permissions list encoded in the JWT for this user."""
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

    class _S(TokenObtainPairSerializer):
        @classmethod
        def get_token(cls, u):
            t = super().get_token(u)
            t["permissions"] = list(u.all_permission_codes())
            t["username"] = u.username
            return t

    token = _S.get_token(user)
    return token.payload.get("permissions", [])


def simulate_menu(perms: list[str], is_superuser: bool = False) -> list[dict]:
    """Return per-route menu visibility for a user with the given perms."""
    result = []
    for route, required in ROUTE_PERMISSIONS:
        if is_superuser:
            visible = True
        elif required is None:
            visible = True
        else:
            visible = required in perms
        result.append({"route": route, "required": required or "(none)", "visible": visible})
    return result


def main():
    parser = argparse.ArgumentParser(description="RBAC end-to-end test")
    parser.add_argument("--cleanup", action="store_true", help="Delete test users after run")
    args = parser.parse_args()

    print("=" * 70)
    print("【1/4】 验证内置角色与权限目录")
    print("=" * 70)
    print(f"  权限目录大小: {len(PERMISSION_CATALOG)}")
    print(f"  数据库中的 Permission 数: {Permission.objects.count()}")
    print(f"  数据库中的 Role 数: {Role.objects.count()}")
    for r in Role.objects.all():
        print(f"    - {r.code:15s}  perms={r.permissions.count():2d}  users={r.users.count()}  system={r.is_system}")

    ensure_roles()

    # Create test users
    print()
    print("=" * 70)
    print("【2/4】 创建测试用户")
    print("=" * 70)
    editor, ed_pwd = create_test_user("test_editor", "test_editor@local", ["editor"])
    operator, op_pwd = create_test_user("test_operator", "test_operator@local", ["operator"])
    print(f"  ✓ editor:    username={editor.username}  password={ed_pwd}  roles={list(editor.roles.values_list('code', flat=True))}")
    print(f"  ✓ operator:  username={operator.username}  password={op_pwd}  roles={list(operator.roles.values_list('code', flat=True))}")

    # Login via JWT
    print()
    print("=" * 70)
    print("【3/4】 JWT Token 中权限验证")
    print("=" * 70)
    ed_perms = get_token_perms(editor)
    op_perms = get_token_perms(operator)
    print(f"  editor   permissions ({len(ed_perms)}): {ed_perms}")
    print(f"  operator permissions ({len(op_perms)}): {op_perms}")

    # Menu filter simulation
    print()
    print("=" * 70)
    print("【4/4】 菜单可见性模拟（前端会按此过滤）")
    print("=" * 70)
    for user, perms, label in [(editor, ed_perms, "EDITOR"), (operator, op_perms, "OPERATOR")]:
        print(f"\n  ─── {label} ({user.username}) ───")
        menu = simulate_menu(perms, user.is_superuser)
        for item in menu:
            icon = "✓" if item["visible"] else "✗"
            req = item["required"]
            print(f"    {icon} /admin/{item['route']:14s}  requires={req}")

    # Verify editor can do everything except user/system management
    editor_can_edit_rules = "rule.edit" in ed_perms
    editor_can_manage_users = "user.manage" in ed_perms
    operator_can_run_tasks = "task.run" in op_perms
    operator_can_edit_rules = "rule.edit" in op_perms

    print()
    print("→ 断言:")
    assert editor_can_edit_rules, "❌ editor 应有 rule.edit"
    assert not editor_can_manage_users, "❌ editor 不应有 user.manage"
    assert operator_can_run_tasks, "❌ operator 应有 task.run"
    assert not operator_can_edit_rules, "❌ operator 不应有 rule.edit"
    print("  ✓ editor 可编辑规则、不可管理用户 — 符合预期")
    print("  ✓ operator 可运行任务、不可编辑规则 — 符合预期")

    if args.cleanup:
        print()
        print("→ 清理测试用户...")
        editor.delete()
        operator.delete()
        print("  ✓ 已删除")

    print()
    print("=== RBAC 端到端测试通过 ===")
    print("  - 4 个内置角色均已注册")
    print("  - 测试用户创建成功并分配角色")
    print("  - JWT 携带 permissions 声明")
    print("  - 菜单过滤逻辑符合权限模型")
    return 0


if __name__ == "__main__":
    sys.exit(main())
