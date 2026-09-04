from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_e164",
        "onesignal_player_id",
        "last_whatsapp_inbound_at",
    )
    search_fields = ("user__username", "user__email", "phone_e164")
