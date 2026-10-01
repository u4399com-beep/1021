"""Seed UA pool with common browser UA strings."""
from django.core.management.base import BaseCommand
from apps.crawler.anti_detection_models import UserAgentPool

UAS = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36", "chrome", "windows"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36", "chrome", "mac"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0", "firefox", "windows"),
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36", "chrome", "linux"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", "safari", "ios"),
    ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36", "chrome", "android"),
]

class Command(BaseCommand):
    help = "Seed UA pool with common browser strings"
    def handle(self, *args, **opts):
        for ua, browser, os_type in UAS:
            obj, created = UserAgentPool.objects.get_or_create(
                user_agent=ua, defaults={"browser": browser, "os": os_type}
            )
            tag = "+" if created else "~"
            self.stdout.write(f"  {tag} {browser}/{os_type}")
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(UAS)} UAs"))
