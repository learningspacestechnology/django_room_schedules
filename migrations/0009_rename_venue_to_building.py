from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("room_schedules", "0008_rename_allow_tablet_booking_to_allow_booking"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Venue",
            new_name="Building",
        ),
        migrations.RenameField(
            model_name="room",
            old_name="venue",
            new_name="building",
        ),
    ]
