from django.urls import path

from .views import suggest

app_name = "crawler"

urlpatterns = [
    path("suggest/", suggest, name="suggest"),
]
