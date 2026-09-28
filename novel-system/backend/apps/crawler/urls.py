from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ProxyPoolViewSet,
    engine_fetch,
    engine_status,
    engine_test,
    hyperbrowser_create_session,
    hyperbrowser_release_session,
    hyperbrowser_status,
    suggest,
)

app_name = "crawler"

router = DefaultRouter()
router.register("proxy-pool", ProxyPoolViewSet)

urlpatterns = [
    path("suggest/", suggest, name="suggest"),
    path("engine/status/", engine_status, name="engine-status"),
    path("engine/test/", engine_test, name="engine-test"),
    path("engine/fetch/", engine_fetch, name="engine-fetch"),
    path("hyperbrowser/status/", hyperbrowser_status, name="hyperbrowser-status"),
    path("hyperbrowser/create-session/", hyperbrowser_create_session, name="hyperbrowser-create"),
    path("hyperbrowser/release-session/", hyperbrowser_release_session, name="hyperbrowser-release"),
    path("captcha/status/", captcha_status, name="captcha-status"),
    path("captcha/solve/", captcha_solve, name="captcha-solve"),
    path("", include(router.urls)),
]
