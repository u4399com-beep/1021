from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    three_tier_status,
    speedup_chapter_fetch,
    ProxyPoolViewSet,
    captcha_solve,
    captcha_status,
    engine_fetch,
    engine_status,
    engine_test,
    hyperbrowser_create_session,
    hyperbrowser_release_session,
    hyperbrowser_status,
    region_clear_override,
    region_set_override,
    region_status,
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
    path("region/status/", region_status, name="region-status"),
    path("region/set-override/", region_set_override, name="region-set-override"),
    path("region/clear-override/", region_clear_override, name="region-clear-override"),
    path("captcha/status/", captcha_status, name="captcha-status"),
    path("captcha/solve/", captcha_solve,
    path("three-tier/status/",
    path("speedup-chapters/", speedup_chapter_fetch, name="speedup-chapters"), three_tier_status,
    speedup_chapter_fetch, name="three-tier-status"), name="captcha-solve"),
    path("", include(router.urls)),
]
