from django.urls import path

from .views import engine_fetch, engine_status, engine_test, suggest

app_name = "crawler"

urlpatterns = [
    path("suggest/", suggest, name="suggest"),
    path("engine/status/", engine_status, name="engine-status"),
    path("engine/test/", engine_test, name="engine-test"),
    path("engine/fetch/", engine_fetch, name="engine-fetch"),
]
