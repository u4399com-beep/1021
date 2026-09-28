"""A/B testing for site themes (v49) — randomly serve one of two themes."""
from __future__ import annotations
import random
import hashlib
from django.db import models
from apps.sites.models import Site, Theme


class ABTestConfig(models.Model):
    """A/B test configuration for a site."""
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="ab_tests")
    theme_a = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="ab_tests_a")
    theme_b = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="ab_tests_b")
    split_ratio = models.FloatField("A/B 分流比例", default=0.5,
        help_text="0.0-1.0，A 主题的比例")
    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Stats
    views_a = models.IntegerField("A 主题浏览", default=0)
    views_b = models.IntegerField("B 主题浏览", default=0)

    class Meta:
        db_table = "sites_ab_test"
        verbose_name = "A/B 测试"
        verbose_name_plural = verbose_name

    def pick_theme(self, visitor_id: str = "") -> Theme:
        """Pick a theme for this visitor. Deterministic if visitor_id given."""
        if not self.enabled:
            return self.theme_a
        if visitor_id:
            # Hash visitor_id for consistent assignment
            h = int(hashlib.md5(visitor_id.encode()).hexdigest(), 16) % 100
            use_a = (h / 100) < self.split_ratio
        else:
            use_a = random.random() < self.split_ratio
        if use_a:
            self.views_a += 1
        else:
            self.views_b += 1
        self.save(update_fields=["views_a", "views_b"])
        return self.theme_a if use_a else self.theme_b
