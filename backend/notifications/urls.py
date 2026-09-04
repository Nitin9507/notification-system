from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/triggers", views.TriggerViewSet, basename="trigger")

cell = "admin/triggers/<int:trigger_id>/templates/<str:channel>/"

urlpatterns = [
    path("admin/matrix/", views.MatrixView.as_view(), name="matrix"),
    path("admin/logs/", views.NotificationLogListView.as_view(), name="logs"),
    path(cell, views.TemplateCellView.as_view(), name="template-cell"),
    path(cell + "toggle/", views.TemplateToggleView.as_view(), name="template-toggle"),
    path(
        cell + "test-send/",
        views.TemplateTestSendView.as_view(),
        name="template-test-send",
    ),
    path("events/", views.EventTriggerListView.as_view(), name="event-list"),
    path("events/<str:code>/fire/", views.FireEventView.as_view(), name="fire-event"),
    path(
        "internal/run-scheduled-triggers/",
        views.RunScheduledTriggersView.as_view(),
        name="run-scheduled-triggers",
    ),
    path(
        "webhooks/whatsapp/",
        views.WhatsAppWebhookView.as_view(),
        name="whatsapp-webhook",
    ),
    path("", include(router.urls)),
]
