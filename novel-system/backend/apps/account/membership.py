"""Front-end user membership (v71) — reader accounts, bookshelf, reading history."""
from __future__ import annotations
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


User = getattr(settings, 'AUTH_USER_MODEL', 'account.User')


class ReaderProfile(models.Model):
    """Front-end reader profile (separate from admin User)."""
    username = models.CharField("用户名", max_length=64, unique=True)
    email = models.EmailField("邮箱", blank=True)
    password_hash = models.CharField("密码哈希", max_length=128, blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    avatar = models.URLField("头像", blank=True)
    
    # Membership
    membership_level = models.CharField("会员等级", max_length=16, default="free",
        choices=[("free", "免费"), ("vip", "VIP"), ("premium", "高级")])
    membership_expires = models.DateTimeField("会员到期", null=True, blank=True)
    coins = models.IntegerField("金币", default=0, help_text="用于付费章节")
    
    # Preferences
    reading_font = models.CharField("阅读字体", max_length=32, default="serif")
    reading_size = models.IntegerField("阅读字号", default=18)
    night_mode = models.BooleanField("夜间模式", default=False)
    
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_reader_profile"
        verbose_name = "读者账户"
        verbose_name_plural = verbose_name

    def __str__(self): return self.username
    
    @property
    def is_vip(self):
        from django.utils import timezone
        return self.membership_level != "free" and (
            self.membership_expires is None or self.membership_expires > timezone.now()
        )


class Bookshelf(models.Model):
    """User's personal bookshelf (收藏)."""
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name="bookshelf")
    book = models.ForeignKey("novel.Book", on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    last_read_chapter = models.IntegerField("最后阅读章节", default=0)
    last_read_at = models.DateTimeField("最后阅读时间", null=True, blank=True)

    class Meta:
        db_table = "account_bookshelf"
        verbose_name = "书架"
        verbose_name_plural = verbose_name
        unique_together = ("reader", "book")
        ordering = ("-added_at",)


class ReadingHistory(models.Model):
    """User's reading history."""
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name="reading_history")
    book = models.ForeignKey("novel.Book", on_delete=models.CASCADE)
    chapter = models.ForeignKey("novel.Chapter", on_delete=models.SET_NULL, null=True, blank=True)
    chapter_order = models.IntegerField("章节序号", default=1)
    read_at = models.DateTimeField(auto_now_add=True)
    read_duration = models.IntegerField("阅读时长(秒)", default=0)

    class Meta:
        db_table = "account_reading_history"
        verbose_name = "阅读历史"
        verbose_name_plural = verbose_name
        ordering = ("-read_at",)
        indexes = [models.Index(fields=["reader", "-read_at"])]
