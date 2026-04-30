from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from room_schedules.models import Building, Room


class RoomGroup(models.Model):
    DISPLAY_GRID = 'grid'
    DISPLAY_FOYER = 'foyer'
    DISPLAY_CHOICES = [
        (DISPLAY_GRID, 'Grid'),
        (DISPLAY_FOYER, 'Foyer'),
    ]

    name = models.CharField(max_length=100)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='room_groups')
    rooms = models.ManyToManyField(Room, related_name='groups', blank=True)
    default_display = models.CharField(max_length=10, choices=DISPLAY_CHOICES, default=DISPLAY_GRID)
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

    class Meta:
        ordering = ['building', 'name']

    def __str__(self):
        return "{}: {} — {}".format(self.pk, self.building.name, self.name)

    def get_absolute_url(self):
        return reverse('room_schedule/room_group', args=[str(self.building_id), str(self.id)])

    def validate_room_buildings(self):
        """Raise ValidationError if any assigned room belongs to a different building."""
        if self.pk is None:
            return
        mismatched = self.rooms.exclude(building_id=self.building_id)
        if mismatched.exists():
            names = ", ".join(r.name for r in mismatched)
            raise ValidationError(
                "All rooms in a group must belong to the same building as the group ({}). "
                "Mismatched: {}".format(self.building.name, names)
            )
