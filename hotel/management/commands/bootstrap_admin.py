import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Створює початкового суперкористувача зі змінних '
        'DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD, якщо його ще немає.'
    )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        if not any((username, email, password)):
            self.stdout.write('Змінні DJANGO_SUPERUSER_* не задані — пропущено.')
            return
        if not all((username, email, password)):
            raise ValueError(
                'Для створення початкового адміністратора задайте всі три '
                'змінні: DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, '
                'DJANGO_SUPERUSER_PASSWORD.'
            )

        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            self.stdout.write('Початковий адміністратор уже існує — без змін.')
            return

        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS('Початкового адміністратора створено.'))
