from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("room_schedules", "0009_rename_venue_to_building"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="building",
            name="artifax_id",
        ),
        migrations.RemoveField(
            model_name="room",
            name="artifax_id",
        ),
        migrations.RemoveField(
            model_name="event",
            name="artifax_id",
        ),
    ]
