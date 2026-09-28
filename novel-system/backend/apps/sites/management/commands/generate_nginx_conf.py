"""生成每个 Site 的 nginx 配置文件，并 reload nginx。

由站群管理界面调用，或由 Site.save() 触发（生产环境建议改为手动按钮避免 reload 风暴）。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand
from django.template import Context, Template

from apps.sites.models import Site


NGINX_SITES_DIR = os.environ.get("NGINX_SITES_DIR", "/app/media/nginx-sites")
THEMES_STATIC_ROOT = os.environ.get("THEMES_STATIC_ROOT", "/usr/share/nginx/themes")


NGINX_TEMPLATE = """\
# Auto-generated for site {{ site.host }} — do not edit by hand
# Created by `python manage.py generate_nginx_conf`
server {
    listen 80;
    server_name {{ site.host }};

    root {{ themes_static_root }}/{{ theme_code }};
    index index.html;

    client_max_body_size 50m;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;

    # Front-end SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Per-site context injection (served by backend)
    location /api/site/ {
        proxy_pass http://backend:8000/api/v1/sites/by-host/?host={{ site.host }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Common API
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Media files (covers, chapters txt, downloads)
    location /media/ {
        proxy_pass http://backend:8000;
    }

    # robots.txt & sitemap.xml — site-specific, served by Django
    location = /robots.txt {
        proxy_pass http://backend:8000/api/v1/sites/by-host/robots.txt?host={{ site.host }};
    }
    location = /sitemap.xml {
        proxy_pass http://backend:8000/api/v1/sites/by-host/sitemap.xml?host={{ site.host }};
    }

    # Per-site head/body inject handled by Django renderer

    access_log /var/log/nginx/{{ site.host }}.access.log main;
    error_log  /var/log/nginx/{{ site.host }}.error.log warn;
}
"""


class Command(BaseCommand):
    help = "Generate per-site nginx config and reload nginx."

    def add_arguments(self, parser):
        parser.add_argument("--host", help="Only generate for this host")
        parser.add_argument("--reload", action="store_true", default=True, help="Reload nginx after generating")
        parser.add_argument("--no-reload", dest="reload", action="store_false")

    def handle(self, *args, **options):
        qs = Site.objects.filter(is_active=True)
        if options.get("host"):
            qs = qs.filter(host=options["host"])
        for site in qs:
            self.handle_site(site, reload_nginx=False)
        if options["reload"]:
            self.reload_nginx()
        self.stdout.write(self.style.SUCCESS(f"Generated {qs.count()} site configs"))

    def handle_site(self, site: Site, reload_nginx: bool = False):
        tpl = Template(NGINX_TEMPLATE)
        ctx = Context({
            "site": site,
            "theme_code": site.theme.code,
            "themes_static_root": THEMES_STATIC_ROOT,
        })
        content = tpl.render(ctx)
        # P0-4: Sanitize host to prevent path traversal
        import re
        safe_host = re.sub(r'[^a-zA-Z0-9.\-]', '_', site.host)
        if safe_host != site.host or '..' in site.host or '/' in site.host:
            self.stdout.write(self.style.ERROR(
                f"  ✗ Unsafe host '{site.host}' — skipping (path traversal blocked)"
            ))
            return
        out_path = Path(NGINX_SITES_DIR) / f"{safe_host}.conf"
        # Ensure the resolved path is within NGINX_SITES_DIR
        try:
            out_path.resolve().relative_to(Path(NGINX_SITES_DIR).resolve())
        except ValueError:
            self.stdout.write(self.style.ERROR(
                f"  ✗ Path traversal detected for host '{site.host}' — skipping"
            ))
            return
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        self.stdout.write(f"  ✓ {safe_host} → {out_path}")
        if reload_nginx:
            self.reload_nginx()

    @staticmethod
    def reload_nginx():
        """Reload nginx inside the nginx container (or skip if not available)."""
        try:
            subprocess.run(["nginx", "-s", "reload"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            # Outside nginx container — caller will reload separately
            print(f"[nginx reload skipped: {e!r}]")
