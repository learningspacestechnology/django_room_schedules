from django.db import models
from django.urls import reverse

from room_schedules.models import Building


class Room(models.Model):
    name = models.CharField(max_length=100)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    o365_calendar_email = models.EmailField(unique=True, null=True, blank=True)
    allow_booking = models.BooleanField(
        default=False,
        help_text="Allow adhoc bookings to be made from the display screen.",
    )

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    def get_absolute_url(self):
        return reverse('event_schedule/room', args=[str(self.building.id), str(self.id)])


