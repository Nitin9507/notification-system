"""
Seed the four triggers from the brief, each with all three channels filled in.

Idempotent: re-running updates the trigger definitions but leaves any message
text the admin has since edited alone, unless --reset is passed.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from notifications.models import Channel, NotificationTemplate, Trigger, TriggerKind

SEED = [
    {
        "code": "user.login",
        "name": "Login",
        "description": "User signs in on the website.",
        "kind": TriggerKind.EVENT,
        "templates": {
            Channel.WHATSAPP: {
                "body": "Welcome back, {{ first_name|default:'there' }}! You just signed in.",
                "wa_template_name": "hello_world",
                "wa_language_code": "en_US",
                "wa_body_params": [],
                "variables": {"first_name": "user.first_name"},
            },
            Channel.EMAIL: {
                "subject": "You logged in successfully",
                "body": (
                    "Hi {{ first_name|default:'there' }},\n\n"
                    "You signed in to {{ site_name }} just now.\n"
                    "If this wasn't you, reset your password immediately.\n"
                ),
                "variables": {"first_name": "user.first_name"},
            },
            Channel.WEB_PUSH: {
                "subject": "Welcome back!",
                "body": "Good to see you again, {{ first_name|default:'there' }}.",
                "variables": {"first_name": "user.first_name"},
            },
        },
    },
    {
        "code": "user.logout",
        "name": "Logout",
        "description": "User signs out.",
        "kind": TriggerKind.EVENT,
        "templates": {
            Channel.WHATSAPP: {
                "body": "You have been signed out of {{ site_name }}. See you soon!",
                "wa_template_name": "hello_world",
                "wa_language_code": "en_US",
                "wa_body_params": [],
                "variables": {},
            },
            Channel.EMAIL: {
                "subject": "You signed out",
                "body": (
                    "Hi {{ first_name|default:'there' }},\n\n"
                    "Your session on {{ site_name }} has ended.\n"
                ),
                "variables": {"first_name": "user.first_name"},
            },
            Channel.WEB_PUSH: {
                "subject": "Signed out",
                "body": "You've been signed out. Come back soon!",
                "variables": {},
            },
        },
    },
    {
        "code": "user.inactive_1d",
        "name": "Not logged in 1 day",
        "description": "User has not visited the website for 24 hours.",
        "kind": TriggerKind.SCHEDULED,
        "inactivity_days": 1,
        "templates": {
            Channel.WHATSAPP: {
                "body": "We miss you, {{ first_name|default:'there' }}! It's been a day.",
                "wa_template_name": "hello_world",
                "wa_language_code": "en_US",
                "wa_body_params": [],
                "variables": {"first_name": "user.first_name"},
            },
            Channel.EMAIL: {
                "subject": "We haven't seen you today",
                "body": "Hi {{ first_name|default:'there' }},\n\nIt's been a day since your last visit.\n",
                "variables": {"first_name": "user.first_name"},
            },
            Channel.WEB_PUSH: {
                "subject": "Still there?",
                "body": "It's been a day — come take a look.",
                "variables": {},
            },
        },
    },
    {
        "code": "user.inactive_1w",
        "name": "Not logged in 1 week",
        "description": "User has not visited the website for 7 days.",
        "kind": TriggerKind.SCHEDULED,
        "inactivity_days": 7,
        "templates": {
            Channel.WHATSAPP: {
                "body": "We miss you, come back! It's been a week.",
                "wa_template_name": "hello_world",
                "wa_language_code": "en_US",
                "wa_body_params": [],
                "variables": {},
            },
            Channel.EMAIL: {
                "subject": "It's been a week...",
                "body": "Hi {{ first_name|default:'there' }},\n\nIt's been a week. Here's what you missed.\n",
                "variables": {"first_name": "user.first_name"},
            },
            Channel.WEB_PUSH: {
                "subject": "Come visit us again",
                "body": "It's been a week since your last visit.",
                "variables": {},
            },
        },
    },
]


class Command(BaseCommand):
    help = "Create the default triggers and their templates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Overwrite existing template text with the seed defaults.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options["reset"]
        for spec in SEED:
            trigger, created = Trigger.objects.update_or_create(
                code=spec["code"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "kind": spec["kind"],
                    "inactivity_days": spec.get("inactivity_days"),
                },
            )
            self.stdout.write(
                f"{'created' if created else 'updated'} trigger {trigger.code}"
            )

            for channel, values in spec["templates"].items():
                existing = NotificationTemplate.objects.filter(
                    trigger=trigger, channel=channel
                ).first()
                if existing and not reset:
                    continue
                NotificationTemplate.objects.update_or_create(
                    trigger=trigger, channel=channel, defaults=values
                )
                self.stdout.write(f"  {channel} template ready")

        self.stdout.write(self.style.SUCCESS("seed complete"))
