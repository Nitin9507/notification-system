import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Trigger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(help_text="Stable identifier used in code, e.g. 'user.login'.", max_length=64, unique=True)),
                ('name', models.CharField(max_length=128)),
                ('description', models.TextField(blank=True)),
                ('kind', models.CharField(choices=[('event', 'Event'), ('scheduled', 'Scheduled')], default='event', max_length=16)),
                ('inactivity_days', models.PositiveIntegerField(blank=True, help_text='Scheduled triggers only: fire for users inactive this many days.', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Master switch for the whole row.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='NotificationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('whatsapp', 'WhatsApp'), ('email', 'Email'), ('web_push', 'Web Push')], max_length=16)),
                ('subject', models.CharField(blank=True, help_text='Email subject / web push title. Unused for WhatsApp.', max_length=255)),
                ('body', models.TextField(help_text='Message body. Supports {{ placeholders }} from the variable map.')),
                ('wa_template_name', models.CharField(blank=True, help_text='Approved WhatsApp template used outside the 24h session window.', max_length=128)),
                ('wa_language_code', models.CharField(blank=True, default='en_US', max_length=16)),
                ('wa_body_params', models.JSONField(blank=True, default=list, help_text='Ordered {{1}}, {{2}}... values for the approved template. Each entry may itself contain {{ placeholders }}.')),
                ('variables', models.JSONField(blank=True, default=dict, help_text='Maps a placeholder to a dotted path in the trigger context, e.g. {"first_name": "user.first_name"}.')),
                ('is_enabled', models.BooleanField(default=True, help_text='The per-cell on/off toggle.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trigger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='templates', to='notifications.trigger')),
            ],
            options={
                'ordering': ['trigger_id', 'channel'],
            },
        ),
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trigger_code', models.CharField(blank=True, max_length=64)),
                ('channel', models.CharField(choices=[('whatsapp', 'WhatsApp'), ('email', 'Email'), ('web_push', 'Web Push')], max_length=16)),
                ('recipient', models.CharField(blank=True, max_length=255)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('body', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped'), ('dry_run', 'Dry run')], max_length=16)),
                ('provider', models.CharField(blank=True, max_length=32)),
                ('provider_message_id', models.CharField(blank=True, max_length=255)),
                ('error', models.TextField(blank=True)),
                ('provider_response', models.JSONField(blank=True, default=dict)),
                ('is_test', models.BooleanField(default=False, help_text="True for admin 'Test send', excluded from dedupe.")),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notification_logs', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='notifications.notificationtemplate')),
                ('trigger', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='notifications.trigger')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddConstraint(
            model_name='notificationtemplate',
            constraint=models.UniqueConstraint(fields=('trigger', 'channel'), name='unique_template_per_trigger_channel'),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(fields=['user', 'trigger', '-created_at'], name='notificatio_user_id_2f2e61_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(fields=['status', '-created_at'], name='notificatio_status_361e70_idx'),
        ),
    ]
