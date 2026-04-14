from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("room_schedules", "0007_room_allow_tablet_booking"),
    ]

    operations = [
        migrations.RenameField(
            model_name="room",
            old_name="allow_tablet_booking",
            new_name="allow_booking",
        ),
    ]
