# Generated manually to accompany 0017_o365_room_and_split_data.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("room_schedules", "0017_o365_room_and_split_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="room",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="room",
            name="building",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                to="room_schedules.building",
            ),
        ),
        migrations.AlterField(
            model_name="room",
            name="o365_calendar_email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.RemoveField(
            model_name="room",
            name="o365_building_hint",
        ),
        migrations.RemoveField(
            model_name="room",
            name="missing_from_tenant",
        ),
        migrations.RemoveField(
            model_name="room",
            name="no_calendar_access",
        ),
    ]
