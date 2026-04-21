import asyncio

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

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

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
