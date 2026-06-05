from django.db import models

from room_schedules.models import Room


class Event(models.Model):
    name = models.CharField(max_length=200)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    organiser = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    o365_event_id = models.CharField(max_length=500, unique=True, null=True, blank=False,
                                     help_text="Internal O365 sync key — do not edit.")
    cancelled = models.BooleanField(
        default=False,
        help_text="Whether the booking is cancelled. Maintained automatically by the O365 sync.")
    sensitivity = models.CharField(
        max_length=20,
        default="normal",
        help_text="O365 sensitivity (normal/personal/private/confidential). "
                  "Maintained automatically by the O365 sync.")

    PRIVATE_SENSITIVITIES = {"private", "confidential"}

    @property
    def is_private(self):
        return self.sensitivity in self.PRIVATE_SENSITIVITIES

    @property
    def display_title(self):
        """Public-facing title: organiser name for private bookings, else the subject."""
        if self.is_private:
            return self.organiser or "Private booking"
        return self.name

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    class Meta:
        ordering = ['start_time', 'end_time']


