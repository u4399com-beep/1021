from django.contrib import admin

from .models import Site, Theme


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "sites_count", "preview")
    list_filter = ("is_active",)
    search_fields = ("code", "name")

    def sites_count(self, obj):
        return obj.sites.count()


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("host", "name", "theme", "is_active", "offset", "updated_at")
    list_filter = ("is_active", "theme")
    search_fields = ("host", "name", "site_title")
    readonly_fields = ("created_at", "updated_at")
    actions = ["regenerate_nginx"]

    def regenerate_nginx(self, request, qs):
        from .management.commands.generate_nginx_conf import Command
        cmd = Command()
        for site in qs:
            cmd.handle_site(site, reload_nginx=False)
        cmd.reload_nginx()
    regenerate_nginx.short_description = "重新生成 nginx 配置"
