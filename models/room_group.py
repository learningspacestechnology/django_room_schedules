from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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
    default_display = models.CharField(
        max_length=10, choices=DISPLAY_CHOICES, default=DISPLAY_GRID,
        help_text="Default view for screens showing this group: Grid (hour-by-hour timetable) or Foyer (summary list).",
    )
    grid_start_hour = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        verbose_name="Grid start hour",
        help_text=(
            "First hour shown on the grid's time bar (0–23, 24-hour clock). "
            "Narrower ranges give each event more horizontal space; EdGEL's reference "
            "uses 8–18 (a 10-hour day). Events outside this window are clipped."
        ),
    )
    grid_end_hour = models.PositiveSmallIntegerField(
        default=18,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        verbose_name="Grid end hour",
        help_text="Last hour shown on the grid's time bar (1–24). Must be greater than the start hour.",
    )
    pagination_duration_seconds = models.PositiveIntegerField(
        default=20,
        verbose_name="Pagination duration (seconds)",
        help_text=(
            "How long each page is held before scrolling to the next. "
            "On single-page screens (and any group view whose bookings fit on one page), "
            "this also controls how often the screensaver appears: content shows for this duration, "
            "screensaver shows for the screensaver duration, then the cycle repeats."
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
            "Deprecated: no longer used. The HTML re-fetch interval is hardcoded to 300s, "
            "and booking changes are picked up within ~10s via state-hash polling."
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

    def clean(self):
        super().clean()
        if self.grid_end_hour <= self.grid_start_hour:
            raise ValidationError({
                'grid_end_hour': "Grid end hour must be greater than the start hour.",
            })

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
