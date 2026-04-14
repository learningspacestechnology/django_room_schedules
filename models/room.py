from django.db import models
from django.urls import reverse

from room_schedules.models import Venue


class Room(models.Model):
    name = models.CharField(max_length=100)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    artifax_id = models.IntegerField(unique=True, null=True, blank=False)
    o365_calendar_email = models.EmailField(unique=True, null=True, blank=False)
    allow_tablet_booking = models.BooleanField(
        default=False,
        help_text="Allow adhoc bookings to be made from the tablet display screen.",
    )

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    def get_absolute_url(self):
        return reverse('event_schedule/room', args=[str(self.venue.id), str(self.id)])


