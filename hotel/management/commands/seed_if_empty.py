from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from hotel.models import Room


FIXTURE_PATH = Path(__file__).resolve().parents[2] / 'fixtures' / 'hotel_seed.json'


class Command(BaseCommand):
    help = (
        'Завантажує початкові дані з hotel/fixtures/hotel_seed.json '
        'лише якщо база порожня (безпечний повторний запуск на Render).'
    )

    def handle(self, *args, **options):
        if Room.objects.exists():
            self.stdout.write('База вже містить номери — сід пропущено.')
            return
        if not FIXTURE_PATH.exists():
            self.stdout.write(self.style.WARNING(f'Фікстури немає: {FIXTURE_PATH}'))
            return
        call_command('loaddata', str(FIXTURE_PATH), verbosity=options['verbosity'])
        self.stdout.write(self.style.SUCCESS(
            f'Початкові дані завантажено з {FIXTURE_PATH.name}.'
        ))
