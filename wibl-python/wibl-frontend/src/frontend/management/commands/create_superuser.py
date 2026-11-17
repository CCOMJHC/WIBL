import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Create superuser from environment variables"

    def handle(self, *args, **options):
        username = os.getenv("SUPERUSER_USERNAME")
        password = os.getenv("SUPERUSER_PASSWORD")

        User.objects.create_superuser(
            username=username,
            password=password,
        )

        self.stdout.write("Admin user created")
