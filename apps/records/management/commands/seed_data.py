# apps/records/management/commands/seed_data.py
import json
from django.core.management.base import BaseCommand
from apps.records.models import FinancialRecord
from apps.users.models import User

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        admin = User.objects.filter(role='ADMIN').first()
        with open('seed_data.json') as f:
            records = json.load(f)
        for r in records:
            FinancialRecord.objects.create(**r, created_by=admin)
        self.stdout.write(f"Seeded {len(records)} records.")