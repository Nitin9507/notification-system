from django.contrib import admin

from .models import NotificationLog, NotificationTemplate, Trigger


class TemplateInline(admin.TabularInline):
    model = NotificationTemplate
    extra = 0
    fields = ("channel", "subject", "body", "is_enabled")


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "inactivity_days", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name")
    inlines = [TemplateInline]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("trigger", "channel", "subject", "is_enabled", "updated_at")
    list_filter = ("channel", "is_enabled")
    search_fields = ("trigger__code", "subject", "body")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "trigger_code",
        "channel",
        "recipient",
        "status",
        "is_test",
    )
    list_filter = ("status", "channel", "is_test")
    search_fields = ("trigger_code", "recipient", "error")
    readonly_fields = [f.name for f in NotificationLog._meta.fields]
