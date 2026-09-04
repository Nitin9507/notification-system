import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_e164', models.CharField(blank=True, help_text="WhatsApp destination in E.164 without '+', e.g. 918559050811.", max_length=20)),
                ('onesignal_player_id', models.CharField(blank=True, help_text='Web push subscription id returned by the OneSignal browser SDK.', max_length=64)),
                ('last_whatsapp_inbound_at', models.DateTimeField(blank=True, help_text='When the user last messaged our WhatsApp number. Free-form text is only permitted for 24h after this.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
