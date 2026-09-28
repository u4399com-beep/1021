from django.apps import AppConfig


class ObfuscatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.obfuscator"
    verbose_name = "页面混淆与伪原创"
