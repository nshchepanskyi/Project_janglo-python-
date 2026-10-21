from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hotel", "0007_profile"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["status", "check_in", "check_out", "room"],
                name="res_status_dates_room_idx",
            ),
        ),
    ]
