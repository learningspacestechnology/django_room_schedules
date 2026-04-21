from django.db import models
from django.urls import reverse

from room_schedules.models import Building


class Room(models.Model):
    name = models.CharField(
        max_length=200,
        help_text="Canonical O365 displayName. Auto-refreshed by the daily sync for O365-backed rooms.",
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Operator-facing label. Leave blank to follow the O365 name.",
    )
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    o365_calendar_email = models.EmailField(unique=True, null=True, blank=True)
    allow_booking = models.BooleanField(
        default=False,
        help_text="Allow adhoc bookings to be made from the display screen.",
    )
    pagination_duration_seconds = models.PositiveIntegerField(
        default=15,
        verbose_name="Pagination duration (seconds)",
        help_text=(
            "How long each page of long content is held before scrolling to the next. "
            "Applies regardless of whether the screensaver is enabled."
        ),
    )
    screensaver_enabled = models.BooleanField(
        default=False,
        verbose_name="Enable screensaver",
        help_text="Show the screensaver image periodically when this screen is displayed.",
    )
    content_duration_seconds = models.PositiveIntegerField(
        default=600,
        verbose_name="Content duration (seconds)",
        help_text=(
            "How long content is shown between screensaver appearances. "
            "Only applies when the screensaver is enabled."
        ),
    )
    screensaver_duration_seconds = models.PositiveIntegerField(
        default=5,
        verbose_name="Screensaver duration (seconds)",
        help_text=(
            "How long the screensaver image is shown before returning to content. "
            "Only applies when the screensaver is enabled."
        ),
    )

    @property
    def label(self):
        """Public-facing name: operator override if set, else the O365 name."""
        return self.display_name or self.name

    def __str__(self):
        return "{}: {}".format(self.pk, self.label)

    def get_absolute_url(self):
        return reverse('room_schedule/room', args=[str(self.building_id), str(self.id)])

    def move_to_building(self, new_building):
        """Move this room to new_building; drop memberships in any RoomGroup
        that belongs to a different building (RoomGroup requires all members
        to share its building)."""
        for group in list(self.groups.exclude(building_id=new_building.pk)):
            group.rooms.remove(self)
        self.building = new_building
        self.save(update_fields=['building'])
