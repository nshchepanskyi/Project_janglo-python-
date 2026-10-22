"""Прив'язка фотографій із media/rooms до конкретних номерів.

Фото лежать у MEDIA_ROOT/rooms (напр. unsplash_01.jpg … unsplash_65.jpg) —
команда проставляє їх у поле Room.photo «один до одного», щоб у каталозі
не було повторів: кожен файл використовується не більше одного разу.

Приклад:
    python manage.py assign_room_photos --dry-run
    python manage.py assign_room_photos

Файли не копіюються — у базі зберігається шлях «rooms/<файл>» відносно
MEDIA_ROOT, тож картинки лишаються на місці.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from hotel.models import Room

# Фото, які лежать у media/rooms, але не є фото номерів (напр. тестові GIF
# з E2E-тестів або згенеровані картки-плейсхолдери) — їх пропускаємо.
EXCLUDED_PATTERNS = (
    re.compile(r"^grandstay_e2e_room", re.IGNORECASE),
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# Підбір фото під тип номера: Single → спальні, Double → просторніші спальні
# та вітальні, Suite → апартаменти з вітальнею/кухнею/каміном. Ключ — номер
# кімнати, значення — файл із media/rooms. Кожен файл використовується рівно
# один раз.
ROOM_PHOTO_MAP = {
    # --- Single (101–122) ---
    "101": "unsplash_01.jpg",
    "102": "unsplash_30.jpg",
    "103": "unsplash_25.jpg",
    "104": "unsplash_46.jpg",
    "105": "unsplash_24.jpg",
    "106": "unsplash_45.jpg",
    "107": "unsplash_53.jpg",
    "108": "unsplash_22.jpg",
    "109": "unsplash_23.jpg",
    "110": "unsplash_50.jpg",
    "111": "unsplash_38.jpg",
    "112": "unsplash_29.jpg",
    "113": "unsplash_36.jpg",
    "114": "unsplash_31.jpg",
    "115": "unsplash_42.jpg",
    "116": "unsplash_52.jpg",
    "117": "unsplash_44.jpg",
    "118": "unsplash_62.jpg",
    "119": "unsplash_33.jpg",
    "120": "unsplash_37.jpg",
    "121": "unsplash_27.jpg",
    "122": "unsplash_39.jpg",
    # --- Double (201–226) ---
    "201": "unsplash_26.jpg",
    "202": "unsplash_34.jpg",
    "203": "unsplash_49.jpg",
    "204": "unsplash_51.jpg",
    "205": "unsplash_40.jpg",
    "206": "unsplash_43.jpg",
    "207": "unsplash_28.jpg",
    "208": "unsplash_06.jpg",
    "209": "unsplash_65.jpg",
    "210": "unsplash_32.jpg",
    "211": "unsplash_11.jpg",
    "212": "unsplash_57.jpg",
    "213": "unsplash_60.jpg",
    "214": "unsplash_03.jpg",
    "215": "unsplash_59.jpg",
    "216": "unsplash_05.jpg",
    "217": "unsplash_63.jpg",
    "218": "unsplash_13.jpg",
    "219": "unsplash_12.jpg",
    "220": "unsplash_47.jpg",
    "221": "unsplash_15.jpg",
    "222": "unsplash_10.jpg",
    "223": "unsplash_04.jpg",
    "224": "unsplash_61.jpg",
    "225": "unsplash_08.jpg",
    "226": "unsplash_21.jpg",
    # --- Suite (301–317) ---
    "301": "unsplash_41.jpg",
    "302": "unsplash_18.jpg",
    "303": "unsplash_17.jpg",
    "304": "unsplash_58.jpg",
    "305": "unsplash_48.jpg",
    "306": "unsplash_07.jpg",
    "307": "unsplash_64.jpg",
    "308": "unsplash_20.jpg",
    "309": "unsplash_02.jpg",
    "310": "unsplash_55.jpg",
    "311": "unsplash_14.jpg",
    "312": "unsplash_56.jpg",
    "313": "unsplash_54.jpg",
    "314": "unsplash_09.jpg",
    "315": "unsplash_19.jpg",
    "316": "unsplash_35.jpg",
    "317": "unsplash_16.jpg",
}


class Command(BaseCommand):
    help = "Роздає фото з media/rooms номерам (по одному фото на номер, без повторів)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pattern",
            default="unsplash_*.jpg",
            help="Маска фото у media/rooms (типово unsplash_*.jpg).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показати розподіл, не змінюючи базу.",
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Не змінювати номери, у яких уже є фото.",
        )
        parser.add_argument(
            "--sequential",
            action="store_true",
            help="Ігнорувати підбір за типом і роздавати фото по порядку.",
        )
        parser.add_argument(
            "--use-numbered",
            action="store_true",
            help=(
                "Віддавати перевагу файлам, названим за номером кімнати "
                "(101.jpg → номер 101), якщо такі є."
            ),
        )

    def handle(self, *args, **options):
        pattern = options["pattern"]
        dry_run = options["dry_run"]
        keep_existing = options["keep_existing"]
        sequential = options["sequential"]

        folder = Path(settings.MEDIA_ROOT) / "rooms"
        if not folder.is_dir():
            self.stderr.write(f"Folder not found: {folder}")
            return

        # Основний пул — фото за маскою; додатково шукаємо файли, названі
        # за номером кімнати (101.jpg), незалежно від маски.
        candidates = {
            path.name: path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in IMAGE_SUFFIXES
            and not any(rule.match(path.name) for rule in EXCLUDED_PATTERNS)
        }
        available = {
            name: path for name, path in candidates.items() if path.match(pattern)
        }
        if not available:
            self.stderr.write(f"No photos matching '{pattern}' in {folder}")
            return

        rooms = list(Room.objects.order_by("number"))
        if keep_existing:
            rooms = [room for room in rooms if not room.photo]

        assignments = self._build_assignments(
            rooms, available, sequential,
            use_numbered=options["use_numbered"], candidates=candidates,
        )

        for room, path in assignments:
            self.stdout.write(f"  #{room.number} <- rooms/{path.name}  ({room.display_title})")

        used = {path.name for _, path in assignments}
        unused = [name for name in sorted(available) if name not in used]
        if unused:
            self.stdout.write(
                self.style.WARNING(
                    "Unused (still in media/rooms): " + ", ".join(unused)
                )
            )
        if len(assignments) < len(rooms):
            self.stdout.write(
                self.style.WARNING(
                    f"Only {len(assignments)} photos for {len(rooms)} rooms — "
                    "some rooms will stay without a photo."
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — database unchanged."))
            return

        with transaction.atomic():
            # Спершу звільняємо фото в номерах, які перепризначаємо: інакше
            # під час «перестановки» (фото А стає фото Б) тимчасово виникне
            # дубль і спрацює UNIQUE-обмеження бази.
            for room, _ in assignments:
                if room.photo:
                    room.photo.name = ""
                    room.save(update_fields=["photo"])
            for room, path in assignments:
                room.photo.name = f"rooms/{path.name}"
                room.save(update_fields=["photo"])

        self.stdout.write(self.style.SUCCESS(f"Updated {len(assignments)} rooms."))

    def _build_assignments(self, rooms, available, sequential, use_numbered=False,
                           candidates=None):
        """Повертає список пар (номер, файл) без повторів файлів."""
        assignments = []
        used = set()
        assigned_rooms = set()
        candidates = candidates or available

        # 1) Файл, названий за номером кімнати (101.jpg → №101) — найточніший збіг.
        if use_numbered:
            for room in rooms:
                match = next(
                    (name for name in sorted(candidates)
                     if name not in used and Path(name).stem == room.number),
                    None,
                )
                if match:
                    assignments.append((room, candidates[match]))
                    used.add(match)
                    assigned_rooms.add(room.pk)

        # 2) Явний підбір за типом номера (спальня / вітальня / апартамент).
        if not sequential:
            for room in rooms:
                if room.pk in assigned_rooms:
                    continue
                name = ROOM_PHOTO_MAP.get(room.number)
                if name and name in available and name not in used:
                    assignments.append((room, available[name]))
                    used.add(name)
                    assigned_rooms.add(room.pk)

        # 3) Решта номерів отримує будь-які вільні фото по порядку.
        rest = [name for name in sorted(available) if name not in used]
        pending = [room for room in rooms if room.pk not in assigned_rooms]
        for room, name in zip(pending, rest):
            assignments.append((room, available[name]))

        assignments.sort(key=lambda pair: pair[0].number)
        return assignments
