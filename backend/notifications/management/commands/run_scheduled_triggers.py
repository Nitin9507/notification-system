"""Evaluate the condition triggers. Run from cron, or by hand during a demo."""

import json

from django.core.management.base import BaseCommand

from notifications.services.scheduled import run_scheduled_triggers


class Command(BaseCommand):
    help = "Fire scheduled triggers (not logged in for N days) for matching users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report who would be notified without sending anything.",
        )

    def handle(self, *args, **options):
        summary = run_scheduled_triggers(dry_run=options["dry_run"])
        self.stdout.write(json.dumps(summary, indent=2))
        self.stdout.write(self.style.SUCCESS("done"))
