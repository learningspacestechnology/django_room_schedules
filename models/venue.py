import asyncio

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Building(models.Model):
    DISPLAY_GRID = 'grid'
    DISPLAY_FOYER = 'foyer'
    DISPLAY_CHOICES = [
        (DISPLAY_GRID, 'Grid'),
        (DISPLAY_FOYER, 'Foyer'),
    ]

    name = models.CharField(max_length=100)
    default_display = models.CharField(
        max_length=10, choices=DISPLAY_CHOICES, default=DISPLAY_GRID,
        help_text="Default view for screens showing this building: Grid (hour-by-hour timetable) or Foyer (summary list).",
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
            "On single-page screens (and any building view whose bookings fit on one page), "
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

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    def clean(self):
        super().clean()
        if self.grid_end_hour <= self.grid_start_hour:
            raise ValidationError({
                'grid_end_hour': "Grid end hour must be greater than the start hour.",
            })

    def get_absolute_url(self):
        return reverse('room_schedule/building', args=[str(self.id)])

    def update_events(self):
        from room_schedules.models import Room, Event
        from room_schedules import o365_requests

        for room in self.room_set.filter(o365_calendar_email__isnull=False):
            events = asyncio.run(o365_requests.get_todays_events(room.o365_calendar_email))
            o365_ids = []
            new_events = 0
            for e in events:
                ev, created = Event.objects.update_or_create(
                    o365_event_id=e['id'],
                    defaults={
                        'name': e['name'][:200],
                        'organiser': e['organiser'][:200],
                        'room': room,
                        'start_time': e['start_time'],
                        'end_time': e['end_time'],
                        'cancelled': e['cancelled'],
                        'sensitivity': e.get('sensitivity', 'normal'),
                    },
                )
                o365_ids.append(ev.id)
                if created:
                    new_events += 1
            Event.objects.filter(room=room, o365_event_id__isnull=False).exclude(
                pk__in=o365_ids
            ).delete()
            print("{}/{} (O365) created {} events and updated {}".format(
                self.name, room.name, new_events, len(o365_ids) - new_events
            ))
