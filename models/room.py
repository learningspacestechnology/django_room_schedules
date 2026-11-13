from django.db import models
from django.urls import reverse

from room_schedules.models import Building


class Room(models.Model):
    DISPLAY_STANDARD = 'standard'
    DISPLAY_SCREEN = 'screen'
    DISPLAY_TABLET = 'tablet'
    DISPLAY_CHOICES = [
        (DISPLAY_STANDARD, 'Standard'),
        (DISPLAY_SCREEN, 'Screen'),
        (DISPLAY_TABLET, 'Tablet'),
    ]
    # URL name each layout is served at. An unrecognised value falls back to
    # Standard rather than failing, so a display never breaks on bad data.
    DISPLAY_URL_NAMES = {
        DISPLAY_STANDARD: 'room_schedule/room',
        DISPLAY_SCREEN: 'room_schedule/room_screen',
        DISPLAY_TABLET: 'room_schedule/room_tablet',
    }

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
    o365_calendar_email = models.EmailField(
        unique=True, null=True, blank=True,
        help_text="The room's O365 mailbox address. Set this to pull bookings from Outlook/O365; "
                  "leave blank for a manually-managed room.",
    )
    allow_booking = models.BooleanField(
        default=False,
        help_text="Allow adhoc bookings to be made from the display screen.",
    )
    default_display = models.CharField(
        max_length=10, choices=DISPLAY_CHOICES, default=DISPLAY_STANDARD,
        help_text=(
            "Layout a device registered to this room is sent to: Standard (list of bookings), "
            "Screen (large status banner with countdown, fills a widescreen display) or "
            "Tablet (the same banner laid out for a 1280×800 tablet). "
            "Pagination and screensaver settings apply to Standard only."
        ),
    )
    pagination_duration_seconds = models.PositiveIntegerField(
        default=60,
        verbose_name="Pagination duration (seconds)",
        help_text=(
            "How long each page is held before scrolling to the next. "
            "Room screens are almost always single-page, so in practice this also controls "
            "how often the screensaver appears: content shows for this duration, "
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

    @property
    def label(self):
        """Public-facing name: operator override if set, else the O365 name."""
        return self.display_name or self.name

    def __str__(self):
        return "{}: {}".format(self.pk, self.label)

    def get_absolute_url(self):
        """URL of the room's chosen layout — what a device registered to it shows."""
        return self.display_url(self.default_display)

    def display_url(self, display):
        url_name = self.DISPLAY_URL_NAMES.get(display, self.DISPLAY_URL_NAMES[self.DISPLAY_STANDARD])
        return reverse(url_name, args=[str(self.building_id), str(self.id)])

    def move_to_building(self, new_building):
        """Move this room to new_building; drop memberships in any RoomGroup
        that belongs to a different building (RoomGroup requires all members
        to share its building)."""
        for group in list(self.groups.exclude(building_id=new_building.pk)):
            group.rooms.remove(self)
        self.building = new_building
        self.save(update_fields=['building'])
