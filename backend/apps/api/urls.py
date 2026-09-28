from django.urls import path

from .views import dashboard, system_info

app_name = "api"

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("system/", system_info, name="system"),
]
