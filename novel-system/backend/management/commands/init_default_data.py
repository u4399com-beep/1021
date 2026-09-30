"""Seed default data:
- 1 superuser (admin/admin123456 by default — change immediately)
- 5 theme records
- Sample categories
- Sample cleaning rules
- Sample classifier keywords
- Sample finished patterns
- Default download template
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.account.models import PERMISSION_CATALOG, Permission, Role
from apps.content_cleaner.models import CleaningRule
from apps.file_download.models import DownloadTemplate
from apps.novel.models import Category
from apps.smart_classifier.models import CategoryKeyword, FinishedPattern
from apps.sites.models import Site, Theme

User = get_user_model()


THEMES = [
    ("simple_reading", "简约阅读", "白底+衬线标题+暗灰正文，类似豆瓣读书风格，阅读优先", {}),
    ("classic_shelf", "古典书架", "木纹背景+宋体+横向卷轴元素，国风", {}),
    ("magazine_modern", "杂志现代", "大图封面+粗体大标题+瀑布流，类似 Flipboard 杂志风", {}),
    ("dark_tech", "暗黑科技", "深色背景+霓虹强调色+卡片瀑布流，二次元/网文站感", {}),
    ("minimal_rank", "极简榜单", "无尽列表+评分+标签云+排行榜，类似 Goodreads", {}),
    ("uaa_clone", "笔趣阁蓝", "克隆 uaa.com 风格，浅蓝顶栏 + 白底 + 淡灰边框，笔趣阁经典配色", {}),
]


CATEGORIES = ["玄幻", "奇幻", "武侠", "仙侠", "都市", "历史", "军事", "游戏",
              "科幻", "悬疑", "灵异", "同人", "言情", "青春", "职场"]


CLEANING_RULES = [
    ("script_and_style", "chapter", "regex", r"<script[^>]*>[\s\S]*?</script>|<style[^>]*>[\s\S]*?</style>", ""),
    ("iframe_remove", "chapter", "regex", r"<iframe[^>]*>[\s\S]*?</iframe>", ""),
    ("ins_ad_remove", "chapter", "css_remove", "ins.adsbygoogle, [class*=ad-]", ""),
    ("recommend_remove", "chapter", "css_remove", ".recommend, .book-tag, .footer-banner", ""),
    ("copyright_text_remove", "chapter", "regex",
     r"(更多精彩.*?关注[^<\n]+|请记住.*?域名[^<\n]+|本书首发[^<\n]+|扫码.*?二维码)",
     ""),
    ("extra_blank_lines", "chapter", "regex", r"\n{3,}", "\n\n"),
    ("trailing_whitespace", "chapter", "regex", r"[ \t]+$", ""),
    ("book_intro_clean", "book", "regex", r"<script[^>]*>[\s\S]*?</script>", ""),
]


KEYWORDS_BY_CATEGORY = {
    "玄幻": ["斗气", "魔法", "天赋", "血脉", "武道", "宗门", "修炼", "天材地宝"],
    "奇幻": ["异世界", "精灵", "矮人", "魔法", "中土", "屠龙", "远征", "酒馆"],
    "武侠": ["江湖", "门派", "刀剑", "内功", "侠客", "镖局", "丐帮", "盟主"],
    "仙侠": ["修仙", "筑基", "结丹", "元婴", "化神", "渡劫", "天劫", "宗门", "飞升"],
    "都市": ["都市", "都市重生", "职场", "校园", "豪门", "娱乐圈"],
    "历史": ["穿越", "乱世", "王朝", "将军", "皇子", "权臣", "开国"],
    "军事": ["军旅", "特种兵", "战争", "军人", "狙击", "战区"],
    "游戏": ["网游", "电竞", "虚拟", "副本", "BOSS", "装备", "主播"],
    "科幻": ["未来", "星际", "机甲", "末世", "宇宙", "AI", "硅基"],
    "悬疑": ["案", "凶", "调查", "警察", "侦探", "悬疑", "推理", "犯罪"],
    "灵异": ["鬼", "僵尸", "诡异", "怪谈", "盗墓", "风水", "茅山"],
    "同人": ["同人", "二创", "综漫", "综影", "衍生"],
    "言情": ["恋爱", "甜宠", "霸道总裁", "灰姑娘", "青梅竹马"],
    "青春": ["校园", "青春", "初恋", "高考", "大学"],
    "职场": ["职场", "商战", "金融", "创业", "公关"],
}


FINISHED_PATTERNS = [
    ("完结标识-已完结", r"已完结|全本|完结篇|大结局|最终章", 100),
    ("完结标识-全书完", r"全书完|本书完结", 100),
    ("完结标识-完本", r"完本", 100),
    ("最新章节-大结局", r"第.{1,5}大结局|结局篇", 100),
    ("最新章节-最终卷", r"最终卷", 100),
]


DOWNLOAD_TEMPLATES = [
    ("默认 TXT 模板", "txt",
     "本书来自 {site_name}，作者：{book_author}",
     "本章节内容由 {site_name} 提供",
     "本小说《{book_title}》由 {site_name} 收集整理。\n作者：{book_author}\n简介：{book_intro}",
     "本小说完结，欢迎访问 {site_name} 阅读更多精彩小说！",
     "— {site_name} | {site_name} —\nhttps://{site_name}\n",
     "广告位招商：联系 QQ 1234567890",
     True, 0.005, "\u200b\u200c\u200d\ufeff"),
    ("EPUB 模板", "epub", "", "",
     "{book_title} - {book_author}\n\n{book_intro}",
     "感谢您阅读本小说，来自 {site_name}",
     "© {site_name}", "", False, 0, ""),
]


class Command(BaseCommand):
    help = "Initialize default data: themes, categories, cleaning rules, classifier keywords, etc."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Truncate and recreate (destructive)")
        parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", "admin123456"))

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding default data..."))

        # 0. Permissions + default roles (RBAC)
        self._seed_permissions()
        self._seed_roles()

        # 1. Superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email=os.environ.get("ADMIN_EMAIL", "admin@local"),
                password=options["admin_password"],
            )
            self.stdout.write(f"  ✓ superuser 'admin' created (password=***hidden***)")
        else:
            self.stdout.write("  - superuser 'admin' already exists, skipping")

        # 2. Themes
        for code, name, desc, schema in THEMES:
            obj, created = Theme.objects.update_or_create(
                code=code, defaults={"name": name, "description": desc, "is_active": True}
            )
            self.stdout.write(f"  {'+' if created else '~'} theme {code}: {name}")

        # 3. Categories
        for cat in CATEGORIES:
            obj, created = Category.objects.get_or_create(name=cat, defaults={"slug": cat})
            self.stdout.write(f"  {'+' if created else '~'} category {cat}")

        # 4. Cleaning rules
        for name, target, strategy, pattern, repl in CLEANING_RULES:
            obj, created = CleaningRule.objects.update_or_create(
                name=name,
                defaults={"target": target, "strategy": strategy, "pattern": pattern, "replacement": repl, "enabled": True},
            )
            self.stdout.write(f"  {'+' if created else '~'} cleaning rule {name}")

        # 5. Classifier keywords
        for cat, kws in KEYWORDS_BY_CATEGORY.items():
            for kw in kws:
                obj, created = CategoryKeyword.objects.get_or_create(
                    category_name=cat, keyword=kw, defaults={"weight": 1.0},
                )
                if created:
                    self.stdout.write(f"  + keyword {cat} ← {kw}")

        # 6. Finished patterns
        for name, pattern, priority in FINISHED_PATTERNS:
            obj, created = FinishedPattern.objects.update_or_create(
                name=name, defaults={"pattern": pattern, "priority": priority, "enabled": True}
            )
            self.stdout.write(f"  {'+' if created else '~'} finished pattern {name}")

        # 7. Download templates
        for tpl in DOWNLOAD_TEMPLATES:
            name, fmt, hdr, ftr, pre, aft, info, ad, conf, dens, chars = tpl
            obj, created = DownloadTemplate.objects.update_or_create(
                name=name, defaults={
                    "output_format": fmt, "chapter_header": hdr, "chapter_footer": ftr,
                    "book_preface": pre, "book_afterword": aft,
                    "site_info_block": info, "ad_block": ad,
                    "enable_confusion": conf, "confusion_density": dens, "confusion_chars": chars,
                    "enabled": True,
                }
            )
            self.stdout.write(f"  {'+' if created else '~'} download template {name}")

        # 8. Default site (if none)
        if not Site.objects.exists():
            Site.objects.create(
                host="localhost",
                name="默认站点",
                theme=Theme.objects.get(code="simple_reading"),
                site_title="我的小说站",
                site_description="小说在线阅读，免费小说下载",
                site_keywords="小说,在线阅读,免费小说",
            )
            self.stdout.write("  + default site localhost → simple_reading")
        else:
            self.stdout.write("  - default site already exists")

        self.stdout.write(self.style.SUCCESS("Default data initialized."))

    # ------------------------------------------------------------------
    # RBAC seeding helpers
    # ------------------------------------------------------------------
    def _seed_permissions(self):
        """Insert all permissions from PERMISSION_CATALOG."""
        for code, name, desc in PERMISSION_CATALOG:
            obj, created = Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": desc},
            )
            self.stdout.write(f"  {'+' if created else '~'} permission {code}")

    def _seed_roles(self):
        """Seed four default roles: super-admin, editor, operator, viewer."""

        # 1) super-admin — has every permission (but is_system=True so it can't be deleted)
        super_admin, _ = Role.objects.get_or_create(
            code="super_admin", defaults={"name": "超级管理员", "is_system": True,
                                            "description": "拥有全部权限，可管理用户和系统设置"}
        )
        super_admin.permissions.set(Permission.objects.all())
        self.stdout.write(f"  ~ role {super_admin.code}: {super_admin.permissions.count()} perms")

        # 2) editor — can manage novels, rules, cleaner, classifier, download
        editor, _ = Role.objects.get_or_create(
            code="editor", defaults={"name": "编辑", "is_system": True,
                                       "description": "管理书籍、采集规则、清洗规则、分类、下载模板"}
        )
        editor.permissions.set(Permission.objects.filter(
            code__in=[
                "novel.view", "novel.edit", "novel.delete",
                "rule.view", "rule.edit",
                "cleaner.edit", "classifier.edit",
                "download.manage",
                "seo.view", "system.view",
            ]
        ))
        self.stdout.write(f"  ~ role {editor.code}: {editor.permissions.count()} perms")

        # 3) operator — can run/pause/stop tasks (but not edit rules)
        operator, _ = Role.objects.get_or_create(
            code="operator", defaults={"name": "操作员", "is_system": True,
                                          "description": "查看规则、运行/暂停/停止采集任务"}
        )
        operator.permissions.set(Permission.objects.filter(
            code__in=[
                "novel.view", "rule.view", "task.view", "task.run",
                "seo.view", "system.view",
            ]
        ))
        self.stdout.write(f"  ~ role {operator.code}: {operator.permissions.count()} perms")

        # 4) viewer — read-only across the board
        viewer, _ = Role.objects.get_or_create(
            code="viewer", defaults={"name": "查看者", "is_system": True,
                                        "description": "只读，可查看所有数据，不可修改"}
        )
        viewer.permissions.set(Permission.objects.filter(
            code__in=["novel.view", "rule.view", "task.view",
                      "seo.view", "system.view"]
        ))
        self.stdout.write(f"  ~ role {viewer.code}: {viewer.permissions.count()} perms")
