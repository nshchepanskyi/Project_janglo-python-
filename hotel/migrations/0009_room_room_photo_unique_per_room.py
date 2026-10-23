

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0008_reservation_active_dates_index'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='room',
            constraint=models.UniqueConstraint(condition=models.Q(('photo', ''), _negated=True), fields=('photo',), name='room_photo_unique_per_room'),
        ),
    ]
