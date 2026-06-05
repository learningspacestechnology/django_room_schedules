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

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    class Meta:
        ordering = ['start_time', 'end_time']


