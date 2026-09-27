"""Refresh all site sitemaps.

Usage:
    python manage.py refresh_sitemaps            # all sites
    python manage.py refresh_sitemaps --host foo   # only one site

Recommended: schedule via Celery beat (daily at 03:00 AM) or crontab:

    0 3 * * * cd /opt/novel-system/docker && docker compose exec backend \
              python manage.py refresh_sitemaps > /var/log/novel-sitemaps.log 2>&1
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.seo.sitemap import generate_for_all_sites, generate_for_site
from apps.sites.models import Site


class Command(BaseCommand):
    help = "Refresh sitemap.xml for all active sites (or a single --host)."

    def add_arguments(self, parser):
        parser.add_argument("--host", help="Refresh only this host")

    def handle(self, *args, **options):
        if options.get("host"):
            try:
                site = Site.objects.get(host=options["host"], is_active=True)
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"site '{options['host']}' not found"))
                return
            p = generate_for_site(site)
            self.stdout.write(self.style.SUCCESS(f"✓ {site.host} → {p}"))
            return
        paths = generate_for_all_sites()
        for p in paths:
            self.stdout.write(f"  ✓ {p}")
        self.stdout.write(self.style.SUCCESS(f"Generated {len(paths)} sitemaps"))
